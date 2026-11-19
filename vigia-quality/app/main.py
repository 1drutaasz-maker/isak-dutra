"""Unsupervised quality monitoring: IsolationForest + explanatory robust deviations."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

app = FastAPI(title="VIGIA Quality", version="1.0.0",
              description="Batch quality anomaly screening (not compliance certification)")


class Batch(BaseModel):
    batch_id: str = Field(min_length=1, max_length=50)
    temperature_c: float = Field(ge=-40, le=250)
    ph: float = Field(ge=0, le=14)
    duration_min: float = Field(ge=0, le=10000)
    yield_pct: float = Field(ge=0, le=100)


class AnalyzeRequest(BaseModel):
    reference: list[Batch] = Field(min_length=50, max_length=5000)
    candidates: list[Batch] = Field(min_length=1, max_length=1000)
    sensitivity: float = Field(default=0.08, ge=0.02, le=0.25)


FIELDS = [
    ("temperature_c", "Temperatura"),
    ("ph", "pH"),
    ("duration_min", "Tempo de processo"),
    ("yield_pct", "Rendimento"),
]


def vectors(batches: list[Batch]) -> np.ndarray:
    return np.asarray(
        [[getattr(batch, field) for field, _ in FIELDS] for batch in batches],
        dtype=float,
    )


@app.get("/api/health")
def health() -> dict:
    return {"service": "vigia-quality", "status": "ok"}


@app.post("/api/analyze")
def analyze(payload: AnalyzeRequest) -> dict:
    reference = vectors(payload.reference)
    candidates = vectors(payload.candidates)

    # Unsupervised baseline: train ONLY on the provided reference batches.
    scaler = StandardScaler().fit(reference)
    detector = IsolationForest(
        n_estimators=160, contamination=payload.sensitivity,
        random_state=42, n_jobs=1,
    ).fit(scaler.transform(reference))
    predictions = detector.predict(scaler.transform(candidates))
    decision = detector.decision_function(scaler.transform(candidates))

    medians = np.median(reference, axis=0)
    mad = np.median(np.abs(reference - medians), axis=0)
    # Robust deviation indicators explain unusual dimensions, not model attribution.
    robust_scale = np.maximum(mad * 1.4826, [0.2, 0.05, 3.0, 0.5])

    results = []
    for row, predicted, score, original in zip(
        candidates, predictions, decision, payload.candidates
    ):
        deviations = np.abs((row - medians) / robust_scale)
        signals = [
            {"metric": FIELDS[int(i)][1], "deviation": round(float(deviations[i]), 2)}
            for i in np.argsort(deviations)[::-1][:2]
        ]
        results.append({
            "batch_id": original.batch_id,
            "anomaly": bool(predicted == -1),
            "decision_score": round(float(score), 4),
            "signals": signals,
            "measurements": original.model_dump(),
        })
    count = sum(int(row["anomaly"]) for row in results)
    return {
        "summary": {
            "reference_batches": len(reference),
            "analyzed_batches": len(candidates),
            "flagged_batches": count,
            "flagged_rate_pct": round(100 * count / len(candidates), 1),
            "sensitivity": payload.sensitivity,
        },
        "batches": results,
        "methodology": (
            "IsolationForest não supervisionado treinado com lotes de referência; "
            "desvios robustos indicam dimensões incomuns, sem explicar causalmente o modelo. "
            "Sinalização estatística NÃO equivale a reprovação sanitária ou laudo de qualidade."
        ),
    }


ROOT = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(ROOT / "web" / "index.html")
