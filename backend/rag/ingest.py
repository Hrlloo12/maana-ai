from __future__ import annotations

import json
import logging
import re
import urllib.request
from pathlib import Path

import faiss
import numpy as np

from agents.text import normalize
from config import settings
from rag.embeddings import get_embedder
from rag.schemas import Chunk, ChunkMetadata, Collection

logger = logging.getLogger("maana.ingest")

MAX_CHUNK_CHARS = 1800
BATCH = 256


def load_collections() -> list[Collection]:
    data = json.loads(settings.corpus_file.read_text(encoding="utf-8"))
    return [Collection.model_validate(c) for c in data["collections"]]


def fetch(url: str, path: Path) -> Path:
    if path.exists() and path.stat().st_size > 0:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading %s", url)
    request = urllib.request.Request(url, headers={"User-Agent": "maana-ingest"})
    with urllib.request.urlopen(request, timeout=300) as response:
        path.write_bytes(response.read())
    return path


def split_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]
    sentences = re.split(r"(?<=[.!?؟])\s+", text)
    parts, current = [], ""
    for sentence in sentences:
        if current and len(current) + len(sentence) + 1 > max_chars:
            parts.append(current.strip())
            current = ""
        current += sentence + " "
    if current.strip():
        parts.append(current.strip())
    return parts


def surah_table(metadata_path: Path) -> list[tuple[int, str, str]]:
    text = metadata_path.read_text(encoding="utf-8")
    block = text[text.index("Sura"):text.index("];", text.index("Sura"))]
    rows = re.findall(
        r"\[(\d+),\s*(\d+),\s*\d+,\s*\d+,\s*'([^']*)',\s*\"([^\"]*)\",\s*'[^']*',\s*'[^']*'\]", block
    )
    table = [(int(count), name_ar, name_en) for _, count, name_ar, name_en in rows]
    if len(table) != 114 or sum(c for c, _, _ in table) != 6236:
        raise RuntimeError("Unexpected Tanzil metadata: expected 114 surahs and 6236 ayahs")
    return table


def quran_chunks(c: Collection, raw: Path) -> tuple[list[Chunk], list[str]]:
    lines = [ln.rstrip("\n") for ln in fetch(c.url, raw / c.file).read_text(encoding="utf-8").splitlines()]
    ayahs = [ln for ln in lines if ln.strip() and not ln.startswith("#")]
    table = surah_table(fetch(c.metadata_url, raw / c.metadata_file))
    if len(ayahs) != 6236:
        raise RuntimeError(f"Expected 6236 ayahs in {c.file}, found {len(ayahs)}")
    chunks, embed_texts, i = [], [], 0
    for surah, (count, name_ar, name_en) in enumerate(table, start=1):
        for ayah in range(1, count + 1):
            text = ayahs[i]
            i += 1
            chunks.append(Chunk(
                chunk_id=f"quran:{surah}:{ayah}",
                doc_id=f"quran:{surah}:{ayah}",
                text=text,
                text_ar=text,
                metadata=ChunkMetadata(
                    source_name=c.name, source_name_ar=c.name_ar, topic=c.id,
                    reference=f"Qur'an {surah}:{ayah} ({name_en})",
                    reference_ar=f"سورة {name_ar}: {ayah}",
                    chapter=name_en, chapter_ar=f"سورة {name_ar}", language="ar",
                ),
            ))
            embed_texts.append(f"سورة {name_ar}: {normalize(text)}")
    return chunks, embed_texts


def hadith_chunks(c: Collection, raw: Path) -> tuple[list[Chunk], list[str]]:
    data = json.loads(fetch(c.url, raw / c.file).read_text(encoding="utf-8"))
    chapters = {ch["id"]: ch for ch in data["chapters"]}
    chunks, embed_texts = [], []
    for h in data["hadiths"]:
        english = h.get("english") or {}
        narrator = (english.get("narrator") or "").strip()
        body = re.sub(r"\s+", " ", english.get("text") or "").strip()
        arabic = (h.get("arabic") or "").strip()
        if not body and not arabic:
            continue
        chapter = chapters.get(h.get("chapterId"), {})
        chapter_en, chapter_ar = chapter.get("english", ""), chapter.get("arabic", "")
        number = h["id"]
        parts = split_text(f"{narrator} {body}".strip()) if body else [arabic[:MAX_CHUNK_CHARS]]
        for k, part in enumerate(parts):
            suffix = f" (part {k + 1}/{len(parts)})" if len(parts) > 1 else ""
            suffix_ar = f" (الجزء {k + 1} من {len(parts)})" if len(parts) > 1 else ""
            chunks.append(Chunk(
                chunk_id=f"{c.id}:{number}#{k}",
                doc_id=f"{c.id}:{number}",
                text=part,
                text_ar=arabic,
                metadata=ChunkMetadata(
                    source_name=c.name, source_name_ar=c.name_ar, topic=c.id,
                    reference=f"{c.name}, {chapter_en}, no. {number} in the source edition{suffix}",
                    reference_ar=f"{c.name_ar}، {chapter_ar}، الحديث رقم {number} في نسخة المصدر{suffix_ar}",
                    chapter=chapter_en, chapter_ar=chapter_ar, language="en" if body else "ar",
                ),
            ))
            embed_texts.append(f"{chapter_en}: {part}")
    return chunks, embed_texts


def load_chunks(raw_dir: Path | None = None) -> tuple[list[Chunk], list[str]]:
    raw = raw_dir or settings.raw_dir
    chunks: list[Chunk] = []
    texts: list[str] = []
    for c in load_collections():
        built = quran_chunks(c, raw) if c.kind == "quran" else hadith_chunks(c, raw)
        logger.info("%s: %s chunks", c.id, len(built[0]))
        chunks += built[0]
        texts += built[1]
    return chunks, texts


def ingest(index_dir: Path | None = None) -> dict:
    index_dir = index_dir or settings.index_dir
    chunks, texts = load_chunks()
    if not chunks:
        raise RuntimeError("No source texts were loaded")
    embedder = get_embedder()
    vectors = []
    for start in range(0, len(texts), BATCH):
        vectors.append(embedder.embed(texts[start:start + BATCH]))
        if start // BATCH % 10 == 0:
            logger.info("Embedded %s / %s", min(start + BATCH, len(texts)), len(texts))
    matrix = np.vstack(vectors).astype("float32")
    index = faiss.IndexFlatIP(matrix.shape[1])
    index.add(matrix)

    index_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_dir / "faiss.index"))
    (index_dir / "chunks.json").write_text(
        json.dumps({"embedder": embedder.name, "chunks": [c.model_dump() for c in chunks]}, ensure_ascii=False),
        encoding="utf-8",
    )
    counts = {}
    for c in chunks:
        counts[c.metadata.topic] = counts.get(c.metadata.topic, 0) + 1
    summary = {"chunks": len(chunks), "collections": counts, "embedder": embedder.name, "dim": int(matrix.shape[1])}
    logger.info("Ingested %s", summary)
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(json.dumps(ingest(), indent=2))
