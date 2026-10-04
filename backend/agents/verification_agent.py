from __future__ import annotations

from agents.base import (
    call_validated,
    format_evidence,
    references_for,
    report_rule,
    supporting_ids,
    unknown_ids,
)
from agents.schemas import (
    EVIDENCE_REQUIRED,
    MISUNDERSTANDING_TYPES,
    ConceptResult,
    EvidenceItem,
    MeaningAnalysis,
    Misunderstanding,
    RejectedClaim,
    ResolutionItem,
    UserInterpretation,
    Verification,
    VerificationLLMOutput,
)
from agents.text import adds_restriction, describes_omission, grounded_in, jaccard
from rag.schemas import RetrievedChunk
from scoring.meaning_alignment import MIN_SCORABLE_SHARE, alignment_score, classify, normalise_weights

ABSTAIN_TEXT = "تعذر التحقق من خلال المصادر المتاحة."

GAP_PRIORITY = ["concept_confusion", "ambiguity_triggered", "distorted_meaning", "missing_intended_meaning"]

SYSTEM_PROMPT = """You are the VERIFICATION AGENT of MA'NA, the reliability layer.

Your question: did the reader understand the meaning THIS CONTENT intended?
You are NOT testing the reader's Islamic knowledge. Background knowledge the content did not state
(obligation, conditions, dates, rituals, distinctions) is never missing. Omitting it is NOT a gap.

For EACH intended concept give exactly one judgement with gap_type:
- "correct_understanding": the reader conveyed this meaning (any wording, even briefly or implicitly).
- "missing_intended_meaning": the reader did not convey this meaning at all.
- "distorted_meaning": the reader contradicts something the content EXPLICITLY states (e.g. the content
  says fasting is obligatory and the reader says it is optional).
- "concept_confusion": the reader equated the term with a DIFFERENT concept (e.g. Hajj = Umrah).
- "ambiguity_triggered": the reader's inaccurate reading concerns something the content did NOT state
  explicitly, but its wording allowed (e.g. the content calls Zakat "charity" or "صدقة" and the reader
  concludes it is optional).
user_understanding: what the reader conveyed about this concept, neutrally.
explanation: one or two sentences citing the reader's words.

misunderstandings: every inaccurate reading the reader expressed, including readings beyond the intended
concepts (e.g. the reader adds "it is optional" while the evidence says it is obligatory). For each give
user_understood, reader_quote (copy the reader's own words that express the inaccurate reading), gap_type, accurate_meaning, why_it_happened ("this wording may lead some readers to..."),
related_concept_id (the intended concept it affects, or ""), confused_with (the other concept, for
concept_confusion), evidence_ids and evidence_quote. Never list omissions as misunderstandings, and never
list the same misunderstanding twice. A reading that is accurate but less complete than the full truth is an
omission, not a misunderstanding, whenever the content itself did not state the missing aspect (e.g. the
content says "Hajj is a journey to Makkah" and the reader says "Hajj is travel to Makkah" without mentioning
worship: that is correct_understanding with no misunderstanding). A concept affected by a misunderstanding cannot be
"correct_understanding".

EVIDENCE RULE: any claim that the reader's reading is religiously inaccurate (concept_confusion,
ambiguity_triggered, or distorted_meaning about a religious fact) must cite evidence_ids AND copy
evidence_quote: one sentence copied word for word from a cited evidence block that directly supports
accurate_meaning. If no evidence block directly supports it, do not make the claim. Evidence that is only
about the same topic but does not state the fact is NOT support.

gap_explanation: a short, respectful summary for the content creator. Do not blame the reader.
No fatwas, no invented sources. Judge meaning, not vocabulary or grammar."""

RETEST_ADDENDUM = """
RE-TEST MODE: the reader has now read a new explanation. previous_resolution: for EACH previous
misunderstanding (by its number) say whether it is "resolved" (gone, accurate meaning now conveyed),
"partially_resolved" (improved but not fully accurate) or "remains" (still present)."""


def _concepts_block(meaning: MeaningAnalysis) -> str:
    return "\n".join(
        f"- {c.id} (weight {c.weight}) {c.concept} | from the content: \"{c.evidence_from_original_content}\""
        for c in meaning.intended_concepts
    )


