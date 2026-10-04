from __future__ import annotations

from pydantic import BaseModel, Field

from agents.base import call_validated, format_evidence, known_ids, report_rule
from agents.schemas import STRATEGY_FIT, ComparisonRow, RefinementLLMOutput, RefinementOutput, Verification, VisualNode
from agents.text import normalize, quote_supported
from llm import LLMError, get_llm
from rag.schemas import RetrievedChunk

MAX_WORDS = 70

PAYLOAD_HINTS = {
    "comparison": 'fill comparison_left_label (the concept in the content), comparison_right_label (the concept it '
                  'was confused with) and comparison_rows: 2-4 objects {"aspect": ..., "left": ..., "right": ...}',
    "step_by_step": "fill steps with 2-5 short ordered strings",
    "example": "fill example with one concrete everyday example",
    "visual": 'fill visual_nodes with 2-5 objects {"label": ..., "detail": ...}',
}

PAYLOAD_PROMPT = """You complete one part of an explanation written by MA'NA. Fill ONLY the fields required by the
given strategy, in the audience language, using only facts from the explanation and the trusted evidence.
Never state a ruling or classification (e.g. sunnah, wajib) that the evidence does not state."""


class StrategyPayload(BaseModel):
    comparison_left_label: str = ""
    comparison_right_label: str = ""
    comparison_rows: list[ComparisonRow] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    example: str = ""
    visual_nodes: list[VisualNode] = Field(default_factory=list)

SYSTEM_PROMPT = """You are the REFINEMENT AGENT of MA'NA. A meaning gap was detected. Do not just rewrite the
sentence: find WHY the reader misunderstood and explain the meaning again in the way that best removes
that specific misunderstanding.

1. root_cause — why the misunderstanding happened:
   - concept_confusion: the reader equated the concept with a different one (e.g. Hajj with Umrah).
   - ambiguous_wording: a word in the content carries another everyday meaning (e.g. "charity" read as optional).
   - abstract_concept: the idea is abstract and the reader could not picture it.
   - missing_context: the reader lacks the background needed to read the term as intended.
   - complex_process: the meaning involves a sequence or procedure the reader did not follow.
   - overgeneralization: the reader stretched the meaning beyond what it covers.
   diagnosis: one or two sentences explaining the cause, referring to the reader's words.

2. strategy — the explanation method that fits the cause:
   - comparison: a concise side-by-side contrast. Fill comparison_left_label, comparison_right_label and 2-4
     comparison_rows (aspect, left, right). Use it for concept_confusion (e.g. Hajj vs Umrah) and for
     ambiguous_wording, contrasting the everyday reading of the word with its intended Islamic meaning
     (e.g. "charity" / «صدقة» as a voluntary gift vs Zakat as an obligation).
   - example: one concrete, everyday example that makes the meaning tangible. Fill example.
   - visual: a simple chain of 2-5 nodes the interface draws as a diagram (e.g. a sequence in time, or the
     parts of a concept and how they relate). Fill visual_nodes (label, detail).
   - step_by_step: 2-5 short ordered steps, for meanings that unfold in a sequence (e.g. from dawn to sunset).
     Fill steps.
   - simplification: plain, short wording, with no extra fields. Use it ONLY for missing_context, when the
     reader simply lacked context and a clearer sentence is enough. Never use it when a contrast, an example
     or steps would show the meaning better.
   Allowed strategies per cause: concept_confusion -> comparison; ambiguous_wording -> comparison or example;
   abstract_concept -> example or visual; missing_context -> simplification, example or step_by_step;
   complex_process -> step_by_step or visual; overgeneralization -> example or comparison.
   Choose the root cause carefully: a meaning that involves time, order or several actions (e.g. fasting
   from dawn until sunset) is complex_process. For missing_context prefer example or step_by_step;
   choose simplification only when neither would add anything.
   strategy_reason: one sentence on why this method fits this cause.

3. improved_content — the new explanation the reader will read: 1-2 sentences (under 45 words), close to the
   creator's words, fixing ONLY the detected gaps. The strategy fields complement it.

Rules:
- Use ONLY facts stated in the TRUSTED EVIDENCE or the original content. No rulings, opinions or fatwas.
  This applies to every comparison cell, step, example and diagram node as well: never state a ruling or
  classification (e.g. sunnah, wajib, recommended) unless the evidence states it word for word; leave the
  aspect out instead.
- evidence_quotes: copy, word for word, the evidence sentences that support the facts you added.
  evidence_ids: the IDs of those blocks.
- Simple, natural language for a non-specialist reader of the audience language. Keep key Arabic terms.
- changes: one item per gap fixed (original_issue, improvement, reason).
The reader is re-tested afterwards with the same neutral question as the first time, so do not write a
question."""


