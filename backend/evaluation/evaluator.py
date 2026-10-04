from __future__ import annotations

import argparse
import json
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

from agents.schemas import EVIDENCE_REQUIRED, STRATEGY_FIT
from agents.text import mentions_any, normalize, quote_supported
from config import settings

HERE = Path(__file__).resolve().parent
RESULTS_DIR = HERE / "results"

METRIC_LABELS = {
    "intended_concept_extraction": "Intended Concept Extraction (recall of expected meanings)",
    "background_leakage_rate": "Background leakage into intended meaning (lower is better)",
    "meaning_gap_detection_accuracy": "Meaning Gap Detection Accuracy (status)",
    "gap_type_accuracy": "Gap Type Accuracy",
    "topic_gate_accuracy": "RAG topic gate accuracy",
    "rag_relevance_precision": "RAG Relevance (precision of kept evidence)",
    "irrelevant_retrieval_rejection": "Irrelevant retrieval rejected (out-of-scope content)",
    "citation_correctness": "Citation Correctness",
    "unsupported_claim_rate": "Unsupported Claim Rate (lower is better)",
    "abstention_accuracy": "Abstention Accuracy",
    "abstention_precision": "Abstention precision",
    "abstention_recall": "Abstention recall",
    "refinement_strategy_fit": "Refinement: strategy fits the cause",
    "refinement_relevance": "Refinement Relevance (explanation covers the gap)",
    "before_after_resolution_rate": "Before/After: misunderstanding resolved or partially resolved",
    "mean_before_alignment": "Mean alignment before",
    "mean_after_alignment": "Mean alignment after",
    "mean_improvement_points": "Mean improvement (points)",
    "agent_first_pass_rate": "Agent outputs valid on first attempt",
    "agent_final_pass_rate": "Agent outputs valid after correction",
}
COUNT_KEYS = {"mean_improvement_points", "n_cases", "n_retested", "n_errors", "n_claims", "n_citations",
              "guard_rejections", "mean_before_alignment", "mean_after_alignment"}


def load_cases() -> list[dict]:
    return json.loads((HERE / "dataset.json").read_text(encoding="utf-8"))["cases"]


def pct(values: list[float]) -> float | None:
    return round(100 * mean(values), 1) if values else None


def has_any(text: str, words: list[str]) -> bool:
    body = normalize(text)
    return any(normalize(w) and normalize(w) in body for w in words)


def group_recall(groups: list[list[str]], text: str) -> float | None:
    if not groups:
        return None
    return sum(1 for g in groups if has_any(text, g)) / len(groups)


def expected_list(value) -> list[str]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def check_citations(state: dict, case: dict) -> tuple[list[bool], list[bool]]:
    chunks = {c["evidence_id"]: c for c in state.get("rag_context", [])}
    allowed = set(case["expected_topics"])
    citations: list[bool] = []
    claims: list[bool] = []

    def cite_ok(eid: str) -> bool:
        c = chunks.get(eid)
        return bool(c) and c["metadata"]["topic"] in allowed

    def claim_ok(ids: list[str], quote: str) -> bool:
        return any(cite_ok(i) and quote_supported(quote, chunks[i]["text"]) for i in ids)

    meaning = state.get("meaning_analysis") or {}
    for c in meaning.get("intended_concepts", []):
        citations += [cite_ok(i) for i in c.get("evidence_ids", [])]
    for item in meaning.get("background_knowledge", []) + meaning.get("potential_ambiguities", []):
        citations += [cite_ok(i) for i in item["evidence_ids"]]
        claims.append(claim_ok(item["evidence_ids"], item.get("evidence_quote", "")))
    for key in ("verification", "second_verification"):
        for m in (state.get(key) or {}).get("misunderstandings", []):
            citations += [cite_ok(i) for i in m["evidence_ids"]]
            if m["gap_type"] in EVIDENCE_REQUIRED:
                claims.append(claim_ok(m["evidence_ids"], m.get("evidence_quote", "")))
    refinement = state.get("refinement") or {}
    if refinement:
        citations += [cite_ok(i) for i in refinement.get("evidence_ids", [])]
        for q in refinement.get("evidence_quotes", []):
            claims.append(any(quote_supported(q, c["text"]) for c in chunks.values()))
    return citations, claims


