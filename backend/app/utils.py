from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd


def safe_float(value: Any, digits: int = 4) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return round(number, digits)


def jsonable(value: Any, digits: int = 4) -> Any:
    if isinstance(value, dict):
        return {str(key): jsonable(item, digits) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(item, digits) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return safe_float(value, digits)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (pd.Timestamp, datetime, date, np.datetime64)):
        try:
            stamp = pd.Timestamp(value)
        except (TypeError, ValueError):
            return str(value)
        if pd.isna(stamp):
            return None
        return stamp.isoformat()
    if value is pd.NaT:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (str, int)):
        return value
    return str(value)


def records_from_frame(frame: pd.DataFrame, limit: int | None = None) -> list[dict[str, Any]]:
    if limit is not None:
        frame = frame.head(limit)
    return [jsonable(row) for row in frame.to_dict(orient="records")]


def format_number(value: Any) -> str:
    number = safe_float(value)
    if number is None:
        return "—"
    absolute = abs(number)
    if absolute >= 100_000_000:
        return f"{number / 100_000_000:.2f} 亿"
    if absolute >= 10_000:
        return f"{number / 10_000:.2f} 万"
    if absolute >= 100:
        return f"{number:,.0f}"
    if absolute >= 1:
        return f"{number:,.2f}".rstrip("0").rstrip(".")
    return f"{number:.4f}".rstrip("0").rstrip(".")


def format_percent(value: Any, digits: int = 1) -> str:
    number = safe_float(value)
    if number is None:
        return "—"
    return f"{number * 100:.{digits}f}%"

