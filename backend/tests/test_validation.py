from agents.meaning_agent import validate_meaning
from agents.refinement_agent import validate_refinement
from agents.schemas import (
    ConceptJudgement,
    IntendedConcept,
    MeaningAnalysis,
    Misunderstanding,
    RefinementLLMOutput,
    Verification,
    VerificationLLMOutput,
)
from agents.text import grounded_in, is_yes_no_question, mentions_any, normalize, quote_supported
from agents.understanding_agent import validate_understanding
from agents.verification_agent import build_verification, validate_verification
from agents.schemas import UserInterpretation
from rag.schemas import RetrievedChunk

TEXT = "Zakat is one of the five pillars of Islam. It is an obligatory act of worship, not a voluntary donation."


def chunk(text: str = TEXT, eid: str = "E1") -> RetrievedChunk:
    return RetrievedChunk.model_validate({
        "chunk_id": f"c-{eid}", "doc_id": f"d-{eid}", "text": text, "evidence_id": eid, "relevance_score": 0.8,
        "metadata": {"source_name": "S", "topic": "zakat", "reference": "Q 9:60", "language": "en",
                     "review_status": "reviewed"},
    })


def meaning(*concepts: str) -> MeaningAnalysis:
    return MeaningAnalysis(
        topic="الزكاة", understanding_question="بكلماتك، ماذا فهمت؟",
        intended_concepts=[IntendedConcept(id=f"C{i}", concept=c, evidence_from_original_content="a form of charity",
                                           weight=1 / len(concepts)) for i, c in enumerate(concepts, 1)],
    )


def test_arabic_normalisation_and_grounding():
    assert normalize("الزَّكَاةُ فريضةٌ") == normalize("الزكاة فريضه")
    assert grounded_in("رحلة يقوم بها المسلمون", "الحج رحلةٌ يقوم بها المسلمون إلى مكة.")
    assert not grounded_in("obligatory once a year", "Zakat is a form of charity in Islam.")
    assert quote_supported("It is an obligatory act of worship", TEXT)
    assert not quote_supported("Zakat is optional for Muslims", TEXT)
    assert not quote_supported("obligatory", TEXT)
    assert mentions_any("الحج والعمرة", ["العمرة"]) and not mentions_any("الحج", ["umrah"])
    assert is_yes_no_question("هل الزكاة واجبة؟") and not is_yes_no_question("ماذا فهمت؟")


def test_meaning_validator_flags_ungrounded_duplicate_and_unsupported():
    a = MeaningAnalysis.model_validate({
        "topic": "الزكاة", "understanding_question": "Is Zakat obligatory?",
        "intended_concepts": [
            {"concept": "الزكاة نوع من العطاء", "evidence_from_original_content": "a form of charity"},
            {"concept": "الزكاة نوع من العطاء", "evidence_from_original_content": "a form of charity"},
            {"concept": "الزكاة لها نصاب", "evidence_from_original_content": "nisab threshold"},
        ],
        "background_knowledge": [{"concept": "x", "evidence_ids": ["E1"], "evidence_quote": "made up sentence here"}],
    })
    issues = " ".join(validate_meaning(a, "Zakat is a form of charity in Islam.", [chunk()]))
    assert "not in the original content" in issues
    assert "repeat the same idea" in issues
    assert "not supported" in issues
    assert "yes/no" in issues


def test_understanding_validator_rejects_judgements():
    out = UserInterpretation(user_interpretation=["فهم القارئ خاطئ"])
    assert validate_understanding(out, "الزكاة تبرع اختياري")
    assert not validate_understanding(UserInterpretation(user_interpretation=["يرى أنها تبرع"]), "الزكاة تبرع اختياري")


def test_verification_validator_detects_inconsistency():
    out = VerificationLLMOutput.model_validate({
        "judgements": [{"concept_id": "C1", "gap_type": "correct_understanding", "explanation": "x"},
                       {"concept_id": "C1", "gap_type": "correct_understanding", "explanation": "x"}],
        "misunderstandings": [{"user_understood": "optional", "gap_type": "ambiguity_triggered",
                               "accurate_meaning": "obligatory", "why_it_happened": "charity",
                               "related_concept_id": "C1", "evidence_ids": ["E7"]}],
    })
    issues = " ".join(validate_verification(out, meaning("giving", "islam"), [chunk()], previous_count=1))
    assert "Missing judgements for ['C2']" in issues
    assert "Several judgements" in issues
    assert "unknown evidence" in issues
    assert "no supporting evidence_quote" in issues
    assert "Contradiction" in issues
    assert "previous_resolution is missing" in issues


