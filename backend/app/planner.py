from __future__ import annotations

from typing import Any

from .engine import AnalysisError, execute_analysis
from .insights import primary_columns
from .llm import is_configured, plan_with_llm
from .profiling import (
    dimension_columns,
    is_additive,
    measure_columns,
    measure_priority,
    time_columns,
)
from .schemas import AnalysisResult, AnalysisSpec, AskRequest, AskResponse


INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "trend": ("趋势", "变化", "增长", "下降", "走势", "随时间的", "trend", "over time", "month", "year"),
    "rank": ("排名", "排行", "最高", "最低", "最多", "top", "前几", "rank", "largest", "smallest"),
    "correlation": ("相关", "关系", "影响", "是否有关", "correlation", "relationship", "affect"),
    "distribution": ("分布", "异常", "离群", "偏度", "histogram", "outlier", "distribution", "skew"),
    "compare": ("对比", "比较", "差异", "分别", "compare", "versus", " vs "),
    "count": ("多少", "几个", "数量", "记录数", "how many", "count"),
    "overview": ("概览", "总结", "整体", "值得关注", "overview", "summary", "insight"),
}

CHART_NAMES = {
    "line": "折线图",
    "bar": "柱状图",
    "scatter": "散点图",
    "histogram": "直方图",
    "table": "数据表",
}


def _mentions(question: str, name: str) -> bool:
    return name.lower() in question.lower()


