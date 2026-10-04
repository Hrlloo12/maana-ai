from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from config import settings

if settings.database_url.startswith("sqlite:///"):
    Path(settings.database_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False}, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def _add_missing_columns() -> None:
    inspector = inspect(engine)
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            continue
        existing = {c["name"] for c in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name not in existing and column.nullable:
                ddl = column.type.compile(dialect=engine.dialect)
                with engine.begin() as conn:
                    conn.execute(text(f'ALTER TABLE {table.name} ADD COLUMN "{column.name}" {ddl}'))


def init_db() -> None:
    from db import models

    assert models.ContentSession
    Base.metadata.create_all(engine)
    _add_missing_columns()
