from __future__ import annotations

import json
import threading

import faiss
import numpy as np

from config import settings
from rag.embeddings import get_embedder
from rag.schemas import Chunk, RetrievedChunk, SourceFile


class Retriever:
    def __init__(self) -> None:
        index_path = settings.index_dir / "faiss.index"
        chunks_path = settings.index_dir / "chunks.json"
        if not index_path.exists() or not chunks_path.exists():
            from rag.ingest import ingest

            ingest()
        self.index = faiss.read_index(str(index_path))
        data = json.loads(chunks_path.read_text(encoding="utf-8"))
        self.chunks = [Chunk.model_validate(c) for c in data["chunks"]]
        self.embedder = get_embedder()
        self.descriptions = {}
        for path in settings.sources_dir.glob("*.json"):
            sf = SourceFile.model_validate_json(path.read_text(encoding="utf-8"))
            self.descriptions[sf.topic] = sf.description

    @property
    def topics(self) -> list[str]:
        return sorted({c.metadata.topic for c in self.chunks})

    def search(
        self,
        queries: list[str],
        limit: int | None = None,
        topics: list[str] | None = None,
        review_statuses: set[str] | None = None,
    ) -> list[RetrievedChunk]:
        review_statuses = review_statuses or settings.allowed_review_statuses
        topic_set = {t.lower() for t in topics} if topics else None
        queries = [q for q in queries if q and q.strip()]
        if not queries:
            return []

        vectors = self.embedder.embed(queries)
        scores, ids = self.index.search(vectors, len(self.chunks))
        best: dict[int, float] = {}
        for row_scores, row_ids in zip(scores, ids):
            for score, idx in zip(row_scores, row_ids):
                if idx < 0:
                    continue
                chunk = self.chunks[idx]
                if chunk.metadata.review_status not in review_statuses:
                    continue
                if topic_set and chunk.metadata.topic not in topic_set:
                    continue
                best[idx] = max(best.get(idx, -1.0), float(score))

        ranked = sorted(best.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        return [
            RetrievedChunk(**self.chunks[idx].model_dump(), relevance_score=round(float(np.clip(s, -1, 1)), 4))
            for idx, s in ranked
        ]


_retriever: Retriever | None = None
_lock = threading.Lock()


def get_retriever() -> Retriever:
    global _retriever
    with _lock:
        if _retriever is None:
            _retriever = Retriever()
    return _retriever


def reset_retriever() -> None:
    global _retriever
    _retriever = None
