from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .charts import bar_option, box_option, histogram_option, line_option, scatter_option
from .profiling import (
    describe_column,
    dimension_columns,
    is_additive,
    measure_columns,
    measure_priority,
    time_columns,
)
from .utils import format_number, format_percent, safe_float


def _round_series(values: pd.Series, digits: int = 4) -> list[float | None]:
    return [safe_float(value, digits) for value in values.tolist()]


def _histogram(values: pd.Series, bins: int = 20) -> tuple[list[float], list[int]]:
    clean = pd.to_numeric(values, errors="coerce").dropna()
    clean = clean[np.isfinite(clean)]
    if clean.empty:
        return [], []
    counts, edges = np.histogram(clean.to_numpy(), bins=min(bins, max(5, int(np.sqrt(len(clean))))))
    return [safe_float(edge, 4) for edge in edges.tolist()], [int(count) for count in counts.tolist()]


def _linear_fit(values: list[float]) -> tuple[float, float]:
    if len(values) < 2:
        return 0.0, 0.0
    x = np.arange(len(values), dtype=float)
    y = np.asarray(values, dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    predicted = slope * x + intercept
    ss_res = float(np.sum((y - predicted) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return float(slope), float(max(0.0, min(1.0, r_squared)))


def _overview_insight(profile: dict[str, Any]) -> dict[str, Any]:
    quality = profile["quality"]
    rows = profile["rows"]
    columns = profile["columns"]
    measures = sum(1 for column in profile["columns_detail"] if column["semantic"] == "measure")
    dimensions = sum(1 for column in profile["columns_detail"] if column["semantic"] == "dimension")
    times = sum(1 for column in profile["columns_detail"] if column["semantic"] == "time")
    parts = []
    if measures:
        parts.append(f"{measures} 个数值字段")
    if dimensions:
        parts.append(f"{dimensions} 个分类字段")
    if times:
        parts.append(f"{times} 个时间字段")
    missing = 1 - float(quality["completeness"])
    detail = f"整体完整度 {format_percent(quality['completeness'])}。"
    if missing > 0:
        detail += f"缺失值占 {format_percent(missing)}。"
    if quality["duplicate_rows"]:
        detail += f"发现 {quality['duplicate_rows']:,} 行完全重复记录。"
    return {
        "id": "overview",
        "kind": "overview",
        "tag": "概览",
        "title": f"{rows:,} 行 × {columns} 列",
        "summary": "、".join(parts) + "。" if parts else "已读取数据表。",
        "detail": detail,
        "confidence": "high",
        "score": 100,
        "chart": None,
        "metrics": {
            "rows": rows,
            "columns": columns,
            "completeness": quality["completeness"],
            "health_score": quality["health_score"],
        },
        "columns": [],
        "spec": None,
    }


def _missing_insight(profile: dict[str, Any]) -> dict[str, Any] | None:
    columns = [
        column
        for column in profile["columns_detail"]
        if column["missing"] > 0 and profile["rows"] > 0
    ]
    if not columns:
        return None
    columns.sort(key=lambda column: column["missing_rate"], reverse=True)
    top = columns[:8]
    ordered = list(reversed(top))
    labels = [column["name"] for column in ordered]
    values = [round(float(column["missing_rate"]) * 100, 2) for column in ordered]
    worst = columns[0]
    if len(columns) == 1:
        title = f"`{worst['name']}` 有 {format_percent(worst['missing_rate'])} 缺失"
    else:
        title = f"{len(columns)} 个字段存在缺失，最高 {format_percent(worst['missing_rate'])}"
    summary = f"缺失最集中在 `{worst['name']}`，共 {worst['missing']:,} 个空值。"
    detail = "缺失值会改变分组占比和平均值。若缺失并非随机，建议先补充或单独标记。"
    return {
        "id": "missing-values",
        "kind": "missing",
        "tag": "数据质量",
        "title": title,
        "summary": summary,
        "detail": detail,
        "confidence": "high",
        "score": 72 + float(worst["missing_rate"]) * 100,
        "chart": bar_option(labels, values, "缺失率 (%)", horizontal=True),
        "metrics": {
            "columns": len(columns),
            "max_missing_rate": worst["missing_rate"],
            "total_missing": sum(column["missing"] for column in columns),
        },
        "columns": [column["name"] for column in columns[:5]],
        "spec": None,
    }


def _duplicate_insight(profile: dict[str, Any]) -> dict[str, Any] | None:
    quality = profile["quality"]
    if not quality["duplicate_rows"]:
        return None
    return {
        "id": "duplicate-rows",
        "kind": "duplicate",
        "tag": "数据质量",
        "title": f"发现 {quality['duplicate_rows']:,} 行完全重复",
        "summary": f"占全部记录的 {format_percent(quality['duplicate_rate'])}。",
        "detail": "重复记录会放大计数、求和和占比。建议确认业务含义后在导入前去重。",
        "confidence": "high",
        "score": 68,
        "chart": None,
        "metrics": {
            "duplicate_rows": quality["duplicate_rows"],
            "duplicate_rate": quality["duplicate_rate"],
        },
        "columns": [],
        "spec": None,
    }


def _constant_insight(profile: dict[str, Any]) -> dict[str, Any] | None:
    columns = profile["quality"]["constant_columns"]
    if not columns:
        return None
    shown = "、".join(f"`{name}`" for name in columns[:3])
    return {
        "id": "constant-columns",
        "kind": "quality",
        "tag": "数据质量",
        "title": f"{len(columns)} 个字段只有一个取值",
        "summary": f"{shown} 无法用于分组或对比。",
        "detail": "这类字段通常来自导入错误或筛选后的数据，确认后可删除以简化分析。",
        "confidence": "high",
        "score": 34,
        "chart": None,
        "metrics": {"columns": columns},
        "columns": columns,
        "spec": None,
    }


def _outlier_insight(
    frame: pd.DataFrame,
    profile: dict[str, Any],
    used_columns: set[str],
) -> dict[str, Any] | None:
    candidates: list[tuple[float, dict[str, Any]]] = []
    for column in measure_columns(profile):
        stats = column.get("stats", {})
        rate = float(stats.get("outlier_rate") or 0)
        if rate >= 0.02 and int(stats.get("outliers") or 0) >= 3:
            candidates.append((rate, column))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    rate, column = candidates[0]
    name = column["name"]
    series = pd.to_numeric(frame[name], errors="coerce").dropna()
    if series.empty:
        return None
    q1 = float(series.quantile(0.25))
    median = float(series.median())
    q3 = float(series.quantile(0.75))
    lower = float(column["stats"].get("iqr_lower") or q1)
    upper = float(column["stats"].get("iqr_upper") or q3)
    outliers = series[(series < lower) | (series > upper)]
    box = [float(series.min()), q1, median, q3, float(series.max())]
    used_columns.add(name)
    return {
        "id": f"outliers-{name}",
        "kind": "outlier",
        "tag": "异常值",
        "title": f"`{name}` 有 {format_percent(rate)} 的异常值",
        "summary": f"{len(outliers):,} 个样本落在 IQR 区间 [{format_number(lower)}, {format_number(upper)}] 之外。",
        "detail": f"最大值 {format_number(series.max())}，中位数 {format_number(median)}。异常不一定是错误，建议先核实来源。",
        "confidence": "medium",
        "score": 50 + rate * 100,
        "chart": box_option(name, [safe_float(value) for value in box], _round_series(outliers.head(400))),
        "metrics": {
            "outliers": int(len(outliers)),
            "outlier_rate": rate,
            "lower": lower,
            "upper": upper,
            "max": safe_float(series.max()),
        },
        "columns": [name],
        "spec": {
            "chart_type": "histogram",
            "x": name,
            "y": None,
            "aggregation": "count",
            "filters": [],
            "sort": "x",
            "limit": 20,
        },
    }


def _correlation_insights(
    frame: pd.DataFrame,
    profile: dict[str, Any],
    limit: int = 2,
) -> list[dict[str, Any]]:
    measures = [column for column in measure_columns(profile) if column["stats"].get("count", 0) >= 10]
    if len(measures) < 2:
        return []
    pairs: list[tuple[float, str, str, int]] = []
    for index, left in enumerate(measures):
        for right in measures[index + 1 :]:
            left_values = pd.to_numeric(frame[left["name"]], errors="coerce")
            right_values = pd.to_numeric(frame[right["name"]], errors="coerce")
            valid = pd.concat([left_values, right_values], axis=1).dropna()
            if len(valid) < 10:
                continue
            if valid.iloc[:, 0].std() == 0 or valid.iloc[:, 1].std() == 0:
                continue
            correlation = float(valid.iloc[:, 0].corr(valid.iloc[:, 1]))
            if pd.isna(correlation):
                continue
            if abs(correlation) >= 0.5:
                pairs.append((correlation, left["name"], right["name"], len(valid)))
    pairs.sort(key=lambda item: abs(item[0]), reverse=True)

    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for correlation, left, right, count in pairs:
        key = tuple(sorted((left, right)))
        if key in seen:
            continue
        seen.add(key)
        left_values = pd.to_numeric(frame[left], errors="coerce")
        right_values = pd.to_numeric(frame[right], errors="coerce")
        valid = pd.concat([left_values, right_values], axis=1).dropna()
        valid.columns = ["x", "y"]
        sample = valid.sample(n=min(500, len(valid)), random_state=7)
        points = [
            [safe_float(row.x), safe_float(row.y)]
            for row in sample.itertuples(index=False)
            if safe_float(row.x) is not None and safe_float(row.y) is not None
        ]
        slope, intercept = np.polyfit(valid["x"].to_numpy(), valid["y"].to_numpy(), 1)
        x0, x1 = float(valid["x"].min()), float(valid["x"].max())
        y0, y1 = slope * x0 + intercept, slope * x1 + intercept
        direction = "正" if correlation > 0 else "负"
        strength = "强" if abs(correlation) >= 0.7 else "中等"
        results.append(
            {
                "id": f"correlation-{left}-{right}".replace(" ", "-"),
                "kind": "correlation",
                "tag": "相关性",
                "title": f"`{left}` 与 `{right}` 呈{strength}{direction}相关（r={correlation:.2f}）",
                "summary": f"基于 {count:,} 个有效样本；{left} 越高，{right} 通常越{'高' if correlation > 0 else '低'}。",
                "detail": "相关不等于因果。建议按分类字段分层后再判断，避免辛普森悖论。",
                "confidence": "high" if abs(correlation) >= 0.7 and count >= 30 else "medium",
                "score": 50 + abs(correlation) * 30,
                "chart": scatter_option(
                    points,
                    left,
                    right,
                    (x0, y0, x1, y1, correlation),
                ),
                "metrics": {
                    "correlation": safe_float(correlation),
                    "samples": count,
                    "slope": safe_float(slope),
                },
                "columns": [left, right],
                "spec": {
                    "chart_type": "scatter",
                    "x": left,
                    "y": right,
                    "aggregation": "sum",
                    "filters": [],
                    "sort": "none",
                    "limit": 500,
                },
            }
        )
        if len(results) >= limit:
            break
    return results


def _trend_insight(
    frame: pd.DataFrame,
    profile: dict[str, Any],
    used_columns: set[str],
) -> dict[str, Any] | None:
    times = [column for column in time_columns(profile) if column["stats"].get("count", 0) >= 5]
    measures = measure_columns(profile)
    if not times or not measures:
        return None
    time_column = max(times, key=lambda column: column["stats"].get("range_days", 0))
    measures = sorted(
        measures,
        key=lambda column: measure_priority(column["name"], profile),
        reverse=True,
    )
    measure = measures[0]
    dates = pd.to_datetime(frame[time_column["name"]], errors="coerce")
    values = pd.to_numeric(frame[measure["name"]], errors="coerce")
    valid = pd.DataFrame({"date": dates, "value": values}).dropna()
    if len(valid) < 5:
        return None
    range_days = int((valid["date"].max() - valid["date"].min()).days)
    if range_days <= 45:
        grain, period_freq, grain_label = "day", "D", "日"
    elif range_days <= 180:
        grain, period_freq, grain_label = "week", "W", "周"
    elif range_days <= 365 * 3:
        grain, period_freq, grain_label = "month", "M", "月"
    else:
        grain, period_freq, grain_label = "quarter", "Q", "季度"
    additive = is_additive(measure["name"])
    aggregation = "sum" if additive else "avg"
    valid["period"] = valid["date"].dt.to_period(period_freq).astype(str)
    pandas_agg = "mean" if aggregation == "avg" else aggregation
    grouped = valid.groupby("period", sort=True)["value"].agg(pandas_agg)
    if len(grouped) < 3:
        return None
    labels = [str(label) for label in grouped.index.tolist()]
    values_list = [safe_float(value) for value in grouped.tolist()]
    clean_values = [value for value in values_list if value is not None]
    slope, r_squared = _linear_fit(clean_values)
    first, last = clean_values[0], clean_values[-1]
    change = (last - first) / abs(first) if first else 0.0
    if change > 0.05:
        direction, arrow = "上升", "↑"
    elif change < -0.05:
        direction, arrow = "下降", "↓"
    else:
        direction, arrow = "基本平稳", "→"
    confidence = "high" if r_squared >= 0.5 and len(clean_values) >= 6 else "medium"
    if len(clean_values) < 4:
        confidence = "low"
    used_columns.add(measure["name"])
    return {
        "id": f"trend-{measure['name']}-{grain}",
        "kind": "trend",
        "tag": "趋势",
        "title": f"`{measure['name']}` 整体{direction} {arrow}",
        "summary": f"从 {labels[0]} 的 {format_number(first)} 到 {labels[-1]} 的 {format_number(last)}，变化 {change:+.1%}。",
        "detail": f"按{grain_label}汇总（{aggregation}），线性拟合 R²={r_squared:.2f}。建议再结合同比、季节性和分组拆解验证。",
        "confidence": confidence,
        "score": 66 + min(abs(change), 1) * 18 + r_squared * 10,
        "chart": line_option(labels, [{"name": measure["name"], "data": values_list}], time_column["name"], measure["name"]),
        "metrics": {
            "first": first,
            "last": last,
            "change": safe_float(change),
            "slope": safe_float(slope),
            "r_squared": safe_float(r_squared),
            "periods": len(clean_values),
            "grain": grain,
        },
        "columns": [time_column["name"], measure["name"]],
        "spec": {
            "chart_type": "line",
            "x": time_column["name"],
            "y": measure["name"],
            "aggregation": aggregation,
            "group_by": None,
            "time_grain": grain,
            "filters": [],
            "sort": "x",
            "limit": 200,
        },
    }


def _category_insight(
    frame: pd.DataFrame,
    profile: dict[str, Any],
    used_columns: set[str],
) -> dict[str, Any] | None:
    dimensions = dimension_columns(profile)
    measures = measure_columns(profile)
    if not dimensions or not measures:
        return None
    best: tuple[float, dict[str, Any], dict[str, Any], pd.Series, float, float] | None = None
    for dimension in dimensions:
        if dimension["unique"] < 2 or dimension["unique"] > 20:
            continue
        for measure in measures:
            if measure_priority(measure["name"], profile) < 1:
                continue
            values = pd.to_numeric(frame[measure["name"]], errors="coerce")
            grouping = frame[dimension["name"]].astype("string")
            valid = pd.DataFrame({"group": grouping, "value": values}).dropna()
            if len(valid) < 5:
                continue
            aggregation = "sum" if is_additive(measure["name"]) else "avg"
            pandas_agg = "mean" if aggregation == "avg" else aggregation
            grouped = valid.groupby("group")["value"].agg(pandas_agg).sort_values(ascending=False)
            if grouped.empty or grouped.sum() == 0:
                continue
            top_share = float(grouped.iloc[0] / grouped.sum()) if aggregation == "sum" else 0.0
            candidate_score = top_share * 2 + measure_priority(measure["name"], profile)
            if best is None or candidate_score > best[0]:
                best = (candidate_score, dimension, measure, grouped, top_share, aggregation)  # type: ignore[assignment]
    if best is None:
        return None
    _, dimension, measure, grouped, top_share, aggregation = best
    top = grouped.head(10)
    ordered = top.sort_values(ascending=True)
    labels = [str(label) for label in ordered.index.tolist()]
    values = [safe_float(value) for value in ordered.tolist()]
    top_name = str(grouped.index[0])
    top_value = float(grouped.iloc[0])
    top3_share = float(grouped.head(3).sum() / grouped.sum()) if aggregation == "sum" else 0.0
    if top_share >= 0.5:
        title = f"`{measure['name']}` 高度集中在 `{top_name}`（{format_percent(top_share)}）"
    elif top_share >= 0.3:
        title = f"`{measure['name']}` 主要集中在 `{top_name}`（{format_percent(top_share)}）"
    else:
        title = f"`{measure['name']}` 在 `{dimension['name']}` 上分布较均衡"
    summary = f"第一名 `{top_name}` 为 {format_number(top_value)}"
    if aggregation == "sum":
        summary += f"，前 3 名合计占 {format_percent(top3_share)}。"
    else:
        summary += f"，共 {dimension['unique']} 个分组。"
    used_columns.add(measure["name"])
    return {
        "id": f"category-{dimension['name']}-{measure['name']}",
        "kind": "category",
        "tag": "分组对比",
        "title": title,
        "summary": summary,
        "detail": "分组差异适合用来定位重点区域、渠道或品类；如果分组数量很多，建议先合并长尾。",
        "confidence": "high" if profile["rows"] >= 20 else "medium",
        "score": 46 + top_share * 24,
        "chart": bar_option(labels, values, measure["name"], horizontal=True),
        "metrics": {
            "top_group": top_name,
            "top_value": safe_float(top_value),
            "top_share": safe_float(top_share),
            "top3_share": safe_float(top3_share),
            "groups": int(grouped.size),
            "aggregation": aggregation,
        },
        "columns": [dimension["name"], measure["name"]],
        "spec": {
            "chart_type": "bar",
            "x": dimension["name"],
            "y": measure["name"],
            "aggregation": aggregation,
            "group_by": None,
            "filters": [],
            "sort": "y",
            "limit": 10,
        },
    }


def _distribution_insight(
    frame: pd.DataFrame,
    profile: dict[str, Any],
    used_columns: set[str],
) -> dict[str, Any] | None:
    candidates: list[tuple[float, dict[str, Any]]] = []
    for column in measure_columns(profile):
        if column["name"] in used_columns:
            continue
        stats = column.get("stats", {})
        skew = stats.get("skew")
        if skew is None or abs(float(skew)) < 1 or int(stats.get("count") or 0) < 20:
            continue
        candidates.append((abs(float(skew)), column))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    _, column = candidates[0]
    name = column["name"]
    series = pd.to_numeric(frame[name], errors="coerce").dropna()
    if series.empty:
        return None
    skew = float(column["stats"]["skew"])
    mean = float(series.mean())
    median = float(series.median())
    edges, counts = _histogram(series, bins=20)
    if not edges:
        return None
    direction = "右偏" if skew > 0 else "左偏"
    used_columns.add(name)
    return {
        "id": f"distribution-{name}",
        "kind": "distribution",
        "tag": "分布",
        "title": f"`{name}` 分布明显{direction}（偏度 {skew:.2f}）",
        "summary": f"均值 {format_number(mean)}，中位数 {format_number(median)}。",
        "detail": "少数极端值会拉高/拉低平均值；描述典型水平时中位数更稳健，也可以考虑对数变换。",
        "confidence": "medium",
        "score": 40 + min(abs(skew), 5) * 4,
        "chart": histogram_option(edges, counts, name, marks=[mean, median]),
        "metrics": {
            "mean": safe_float(mean),
            "median": safe_float(median),
            "skew": safe_float(skew),
            "samples": int(len(series)),
        },
        "columns": [name],
        "spec": {
            "chart_type": "histogram",
            "x": name,
            "y": None,
            "aggregation": "count",
            "filters": [],
            "sort": "x",
            "limit": 20,
        },
    }


def generate_insights(frame: pd.DataFrame, profile: dict[str, Any]) -> list[dict[str, Any]]:
    used_columns: set[str] = set()
    insights: list[dict[str, Any]] = [_overview_insight(profile)]
    for factory in (
        lambda: _missing_insight(profile),
        lambda: _duplicate_insight(profile),
        lambda: _constant_insight(profile),
        lambda: _outlier_insight(frame, profile, used_columns),
        lambda: _trend_insight(frame, profile, used_columns),
        lambda: _category_insight(frame, profile, used_columns),
        lambda: _distribution_insight(frame, profile, used_columns),
    ):
        insight = factory()
        if insight:
            insights.append(insight)
    insights.extend(_correlation_insights(frame, profile))
    insights = [insight for insight in insights if insight]
    insights.sort(key=lambda insight: float(insight.get("score", 0)), reverse=True)
    overview = [insight for insight in insights if insight["kind"] == "overview"]
    rest = [insight for insight in insights if insight["kind"] != "overview"][:7]
    return overview + rest


def build_suggestions(profile: dict[str, Any]) -> list[str]:
    times = time_columns(profile)
    measures = measure_columns(profile)
    dimensions = dimension_columns(profile)
    suggestions: list[str] = []
    if times and measures:
        suggestions.append(f"{measures[0]['name']}随时间的趋势如何？")
    if dimensions and measures:
        suggestions.append(f"按{dimensions[0]['name']}看，{measures[0]['name']}排名如何？")
    if len(measures) >= 2:
        suggestions.append(f"{measures[0]['name']}和{measures[1]['name']}有什么关系？")
    if measures:
        suggestions.append(f"{measures[0]['name']}的分布是否异常？")
    suggestions.append("这份数据最值得关注的问题是什么？")
    return suggestions[:5]


def primary_columns(profile: dict[str, Any]) -> dict[str, str | None]:
    times = time_columns(profile)
    measures = sorted(
        measure_columns(profile),
        key=lambda column: measure_priority(column["name"], profile),
        reverse=True,
    )
    dimensions = dimension_columns(profile)
    return {
        "time": times[0]["name"] if times else None,
        "measure": measures[0]["name"] if measures else None,
        "dimension": dimensions[0]["name"] if dimensions else None,
    }

