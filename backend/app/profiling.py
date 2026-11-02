from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from .utils import format_number, safe_float


ID_KEYWORDS = (
    "id",
    "编号",
    "序号",
    "编码",
    "代码",
    "code",
    "uuid",
    "phone",
    "手机",
    "电话",
    "邮编",
    "zip",
)
TIME_KEYWORDS = (
    "date",
    "time",
    "datetime",
    "day",
    "month",
    "year",
    "week",
    "quarter",
    "日期",
    "时间",
    "年月",
    "月份",
    "年份",
    "季度",
    "周",
)
MEASURE_KEYWORDS = (
    "amount",
    "revenue",
    "sales",
    "profit",
    "income",
    "cost",
    "price",
    "qty",
    "quantity",
    "orders",
    "count",
    "users",
    "visits",
    "gmv",
    "score",
    "value",
    "金额",
    "销售额",
    "收入",
    "利润",
    "成本",
    "价格",
    "数量",
    "订单",
    "用户",
    "访问",
    "得分",
    "分数",
)
RATE_KEYWORDS = (
    "rate",
    "ratio",
    "percent",
    "pct",
    "margin",
    "average",
    "avg",
    "mean",
    "age",
    "率",
    "比例",
    "占比",
    "均价",
    "平均",
    "年龄",
    "满意度",
)
NON_ADDITIVE_KEYWORDS = RATE_KEYWORDS + ("price", "价格", "单价", "客单价", "年龄")
PRIMARY_MEASURE_KEYWORDS = (
    "revenue",
    "sales",
    "amount",
    "gmv",
    "turnover",
    "销售额",
    "收入",
    "金额",
    "营收",
)


def name_matches(name: str, keywords: tuple[str, ...]) -> bool:
    lowered = name.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def is_id_like(name: str, series: pd.Series) -> bool:
    if name_matches(name, ID_KEYWORDS):
        return True
    non_null = series.dropna()
    if len(non_null) < 20:
        return False
    return non_null.nunique() == len(non_null) and not pd.api.types.is_float_dtype(series)


