from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ReviewStatus = Literal["reviewed", "pending_review"]


class SourceDocument(BaseModel):
    id: str
    source_name: str
    source_name_ar: str = ""
    reference: str
    reference_ar: str = ""
    language: str = "en"
    review_status: ReviewStatus = "pending_review"
    text: str


class SourceFile(BaseModel):
    topic: str
    description: str = ""
    documents: list[SourceDocument]


class ChunkMetadata(BaseModel):
    source_name: str
    source_name_ar: str = ""
    topic: str
    reference: str
    reference_ar: str = ""
    language: str
    review_status: ReviewStatus


class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    metadata: ChunkMetadata


class RetrievedChunk(Chunk):
    evidence_id: str = ""
    relevance_score: float = Field(ge=-1.0, le=1.0)
