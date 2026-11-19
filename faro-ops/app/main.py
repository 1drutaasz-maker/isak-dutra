"""FARO Ops REST API and single-page dashboard."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from .forecast import predict_demand

app = FastAPI(title="FARO Ops", version="1.0.0", description="AI-powered demand planning")


class Sale(BaseModel):
    date: date
    units: float = Field(ge=0, le=1_000_000)


class ForecastRequest(BaseModel):
    sku: str = Field(min_length=1, max_length=80)
    history: list[Sale] = Field(min_length=28, max_length=2000)
    stock: int = Field(ge=0, le=10_000_000)
    lead_days: int = Field(ge=1, le=30)
    horizon: int = Field(ge=1, le=30)

    @field_validator("sku")
    @classmethod
    def clean_sku(cls, sku: str) -> str:
        if not sku.strip():
            raise ValueError("SKU não pode ficar vazio.")
        return sku.strip()


@app.get("/api/health")
def health() -> dict:
    return {"service": "faro-ops", "status": "ok"}


@app.post("/api/forecast")
def forecast(payload: ForecastRequest) -> dict:
    ordered = sorted(payload.history, key=lambda row: row.date)
    try:
        result = predict_demand(
            [s.date for s in ordered],
            [s.units for s in ordered],
            payload.stock, payload.lead_days, payload.horizon,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"sku": payload.sku, **result}


ROOT = Path(__file__).resolve().parent.parent
app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(ROOT / "web" / "index.html")
