from rag.pipeline import filter_candidates
from rag.schemas import RetrievedChunk


def chunk(doc: str, topic: str, score: float, text: str, idx: int = 0) -> RetrievedChunk:
    return RetrievedChunk.model_validate({
        "chunk_id": f"{doc}#{idx}", "doc_id": doc, "text": text, "relevance_score": score,
        "metadata": {"source_name": "S", "topic": topic, "reference": doc, "language": "en",
                     "review_status": "reviewed"},
    })


def test_rule_based_filters_reject_weak_offconcept_and_duplicate_evidence():
    candidates = [
        chunk("zakat-pillar", "zakat", 0.80, "Zakat is one of the five pillars of Islam and is obligatory."),
        chunk("zakat-pillar", "zakat", 0.78, "Zakat is a pillar; a second chunk of the same document.", 1),
        chunk("zakat-copy", "zakat", 0.77, "Zakat is one of the five pillars of Islam and is obligatory."),
        chunk("sadaqah-smile", "sadaqah", 0.74, "Even a smile is charity and a good deed."),
        chunk("zakat-vs-sadaqah", "sadaqah", 0.72, "Zakat is obligatory while sadaqah is voluntary."),
        chunk("zakat-far", "zakat", 0.60, "Zakat al-Fitr is paid at the end of Ramadan."),
        chunk("zakat-weak", "zakat", 0.40, "Zakat appears here weakly."),
    ]
    passed, decisions = filter_candidates(candidates, "zakat", ["zakat", "الزكاة"])
    by_chunk = {k: d.decision for k, d in decisions.items()}
    assert [c.doc_id for c in passed] == ["zakat-pillar", "zakat-vs-sadaqah"]
    assert by_chunk["zakat-pillar#1"] == "duplicate_document"
    assert by_chunk["zakat-copy#0"] == "duplicate_text"
    assert by_chunk["sadaqah-smile#0"] == "off_concept"
    assert by_chunk["zakat-far#0"] == "below_margin"
    assert by_chunk["zakat-weak#0"] == "below_threshold"


def test_live_index_returns_only_primary_and_related_topics(workflow):
    state = workflow.start("t-rag", "الحج رحلة يقوم بها المسلمون إلى مكة.", "Arabic", "Arabic")
    topics = {c["metadata"]["topic"] for c in state["rag_context"]}
    assert topics == {"hajj"}
    assert len(state["rag_context"]) <= 4
    kept = [d for d in state["rag_decisions"] if d["decision"] == "kept"]
    assert all(d["score"] >= 0.5 for d in kept)
