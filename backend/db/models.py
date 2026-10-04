from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.database import Base


class ContentSession(Base):
    __tablename__ = "content_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
    original_content: Mapped[str] = mapped_column(Text)
    content_language: Mapped[str] = mapped_column(String(32))
    target_language: Mapped[str] = mapped_column(String(32))
    topic: Mapped[str | None] = mapped_column(String(128), nullable=True)
    stage: Mapped[str] = mapped_column(String(32))
    status_before: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status_after: Mapped[str | None] = mapped_column(String(32), nullable=True)
    before_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    after_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    gaps: Mapped[list] = mapped_column(JSON, default=list)
    resolved_gaps: Mapped[list] = mapped_column(JSON, default=list)
    remaining_gaps: Mapped[list] = mapped_column(JSON, default=list)
    strategy: Mapped[str | None] = mapped_column(String(32), nullable=True)
    root_cause: Mapped[str | None] = mapped_column(String(32), nullable=True)