def _allowed_causes(verification: Verification) -> list[str]:
    types = {m.gap_type for m in verification.misunderstandings}
    if "concept_confusion" in types:
        return ["concept_confusion"]
    if "ambiguity_triggered" in types:
        return ["ambiguous_wording", "missing_context"]
    if types:
        return [c for c in STRATEGY_FIT if c != "concept_confusion"]
    return ["missing_context", "abstract_concept", "complex_process"]


def _payload_ok(out: RefinementLLMOutput, strategy: str) -> bool:
    if strategy == "comparison":
        return bool(out.comparison_left_label.strip() and out.comparison_right_label.strip()) and len(out.comparison_rows) >= 2
    if strategy == "step_by_step":
        return len([s for s in out.steps if s.strip()]) >= 2
    if strategy == "example":
        return bool(out.example.strip())
    if strategy == "visual":
        return len([n for n in out.visual_nodes if n.label.strip()]) >= 2
    return True


def validate_refinement(
    out: RefinementLLMOutput, verification: Verification, original: str, evidence: list[RetrievedChunk]
) -> list[str]:
    issues: list[str] = []
    causes = _allowed_causes(verification)
    if out.root_cause not in causes:
        issues.append(f"root_cause '{out.root_cause}' does not match the detected gaps; use one of {causes}.")
    fit = STRATEGY_FIT.get(out.root_cause, [])
    if out.strategy not in fit:
        issues.append(f"strategy '{out.strategy}' does not fit root_cause '{out.root_cause}'; use one of {fit}.")
    if not _payload_ok(out, out.strategy):
        issues.append(
            f"The '{out.strategy}' strategy needs its own fields: {PAYLOAD_HINTS.get(out.strategy, '')}."
        )
    text = out.improved_content.strip()
    if not text:
        issues.append("improved_content is empty.")
    elif normalize(text) == normalize(original):
        issues.append("improved_content repeats the original unchanged; fix the detected gap.")
    elif len(text.split()) > MAX_WORDS:
        issues.append(f"improved_content is too long ({len(text.split())} words); keep it concise.")
    if evidence:
        unsupported = [x for x in out.evidence_quotes if not any(quote_supported(x, c.text) for c in evidence)]
        if unsupported:
            issues.append(f"{len(unsupported)} evidence_quotes are not copied word for word from the evidence.")
        if not out.evidence_quotes and any(m.evidence_ids for m in verification.misunderstandings):
            issues.append("evidence_quotes is empty; quote the evidence sentences that support the added facts.")
    return issues


def correct_refinement(out: RefinementLLMOutput, verification: Verification, evidence: list[RetrievedChunk],
                       corrections: list[str]) -> RefinementOutput:
    result = RefinementOutput(**out.model_dump())
    causes = _allowed_causes(verification)
    if result.root_cause not in causes:
        corrections.append(f"root_cause {result.root_cause} -> {causes[0]}")
        result.root_cause = causes[0]
    fit = STRATEGY_FIT[result.root_cause]
    if result.strategy not in fit or not _payload_ok(out, result.strategy):
        chosen = next((s for s in fit if _payload_ok(out, s)), "simplification")
        corrections.append(f"strategy {result.strategy} -> {chosen}")
        result.strategy = chosen
        result.strategy_adjusted = True
    if result.strategy != "comparison":
        result.comparison_left_label, result.comparison_right_label, result.comparison_rows = "", "", []
    if result.strategy != "step_by_step":
        result.steps = []
    if result.strategy != "example":
        result.example = ""
    if result.strategy != "visual":
        result.visual_nodes = []

    supported = [x for x in result.evidence_quotes if any(quote_supported(x, c.text) for c in evidence)]
    if len(supported) != len(result.evidence_quotes):
        corrections.append(f"dropped {len(result.evidence_quotes) - len(supported)} unsupported evidence quotes")
    result.evidence_quotes = supported
    ids = [c.evidence_id for c in evidence if any(quote_supported(x, c.text) for x in supported)]
    result.evidence_ids = ids or known_ids(result.evidence_ids, evidence)
    result.explanation_text = render_explanation(result)
    return result


