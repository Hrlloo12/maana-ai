from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import faiss

from config import settings
from rag.embeddings import get_embedder
from rag.schemas import Chunk, ChunkMetadata, SourceFile

logger = logging.getLogger("maana.ingest")

MAX_CHUNK_CHARS = 900


def split_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    if len(text) <= max_chars:
        return [text.strip()]
    sentences = re.split(r"(?<=[.!?؟])\s+", text)
    chunks, current = [], ""
    for sentence in sentences:
        if current and len(current) + len(sentence) + 1 > max_chars:
            chunks.append(current.strip())
            current = ""
        current += sentence + " "
    if current.strip():
        chunks.append(current.strip())
    return chunks


def load_chunks(sources_dir: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(sources_dir.glob("*.json")):
        source_file = SourceFile.model_validate_json(path.read_text(encoding="utf-8"))
        for doc in source_file.documents:
            for i, piece in enumerate(split_text(doc.text)):
                chunks.append(
                    Chunk(
                        chunk_id=f"{doc.id}#{i}",
                        doc_id=doc.id,
                        text=piece,
                        metadata=ChunkMetadata(
                            source_name=doc.source_name,
                            source_name_ar=doc.source_name_ar,
                            topic=source_file.topic,
                            reference=doc.reference,
                            reference_ar=doc.reference_ar,
                            language=doc.language,
                            review_status=doc.review_status,
                        ),
                    )
                )
    return chunks


def ingest(sources_dir: Path | None = None, index_dir: Path | None = None) -> dict:
    sources_dir = sources_dir or settings.sources_dir
    index_dir = index_dir or settings.index_dir
    chunks = load_chunks(sources_dir)
    if not chunks:
        raise RuntimeError(f"No source documents found in {sources_dir}")

    embedder = get_embedder()
    vectors = embedder.embed([c.text for c in chunks])
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    index_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_dir / "faiss.index"))
    (index_dir / "chunks.json").write_text(
        json.dumps(
            {"embedder": embedder.name, "chunks": [c.model_dump() for c in chunks]},
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    topics = sorted({c.metadata.topic for c in chunks})
    summary = {"chunks": len(chunks), "topics": topics, "embedder": embedder.name, "dim": int(vectors.shape[1])}
    logger.info("Ingested %s", summary)
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(ingest(), indent=2))
