from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ReviewStatus = Literal["reviewed", "pending_review"]


class Collection(BaseModel):
    id: str
    kind: Literal["quran", "hadith"]
    name: str
    name_ar: str
    url: str
    metadata_url: str = ""
    file: str
    metadata_file: str = ""
    license: str
    attribution: str
    homepage: str


class ChunkMetadata(BaseModel):
    source_name: str
    source_name_ar: str = ""
    topic: str
    reference: str
    reference_ar: str = ""
    chapter: str = ""
    chapter_ar: str = ""
    language: str
    review_status: ReviewStatus = "reviewed"


class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    text_ar: str = ""
    metadata: ChunkMetadata


class RetrievedChunk(Chunk):
    evidence_id: str = ""
    relevance_score: float = Field(ge=-1.0, le=1.0)
