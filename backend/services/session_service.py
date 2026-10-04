from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy import select

from db.database import SessionLocal
from db.models import ContentSession
from graph.maana_graph import MaanaWorkflow

_workflow: MaanaWorkflow | None = None


def get_workflow() -> MaanaWorkflow:
    global _workflow
    if _workflow is None:
        _workflow = MaanaWorkflow()
    return _workflow


def set_workflow(workflow: MaanaWorkflow) -> None:
    global _workflow
    _workflow = workflow


def session_view(session_id: str) -> dict[str, Any] | None:
    wf = get_workflow()
    stage = wf.stage(session_id)
    if stage == "not_found":
        return None
    return {"session_id": session_id, "stage": stage, **wf.state(session_id)}


def persist(view: dict[str, Any]) -> None:
    first = view.get("verification") or {}
    final = view.get("final_result") or {}
    with SessionLocal() as db:
        row = db.get(ContentSession, view["session_id"]) or ContentSession(
            id=view["session_id"],
            original_content=view.get("original_content", ""),
            content_language=view.get("content_language", ""),
            target_language=view.get("target_language", ""),
        )
        row.stage = view["stage"]
        row.topic = view.get("rag_primary_topic") or (view.get("meaning_analysis") or {}).get("topic")
        if first:
            row.status_before = first.get("status")
            row.before_score = first.get("alignment_score")
            row.gaps = [m["user_understood"] for m in first.get("misunderstandings", [])] + first.get("missing", [])
        refinement = view.get("refinement") or {}
        if refinement:
            row.strategy = refinement.get("strategy")
            row.root_cause = refinement.get("root_cause")
        if final and final.get("outcome") != "abstained":
            row.status_after = final.get("status_after")
            row.after_score = final.get("after_score")
            row.resolved_gaps = final.get("resolved_gaps", [])
            row.remaining_gaps = final.get("remaining_gaps", [])
        db.add(row)
        db.commit()


def dashboard() -> dict[str, Any]:
    with SessionLocal() as db:
        rows = list(db.scalars(select(ContentSession).order_by(ContentSession.created_at)))

    gap_rows = [r for r in rows if r.status_before in {"partial_gap", "major_gap"}]
    completed = [r for r in rows if r.stage == "completed" and r.after_score is not None]
    retested = [r for r in completed if r.status_before in {"partial_gap", "major_gap"}]
    befores = [r.before_score for r in rows if r.before_score is not None]
    afters = [r.after_score for r in completed]
    concept_counts = Counter(g for r in rows for g in (r.gaps or []))
    topic_counts = Counter((r.topic or "—") for r in gap_rows)
    strategy_counts = Counter(r.strategy for r in rows if r.strategy)

    def avg(values: list[float]) -> float | None:
        return round(sum(values) / len(values), 4) if values else None

    return {
        "content_sessions": len(rows),
        "sessions_with_gaps": len(gap_rows),
        "meaning_gaps_detected": sum(len(r.gaps or []) for r in rows),
        "meaning_gaps_resolved": sum(len(r.resolved_gaps or []) for r in rows),
        "abstentions": sum(1 for r in rows if r.stage == "abstained"),
        "average_before_alignment": avg(befores),
        "average_after_alignment": avg(afters),
        "most_misunderstood_concepts": [{"concept": c, "count": n} for c, n in concept_counts.most_common(8)],
        "gaps_by_topic": [{"topic": t, "count": n} for t, n in topic_counts.most_common(8)],
        "explanation_strategies": [{"strategy": s, "count": n} for s, n in strategy_counts.most_common()],
        "recent_sessions": [
            {
                "session_id": r.id,
                "content": r.original_content[:220],
                "topic": r.topic,
                "stage": r.stage,
                "status_before": r.status_before,
                "status_after": r.status_after,
                "before": r.before_score,
                "after": r.after_score,
                "created_at": r.created_at.isoformat(),
            }
            for r in reversed(rows[-30:])
        ],
        "before_after": [
            {
                "session_id": r.id,
                "topic": r.topic,
                "before": r.before_score,
                "after": r.after_score,
                "created_at": r.created_at.isoformat(),
            }
            for r in retested
        ],
    }
