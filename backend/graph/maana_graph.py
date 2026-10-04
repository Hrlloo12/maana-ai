from __future__ import annotations

import sqlite3
from typing import Any

from langgraph.graph import END, START, StateGraph

from agents.meaning_agent import run_meaning_agent
from agents.refinement_agent import run_refinement_agent
from agents.schemas import MeaningAnalysis, UserInterpretation, Verification
from agents.understanding_agent import run_understanding_agent
from agents.verification_agent import run_verification_agent
from config import settings
from graph.progress import tracked
from graph.state import MaanaState
from rag.pipeline import retrieve_knowledge
from rag.schemas import RetrievedChunk
from scoring.meaning_alignment import improvement_points, overall_resolution

ABSTENTION_MESSAGE = "تعذر التحقق من خلال المصادر المتاحة."
ABSTENTION_REASONS = {
    "no_covered_topic": "المحتوى يتناول موضوعًا لا تغطيه المصادر الموثوقة المتاحة حاليًا.",
    "no_relevant_evidence": "لم تجتز أي وثيقة موثوقة حدّ الصلة المطلوب بالمفهوم المحدد في المحتوى.",
    "no_intended_concepts": "تعذر تحديد معنى مقصود مستند إلى نص المحتوى نفسه.",
    "verification": "تعذر التحقق من فهم القارئ بالاستناد إلى المصادر الموثوقة المتاحة.",
}

INTERRUPT_BEFORE = ["understanding_agent", "refinement_agent", "retest_understanding"]


def _evidence(state: MaanaState) -> list[RetrievedChunk]:
    return [RetrievedChunk.model_validate(c) for c in state.get("rag_context", [])]


def _log(state: MaanaState, report: dict | None, stage: str = "") -> list[dict]:
    log = list(state.get("validation_log", []))
    if report is not None:
        log.append({**report, "stage": stage} if stage else report)
    return log


@tracked("retrieve_knowledge")
def retrieve_node(state: MaanaState) -> dict:
    result = retrieve_knowledge(state["original_content"])
    return {
        "rag_context": [c.model_dump() for c in result.chunks],
        "rag_queries": result.queries,
        "rag_topics": result.topics,
        "rag_primary_topic": result.primary_topic,
        "rag_key_terms": result.key_terms,
        "rag_decisions": [d.model_dump() for d in result.decisions],
        "rag_abstain_reason": result.abstain_reason,
        "rag_sufficient": result.sufficient,
    }


@tracked("meaning_agent")
def meaning_node(state: MaanaState) -> dict:
    analysis, report = run_meaning_agent(state["original_content"], state["target_language"], _evidence(state))
    return {
        "meaning_analysis": analysis.model_dump(),
        "understanding_question": analysis.understanding_question,
        "validation_log": _log(state, report),
    }


@tracked("understanding_agent")
def understanding_node(state: MaanaState) -> dict:
    interp, report = run_understanding_agent(
        state["original_content"], state["understanding_question"], state["user_response"], state["target_language"]
    )
    return {"user_interpretation": interp.model_dump(), "validation_log": _log(state, report)}


@tracked("verification_agent")
def verification_node(state: MaanaState) -> dict:
    v, report = run_verification_agent(
        MeaningAnalysis.model_validate(state["meaning_analysis"]),
        UserInterpretation.model_validate(state["user_interpretation"]),
        state["user_response"],
        _evidence(state),
        state["target_language"],
    )
    return {"verification": v.model_dump(), "before_score": v.alignment_score, "validation_log": _log(state, report)}


@tracked("refinement_agent")
def refinement_node(state: MaanaState) -> dict:
    out, report = run_refinement_agent(
        state["original_content"],
        Verification.model_validate(state["verification"]),
        _evidence(state),
        state["target_language"],
    )
    return {
        "refinement": out.model_dump(),
        "refined_content": out.improved_content,
        "explanation_text": out.explanation_text,
        "follow_up_question": state["understanding_question"],
        "validation_log": _log(state, report),
    }