def column_kind(series: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "number"
    return "string"


def _clean_example(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    return text[:80]


def _top_values(series: pd.Series, limit: int = 8) -> list[dict[str, Any]]:
    try:
        counts = series.dropna().value_counts().head(limit)
    except (TypeError, ValueError):
        return []
    return [
        {"value": _clean_example(value), "count": int(count)}
        for value, count in counts.items()
    ]


def _numeric_stats(series: pd.Series) -> dict[str, Any]:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return {}
    q1 = float(values.quantile(0.25))
    q3 = float(values.quantile(0.75))
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outliers = int(((values < lower) | (values > upper)).sum())
    return {
        "min": safe_float(values.min()),
        "max": safe_float(values.max()),
        "mean": safe_float(values.mean()),
        "median": safe_float(values.median()),
        "std": safe_float(values.std()),
        "q1": safe_float(q1),
        "q3": safe_float(q3),
        "iqr_lower": safe_float(lower),
        "iqr_upper": safe_float(upper),
        "skew": safe_float(values.skew()),
        "zeros": int((values == 0).sum()),
        "negatives": int((values < 0).sum()),
        "outliers": outliers,
        "outlier_rate": safe_float(outliers / len(values)),
        "count": int(len(values)),
    }


def _datetime_stats(series: pd.Series) -> dict[str, Any]:
    values = pd.to_datetime(series, errors="coerce").dropna()
    if values.empty:
        return {}
    minimum = values.min()
    maximum = values.max()
    return {
        "min": minimum.isoformat(),
        "max": maximum.isoformat(),
        "range_days": int((maximum - minimum).days),
        "count": int(len(values)),
    }


def profile_dataframe(
    frame: pd.DataFrame,
    *,
    dropped_empty_rows: int = 0,
    dropped_empty_columns: int = 0,
) -> dict[str, Any]:
    rows = int(len(frame))
    columns = int(len(frame.columns))
    cells = max(rows * columns, 1)
    total_missing = int(frame.isna().sum().sum())
    completeness = 1 - total_missing / cells
    duplicate_rows = int(frame.duplicated().sum()) if rows else 0
    duplicate_rate = duplicate_rows / rows if rows else 0.0

    columns_detail: list[dict[str, Any]] = []
    constant_columns: list[str] = []
    high_cardinality: list[str] = []

    for name in frame.columns:
        series = frame[name]
        kind = column_kind(series)
        missing = int(series.isna().sum())
        unique = int(series.nunique(dropna=True))
        if unique <= 1:
            constant_columns.append(name)
        if unique > max(50, int(rows * 0.8)):
            high_cardinality.append(name)

        is_time = kind == "datetime"
        id_like = is_id_like(name, series)
        if is_time:
            semantic = "time"
        elif kind == "boolean":
            semantic = "flag"
        elif id_like:
            semantic = "id"
        elif kind == "number":
            semantic = "measure"
        else:
            semantic = "dimension"

        stats: dict[str, Any] = {}
        if kind == "number":
            stats = _numeric_stats(series)
        elif kind == "datetime":
            stats = _datetime_stats(series)
        elif kind == "boolean":
            counts = series.value_counts(dropna=True)
            stats = {"true": int(counts.get(True, 0)), "false": int(counts.get(False, 0))}

        examples = []
        for value in series.dropna().head(3).tolist():
            text = _clean_example(value)
            if text and text not in examples:
                examples.append(text)

        columns_detail.append(
            {
                "name": str(name),
                "kind": kind,
                "dtype": str(series.dtype),
                "missing": missing,
                "missing_rate": safe_float(missing / rows) if rows else 0.0,
                "unique": unique,
                "is_measure": semantic == "measure",
                "is_dimension": semantic in {"dimension", "flag"},
                "is_time": is_time,
                "semantic": semantic,
                "examples": examples,
                "top_values": _top_values(series) if unique <= 80 else [],
                "stats": stats,
            }
        )

    health_score = round(100 * completeness)
    health_score -= min(12, int(round(duplicate_rate * 100)))
    health_score = max(0, min(100, health_score))

    return {
        "rows": rows,
        "columns": columns,
        "columns_detail": columns_detail,
        "quality": {
            "completeness": safe_float(completeness),
            "duplicate_rows": duplicate_rows,
            "duplicate_rate": safe_float(duplicate_rate),
            "health_score": health_score,
            "constant_columns": constant_columns,
            "high_cardinality_columns": high_cardinality,
            "dropped_empty_rows": int(dropped_empty_rows),
            "dropped_empty_columns": int(dropped_empty_columns),
        },
    }


def describe_column(profile: dict[str, Any], name: str) -> dict[str, Any] | None:
    for column in profile["columns_detail"]:
        if column["name"] == name:
            return column
    return None


def measure_columns(profile: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        column
        for column in profile["columns_detail"]
        if column["semantic"] == "measure"
        and column["unique"] > 2
        and column["stats"].get("count", 0) >= 3
    ]


def dimension_columns(profile: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        column
        for column in profile["columns_detail"]
        if column["semantic"] == "dimension" and 1 < column["unique"] <= 50
    ]


def time_columns(profile: dict[str, Any]) -> list[dict[str, Any]]:
    return [column for column in profile["columns_detail"] if column["semantic"] == "time"]


def is_additive(name: str) -> bool:
    return not name_matches(name, NON_ADDITIVE_KEYWORDS)


def measure_priority(name: str, profile: dict[str, Any]) -> float:
    score = 0.0
    if name_matches(name, MEASURE_KEYWORDS):
        score += 3
    if name_matches(name, PRIMARY_MEASURE_KEYWORDS):
        score += 6
    column = describe_column(profile, name)
    if column:
        stats = column.get("stats", {})
        if stats.get("std"):
            score += min(2, float(stats["std"]) / (abs(float(stats.get("mean") or 1)) + 1e-9))
        if stats.get("outlier_rate"):
            score += min(1, float(stats["outlier_rate"]) * 5)
    return score


def summarize_number(value: Any) -> str:
    return format_number(value)


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return cleaned or "insight"

