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

GRADE_POOL = 9
POOL_PER_COLLECTION = 3
GRADE_TEXT_CHARS = 900

PLANNER_PROMPT = """You are the retrieval planner of MA'NA. The knowledge base contains the full text of the Holy
Qur'an (Arabic, Uthmani script) and of Sahih al-Bukhari and Sahih Muslim (Arabic with English translation).
Identify the exact Islamic concept the content is about, so that only evidence about THAT concept is retrieved.

- in_scope: false when the content is not about an Islamic belief, act of worship, ruling or concept that the
  Qur'an or hadith address (e.g. general facts about countries, languages, sport, food brands). Otherwise true.
- concept: a short English name of the concept (e.g. "Zakat", "Hajj and Umrah", "Fasting in Ramadan").
- concept_ar: its Arabic name (e.g. "الزكاة").
- key_terms: names of the concept as they appear in the texts: Arabic words (e.g. "الزكاة", "زكاة") and
  their English translation forms (e.g. "zakat", "obligatory charity").
- search_queries: 2 short English queries and 2 short Arabic queries about the meaning of THIS concept as the
  content states it."""

GRADER_PROMPT = """You are the evidence relevance grader of MA'NA. Decide, for each retrieved passage from the Qur'an
or hadith, whether it is about the SAME concept the content talks about, so that it can verify or explain this
content's meaning or a confusion readers commonly make with it.

A passage is NOT relevant when it is about a different practice or ruling that only shares a word with the
content (e.g. voluntary fasting when the content is about fasting in Ramadan), when it is about a specific
sub-type or special case that the content does not mention (e.g. Zakat al-Fitr when the content is about Zakat
in general), or when it only mentions the concept in passing while being about something else. When in doubt,
mark it not relevant. Return one grade per passage number."""


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
    reference_ar: str = ""
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


def plan_retrieval(content: str) -> QueryPlan:
    return get_llm().complete_json(PLANNER_PROMPT, f"CONTENT:\n{content}", QueryPlan)


def filter_candidates(
    candidates: list[RetrievedChunk], key_terms: list[str], pool: int = GRADE_POOL
) -> tuple[list[RetrievedChunk], dict[str, RetrievalDecision]]:
    on_concept = {c.chunk_id for c in candidates if mentions_any(f"{c.text} {c.text_ar}", key_terms)}
    top: dict[str, float] = {}
    for c in candidates:
        if c.chunk_id in on_concept:
            top[c.metadata.topic] = max(top.get(c.metadata.topic, 0.0), c.relevance_score)
    passed: list[RetrievedChunk] = []
    decisions: dict[str, RetrievalDecision] = {}
    for c in candidates:
        threshold = settings.rag_min_relevance_quran if c.metadata.topic == "quran" else settings.rag_min_relevance
        if c.chunk_id not in on_concept:
            reason = "off_concept"
        elif c.relevance_score < threshold:
            reason = "below_threshold"
        elif c.relevance_score < top[c.metadata.topic] - settings.rag_relative_margin:
            reason = "below_margin"
        elif any(k.doc_id == c.doc_id for k in passed):
            reason = "duplicate_document"
        elif any(jaccard(k.text, c.text) >= settings.rag_duplicate_similarity for k in passed):
            reason = "duplicate_text"
        elif len(passed) >= pool or sum(1 for k in passed if k.metadata.topic == c.metadata.topic) >= POOL_PER_COLLECTION:
            reason = "over_limit"
        else:
            reason = "candidate"
            passed.append(c)
        decisions[c.chunk_id] = RetrievalDecision(
            doc_id=c.doc_id, topic=c.metadata.topic, reference=c.metadata.reference,
            reference_ar=c.metadata.reference_ar, score=c.relevance_score, decision=reason,
        )
    return passed, decisions


def grade_candidates(content: str, concept: str, candidates: list[RetrievedChunk]) -> dict[int, EvidenceGrade] | None:
    if not candidates:
        return {}
    passages = "\n\n".join(
        f"[{i}] ({c.metadata.reference}) {c.text[:GRADE_TEXT_CHARS]}" for i, c in enumerate(candidates, 1)
    )
    user = f"CONTENT:\n{content}\n\nCONCEPT: {concept}\n\nPASSAGES:\n{passages}\n\nReturn the grades JSON."
    try:
        out = get_llm().complete_json(GRADER_PROMPT, user, EvidenceGrades)
    except LLMError as exc:
        logger.warning("Evidence grading unavailable, keeping rule-based selection: %s", exc)
        return None
    return {g.passage: g for g in out.grades}


def select_evidence(
    content: str, concept: str, candidates: list[RetrievedChunk], key_terms: list[str]
) -> tuple[list[RetrievedChunk], list[RetrievalDecision]]:
    passed, decisions = filter_candidates(candidates, key_terms)
    grades = grade_candidates(content, concept, passed)
    relevant: dict[str, list[RetrievedChunk]] = {}
    for i, c in enumerate(passed, 1):
        d = decisions[c.chunk_id]
        grade = grades.get(i) if grades is not None else None
        if grades is not None and (grade is None or not grade.relevant):
            d.decision, d.note = "judged_irrelevant", grade.reason if grade else "not graded"
        else:
            d.note = grade.reason if grade else ""
            relevant.setdefault(c.metadata.topic, []).append(c)
    kept: list[RetrievedChunk] = []
    queues = sorted(relevant.values(), key=lambda q: -q[0].relevance_score)
    while len(kept) < settings.rag_top_k and any(queues):
        for q in queues:
            if q and len(kept) < settings.rag_top_k:
                kept.append(q.pop(0))
    for q in queues:
        for c in q:
            decisions[c.chunk_id].decision = "over_limit"
    for c in kept:
        decisions[c.chunk_id].decision = "kept"
    for i, c in enumerate(kept, start=1):
        c.evidence_id = f"E{i}"
    return kept, list(decisions.values())


def retrieve_knowledge(content: str) -> RetrievalResult:
    retriever = get_retriever()
    plan = plan_retrieval(content)
    concept = plan.concept.strip() or plan.concept_ar.strip()
    queries = [content] + [q for q in plan.search_queries if q.strip()][:4]
    key_terms = [t for t in plan.key_terms if t.strip()]
    if plan.concept_ar.strip():
        key_terms.append(plan.concept_ar.strip())

    if not plan.in_scope or not concept:
        return RetrievalResult(
            chunks=[], queries=queries, topics=[], primary_topic=plan.concept_ar, key_terms=key_terms,
            sufficient=False, top_score=0.0, abstain_reason="no_covered_topic",
        )

    candidates = retriever.search(queries, terms=key_terms)
    kept, decisions = select_evidence(content, concept, candidates, key_terms)
    return RetrievalResult(
        chunks=kept,
        queries=queries,
        topics=sorted({c.metadata.topic for c in kept}),
        primary_topic=plan.concept_ar or concept,
        key_terms=key_terms,
        sufficient=bool(kept),
        top_score=candidates[0].relevance_score if candidates else 0.0,
        decisions=decisions,
        abstain_reason="" if kept else "no_relevant_evidence",
    )
