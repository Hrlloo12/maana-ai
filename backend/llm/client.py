from __future__ import annotations

import json
import logging
import re
import time
from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from config import settings

logger = logging.getLogger("maana.llm")

T = TypeVar("T", bound=BaseModel)

DEFAULT_MODELS = {
    "openai": "gpt-4.1",
    "gemini": "gemini-3.5-flash",
    "anthropic": "claude-opus-5",
}
GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

RATE_LIMIT_RETRIES = 4
RATE_LIMIT_MAX_WAIT = 65.0
PARSE_ATTEMPTS = 3


class LLMError(RuntimeError):
    def __init__(self, message: str, code: str = "provider"):
        super().__init__(message)
        self.code = code


class ChatBackend(Protocol):
    def chat(self, system: str, user: str, json_mode: bool) -> str: ...


class OpenAICompatibleBackend:
    def __init__(self, api_key: str, model: str, base_url: str | None):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key, base_url=base_url or None, timeout=settings.llm_timeout)
        self.model = model

    def chat(self, system: str, user: str, json_mode: bool) -> str:
        kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=settings.llm_temperature,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            **kwargs,
        )
        return resp.choices[0].message.content or ""


class AnthropicBackend:
    def __init__(self, api_key: str, model: str, base_url: str | None):
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key, base_url=base_url or None, timeout=settings.llm_timeout)
        self.model = model

    def chat(self, system: str, user: str, json_mode: bool) -> str:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        if resp.stop_reason == "refusal":
            raise LLMError("The model declined this request.", code="refused")
        return "".join(block.text for block in resp.content if block.type == "text")


def _extract_json(text: str, repair: bool = False) -> dict:
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            text = text[start : end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        if not repair:
            raise
        return json.loads(_BAD_ESCAPE.sub(r"\\\\", text))


_BAD_ESCAPE = re.compile(r"\\(?![\"\\/bfnrt]|u[0-9a-fA-F]{4})")


def _rate_limit_wait(exc: Exception) -> float | None:
    text = str(exc)
    if "503" in text or "UNAVAILABLE" in text:
        return 10.0
    if "429" not in text and "RateLimit" not in type(exc).__name__:
        return None
    if "PerDay" in text:
        return None
    match = re.search(r"retry in ([\d.]+)s", text, re.IGNORECASE)
    return min(float(match.group(1)) + 1 if match else 20.0, RATE_LIMIT_MAX_WAIT)


class LLMClient:
    def __init__(self, backend: ChatBackend | None = None):
        self._backend = backend

    @property
    def backend(self) -> ChatBackend:
        if self._backend is None:
            self._backend = self._build_backend()
        return self._backend

    @staticmethod
    def _build_backend() -> ChatBackend:
        provider = settings.llm_provider
        if not settings.llm_api_key:
            raise LLMError(
                "LLM_API_KEY is not set. Copy backend/.env.example to backend/.env and add your API key.",
                code="no_key",
            )
        model = settings.llm_model or DEFAULT_MODELS.get(provider, "")
        if provider == "openai":
            return OpenAICompatibleBackend(settings.llm_api_key, model, settings.llm_base_url)
        if provider == "gemini":
            return OpenAICompatibleBackend(
                settings.llm_api_key, model, settings.llm_base_url or GEMINI_OPENAI_BASE_URL
            )
        if provider == "anthropic":
            return AnthropicBackend(settings.llm_api_key, model, settings.llm_base_url)
        raise LLMError(f"Unknown LLM_PROVIDER '{provider}'. Use openai, gemini or anthropic.", code="config")

    def _chat(self, system: str, user: str) -> str:
        for attempt in range(RATE_LIMIT_RETRIES + 1):
            try:
                return self.backend.chat(system, user, json_mode=True)
            except LLMError:
                raise
            except Exception as exc:
                wait = _rate_limit_wait(exc)
                if wait is None or attempt == RATE_LIMIT_RETRIES:
                    if "429" in str(exc):
                        quota = re.search(r"quotaId'?\"?:\s*'?\"?([\w-]+)", str(exc))
                        raise LLMError(
                            "The LLM provider's rate limit or quota was reached"
                            f"{f' ({quota.group(1)})' if quota else ''}. Wait a minute and try again, "
                            "or use a key with a higher quota.",
                            code="rate_limit",
                        ) from exc
                    raise LLMError(f"LLM provider error: {exc}") from exc
                logger.warning("Rate limited by the LLM provider; retrying in %.0fs", wait)
                time.sleep(wait)
        raise LLMError("LLM provider unavailable.")

    def complete_json(self, system: str, user: str, schema: type[T]) -> T:
        schema_hint = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        full_system = (
            f"{system}\n\nRespond with ONE valid JSON object only — no markdown, no prose. "
            f"It must match this JSON schema:\n{schema_hint}"
        )
        prompt = user
        last_error: Exception | None = None
        for attempt in range(PARSE_ATTEMPTS):
            try:
                raw = self._chat(full_system, prompt)
                return schema.model_validate(_extract_json(raw, repair=attempt == PARSE_ATTEMPTS - 1))
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                logger.warning("Invalid JSON from LLM (attempt %s): %s", attempt + 1, exc)
                prompt = f"{user}\n\nYour previous answer was invalid ({exc.__class__.__name__}: {str(exc)[:300]}). Return corrected JSON only."
        raise LLMError(f"LLM returned invalid structured output: {last_error}", code="invalid_output")


_client: LLMClient | None = None


def get_llm() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


def set_llm(client: LLMClient) -> None:
    global _client
    _client = client