def _context_block(meaning: MeaningAnalysis) -> str:
    amb = "\n".join(
        f"- \"{a.phrase}\": {a.risk} Possible reading: {a.possible_misunderstanding} "
        f"(evidence: {', '.join(a.evidence_ids)})"
        for a in meaning.potential_ambiguities
    )
    bg = "\n".join(f"- {b.concept} (evidence: {', '.join(b.evidence_ids)})" for b in meaning.background_knowledge)
    return (
        f"POTENTIAL AMBIGUITIES IN THE WORDING:\n{amb or '- (none)'}\n\n"
        f"BACKGROUND KNOWLEDGE (context only, NOT scored):\n{bg or '- (none)'}"
    )


def validate_verification(
    out: VerificationLLMOutput,
    meaning: MeaningAnalysis,
    evidence: list[RetrievedChunk],
    previous_count: int = 0,
    user_response: str = "",
) -> list[str]:
    issues: list[str] = []
    expected = [c.id for c in meaning.intended_concepts]
    given = [j.concept_id.strip().upper() for j in out.judgements]
    missing = [c for c in expected if c not in given]
    extra = [c for c in given if c not in expected]
    dupes = sorted({c for c in given if given.count(c) > 1})
    if missing:
        issues.append(f"Missing judgements for {missing}; give exactly one judgement per intended concept.")
    if extra:
        issues.append(f"Judgements for unknown concept IDs {extra}.")
    if dupes:
        issues.append(f"Several judgements for {dupes}; give exactly one each.")
    for j in out.judgements:
        if j.gap_type in EVIDENCE_REQUIRED and not supporting_ids(j.evidence_ids, j.evidence_quote, evidence):
            issues.append(
                f"Judgement {j.concept_id} ({j.gap_type}) is not supported: copy an evidence_quote word for word "
                "from a cited block that states the accurate meaning, or change the gap type."
            )
    judged = {j.concept_id.strip().upper(): j.gap_type for j in out.judgements}
    for i, m in enumerate(out.misunderstandings, 1):
        if describes_omission(m.user_understood):
            issues.append(
                f"Misunderstanding {i} describes something the reader did not mention. An omission is not a "
                "misunderstanding: remove it, and judge the concept by what the reader actually said."
            )
        if user_response and adds_restriction(m.user_understood, user_response):
            issues.append(
                f"Misunderstanding {i} attributes a restriction (only / merely / فقط / مجرد) that the reader never "
                "stated. Not mentioning a detail the content did not state is an omission: remove it."
            )
        if not grounded_in(m.reader_quote, user_response):
            issues.append(
                f"Misunderstanding {i} has no reader_quote copied from the reader's answer. If the reader did not "
                "actually say something inaccurate, it is an omission: remove it."
            )
        if unknown_ids(m.evidence_ids, evidence):
            issues.append(f"Misunderstanding {i} cites unknown evidence IDs {unknown_ids(m.evidence_ids, evidence)}.")
        if m.gap_type in EVIDENCE_REQUIRED and not supporting_ids(m.evidence_ids, m.evidence_quote, evidence):
            issues.append(
                f"Misunderstanding {i} ({m.gap_type}) has no supporting evidence_quote copied from a cited block; "
                "support it or remove it."
            )
        related = m.related_concept_id.strip().upper()
        if related and related not in expected:
            issues.append(f"Misunderstanding {i} refers to unknown concept {related}.")
        if related and judged.get(related) == "correct_understanding":
            issues.append(
                f"Contradiction: misunderstanding {i} affects {related}, which is judged correct_understanding."
            )
        for k in range(i, len(out.misunderstandings)):
            if jaccard(m.user_understood, out.misunderstandings[k].user_understood) >= 0.75:
                issues.append(f"Misunderstandings {i} and {k + 1} are duplicates; merge them.")
    if previous_count:
        indices = {r.index for r in out.previous_resolution}
        absent = [i for i in range(1, previous_count + 1) if i not in indices]
        if absent:
            issues.append(f"previous_resolution is missing items {absent}.")
    return issues


