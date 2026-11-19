"""Time-series forecasting with chronological holdout and recursive multi-step predictions."""
from __future__ import annotations

from datetime import date, timedelta
from math import ceil, pi, sin, cos, sqrt
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error


def _vector(values: list[float], idx: int, weekday: int) -> list[float]:
    last7 = values[idx - 7:idx]
    last14 = values[idx - 14:idx]
    return [
        values[idx - 1],
        values[idx - 7],
        values[idx - 14],
        float(np.mean(last7)),
        float(np.mean(last14)),
        float(np.std(last7)),
        float(np.max(last7)),
        float(np.min(last7)),
        sin(2 * pi * weekday / 7),
        cos(2 * pi * weekday / 7),
        float(idx),
    ]


def predict_demand(
    dates: list[date],
    demand: list[float],
    stock: int,
    lead_days: int,
    horizon: int,
) -> dict:
    """Forecast one SKU; rejects gaps/duplicates to avoid silent temporal leakage."""
    if len(dates) < 28 or len(dates) != len(demand):
        raise ValueError("São necessários pelo menos 28 dias de vendas.")
    if len(set(dates)) != len(dates):
        raise ValueError("Datas duplicadas não são permitidas.")
    if any((dates[i] - dates[i - 1]).days != 1 for i in range(1, len(dates))):
        raise ValueError("O histórico precisa ter um registro por dia, sem lacunas.")
    if any(not np.isfinite(x) or x < 0 for x in demand):
        raise ValueError("As vendas precisam ser números finitos e não negativos.")
    if lead_days > horizon:
        raise ValueError("O horizonte deve ser igual ou maior que o prazo de reposição.")

    x = np.array(
        [_vector(demand, idx, dates[idx].weekday()) for idx in range(14, len(demand))],
        dtype=float,
    )
    y = np.array(demand[14:], dtype=float)
    cut = max(8, int(len(y) * 0.8))
    if cut >= len(y):
        cut = len(y) - 1
    train_x, val_x = x[:cut], x[cut:]
    train_y, val_y = y[:cut], y[cut:]

    def model() -> RandomForestRegressor:
        return RandomForestRegressor(
            n_estimators=96, min_samples_leaf=2, max_features=0.9,
            random_state=42, n_jobs=1,
        )

    evaluator = model()
    evaluator.fit(train_x, train_y)
    validation_pred = np.maximum(0.0, evaluator.predict(val_x))
    mae = float(mean_absolute_error(val_y, validation_pred))
    baseline = float(mean_absolute_error(val_y, val_x[:, 0]))
    improvement = 100 * (baseline - mae) / baseline if baseline > 0 else 0.0

    final_model = model()
    final_model.fit(x, y)
    rolling = list(map(float, demand))
    forecasts = []
    for step in range(horizon):
        future_date = dates[-1] + timedelta(days=step + 1)
        feature = _vector(rolling, len(rolling), future_date.weekday())
        pred = max(0.0, float(final_model.predict(np.array([feature]))[0]))
        forecasts.append(pred)
        rolling.append(pred)

    # Heuristic bands, NOT statistically calibrated prediction intervals.
    points = []
    for i, value in enumerate(forecasts):
        spread = max(mae, value * 0.15) * sqrt((i + 1) / 7 + 1)
        points.append({
            "date": (dates[-1] + timedelta(days=i + 1)).isoformat(),
            "units": round(value, 1),
            "lower_heuristic": round(max(0, value - spread), 1),
            "upper_heuristic": round(value + spread, 1),
        })

    avg_daily = sum(forecasts[:lead_days]) / lead_days
    safety_stock = ceil(max(mae, 1) * sqrt(lead_days) * 1.65)
    reorder_point = ceil(avg_daily * lead_days + safety_stock)
    purchase_suggestion = max(0, reorder_point - stock)

    return {
        "forecast": points,
        "metrics": {
            "validation_days": len(val_y),
            "mae": round(mae, 2),
            "naive_mae": round(baseline, 2),
            "improvement_vs_naive_pct": round(improvement, 1),
        },
        "inventory": {
            "stock": stock,
            "lead_days": lead_days,
            "reorder_point": reorder_point,
            "safety_stock": safety_stock,
            "suggested_purchase": purchase_suggestion,
            "status": "REPOR" if purchase_suggestion else "OK",
            "forecast_demand_in_lead_time": round(sum(forecasts[:lead_days]), 1),
        },
        "methodology": (
            "RandomForest; avaliação com divisão temporal 80/20; baseline último dia. "
            "Faixas são heurísticas, não intervalos de confiança calibrados. "
            "Reposição é sugestão operacional, não decisão automática."
        ),
    }