def render_explanation(r: RefinementOutput) -> str:
    parts = [r.improved_content.strip()]
    if r.strategy == "comparison" and r.comparison_rows:
        parts.append(f"{r.comparison_left_label} | {r.comparison_right_label}")
        parts += [f"- {row.aspect}: {row.left} | {row.right}" for row in r.comparison_rows]
    elif r.strategy == "step_by_step":
        parts += [f"{i}. {s}" for i, s in enumerate(r.steps, 1)]
    elif r.strategy == "example" and r.example:
        parts.append(r.example.strip())
    elif r.strategy == "visual" and r.visual_nodes:
        parts.append(" -> ".join(f"{n.label} ({n.detail})" if n.detail else n.label for n in r.visual_nodes))
    return "\n".join(p for p in parts if p)


def run_refinement_agent(
    original_content: str,
    verification: Verification,
    evidence: list[RetrievedChunk],
    target_language: str,
) -> tuple[RefinementOutput, dict]:
    gaps = [
        f"- [{m.gap_type}] The reader understood: {m.user_understood} | Accurate meaning: {m.accurate_meaning}"
        f" | Likely cause: {m.why_it_happened}" + (f" | Confused with: {m.confused_with}" if m.confused_with else "")
        for m in verification.misunderstandings
    ]
    gaps += [f"- [missing_intended_meaning] Did not come across: {c}" for c in verification.missing]
    kept = [f"- {c}" for c in verification.what_arrived]
    cited = {e.evidence_id for e in verification.evidence}
    relevant = [c for c in evidence if c.evidence_id in cited] or evidence

    user = f"""ORIGINAL CONTENT:
\"\"\"{original_content}\"\"\"

AUDIENCE LANGUAGE: {target_language}
{report_rule(target_language)}
Reader-facing fields: improved_content, comparison labels and rows, steps, example and visual_nodes.
Analytical fields: diagnosis, strategy_reason and changes.

DETECTED GAPS TO FIX:
{chr(10).join(gaps) or '- (none)'}

ALREADY ARRIVED (keep these clear):
{chr(10).join(kept) or '- (none)'}

ALLOWED ROOT CAUSES FOR THESE GAPS: {_allowed_causes(verification)}

GAP SUMMARY: {verification.gap_explanation}

TRUSTED EVIDENCE:
{format_evidence(relevant)}

Return the refinement JSON."""
    out, report = call_validated(
        "refinement_agent", SYSTEM_PROMPT, user, RefinementLLMOutput,
        lambda o: validate_refinement(o, verification, original_content, relevant),
    )
    if out.strategy in STRATEGY_FIT.get(out.root_cause, []) and not _payload_ok(out, out.strategy):
        complete_payload(out, relevant, target_language, report["corrections"])
    return correct_refinement(out, verification, relevant, report["corrections"]), report


def complete_payload(out: RefinementLLMOutput, evidence: list[RetrievedChunk], language: str,
                     corrections: list[str]) -> None:
    user = f"""STRATEGY: {out.strategy}
REQUIRED: {PAYLOAD_HINTS[out.strategy]}
AUDIENCE LANGUAGE: {language}

EXPLANATION:
{out.improved_content}

DIAGNOSIS: {out.diagnosis}

TRUSTED EVIDENCE:
{format_evidence(evidence)}

Return the JSON."""
    try:
        payload = get_llm().complete_json(PAYLOAD_PROMPT, user, StrategyPayload)
    except LLMError:
        return
    for field in StrategyPayload.model_fields:
        value = getattr(payload, field)
        if value:
            setattr(out, field, value)
    if _payload_ok(out, out.strategy):
        corrections.append(f"completed missing {out.strategy} fields with a targeted call")