def _mentioned_columns(question: str, columns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [column for column in columns if _mentions(question, column["name"])]


def _intent(question: str, mentioned: list[dict[str, Any]]) -> str:
    lowered = question.lower()
    scores = {intent: 0.0 for intent in INTENT_KEYWORDS}
    for intent, keywords in INTENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in lowered:
                scores[intent] += max(1.0, len(keyword) / 3)
    numeric = [column for column in mentioned if column["kind"] == "number"]
    times = [column for column in mentioned if column["kind"] == "datetime"]
    dimensions = [column for column in mentioned if column["semantic"] in {"dimension", "flag"}]
    if times:
        scores["trend"] += 2.5
    if len(numeric) >= 2:
        scores["correlation"] += 2
    if dimensions:
        scores["rank"] += 1.5
        scores["compare"] += 1
    if len(numeric) == 1:
        scores["distribution"] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "overview"


def _pick_measure(
    profile: dict[str, Any],
    mentioned: list[dict[str, Any]],
    *,
    exclude: set[str] | None = None,
) -> dict[str, Any] | None:
    exclude = exclude or set()
    candidates = [
        column
        for column in mentioned
        if column["kind"] == "number" and column["name"] not in exclude
    ]
    if candidates:
        return candidates[0]
    measures = [
        column
        for column in measure_columns(profile)
        if column["name"] not in exclude
    ]
    if not measures:
        return None
    return max(measures, key=lambda column: measure_priority(column["name"], profile))


def _pick_dimension(profile: dict[str, Any], mentioned: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [
        column
        for column in mentioned
        if column["semantic"] in {"dimension", "flag"}
    ]
    if candidates:
        return candidates[0]
    dimensions = dimension_columns(profile)
    if not dimensions:
        return None
    return max(dimensions, key=lambda column: min(column["unique"], 12))


def _pick_time(profile: dict[str, Any], mentioned: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [column for column in mentioned if column["kind"] == "datetime"]
    if candidates:
        return candidates[0]
    times = time_columns(profile)
    if not times:
        return None
    return max(times, key=lambda column: column["stats"].get("range_days", 0))


def _explain(spec: AnalysisSpec) -> str:
    chart = CHART_NAMES.get(spec.chart_type, "图表")
    if spec.chart_type == "scatter":
        return f"使用{chart}查看 `{spec.x}` 与 `{spec.y}` 的关系。"
    if spec.chart_type == "histogram":
        return f"使用{chart}查看 `{spec.x}` 的分布。"
    if spec.aggregation == "count":
        return f"按 `{spec.x}` 统计记录数，使用{chart}展示。"
    aggregation_name = {
        "sum": "求和",
        "avg": "平均值",
        "median": "中位数",
        "min": "最小值",
        "max": "最大值",
        "count_distinct": "去重计数",
    }.get(spec.aggregation, spec.aggregation)
    return f"按 `{spec.x}` 对 `{spec.y}` 做{aggregation_name}，使用{chart}展示。"


def _fallback_overview(dataset: dict[str, Any], question: str) -> AskResponse:
    insights = [insight for insight in dataset["insights"] if insight["kind"] != "overview"][:3]
    if insights:
        lines = [f"- **{insight['title']}**：{insight['summary']}" for insight in insights]
        answer = "我先从数据里挑出最值得关注的几个信号：\n\n" + "\n".join(lines)
    else:
        answer = "这份数据目前没有检测到明显的趋势、异常或分组差异。可以尝试指定字段，例如“按地区看销售额排名”。"
    return AskResponse(question=question, answer=answer, intent="overview", spec=None, result=None)


def _run_spec(dataset: dict[str, Any], spec: AnalysisSpec) -> AnalysisResult:
    return execute_analysis(dataset, spec)


def answer_question(dataset: dict[str, Any], request: AskRequest) -> AskResponse:
    question = request.question.strip()
    profile = dataset["profile"]
    all_columns = profile["columns_detail"]
    mentioned = _mentioned_columns(question, all_columns)
    intent = _intent(question, mentioned)
    used_llm = False

    if is_configured():
        planned = plan_with_llm(dataset, question)
        if planned:
            payload, explanation = planned
            payload.setdefault("limit", 50)
            try:
                spec = AnalysisSpec(**payload)
                result = _run_spec(dataset, spec)
                answer = f"{explanation}\n\n{result.summary}" if result.summary else explanation
                return AskResponse(
                    question=question,
                    answer=answer,
                    intent=spec.chart_type,
                    spec=spec,
                    result=result,
                    used_llm=True,
                )
            except (AnalysisError, ValueError):
                pass

    if intent == "overview":
        return _fallback_overview(dataset, question)

    primary = primary_columns(profile)
    if intent == "trend":
        time_column = _pick_time(profile, mentioned)
        if time_column is None and primary["time"]:
            time_column = next(column for column in all_columns if column["name"] == primary["time"])
        measure = _pick_measure(profile, mentioned)
        if time_column and measure:
            spec = AnalysisSpec(
                chart_type="line",
                x=time_column["name"],
                y=measure["name"],
                aggregation="sum" if is_additive(measure["name"]) else "avg",
                time_grain="month",
                sort="x",
                limit=200,
            )
            result = _run_spec(dataset, spec)
            return AskResponse(
                question=question,
                answer=f"{_explain(spec)}\n\n{result.summary}",
                intent="trend",
                spec=spec,
                result=result,
                used_llm=used_llm,
            )

    if intent == "correlation":
        first = _pick_measure(profile, mentioned)
        second = _pick_measure(profile, mentioned, exclude={first["name"]} if first else None)
        if first and second:
            spec = AnalysisSpec(
                chart_type="scatter",
                x=first["name"],
                y=second["name"],
                aggregation="sum",
                sort="none",
                limit=500,
            )
            result = _run_spec(dataset, spec)
            return AskResponse(
                question=question,
                answer=f"{_explain(spec)}\n\n{result.summary}",
                intent="correlation",
                spec=spec,
                result=result,
                used_llm=used_llm,
            )

    if intent == "distribution":
        measure = _pick_measure(profile, mentioned)
        if measure:
            spec = AnalysisSpec(
                chart_type="histogram",
                x=measure["name"],
                aggregation="count",
                sort="x",
                limit=30,
            )
            result = _run_spec(dataset, spec)
            return AskResponse(
                question=question,
                answer=f"{_explain(spec)}\n\n{result.summary}",
                intent="distribution",
                spec=spec,
                result=result,
                used_llm=used_llm,
            )

    if intent == "count":
        dimension = _pick_dimension(profile, mentioned)
        if dimension:
            spec = AnalysisSpec(
                chart_type="bar",
                x=dimension["name"],
                aggregation="count",
                sort="y",
                limit=20,
            )
            result = _run_spec(dataset, spec)
            return AskResponse(
                question=question,
                answer=f"{_explain(spec)}\n\n{result.summary}",
                intent="count",
                spec=spec,
                result=result,
                used_llm=used_llm,
            )

    dimension = _pick_dimension(profile, mentioned)
    measure = _pick_measure(profile, mentioned)
    if dimension and measure:
        spec = AnalysisSpec(
            chart_type="bar",
            x=dimension["name"],
            y=measure["name"],
            aggregation="sum" if is_additive(measure["name"]) else "avg",
            sort="y",
            limit=12,
        )
        result = _run_spec(dataset, spec)
        return AskResponse(
            question=question,
            answer=f"{_explain(spec)}\n\n{result.summary}",
            intent="compare",
            spec=spec,
            result=result,
            used_llm=used_llm,
        )

    time_column = _pick_time(profile, mentioned)
    if time_column and measure:
        spec = AnalysisSpec(
            chart_type="line",
            x=time_column["name"],
            y=measure["name"],
            aggregation="sum" if is_additive(measure["name"]) else "avg",
            time_grain="month",
            sort="x",
            limit=200,
        )
        result = _run_spec(dataset, spec)
        return AskResponse(
            question=question,
            answer=f"{_explain(spec)}\n\n{result.summary}",
            intent="trend",
            spec=spec,
            result=result,
            used_llm=used_llm,
        )

    return _fallback_overview(dataset, question)

