from __future__ import annotations

import json

import numpy as np
import pandas as pd

from app.insights import build_suggestions, generate_insights
from app.profiling import profile_dataframe


def _frame() -> pd.DataFrame:
    rng = np.random.default_rng(3)
    dates = pd.date_range("2024-01-01", periods=120, freq="D")
    trend = np.arange(120) * 3.5
    noise = rng.normal(0, 12, 120)
    revenue = 100 + trend + noise
    profit = revenue * 0.22 + rng.normal(0, 4, 120)
    region = rng.choice(["华东", "华北", "华南"], size=120, p=[0.5, 0.3, 0.2])
    score = rng.normal(4, 0.5, 120)
    score[:12] = np.nan
    return pd.DataFrame(
        {
            "date": dates,
            "region": region,
            "revenue": revenue,
            "profit": profit,
            "score": score,
        }
    )


def test_profile_and_insights() -> None:
    frame = _frame()
    profile = profile_dataframe(frame)
    assert profile["rows"] == 120
    assert profile["columns"] == 5
    columns = {column["name"]: column for column in profile["columns_detail"]}
    assert columns["date"]["kind"] == "datetime"
    assert columns["revenue"]["kind"] == "number"
    assert columns["score"]["missing"] == 12

    insights = generate_insights(frame, profile)
    kinds = {insight["kind"] for insight in insights}
    assert "overview" in kinds
    assert "trend" in kinds
    assert "correlation" in kinds
    assert "category" in kinds
    assert len(insights) <= 8
    json.dumps(insights, ensure_ascii=False)
    assert build_suggestions(profile)


def test_profile_detects_id_and_dates() -> None:
    frame = pd.DataFrame(
        {
            "customer_id": [f"C{index:05d}" for index in range(30)],
            "created_at": pd.date_range("2025-01-01", periods=30, freq="D"),
            "amount": np.linspace(10, 300, 30),
            "segment": ["A", "B"] * 15,
        }
    )
    profile = profile_dataframe(frame)
    columns = {column["name"]: column for column in profile["columns_detail"]}
    assert columns["customer_id"]["semantic"] == "id"
    assert columns["created_at"]["kind"] == "datetime"
    assert columns["amount"]["is_measure"] is True
    assert columns["segment"]["is_dimension"] is True