def evaluate_case(wf, case: dict, sid: str) -> dict:
    row: dict = {"id": case["id"], "category": case["category"]}
    state = wf.start(sid, case["content"], case["language"], case["language"])
    if wf.stage(sid) == "awaiting_response":
        state = wf.submit_response(sid, case["user_response"])
    stage = wf.stage(sid)
    verification = state.get("verification") or {}
    status = "insufficient_evidence" if stage == "abstained" else verification.get("status")
    row.update(status=status, expected_status=case["expected_status"], primary_topic=state.get("rag_primary_topic", ""))
    row["status_ok"] = status in case["expected_status"]
    row["abstained"] = stage == "abstained"
    row["expected_abstain"] = case["expected_status"] == ["insufficient_evidence"]
    row["topic_ok"] = state.get("rag_primary_topic", "") == case["expected_primary_topic"]

    kept = state.get("rag_context", [])
    row["kept_evidence"] = [c["doc_id"] for c in kept]
    row["evidence_relevant"] = [
        c["metadata"]["topic"] in case["expected_topics"] and mentions_any(c["text"], case["concept_terms"])
        for c in kept
    ]

    meaning = state.get("meaning_analysis") or {}
    concepts = meaning.get("intended_concepts", [])
    if concepts:
        text = " ".join(f"{c['concept']} {c['evidence_from_original_content']}" for c in concepts)
        row["concept_recall"] = group_recall(case["expected_concepts"], text)
        concept_only = " ".join(c["concept"] for c in concepts)
        row["background_leak"] = any(has_any(concept_only, g) for g in case["forbidden_intended"])
        row["intended_concepts"] = [c["concept"] for c in concepts]

    expected_types = expected_list(case.get("expected_gap_type"))
    if expected_types and verification and not row["abstained"]:
        row["gap_type"] = verification.get("primary_gap_type")
        row["gap_type_ok"] = row["gap_type"] in expected_types
    row["before"] = verification.get("alignment_score") if verification else None

    if stage == "gap_detected" and case.get("retest_response"):
        state = wf.refine(sid)
        r = state["refinement"]
        row.update(
            root_cause=r["root_cause"], strategy=r["strategy"], strategy_adjusted=r["strategy_adjusted"],
            explanation=state["explanation_text"],
        )
        strategy_ok = r["strategy"] in STRATEGY_FIT[r["root_cause"]]
        if case.get("expected_strategy"):
            strategy_ok = strategy_ok and r["strategy"] in case["expected_strategy"]
        if case.get("expected_root_cause"):
            strategy_ok = strategy_ok and r["root_cause"] in case["expected_root_cause"]
        row["strategy_ok"] = strategy_ok
        row["refinement_relevance"] = group_recall(case.get("refinement_terms", []), state["explanation_text"])
        state = wf.submit_retest(sid, case["retest_response"])
        final = state["final_result"]
        row.update(after=final["after_score"], resolution=final.get("resolution"))
        row["resolution_ok"] = final.get("resolution") in case.get("expected_resolution", ["resolved"])

    citations, claims = check_citations(state, case)
    row["citations_ok"], row["claims_supported"] = citations, claims
    row["guard_rejections"] = sum(len((state.get(k) or {}).get("rejected_claims", []))
                                  for k in ("verification", "second_verification"))
    row["guard_rejections"] += sum(len(e.get("corrections", [])) for e in state.get("validation_log", []))
    row["validation"] = [
        {"agent": e["agent"], "first_ok": not e["issues_first"], "final_ok": not e["issues_final"]}
        for e in state.get("validation_log", [])
    ]
    row["trace"] = {
        "rag_decisions": state.get("rag_decisions", []),
        "misunderstandings": [m["user_understood"] for m in verification.get("misunderstandings", [])],
        "rejected_claims": verification.get("rejected_claims", []),
        "gap_explanation": verification.get("gap_explanation", ""),
    }
    return row


def aggregate(rows: list[dict]) -> dict:
    ok = [r for r in rows if "error" not in r]

    def vals(key: str, rs: list[dict] | None = None) -> list[float]:
        return [float(r[key]) for r in (rs if rs is not None else ok) if r.get(key) is not None]

    flat = lambda key: [float(x) for r in ok for x in r.get(key, [])]
    abstained = [r for r in ok if r["abstained"]]
    expect_abstain = [r for r in ok if r["expected_abstain"]]
    retested = [r for r in ok if "after" in r]
    validation = [v for r in ok for v in r["validation"]]
    return {
        "intended_concept_extraction": pct(vals("concept_recall")),
        "background_leakage_rate": pct(vals("background_leak")),
        "meaning_gap_detection_accuracy": pct([float(r.get("status_ok", False)) for r in rows]),
        "gap_type_accuracy": pct(vals("gap_type_ok")),
        "topic_gate_accuracy": pct(vals("topic_ok")),
        "rag_relevance_precision": pct(flat("evidence_relevant")),
        "irrelevant_retrieval_rejection": pct([float(not r["kept_evidence"]) for r in expect_abstain]),
        "citation_correctness": pct(flat("citations_ok")),
        "unsupported_claim_rate": pct([1.0 - x for x in flat("claims_supported")]),
        "abstention_accuracy": pct([float(r["abstained"] == r["expected_abstain"]) for r in ok]),
        "abstention_precision": pct([float(r["expected_abstain"]) for r in abstained]),
        "abstention_recall": pct([float(r["abstained"]) for r in expect_abstain]),
        "refinement_strategy_fit": pct(vals("strategy_ok")),
        "refinement_relevance": pct(vals("refinement_relevance")),
        "before_after_resolution_rate": pct(vals("resolution_ok")),
        "mean_before_alignment": round(mean(vals("before", retested)), 3) if retested else None,
        "mean_after_alignment": round(mean(vals("after", retested)), 3) if retested else None,
        "mean_improvement_points": round(100 * mean([r["after"] - r["before"] for r in retested]), 1) if retested else None,
        "agent_first_pass_rate": pct([float(v["first_ok"]) for v in validation]),
        "agent_final_pass_rate": pct([float(v["final_ok"]) for v in validation]),
        "n_cases": len(rows),
        "n_errors": len(rows) - len(ok),
        "n_retested": len(retested),
        "n_citations": len(flat("citations_ok")),
        "n_claims": len(flat("claims_supported")),
        "guard_rejections": sum(r["guard_rejections"] for r in ok),
    }


