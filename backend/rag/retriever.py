from __future__ import annotations

import json
import threading
from collections import defaultdict

import faiss
import numpy as np

from agents.text import _stem, normalize
from config import settings
from rag.embeddings import get_embedder
from rag.schemas import Chunk, RetrievedChunk

CANDIDATES_PER_QUERY = 60
KEYWORD_PER_COLLECTION = 25


class Retriever:
    def __init__(self) -> None:
        index_path = settings.index_dir / "faiss.index"
        chunks_path = settings.index_dir / "chunks.json"
        if not index_path.exists() or not chunks_path.exists():
            from rag.ingest import ingest

            ingest()
        self.index = faiss.read_index(str(index_path))
        self.matrix = self.index.reconstruct_n(0, self.index.ntotal)
        data = json.loads(chunks_path.read_text(encoding="utf-8"))
        self.chunks = [Chunk.model_validate(c) for c in data["chunks"]]
        self.embedder = get_embedder()
        self.postings: dict[str, list[int]] = defaultdict(list)
        for i, c in enumerate(self.chunks):
            for stem in {_stem(w) for w in normalize(f"{c.text} {c.text_ar}").split()}:
                self.postings[stem].append(i)

    @property
    def topics(self) -> list[str]:
        return sorted({c.metadata.topic for c in self.chunks})

    def keyword_hits(self, terms: list[str]) -> set[int]:
        hits: set[int] = set()
        for term in terms:
            stems = [_stem(w) for w in normalize(term).split()]
            if not stems:
                continue
            found = set(self.postings.get(stems[0], []))
            for s in stems[1:]:
                found &= set(self.postings.get(s, []))
            hits |= found
        return hits

    def search(
        self,
        queries: list[str],
        limit: int | None = None,
        topics: list[str] | None = None,
        review_statuses: set[str] | None = None,
        terms: list[str] | None = None,
        per_query: int = CANDIDATES_PER_QUERY,
    ) -> list[RetrievedChunk]:
        review_statuses = review_statuses or settings.allowed_review_statuses
        topic_set = {t.lower() for t in topics} if topics else None
        queries = [q for q in queries if q and q.strip()]
        if not queries:
            return []

        vectors = self.embedder.embed(queries)
        candidates: set[int] = set()
        _, ids = self.index.search(vectors, min(per_query, len(self.chunks)))
        candidates |= {int(i) for row in ids for i in row if i >= 0}
        if terms:
            by_topic: dict[str, list[int]] = defaultdict(list)
            for i in self.keyword_hits(terms):
                by_topic[self.chunks[i].metadata.topic].append(i)
            for hits_list in by_topic.values():
                hits = np.array(hits_list, dtype=np.int64)
                hit_scores = (self.matrix[hits] @ vectors.T).max(axis=1)
                order = np.argsort(-hit_scores)[:KEYWORD_PER_COLLECTION]
                candidates |= {int(hits[j]) for j in order}

        ordered = np.fromiter(candidates, dtype=np.int64)
        scores = (self.matrix[ordered] @ vectors.T).max(axis=1)
        ranked = []
        for idx, score in sorted(zip(ordered.tolist(), scores.tolist()), key=lambda kv: kv[1], reverse=True):
            chunk = self.chunks[idx]
            if chunk.metadata.review_status not in review_statuses:
                continue
            if topic_set and chunk.metadata.topic not in topic_set:
                continue
            ranked.append((idx, score))
        return [
            RetrievedChunk(**self.chunks[idx].model_dump(), relevance_score=round(float(np.clip(s, -1, 1)), 4))
            for idx, s in ranked[:limit]
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
