from scoring.meaning_alignment import alignment_score, classify, improvement_points, normalise_weights, overall_resolution


def test_weights_sum_to_one():
    w = normalise_weights({"C1": 3, "C2": 2, "C3": 1})
    assert abs(sum(w.values()) - 1.0) < 1e-3
    assert w["C1"] > w["C2"] > w["C3"]
    assert normalise_weights({"C1": 0, "C2": 0}) == {"C1": 0.5, "C2": 0.5}


def test_score_is_sum_of_understood_weights():
    w = normalise_weights({"C1": 0.5, "C2": 0.25, "C3": 0.25})
    assert alignment_score(w, {"C2", "C3"}) == 0.5
    assert alignment_score(w, {"C1", "C2", "C3"}) == 1.0


def test_classification_rules():
    assert classify(1.0, 0.0, False) == "understood"
    assert classify(1.0, 0.0, True) == "partial_gap"
    assert classify(0.7, 0.3, True) == "partial_gap"
    assert classify(0.5, 0.5, True) == "major_gap"
    assert classify(0.3, 0.0, False) == "major_gap"
    assert improvement_points(0.4, 1.0) == 60


def test_overall_resolution():
    assert overall_resolution([]) is None
    assert overall_resolution(["resolved", "resolved"]) == "resolved"
    assert overall_resolution(["remains"]) == "remains"
    assert overall_resolution(["resolved", "remains"]) == "partially_resolved"
