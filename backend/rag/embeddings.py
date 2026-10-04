from __future__ import annotations

import os
from functools import lru_cache

import numpy as np

from config import settings


class Embedder:
    name: str

    def embed(self, texts: list[str]) -> np.ndarray:
        raise NotImplementedError


def _normalise(vectors: np.ndarray) -> np.ndarray:
    vectors = np.asarray(vectors, dtype="float32")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


class LocalEmbedder(Embedder):
    def __init__(self, model_name: str):
        from fastembed import TextEmbedding

        settings.model_cache_dir.mkdir(parents=True, exist_ok=True)
        self.name = f"local:{model_name}"
        self.model = TextEmbedding(model_name=model_name, cache_dir=str(settings.model_cache_dir))

    def embed(self, texts: list[str]) -> np.ndarray:
        return _normalise(np.array(list(self.model.embed(texts))))


class OpenAIEmbedder(Embedder):
    def __init__(self, model_name: str):
        from openai import OpenAI

        key = os.getenv("EMBEDDING_API_KEY") or settings.llm_api_key
        base_url = os.getenv("EMBEDDING_BASE_URL") or settings.llm_base_url or None
        self.client = OpenAI(api_key=key, base_url=base_url)
        self.model_name = model_name
        self.name = f"openai:{model_name}"

    def embed(self, texts: list[str]) -> np.ndarray:
        resp = self.client.embeddings.create(model=self.model_name, input=texts)
        return _normalise(np.array([d.embedding for d in resp.data]))


@lru_cache(maxsize=1)
def get_embedder() -> Embedder:
    if settings.embedding_provider == "openai":
        model = settings.embedding_model
        if model.startswith("sentence-transformers/"):
            model = "text-embedding-3-small"
        return OpenAIEmbedder(model)
    return LocalEmbedder(settings.embedding_model)