def run_verification_agent(
    meaning: MeaningAnalysis,
    interpretation: UserInterpretation,
    user_response: str,
    evidence: list[RetrievedChunk],
    language: str,
    content_read: str | None = None,
    previous: list[Misunderstanding] | None = None,
) -> tuple[Verification, dict | None]:
    if not evidence or not meaning.intended_concepts:
        return (
            Verification(status="insufficient_evidence", primary_gap_type="insufficient_evidence",
                         gap_explanation=ABSTAIN_TEXT),
            None,
        )

    previous = previous or []
    retest = ""
    if previous:
        items = "\n".join(
            f"{i}. {m.user_understood} (accurate: {m.accurate_meaning})" for i, m in enumerate(previous, 1)
        )
        retest = f"\nPREVIOUS MISUNDERSTANDINGS (first test):\n{items}\n"
    read = f"\nTHE EXPLANATION THE READER READ THIS TIME:\n\"\"\"{content_read}\"\"\"\n" if content_read else ""

    user = f"""INTENDED CONCEPTS (from the original content, the ONLY things to score):
{_concepts_block(meaning)}

{_context_block(meaning)}
{read}
READER'S ANSWER ({language}):
\"\"\"{user_response}\"\"\"

READER'S INTERPRETATION (from the Understanding Agent):
{interpretation.model_dump_json(indent=1)}
{retest}
TRUSTED EVIDENCE:
{format_evidence(evidence)}

{report_rule()}
Copy evidence_quote exactly as written in the evidence. Return one judgement per intended concept ID."""
    system = SYSTEM_PROMPT + (RETEST_ADDENDUM if previous else "")
    out, report = call_validated(
        "verification_agent", system, user, VerificationLLMOutput,
        lambda o: validate_verification(o, meaning, evidence, len(previous), user_response),
    )
    return build_verification(meaning, out, evidence, previous, report, user_response), report