def by_category(rows: list[dict]) -> dict:
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        groups[r["category"]].append(r)
    return {k: {"n": len(v), "status_accuracy": pct([float(r.get("status_ok", False)) for r in v])}
            for k, v in sorted(groups.items())}


def run_full(cases: list[dict]) -> dict:
    from langgraph.checkpoint.memory import InMemorySaver

    from graph.maana_graph import MaanaWorkflow

    wf = MaanaWorkflow(checkpointer=InMemorySaver())
    rows = []
    for case in cases:
        sid = f"eval-{case['id']}-{int(time.time())}"
        started = time.time()
        try:
            row = evaluate_case(wf, case, sid)
        except Exception as exc:
            row = {"id": case["id"], "category": case["category"], "error": f"{type(exc).__name__}: {exc}"}
        row["seconds"] = round(time.time() - started, 1)
        rows.append(row)
        verdict = "ERROR " + row["error"] if "error" in row else f"{row['status']} ({'ok' if row['status_ok'] else 'MISS'})"
        print(f"  {case['id']:<30} {verdict}", flush=True)
    return {
        "mode": f"full ({settings.llm_provider}:{settings.llm_model or 'default'})",
        "metrics": aggregate(rows),
        "categories": by_category(rows),
        "cases": rows,
    }


def run_retrieval_only(cases: list[dict]) -> dict:
    from rag.retriever import get_retriever

    retriever = get_retriever()
    rows, precision = [], []
    for case in cases:
        if not case["expected_primary_topic"]:
            continue
        chunks = retriever.search([case["content"]], limit=settings.rag_top_k, topics=case["expected_topics"])
        rel = [c.metadata.topic in case["expected_topics"] and mentions_any(c.text, case["concept_terms"]) for c in chunks]
        precision += [float(x) for x in rel]
        rows.append({"id": case["id"], "top": [(c.doc_id, c.relevance_score) for c in chunks]})
    return {"mode": "retrieval-only (dense search, no LLM)", "metrics": {"rag_relevance_precision": pct(precision)},
            "categories": {}, "cases": rows}


def write_results(result: dict) -> Path:
    RESULTS_DIR.mkdir(exist_ok=True)
    result["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    (RESULTS_DIR / "latest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    m = result["metrics"]
    lines = [f"# MA'NA evaluation: {result['mode']}", "", f"Generated: {result['generated_at']}", "",
             "| Metric | Value |", "|---|---|"]
    for key, value in m.items():
        label = METRIC_LABELS.get(key, key.replace("_", " "))
        shown = "n/a" if value is None else (f"{value}" if key in COUNT_KEYS or key.startswith("n_") else f"{value}%")
        lines.append(f"| {label} | {shown} |")
    if result["categories"]:
        lines += ["", "| Category | Cases | Status accuracy |", "|---|---|---|"]
        lines += [f"| {k} | {v['n']} | {v['status_accuracy']}% |" for k, v in result["categories"].items()]
    misses = [r for r in result["cases"] if "error" in r or not r.get("status_ok", True)]
    if misses:
        lines += ["", "## Cases that missed the expected status", ""]
        lines += [f"- {r['id']}: {r.get('error') or r.get('status')} (expected {r.get('expected_status')})" for r in misses]
    md = RESULTS_DIR / "latest.md"
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the MA'NA evaluation")
    parser.add_argument("--retrieval-only", action="store_true")
    parser.add_argument("--cases", default="", help="Comma-separated case IDs")
    args = parser.parse_args()

    cases = load_cases()
    if args.cases:
        wanted = set(args.cases.split(","))
        cases = [c for c in cases if c["id"] in wanted]
    print(f"Running {len(cases)} cases...", flush=True)
    result = run_retrieval_only(cases) if args.retrieval_only else run_full(cases)
    path = write_results(result)
    print(json.dumps(result["metrics"], indent=2))
    print(f"Saved to {path}")


if __name__ == "__main__":
    main()
