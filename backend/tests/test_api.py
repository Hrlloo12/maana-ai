from fastapi.testclient import TestClient

from main import app


def test_api_end_to_end(workflow):
    with TestClient(app) as client:
        assert client.get("/api/health").json()["vector_index_ready"] is True

        r = client.post("/api/content/analyze", json={"content": "Zakat is a form of charity in Islam."})
        assert r.status_code == 200, r.text
        sid = r.json()["session_id"]
        assert r.json()["stage"] == "awaiting_response"

        r = client.post("/api/content/refine", json={"session_id": sid})
        assert r.status_code == 409 and "المرحلة" in r.json()["detail"]

        r = client.post("/api/understanding/analyze", json={"session_id": sid, "response": "Money you can choose to give."})
        assert r.json()["stage"] == "gap_detected"
        r = client.post("/api/content/refine", json={"session_id": sid}).json()
        assert r["stage"] == "awaiting_retest"
        assert r["refinement"]["strategy"] and r["explanation_text"]
        r = client.post("/api/understanding/retest", json={"session_id": sid, "response": "It is obligatory, not optional."})
        assert r.json()["stage"] == "completed"

        final = client.get(f"/api/session/{sid}").json()["final_result"]
        assert final["after_score"] == 1.0
        assert final["resolution"] == "resolved"
        assert "retrieve_knowledge" in client.get(f"/api/session/{sid}/progress").json()["completed"]

        dash = client.get("/api/dashboard").json()
        assert dash["content_sessions"] >= 1
        assert dash["meaning_gaps_resolved"] >= 1
        assert dash["recent_sessions"][0]["session_id"]
        docs = client.get("/api/sources").json()["documents"]
        assert docs and all(d["source_name_ar"] and d["reference_ar"] for d in docs)
        assert client.get("/api/demo").json()["scenarios"]


def test_api_errors_are_arabic(workflow):
    with TestClient(app) as client:
        r = client.get("/api/session/nope")
        assert r.status_code == 404 and r.json()["detail"] == "الجلسة غير موجودة."
        r = client.post("/api/content/analyze", json={"content": "abc"})
        assert r.status_code == 422 and "المدخلات" in r.json()["detail"]
        r = client.post("/api/understanding/analyze", json={"session_id": "nope", "response": "نص"})
        assert r.status_code == 404