def build_verification(
    meaning: MeaningAnalysis,
    out: VerificationLLMOutput,
    evidence: list[RetrievedChunk],
    previous: list[Misunderstanding] | None = None,
    report: dict | None = None,
    user_response: str | None = None,
) -> Verification:
    corrections = report["corrections"] if report is not None else []
    concepts = {c.id: c for c in meaning.intended_concepts}
    judgements = {}
    for j in out.judgements:
        judgements.setdefault(j.concept_id.strip().upper(), j)

    results: dict[str, ConceptResult] = {}
    unverified: list[str] = []
    rejected: list[RejectedClaim] = []
    for cid, concept in concepts.items():
        j = judgements.get(cid)
        if j is None:
            unverified.append(concept.concept)
            continue
        ids = supporting_ids(j.evidence_ids, j.evidence_quote, evidence)
        if j.gap_type in EVIDENCE_REQUIRED and not ids:
            unverified.append(concept.concept)
            rejected.append(RejectedClaim(claim=f"{concept.concept}: {j.explanation}", reason="unsupported_by_evidence"))
            continue
        results[cid] = ConceptResult(
            concept_id=cid,
            concept=concept.concept,
            weight=concept.weight,
            gap_type=j.gap_type,
            user_understanding=j.user_understanding,
            explanation=j.explanation,
            evidence_ids=ids,
            evidence_quote=j.evidence_quote if ids else "",
        )

    misunderstandings: list[Misunderstanding] = []
    quotes: dict[str, str] = {}
    unsaid: set[str] = set()
    for m in out.misunderstandings:
        if user_response is not None and not grounded_in(m.reader_quote, user_response):
            rejected.append(RejectedClaim(claim=m.user_understood, reason="not_said_by_reader"))
            unsaid.add(m.related_concept_id.strip().upper())
            continue
        if user_response is not None and adds_restriction(m.user_understood, user_response):
            rejected.append(RejectedClaim(claim=m.user_understood, reason="restriction_not_said"))
            unsaid.add(m.related_concept_id.strip().upper())
            continue
        if describes_omission(m.user_understood):
            rejected.append(RejectedClaim(claim=m.user_understood, reason="omission_not_misunderstanding"))
            unsaid.add(m.related_concept_id.strip().upper())
            continue
        ids = supporting_ids(m.evidence_ids, m.evidence_quote, evidence)
        related = m.related_concept_id.strip().upper()
        related = related if related in results else ""
        if m.gap_type in EVIDENCE_REQUIRED and not ids:
            rejected.append(RejectedClaim(claim=m.user_understood, reason="unsupported_by_evidence"))
            continue
        if m.gap_type == "distorted_meaning" and not ids and not related:
            rejected.append(RejectedClaim(claim=m.user_understood, reason="no_reference_point"))
            continue
        if any(jaccard(m.user_understood, x.user_understood) >= 0.75 for x in misunderstandings):
            corrections.append(f"merged duplicate misunderstanding: {m.user_understood}")
            continue
        for eid in ids:
            quotes.setdefault(eid, m.evidence_quote)
        misunderstandings.append(
            Misunderstanding(
                user_understood=m.user_understood,
                gap_type=m.gap_type,
                accurate_meaning=m.accurate_meaning,
                why_it_happened=m.why_it_happened,
                related_concept_id=related,
                confused_with=m.confused_with,
                evidence_ids=ids,
                evidence_quote=m.evidence_quote if ids else "",
                source_reference=references_for(ids, evidence),
            )
        )
        if related and results[related].gap_type == "correct_understanding":
            corrections.append(f"{related} changed from correct_understanding to {m.gap_type}")
            results[related].gap_type = m.gap_type
            if not results[related].evidence_ids:
                results[related].evidence_ids = ids
                results[related].evidence_quote = m.evidence_quote if ids else ""

    explained = {m.related_concept_id for m in misunderstandings}
    for cid in unsaid - explained:
        r = results.get(cid)
        if r and r.gap_type in MISUNDERSTANDING_TYPES:
            corrections.append(f"{cid} restored to correct_understanding: its only misunderstanding was not said by the reader")
            r.gap_type = "correct_understanding"
            r.evidence_ids = []
    for r in results.values():
        if r.gap_type in MISUNDERSTANDING_TYPES and r.concept_id not in explained:
            misunderstandings.append(
                Misunderstanding(
                    user_understood=r.user_understanding or r.explanation,
                    gap_type=r.gap_type,
                    accurate_meaning=r.concept,
                    why_it_happened=r.explanation,
                    related_concept_id=r.concept_id,
                    evidence_ids=r.evidence_ids,
                    evidence_quote=r.evidence_quote,
                    source_reference=references_for(r.evidence_ids, evidence),
                )
            )

    if not results or len(results) / len(concepts) < MIN_SCORABLE_SHARE:
        return Verification(
            status="insufficient_evidence",
            primary_gap_type="insufficient_evidence",
            unverified_concepts=unverified,
            rejected_claims=rejected,
            gap_explanation=ABSTAIN_TEXT,
            confidence=out.confidence,
        )

    weights = normalise_weights({cid: r.weight for cid, r in results.items()})
    for cid, r in results.items():
        r.weight = weights[cid]
    understood = {cid for cid, r in results.items() if r.gap_type == "correct_understanding"}
    score = alignment_score(weights, understood)
    misunderstood_weight = sum(r.weight for r in results.values() if r.gap_type in MISUNDERSTANDING_TYPES)
    status = classify(score, misunderstood_weight, bool(misunderstandings))

    present = {m.gap_type for m in misunderstandings} | {r.gap_type for r in results.values()}
    primary = next((g for g in GAP_PRIORITY if g in present), "correct_understanding")

    cited = {eid for r in results.values() for eid in r.evidence_ids}
    cited |= {eid for m in misunderstandings for eid in m.evidence_ids}
    cited |= {eid for c in meaning.intended_concepts for eid in c.evidence_ids}
    evidence_items = [
        EvidenceItem(
            evidence_id=c.evidence_id,
            source_name=c.metadata.source_name,
            source_name_ar=c.metadata.source_name_ar,
            reference=c.metadata.reference,
            reference_ar=c.metadata.reference_ar,
            topic=c.metadata.topic,
            supporting_text=c.text,
            supporting_text_ar=c.text_ar,
            relevance_score=c.relevance_score,
            verified_quote=quotes.get(c.evidence_id, ""),
        )
        for c in evidence
        if c.evidence_id in cited
    ]

    resolution: list[ResolutionItem] = []
    if previous:
        by_index = {r.index: r for r in out.previous_resolution}
        for i, m in enumerate(previous, 1):
            r = by_index.get(i)
            status_i = r.status if r else ("remains" if m.gap_type in present else "resolved")
            resolution.append(ResolutionItem(user_understood=m.user_understood, status=status_i, note=r.note if r else ""))

    ordered = [results[cid] for cid in concepts if cid in results]
    return Verification(
        status=status,
        alignment_score=score,
        primary_gap_type=primary,
        concept_results=ordered,
        what_arrived=[r.concept for r in ordered if r.gap_type == "correct_understanding"],
        missing=[r.concept for r in ordered if r.gap_type == "missing_intended_meaning"],
        misunderstandings=misunderstandings,
        unverified_concepts=unverified,
        rejected_claims=rejected,
        evidence=evidence_items,
        gap_explanation=out.gap_explanation,
        previous_resolution=resolution,
        confidence=out.confidence,
    )
