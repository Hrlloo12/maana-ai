from __future__ import annotations

from agents.base import (
    call_validated,
    format_evidence,
    known_ids,
    references_for,
    report_rule,
    supporting_ids,
    unknown_ids,
)
from agents.schemas import MeaningAnalysis
from agents.text import grounded_in, is_yes_no_question, jaccard
from rag.schemas import RetrievedChunk
from scoring.meaning_alignment import normalise_weights

MAX_INTENDED = 4
DUPLICATE_SIMILARITY = 0.75

SYSTEM_PROMPT = """You are the MEANING AGENT of MA'NA. MA'NA checks whether the meaning a creator INTENDED with
a specific piece of Islamic content actually reached the audience. It is NOT a quiz about the reader's
Islamic knowledge.

Produce:
1. topic — a short name of the content's subject.

2. intended_concepts — ONLY what the original content itself says or strongly implies.
   - 1-4 distinct meanings (short content usually has 1-2). Never list the same idea twice, and never merge
     two ideas the content states separately (e.g. "Sadaqah is voluntary; even a smile can be sadaqah" has
     two concepts: that it is voluntary, and that non-material acts such as a smile count).
   - evidence_from_original_content: copy the exact words of the content that carry the concept.
   - weight: relative importance within the content; weights sum to 1.0.
   - evidence_ids: evidence IDs that confirm the concept is accurate, if any.
   - NEVER add facts the content does not state (obligation, conditions, dates, rituals, rulings,
     distinctions) just because they are true or appear in the evidence. Those go to background_knowledge.
   Example: "Hajj is a journey Muslims make to Makkah." -> intended: "Hajj involves Muslims travelling to
   Makkah". NOT intended: "Hajj is obligatory", "Hajj has a fixed time", "Hajj differs from Umrah".

3. background_knowledge — facts from the TRUSTED EVIDENCE that help verify or explain THIS concept.
   Each item cites evidence_ids and copies evidence_quote: one sentence copied word for word from the cited
   evidence that states the fact. Context only: the reader is never expected to mention it.

4. potential_ambiguities — wording that is acceptable but easy to misunderstand. Give the phrase, the risk,
   the possible misunderstanding, evidence_ids and an evidence_quote copied word for word from the evidence
   showing why that reading would be inaccurate. Use careful wording and never say the content is wrong.

5. understanding_question — ONE open, neutral question asking the reader to explain the content in their
   own words. It must not be a yes/no question and must not reveal, hint at or presuppose any answer.

Use only the evidence for background and ambiguity claims. No rulings or fatwas."""


def validate_meaning(analysis: MeaningAnalysis, content: str, evidence: list[RetrievedChunk]) -> list[str]:
    issues: list[str] = []
    concepts = analysis.intended_concepts
    if not concepts:
        issues.append("intended_concepts is empty: list the meaning(s) the content itself states.")
    if len(concepts) > MAX_INTENDED:
        issues.append(f"Too many intended_concepts ({len(concepts)}); keep at most {MAX_INTENDED}.")
    for i, c in enumerate(concepts, 1):
        if not grounded_in(c.evidence_from_original_content, content):
            issues.append(
                f"Intended concept {i} ('{c.concept}') quotes '{c.evidence_from_original_content}', which is not "
                "in the original content. Intended concepts must come from the content; move facts that only "
                "appear in the evidence to background_knowledge."
            )
        if unknown_ids(c.evidence_ids, evidence):
            issues.append(f"Intended concept {i} cites unknown evidence IDs {unknown_ids(c.evidence_ids, evidence)}.")
        for j in range(i, len(concepts)):
            if jaccard(c.concept, concepts[j].concept) >= DUPLICATE_SIMILARITY:
                issues.append(f"Intended concepts {i} and {j + 1} repeat the same idea; merge them.")
    for kind, items in (("background_knowledge", analysis.background_knowledge),
                        ("potential_ambiguities", analysis.potential_ambiguities)):
        for i, item in enumerate(items, 1):
            if not supporting_ids(item.evidence_ids, item.evidence_quote, evidence):
                issues.append(
                    f"{kind} item {i} is not supported: evidence_quote must be copied word for word from one of "
                    "its cited evidence blocks. Drop the item if no evidence states it."
                )
    if not analysis.understanding_question.strip():
        issues.append("understanding_question is empty.")
    elif is_yes_no_question(analysis.understanding_question):
        issues.append("understanding_question is a yes/no question; ask an open question instead.")
    return issues


def run_meaning_agent(
    content: str, target_language: str, evidence: list[RetrievedChunk]
) -> tuple[MeaningAnalysis, dict]:
    user = f"""ORIGINAL CONTENT SUBMITTED BY THE CREATOR:
\"\"\"{content}\"\"\"

AUDIENCE LANGUAGE: {target_language}
{report_rule(target_language)}
The understanding_question is addressed to the reader. Copy evidence_from_original_content exactly as
written in the content, and copy evidence_quote exactly as written in the evidence.

TRUSTED EVIDENCE:
{format_evidence(evidence)}

Return the meaning analysis JSON."""
    analysis, report = call_validated(
        "meaning_agent", SYSTEM_PROMPT, user, MeaningAnalysis,
        lambda a: validate_meaning(a, content, evidence),
    )
    return post_process(analysis, content, evidence, report), report


def post_process(
    analysis: MeaningAnalysis, content: str, evidence: list[RetrievedChunk], report: dict | None = None
) -> MeaningAnalysis:
    corrections = report["corrections"] if report is not None else []
    kept = []
    for c in analysis.intended_concepts:
        if not c.concept.strip():
            continue
        if not grounded_in(c.evidence_from_original_content, content):
            corrections.append(f"dropped ungrounded intended concept: {c.concept}")
            continue
        if any(jaccard(c.concept, k.concept) >= DUPLICATE_SIMILARITY for k in kept):
            corrections.append(f"dropped duplicate intended concept: {c.concept}")
            continue
        kept.append(c)
    analysis.intended_concepts = kept[:MAX_INTENDED]
    for i, concept in enumerate(analysis.intended_concepts, start=1):
        concept.id = f"C{i}"
        concept.evidence_ids = known_ids(concept.evidence_ids, evidence)
        concept.source_reference = references_for(concept.evidence_ids, evidence)
    weights = normalise_weights({c.id: c.weight for c in analysis.intended_concepts})
    for concept in analysis.intended_concepts:
        concept.weight = weights[concept.id]

    for name in ("background_knowledge", "potential_ambiguities"):
        valid = []
        for item in getattr(analysis, name):
            ids = supporting_ids(item.evidence_ids, item.evidence_quote, evidence)
            if not ids:
                corrections.append(f"dropped unsupported {name} item")
                continue
            item.evidence_ids = ids
            item.source_reference = references_for(ids, evidence)
            valid.append(item)
        setattr(analysis, name, valid)
    return analysis