@tracked("retest_understanding")
def retest_understanding_node(state: MaanaState) -> dict:
    interp, report = run_understanding_agent(
        state["explanation_text"], state["follow_up_question"], state["follow_up_response"], state["target_language"]
    )
    return {"second_interpretation": interp.model_dump(), "validation_log": _log(state, report, "retest")}


@tracked("retest_verification")
def retest_verification_node(state: MaanaState) -> dict:
    first = Verification.model_validate(state["verification"])
    v, report = run_verification_agent(
        MeaningAnalysis.model_validate(state["meaning_analysis"]),
        UserInterpretation.model_validate(state["second_interpretation"]),
        state["follow_up_response"],
        _evidence(state),
        state["target_language"],
        content_read=state["explanation_text"],
        previous=first.misunderstandings,
    )
    return {
        "second_verification": v.model_dump(),
        "after_score": v.alignment_score,
        "validation_log": _log(state, report, "retest"),
    }


@tracked("safe_abstention")
def abstention_node(state: MaanaState) -> dict:
    if state.get("verification"):
        stage, code = "verification", "verification"
    elif state.get("meaning_analysis"):
        stage, code = "meaning", "no_intended_concepts"
    else:
        stage, code = "retrieval", state.get("rag_abstain_reason") or "no_relevant_evidence"
    return {
        "abstention": {
            "message": ABSTENTION_MESSAGE,
            "stage": stage,
            "reason_code": code,
            "reason": ABSTENTION_REASONS.get(code, ABSTENTION_REASONS["no_relevant_evidence"]),
        }
    }


@tracked("finalize")
def finalize_node(state: MaanaState) -> dict:
    first = state.get("verification") or {}
    second = state.get("second_verification") or {}
    if state.get("abstention"):
        return {"final_result": {"outcome": "abstained", **state["abstention"]}}

    before = first.get("alignment_score", 0.0)
    after = second.get("alignment_score", before) if second else before

    first_missing = first.get("missing", [])
    gaps_before = [m["user_understood"] for m in first.get("misunderstandings", [])] + first_missing
    resolved: list[str] = []
    partially: list[str] = []
    remaining: list[str] = []
    statuses: list[str] = []
    if second:
        for item in second.get("previous_resolution", []):
            {"resolved": resolved, "partially_resolved": partially, "remains": remaining}[item["status"]].append(
                item["user_understood"]
            )
            statuses.append(item["status"])
        arrived_now = set(second.get("what_arrived", []))
        for concept in first_missing:
            (resolved if concept in arrived_now else remaining).append(concept)
            statuses.append("resolved" if concept in arrived_now else "remains")
        for concept in second.get("missing", []):
            if concept not in first_missing:
                remaining.append(concept)
                statuses.append("remains")
        remaining += [m["user_understood"] for m in second.get("misunderstandings", [])
                      if m["user_understood"] not in remaining]

    refinement = state.get("refinement") or {}
    sources: dict[str, dict] = {}
    for item in first.get("evidence", []) + second.get("evidence", []):
        sources.setdefault(item["reference"], item)

    return {
        "after_score": after,
        "final_result": {
            "outcome": "understood_first_time" if first.get("status") == "understood" else "retested",
            "status_before": first.get("status"),
            "status_after": second.get("status") or first.get("status"),
            "before_score": before,
            "after_score": after,
            "improvement_points": improvement_points(before, after),
            "resolution": overall_resolution(statuses),
            "gaps_detected": gaps_before,
            "resolved_gaps": resolved,
            "partially_resolved_gaps": partially,
            "remaining_gaps": remaining,
            "root_cause": refinement.get("root_cause"),
            "explanation_strategy": refinement.get("strategy"),
            "sources_used": list(sources.values()),
        },
    }


def route_after_retrieval(state: MaanaState) -> str:
    return "meaning_agent" if state.get("rag_sufficient") else "safe_abstention"


def route_after_meaning(state: MaanaState) -> str:
    return "understanding_agent" if state.get("meaning_analysis", {}).get("intended_concepts") else "safe_abstention"


