from datetime import date, timedelta

from fastapi.testclient import TestClient
from app.forecast import predict_demand
from app.main import app

client = TestClient(app)


def sample(n=100):
    origin = date(2026, 1, 1)
    return [
        {"date": (origin + timedelta(days=i)).isoformat(),
         "units": 30 + (i % 7) * 3 + i * 0.1}
        for i in range(n)
    ]


def test_forecast_response_and_business_rules():
    payload = {"sku": "LEITE-001", "history": sample(), "stock": 10,
               "lead_days": 7, "horizon": 14}
    result = client.post("/api/forecast", json=payload)
    assert result.status_code == 200, result.text
    body = result.json()
    assert len(body["forecast"]) == 14
    assert body["forecast"][0]["units"] >= 0
    assert body["inventory"]["suggested_purchase"] > 0
    assert body["inventory"]["status"] == "REPOR"
    assert body["metrics"]["validation_days"] > 0
    assert body["metrics"]["mae"] >= 0


def test_consecutive_dates_required():
    records = sample(60)
    records.pop(10)
    response = client.post("/api/forecast", json={
        "sku": "SKU", "history": records, "stock": 30, "lead_days": 3, "horizon": 7,
    })
    assert response.status_code == 422
    assert "lacunas" in response.json()["detail"]


def test_duplicate_dates_rejected():
    records = sample(60)
    records[1]["date"] = records[0]["date"]
    response = client.post("/api/forecast", json={
        "sku": "SKU", "history": records, "stock": 30, "lead_days": 3, "horizon": 7,
    })
    assert response.status_code == 422


def test_stock_sufficient():
    records = sample(80)
    response = client.post("/api/forecast", json={
        "sku": "SKU", "history": records, "stock": 9999, "lead_days": 2, "horizon": 7,
    })
    assert response.status_code == 200
    assert response.json()["inventory"]["status"] == "OK"
    assert response.json()["inventory"]["suggested_purchase"] == 0


def test_validation():
    response = client.post("/api/forecast", json={
        "sku": "SKU", "history": sample(80), "stock": -1,
        "lead_days": 8, "horizon": 7,
    })
    assert response.status_code == 422


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"