def test_misunderstanding_needs_verbatim_support():
    out = VerificationLLMOutput.model_validate({
        "judgements": [ConceptJudgement(concept_id="C1", gap_type="correct_understanding", explanation="x").model_dump()],
        "misunderstandings": [{"user_understood": "optional", "gap_type": "ambiguity_triggered",
                               "accurate_meaning": "obligatory", "why_it_happened": "charity",
                               "related_concept_id": "C1", "evidence_ids": ["E1"],
                               "evidence_quote": "Zakat is recommended but optional"}],
    })
    v = build_verification(meaning("giving"), out, [chunk()])
    assert v.misunderstandings == []
    assert v.rejected_claims[0].reason == "unsupported_by_evidence"
    assert v.status == "understood"

    out.misunderstandings[0].evidence_quote = "It is an obligatory act of worship, not a voluntary donation."
    v = build_verification(meaning("giving"), out, [chunk()])
    assert v.concept_results[0].gap_type == "ambiguity_triggered"
    assert v.alignment_score == 0.0 and v.status == "major_gap"
    assert v.evidence[0].verified_quote


def test_refinement_validator_enforces_strategy_fit_and_evidence():
    verification = Verification(status="major_gap", misunderstandings=[Misunderstanding(
        user_understood="الحج هو العمرة", gap_type="concept_confusion", accurate_meaning="مختلفان",
        why_it_happened="رحلة", confused_with="العمرة", evidence_ids=["E1"])])
    out = RefinementLLMOutput(root_cause="ambiguous_wording", diagnosis="d", strategy="example", strategy_reason="r",
                              improved_content="الحج رحلة يقوم بها المسلمون إلى مكة.",
                              evidence_quotes=["invented quote text here"])
    issues = " ".join(validate_refinement(out, verification, "الحج رحلة يقوم بها المسلمون إلى مكة.", [chunk()]))
    assert "does not match the detected gaps" in issues
    assert "'example' strategy needs its own fields" in issues
    assert "repeats the original" in issues
    assert "not copied word for word" in issues


def test_misunderstanding_not_said_by_reader_is_rejected():
    out = VerificationLLMOutput.model_validate({
        "judgements": [ConceptJudgement(concept_id="C1", gap_type="correct_understanding", explanation="x").model_dump()],
        "misunderstandings": [{"user_understood": "الحج مجرد سفر عادي", "gap_type": "ambiguity_triggered",
                               "reader_quote": "الحج سياحة وترفيه", "accurate_meaning": "عبادة",
                               "related_concept_id": "C1", "evidence_ids": ["E1"],
                               "evidence_quote": "It is an obligatory act of worship, not a voluntary donation."}],
    })
    v = build_verification(meaning("giving"), out, [chunk()], user_response="الحج سفر المسلمين إلى مكة.")
    assert v.misunderstandings == [] and v.status == "understood"
    assert v.rejected_claims[0].reason == "not_said_by_reader"


def test_restriction_the_reader_never_stated_is_rejected():
    from agents.text import adds_restriction
    assert adds_restriction("الظن أن الصوم يقتصر على ترك الطعام فقط", "Muslims don't eat or drink from dawn to sunset.")
    assert adds_restriction("Hajj is merely a trip", "Hajj is travel to Makkah.")
    assert not adds_restriction("الزكاة اختيارية", "الزكاة تبرع إذا أراد")
    assert not adds_restriction("الصدقة مال فقط", "الصدقة مال فقط ولا شيء غيره")
    out = VerificationLLMOutput.model_validate({
        "judgements": [ConceptJudgement(concept_id="C1", gap_type="correct_understanding", explanation="x").model_dump()],
        "misunderstandings": [{"user_understood": "الظن أن الصوم يقتصر على ترك الطعام فقط", "gap_type": "ambiguity_triggered",
                               "reader_quote": "don't eat or drink", "accurate_meaning": "x",
                               "evidence_ids": ["E1"],
                               "evidence_quote": "It is an obligatory act of worship, not a voluntary donation."}],
    })
    v = build_verification(meaning("giving"), out, [chunk()], user_response="Muslims don't eat or drink from dawn to sunset.")
    assert v.misunderstandings == [] and v.status == "understood"
    assert v.rejected_claims[0].reason == "restriction_not_said"


def test_broken_escapes_are_retried_before_repair():
    import json
    import pytest
    from llm.client import _extract_json
    bad = '{"a": "x ' + chr(92) + 'u06 y"}'
    with pytest.raises(json.JSONDecodeError):
        _extract_json(bad)
    assert _extract_json(bad, repair=True)["a"].startswith("x ")


def test_concept_is_restored_when_its_only_misunderstanding_was_not_said():
    out = VerificationLLMOutput.model_validate({
        "judgements": [{"concept_id": "C1", "gap_type": "distorted_meaning", "explanation": "x"}],
        "misunderstandings": [{"user_understood": "الصوم يقتصر على ترك الطعام فقط", "gap_type": "distorted_meaning",
                               "reader_quote": "don't eat or drink", "accurate_meaning": "x",
                               "related_concept_id": "C1"}],
    })
    v = build_verification(meaning("fasting"), out, [chunk()], user_response="Muslims don't eat or drink from dawn to sunset.")
    assert v.concept_results[0].gap_type == "correct_understanding"
    assert v.alignment_score == 1.0 and v.status == "understood"
