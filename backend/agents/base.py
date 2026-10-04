from __future__ import annotations

import logging
from typing import Callable, TypeVar

from pydantic import BaseModel

from agents.text import quote_supported
from llm import LLMError, get_llm
from rag.schemas import RetrievedChunk

logger = logging.getLogger("maana.agents")

T = TypeVar("T", bound=BaseModel)

REPORT_LANGUAGE = "Arabic"
MAX_CORRECTIONS = 1


def format_evidence(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(no evidence available)"
    return "\n\n".join(
        f"[{c.evidence_id}] source: {c.metadata.source_name} | reference: {c.metadata.reference} "
        f"| topic: {c.metadata.topic}\n{c.text}"
        for c in chunks
    )


def known_ids(ids: list[str], chunks: list[RetrievedChunk]) -> list[str]:
    known = {c.evidence_id for c in chunks}
    seen: list[str] = []
    for raw in ids:
        eid = raw.strip().strip("[]").upper()
        if eid in known and eid not in seen:
            seen.append(eid)
    return seen


def unknown_ids(ids: list[str], chunks: list[RetrievedChunk]) -> list[str]:
    known = {c.evidence_id for c in chunks}
    return [i for i in ids if i.strip().strip("[]").upper() not in known]


def supporting_ids(ids: list[str], quote: str, chunks: list[RetrievedChunk]) -> list[str]:
    by_id = {c.evidence_id: c for c in chunks}
    return [i for i in known_ids(ids, chunks) if quote_supported(quote, by_id[i].text)]


def references_for(ids: list[str], chunks: list[RetrievedChunk]) -> str:
    by_id = {c.evidence_id: c for c in chunks}
    refs = dict.fromkeys(by_id[i].metadata.reference for i in ids if i in by_id)
    return "; ".join(refs)


def report_rule(audience_language: str | None = None) -> str:
    rule = (
        f"Write every analytical text value (concepts, explanations, diagnoses, reasons, summaries) in "
        f"{REPORT_LANGUAGE}, using clear and natural Modern Standard Arabic. Keep JSON keys and enum values "
        "in English."
    )
    if audience_language:
        rule += f" Texts addressed to the reader (questions, explanations to read) must be in {audience_language}."
    return rule


def call_validated(
    agent: str,
    system: str,
    user: str,
    schema: type[T],
    validate: Callable[[T], list[str]],
) -> tuple[T, dict]:
    llm = get_llm()
    prompt = user
    first: list[str] = []
    issues: list[str] = []
    attempts = 0
    out = None
    for attempts in range(1, MAX_CORRECTIONS + 2):
        try:
            candidate = llm.complete_json(system, prompt, schema)
        except LLMError as exc:
            if out is None or exc.code != "invalid_output":
                raise
            logger.warning("%s correction attempt failed, keeping the first output: %s", agent, exc)
            break
        out = candidate
        issues = validate(out)
        if attempts == 1:
            first = issues
        if not issues:
            break
        logger.warning("%s output failed validation (attempt %s): %s", agent, attempts, issues)
        prompt = (
            f"{user}\n\nYOUR PREVIOUS ANSWER FAILED VALIDATION:\n- " + "\n- ".join(issues)
            + "\nReturn the complete corrected JSON object."
        )
    report = {"agent": agent, "attempts": attempts, "issues_first": first, "issues_final": issues, "corrections": []}
    return out, report
