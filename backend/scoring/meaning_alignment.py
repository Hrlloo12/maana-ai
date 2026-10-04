from __future__ import annotations

UNDERSTOOD_THRESHOLD = 0.8
MAJOR_GAP_THRESHOLD = 0.5
MIN_SCORABLE_SHARE = 0.5


def normalise_weights(raw: dict[str, float]) -> dict[str, float]:
    if not raw:
        return {}
    cleaned = {cid: max(0.0, float(w or 0.0)) for cid, w in raw.items()}
    total = sum(cleaned.values())
    if total <= 0:
        return {cid: round(1 / len(cleaned), 4) for cid in cleaned}
    return {cid: round(w / total, 4) for cid, w in cleaned.items()}


def alignment_score(weights: dict[str, float], understood_ids: set[str]) -> float:
    return round(min(1.0, sum(w for cid, w in weights.items() if cid in understood_ids)), 4)


def classify(score: float, misunderstood_weight: float, has_misunderstanding: bool) -> str:
    if score >= UNDERSTOOD_THRESHOLD and not has_misunderstanding:
        return "understood"
    if score < MAJOR_GAP_THRESHOLD or misunderstood_weight >= 0.5:
        return "major_gap"
    return "partial_gap"


def overall_resolution(statuses: list[str]) -> str | None:
    if not statuses:
        return None
    if all(s == "resolved" for s in statuses):
        return "resolved"
    if all(s == "remains" for s in statuses):
        return "remains"
    return "partially_resolved"


def improvement_points(before: float, after: float) -> int:
    return round((after - before) * 100)
