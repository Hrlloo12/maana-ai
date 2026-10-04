from agents.schemas import MeaningAnalysis
from llm.client import LLMClient, set_llm
from tests.conftest import FakeBackend

HAJJ = "الحج رحلة يقوم بها المسلمون إلى مكة."
ZAKAT = "Zakat is a form of charity in Islam."


def test_hajj_correct_paraphrase_is_not_penalised_for_background(workflow, fake_llm):
    sid = "t-hajj-ok"
    state = workflow.start(sid, HAJJ, "Arabic", "Arabic")
    meaning = state["meaning_analysis"]
    assert [c["concept"] for c in meaning["intended_concepts"]] == ["الحج رحلة المسلمين إلى مكة"]
    assert meaning["intended_concepts"][0]["weight"] == 1.0
    assert meaning["background_knowledge"]

    state = workflow.submit_response(sid, "الحج يعني أن المسلمين يذهبون إلى مكة.")
    v = state["verification"]
    assert v["status"] == "understood"
    assert v["alignment_score"] == 1.0
    assert v["missing"] == [] and v["misunderstandings"] == []
    assert workflow.stage(sid) == "completed"
    assert "refinement" not in fake_llm.calls


def test_hajj_confused_with_umrah_uses_comparison_and_is_resolved(workflow):
    sid = "t-hajj-umrah"
    workflow.start(sid, HAJJ, "Arabic", "Arabic")
    state = workflow.submit_response(sid, "الحج هو العمرة.")
    v = state["verification"]
    assert v["primary_gap_type"] == "concept_confusion"
    assert v["status"] == "major_gap"
    m = v["misunderstandings"][0]
    assert m["evidence_ids"] and m["source_reference"] and m["evidence_quote"]
    assert m["confused_with"] == "العمرة"
    assert any(e["verified_quote"] for e in v["evidence"])
    assert workflow.stage(sid) == "gap_detected"

    state = workflow.refine(sid)
    r = state["refinement"]
    assert r["root_cause"] == "concept_confusion"
    assert r["strategy"] == "comparison"
    assert len(r["comparison_rows"]) == 2
    assert "العمرة" in state["explanation_text"]

    state = workflow.submit_retest(sid, "الحج عبادة لها وقت محدد، وليس هو العمرة.")
    final = state["final_result"]
    assert final["explanation_strategy"] == "comparison"
    assert final["resolution"] == "resolved"
    assert final["after_score"] > final["before_score"]


def test_zakat_ambiguity_triggered_refine_and_retest(workflow, fake_llm):
    sid = "t-zakat"
    state = workflow.start(sid, ZAKAT, "English", "English")
    assert state["rag_primary_topic"] == "الزكاة"
    assert 0 < len(state["rag_context"]) <= 4
    assert all(c["metadata"]["topic"] in {"quran", "bukhari", "muslim"} for c in state["rag_context"])
    assert state["meaning_analysis"]["potential_ambiguities"][0]["phrase"] == "charity"

    state = workflow.submit_response(sid, "It is an optional donation you can choose to give.")
    v = state["verification"]
    assert v["primary_gap_type"] == "ambiguity_triggered"
    assert v["status"] in {"partial_gap", "major_gap"}
    assert v["misunderstandings"][0]["user_understood"] == "الزكاة اختيارية"

    state = workflow.refine(sid)
    assert workflow.stage(sid) == "awaiting_retest"
    assert state["refinement"]["strategy"] == "comparison"
    assert not state["refinement"]["strategy_adjusted"]
    assert state["refinement"]["evidence_quotes"]
    assert state["follow_up_question"] == state["understanding_question"]

    state = workflow.submit_retest(sid, "Zakat is not optional; it is an obligatory form of giving in Islam.")
    assert workflow.stage(sid) == "completed"
    final = state["final_result"]
    assert final["after_score"] == 1.0 > final["before_score"]
    assert final["resolution"] == "resolved"
    assert "الزكاة اختيارية" in final["resolved_gaps"]
    assert final["sources_used"]
    assert fake_llm.calls == ["planner", "grader", "meaning", "understanding", "verification", "refinement",
                              "understanding", "verification"]
    assert {e["agent"] for e in state["validation_log"]} == {
        "meaning_agent", "understanding_agent", "verification_agent", "refinement_agent"}


