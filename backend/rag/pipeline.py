from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from agents.schemas import QueryPlan
from agents.text import jaccard, mentions_any
from config import settings
from llm import LLMError, get_llm
from rag.retriever import get_retriever
from rag.schemas import RetrievedChunk

logger = logging.getLogger("maana.rag")

GRADE_POOL = 6

PLANNER_PROMPT = """You are the retrieval planner of MA'NA. Identify the exact Islamic concept that the content
is about, so that only evidence about THAT concept is retrieved.

- primary_topic: the ONE topic from AVAILABLE TOPICS that the content is mainly about. Return "" when the
  content's main concept is not one of the available topics. Never force a match: content about prayer,
  music, marriage, food or anything else outside the list must get "", even if it mentions a covered word
  in passing.
- related_topics: at most ONE other available topic, and only when it is a concept readers commonly
  confuse with the primary one (e.g. zakat <-> sadaqah). Otherwise [].
- key_terms: names of the primary concept as they may appear in sources: English, transliterations and
  Arabic script (e.g. ["zakat", "zakah", "الزكاة"]).
- search_queries: 2 short English queries and 1 short Arabic query about the meaning of THIS concept as the
  content states it."""

GRADER_PROMPT = """You are the evidence relevance grader of MA'NA. Decide, for each retrieved passage, whether it is
about the SAME concept the content talks about, so that it can verify or explain this content's meaning or a
confusion readers commonly make with it.

A passage is NOT relevant when it is about a different practice or ruling that only shares a word with the
content (e.g. voluntary fasting when the content is about fasting in Ramadan), when it is about a specific
sub-type or special case that the content does not mention (e.g. Zakat al-Fitr when the content is about Zakat
in general), or when it only mentions the concept in passing while being about something else. When in doubt,
mark it not relevant.
Return one grade per passage number."""


class EvidenceGrade(BaseModel):
    passage: int
    relevant: bool
    reason: str = ""


class EvidenceGrades(BaseModel):
    grades: list[EvidenceGrade] = Field(default_factory=list)


class RetrievalDecision(BaseModel):
    doc_id: str
    topic: str
    reference: str
    score: float
    decision: str
    note: str = ""


class RetrievalResult(BaseModel):
    chunks: list[RetrievedChunk]
    queries: list[str]
    topics: list[str]
    primary_topic: str = ""
    key_terms: list[str] = Field(default_factory=list)
    sufficient: bool
    top_score: float
    decisions: list[RetrievalDecision] = Field(default_factory=list)
    abstain_reason: str = ""


def plan_retrieval(content: str, topics: dict[str, str]) -> QueryPlan:
    listing = "\n".join(f"- {name}: {desc}" for name, desc in sorted(topics.items()))
    return get_llm().complete_json(PLANNER_PROMPT, f"AVAILABLE TOPICS:\n{listing}\n\nCONTENT:\n{content}", QueryPlan)


def filter_candidates(
    candidates: list[RetrievedChunk], primary: str, key_terms: list[str], pool: int = GRADE_POOL
) -> tuple[list[RetrievedChunk], dict[str, RetrievalDecision]]:
    top = max((c.relevance_score for c in candidates if c.metadata.topic == primary), default=0.0)
    passed: list[RetrievedChunk] = []
    decisions: dict[str, RetrievalDecision] = {}
    for c in candidates:
        if c.relevance_score < settings.rag_min_relevance:
            reason = "below_threshold"
        elif c.relevance_score < top - settings.rag_relative_margin:
            reason = "below_margin"
        elif not mentions_any(c.text, key_terms):
            reason = "off_concept"
        elif any(k.doc_id == c.doc_id for k in passed):
            reason = "duplicate_document"
        elif any(jaccard(k.text, c.text) >= settings.rag_duplicate_similarity for k in passed):
            reason = "duplicate_text"
        elif len(passed) >= pool:
            reason = "over_limit"
        else:
            reason = "candidate"
            passed.append(c)
        decisions[c.chunk_id] = RetrievalDecision(
            doc_id=c.doc_id, topic=c.metadata.topic, reference=c.metadata.reference,
            score=c.relevance_score, decision=reason,
        )
    return passed, decisions


def grade_candidates(content: str, primary: str, candidates: list[RetrievedChunk]) -> dict[int, EvidenceGrade] | None:
    if not candidates:
        return {}
    passages = "\n\n".join(f"[{i}] {c.text}" for i, c in enumerate(candidates, 1))
    user = f"CONTENT:\n{content}\n\nCONCEPT: {primary}\n\nPASSAGES:\n{passages}\n\nReturn the grades JSON."
    try:
        out = get_llm().complete_json(GRADER_PROMPT, user, EvidenceGrades)
    except LLMError as exc:
        logger.warning("Evidence grading unavailable, keeping rule-based selection: %s", exc)
        return None
    return {g.passage: g for g in out.grades}


def select_evidence(
    content: str, candidates: list[RetrievedChunk], primary: str, key_terms: list[str]
) -> tuple[list[RetrievedChunk], list[RetrievalDecision]]:
    passed, decisions = filter_candidates(candidates, primary, key_terms)
    grades = grade_candidates(content, primary, passed)
    kept: list[RetrievedChunk] = []
    for i, c in enumerate(passed, 1):
        d = decisions[c.chunk_id]
        grade = grades.get(i) if grades is not None else None
        if grades is not None and (grade is None or not grade.relevant):
            d.decision, d.note = "judged_irrelevant", grade.reason if grade else "not graded"
        elif len(kept) >= settings.rag_top_k:
            d.decision = "over_limit"
        else:
            d.decision, d.note = "kept", grade.reason if grade else ""
            kept.append(c)
    if not any(k.metadata.topic == primary for k in kept):
        for c in kept:
            decisions[c.chunk_id].decision = "no_primary_evidence"
        kept = []
    for i, c in enumerate(kept, start=1):
        c.evidence_id = f"E{i}"
    return kept, list(decisions.values())


def retrieve_knowledge(content: str) -> RetrievalResult:
    retriever = get_retriever()
    available = retriever.topics
    plan = plan_retrieval(content, {t: retriever.descriptions.get(t, "") for t in available})

    primary = plan.primary_topic.strip().lower()
    primary = primary if primary in available else ""
    related = [t.strip().lower() for t in plan.related_topics if t.strip().lower() in available]
    related = [t for t in related if t != primary][:1]
    queries = [content] + [q for q in plan.search_queries if q.strip()][:4]
    key_terms = [t for t in plan.key_terms if t.strip()] + ([primary] if primary else [])

    if not primary:
        return RetrievalResult(
            chunks=[], queries=queries, topics=[], key_terms=key_terms, sufficient=False, top_score=0.0,
            abstain_reason="no_covered_topic",
        )

    candidates = retriever.search(queries, topics=[primary, *related])
    kept, decisions = select_evidence(content, candidates, primary, key_terms)
    return RetrievalResult(
        chunks=kept,
        queries=queries,
        topics=[primary, *related],
        primary_topic=primary,
        key_terms=key_terms,
        sufficient=bool(kept),
        top_score=candidates[0].relevance_score if candidates else 0.0,
        decisions=decisions,
        abstain_reason="" if kept else "no_relevant_evidence",
    )
