from __future__ import annotations

from typing import Any, TypedDict


class MaanaState(TypedDict, total=False):
    session_id: str
    original_content: str
    content_language: str
    target_language: str

    rag_context: list[dict[str, Any]]
    rag_queries: list[str]
    rag_topics: list[str]
    rag_primary_topic: str
    rag_key_terms: list[str]
    rag_decisions: list[dict[str, Any]]
    rag_abstain_reason: str
    rag_sufficient: bool

    meaning_analysis: dict[str, Any]
    understanding_question: str

    user_response: str
    user_interpretation: dict[str, Any]
    verification: dict[str, Any]

    refined_content: str
    refinement: dict[str, Any]
    explanation_text: str
    follow_up_question: str
    follow_up_response: str
    second_interpretation: dict[str, Any]
    second_verification: dict[str, Any]

    before_score: float
    after_score: float
    final_result: dict[str, Any]
    abstention: dict[str, Any]
    validation_log: list[dict[str, Any]]