def route_after_verification(state: MaanaState) -> str:
    status = state["verification"]["status"]
    if status == "understood":
        return "finalize"
    if status == "insufficient_evidence":
        return "safe_abstention"
    return "refinement_agent"


def build_graph(checkpointer: Any):
    g = StateGraph(MaanaState)
    g.add_node("retrieve_knowledge", retrieve_node)
    g.add_node("meaning_agent", meaning_node)
    g.add_node("understanding_agent", understanding_node)
    g.add_node("verification_agent", verification_node)
    g.add_node("refinement_agent", refinement_node)
    g.add_node("retest_understanding", retest_understanding_node)
    g.add_node("retest_verification", retest_verification_node)
    g.add_node("safe_abstention", abstention_node)
    g.add_node("finalize", finalize_node)

    g.add_edge(START, "retrieve_knowledge")
    g.add_conditional_edges("retrieve_knowledge", route_after_retrieval, ["meaning_agent", "safe_abstention"])
    g.add_conditional_edges("meaning_agent", route_after_meaning, ["understanding_agent", "safe_abstention"])
    g.add_edge("understanding_agent", "verification_agent")
    g.add_conditional_edges(
        "verification_agent", route_after_verification, ["finalize", "safe_abstention", "refinement_agent"]
    )
    g.add_edge("refinement_agent", "retest_understanding")
    g.add_edge("retest_understanding", "retest_verification")
    g.add_edge("retest_verification", "finalize")
    g.add_edge("safe_abstention", "finalize")
    g.add_edge("finalize", END)
    return g.compile(checkpointer=checkpointer, interrupt_before=INTERRUPT_BEFORE)


def sqlite_checkpointer():
    from langgraph.checkpoint.sqlite import SqliteSaver

    settings.checkpoint_db.parent.mkdir(parents=True, exist_ok=True)
    return SqliteSaver(sqlite3.connect(str(settings.checkpoint_db), check_same_thread=False))


STAGES = {
    "understanding_agent": "awaiting_response",
    "refinement_agent": "gap_detected",
    "retest_understanding": "awaiting_retest",
}


class MaanaWorkflow:
    def __init__(self, checkpointer: Any | None = None):
        self.graph = build_graph(checkpointer or sqlite_checkpointer())

    @staticmethod
    def _config(session_id: str) -> dict:
        return {"configurable": {"thread_id": session_id}}

    def stage(self, session_id: str) -> str:
        snap = self.graph.get_state(self._config(session_id))
        if not snap.values:
            return "not_found"
        if snap.next:
            return STAGES.get(snap.next[0], "processing")
        return "abstained" if snap.values.get("abstention") else "completed"

    def state(self, session_id: str) -> dict:
        return dict(self.graph.get_state(self._config(session_id)).values)

    def start(self, session_id: str, content: str, content_language: str, target_language: str) -> dict:
        self.graph.invoke(
            {
                "session_id": session_id,
                "original_content": content,
                "content_language": content_language,
                "target_language": target_language,
            },
            self._config(session_id),
        )
        return self.state(session_id)

    def submit_response(self, session_id: str, response: str) -> dict:
        self._expect(session_id, "awaiting_response")
        self.graph.update_state(self._config(session_id), {"user_response": response})
        self.graph.invoke(None, self._config(session_id))
        return self.state(session_id)

    def refine(self, session_id: str) -> dict:
        self._expect(session_id, "gap_detected")
        self.graph.invoke(None, self._config(session_id))
        return self.state(session_id)

    def submit_retest(self, session_id: str, response: str) -> dict:
        self._expect(session_id, "awaiting_retest")
        self.graph.update_state(self._config(session_id), {"follow_up_response": response})
        self.graph.invoke(None, self._config(session_id))
        return self.state(session_id)

    def _expect(self, session_id: str, stage: str) -> None:
        current = self.stage(session_id)
        if current != stage:
            raise WorkflowStageError(f"Session is at stage '{current}', expected '{stage}'.")


class WorkflowStageError(ValueError):
    pass
