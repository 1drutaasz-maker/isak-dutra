from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def make_batches(count=100):
    return [{
        "batch_id": f"L{i:04d}",
        "temperature_c": 40 + (i % 7 - 3) * 0.3,
        "ph": 4.5 + (i % 9 - 4) * 0.025,
        "duration_min": 180 + (i % 13 - 6) * 2,
        "yield_pct": 91 + (i % 11 - 5) * 0.2,
    } for i in range(count)]


def test_anomaly_detected_on_extreme_batch():
    candidate = make_batches(1)[0]
    candidate.update({
        "batch_id": "EXTREMO",
        "temperature_c": 82,
        "ph": 7.8,
        "duration_min": 500,
        "yield_pct": 37,
    })
    response = client.post("/api/analyze", json={
        "reference": make_batches(),
        "candidates": [candidate],
    })
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["summary"]["flagged_batches"] == 1
    assert result["batches"][0]["anomaly"] is True
    assert len(result["batches"][0]["signals"]) == 2


def test_invalid_reference_is_rejected():
    response = client.post("/api/analyze", json={
        "reference": make_batches(10), "candidates": make_batches(1),
    })
    assert response.status_code == 422


def test_normal_candidate_and_repeatability():
    payload = {"reference": make_batches(), "candidates": make_batches(3)}
    a = client.post("/api/analyze", json=payload).json()
    b = client.post("/api/analyze", json=payload).json()
    assert a == b
    assert len(a["batches"]) == 3
    assert client.get("/api/health").json()["status"] == "ok"
