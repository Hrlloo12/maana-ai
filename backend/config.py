from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    llm_model: str = os.getenv("LLM_MODEL", "").strip()
    llm_api_key: str = os.getenv("LLM_API_KEY", "").strip()
    llm_base_url: str = os.getenv("LLM_BASE_URL", "").strip()
    llm_temperature: float = _float("LLM_TEMPERATURE", 0.1)
    llm_timeout: float = _float("LLM_TIMEOUT", 90)

    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "local").strip().lower()
    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    ).strip()
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "4"))
    rag_min_relevance: float = _float("RAG_MIN_RELEVANCE", 0.6)
    rag_min_relevance_quran: float = _float("RAG_MIN_RELEVANCE_QURAN", 0.45)
    rag_relative_margin: float = _float("RAG_RELATIVE_MARGIN", 0.15)
    rag_duplicate_similarity: float = _float("RAG_DUPLICATE_SIMILARITY", 0.8)
    corpus_file: Path = BASE_DIR / "data" / "corpus.json"
    raw_dir: Path = BASE_DIR / "data" / "raw"
    index_dir: Path = BASE_DIR / "data" / "index"
    model_cache_dir: Path = BASE_DIR / "data" / "model_cache"

    app_env: str = os.getenv("APP_ENV", "development").strip().lower()
    demo_mode: bool = _bool("DEMO_MODE", True)
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'maana.db'}")
    checkpoint_db: Path = BASE_DIR / "data" / "checkpoints.db"
    cors_origins: list[str] = field(
        default_factory=lambda: [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
    )

    @property
    def production(self) -> bool:
        return self.app_env == "production"

    @property
    def allowed_review_statuses(self) -> set[str]:
        return {"reviewed"} if self.production else {"reviewed", "pending_review"}


settings = Settings()