def test_zakat_paraphrase_without_background_scores_high(workflow):
    sid = "t-zakat-ok"
    workflow.start(sid, ZAKAT, "English", "English")
    state = workflow.submit_response(sid, "Zakat is a form of giving in Islam.")
    assert state["verification"]["status"] == "understood"
    assert state["verification"]["alignment_score"] == 1.0


def test_out_of_scope_content_abstains_with_arabic_message(workflow, fake_llm):
    sid = "t-abstain"
    state = workflow.start(sid, "Listening to music is forbidden in Islam.", "English", "English")
    assert workflow.stage(sid) == "abstained"
    assert state["abstention"]["message"] == "تعذر التحقق من خلال المصادر المتاحة."
    assert state["abstention"]["reason_code"] == "no_covered_topic"
    assert "meaning" not in fake_llm.calls


def test_all_evidence_judged_irrelevant_abstains(workflow):
    set_llm(LLMClient(FakeBackend(irrelevant_grades=True)))
    state = workflow.start("t-irrelevant", ZAKAT, "English", "English")
    assert workflow.stage("t-irrelevant") == "abstained"
    assert state["abstention"]["reason_code"] == "no_relevant_evidence"
    assert {d["decision"] for d in state["rag_decisions"]} >= {"judged_irrelevant"}


def test_invented_citations_and_unsupported_background_are_dropped(workflow):
    set_llm(LLMClient(FakeBackend(invent_citation=True)))
    state = workflow.start("t-cite", ZAKAT, "English", "English")
    meaning = MeaningAnalysis.model_validate(state["meaning_analysis"])
    retrieved = {c["evidence_id"] for c in state["rag_context"]}
    for item in [*meaning.intended_concepts, *meaning.background_knowledge]:
        assert "E99" not in item.evidence_ids
        assert set(item.evidence_ids) <= retrieved
    assert [b.concept for b in meaning.background_knowledge] == ["الزكاة فريضة بشروط"]
    assert abs(sum(c.weight for c in meaning.intended_concepts) - 1.0) < 1e-3
    log = state["validation_log"][0]
    assert log["agent"] == "meaning_agent" and log["attempts"] == 2 and log["issues_first"]


def test_background_fact_cannot_become_intended_meaning(workflow):
    backend = FakeBackend(ungrounded_concept=True)
    set_llm(LLMClient(backend))
    state = workflow.start("t-ground", ZAKAT, "English", "English")
    concepts = [c["concept"] for c in state["meaning_analysis"]["intended_concepts"]]
    assert "الزكاة فريضة لها نصاب" not in concepts
    assert len(concepts) == 2
    assert backend.calls.count("meaning") == 2
    assert any("ungrounded" in c for c in state["validation_log"][0]["corrections"])


def test_unsupported_confusion_claim_is_rejected(workflow):
    set_llm(LLMClient(FakeBackend(unsourced_confusion=True)))
    workflow.start("t-nosrc", HAJJ, "Arabic", "Arabic")
    state = workflow.submit_response("t-nosrc", "الحج هو العمرة.")
    v = state["verification"]
    assert v["status"] == "insufficient_evidence"
    assert v["misunderstandings"] == []
    assert v["rejected_claims"]
    assert workflow.stage("t-nosrc") == "abstained"


def test_incompatible_strategy_is_corrected(workflow):
    set_llm(LLMClient(FakeBackend(bad_strategy=True)))
    workflow.start("t-strategy", HAJJ, "Arabic", "Arabic")
    workflow.submit_response("t-strategy", "الحج هو العمرة.")
    state = workflow.refine("t-strategy")
    r = state["refinement"]
    assert r["root_cause"] == "concept_confusion"
    assert r["strategy_adjusted"] is True
    assert r["strategy"] == "simplification"
    log = [e for e in state["validation_log"] if e["agent"] == "refinement_agent"][0]
    assert log["attempts"] == 2 and log["issues_final"]


def test_missing_strategy_fields_are_completed(workflow):
    backend = FakeBackend(empty_payload=True)
    set_llm(LLMClient(backend))
    workflow.start("t-payload", HAJJ, "Arabic", "Arabic")
    workflow.submit_response("t-payload", "الحج هو العمرة.")
    state = workflow.refine("t-payload")
    r = state["refinement"]
    assert r["strategy"] == "comparison" and not r["strategy_adjusted"]
    assert len(r["comparison_rows"]) == 2
    assert backend.calls.count("payload") == 1
