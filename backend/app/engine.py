from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from .charts import bar_option, empty_option, grouped_bar_option, histogram_option, line_option, scatter_option
from .schemas import AnalysisResult, AnalysisSpec, Filter
from .storage import dataset_path
from .utils import format_number, format_percent, records_from_frame, safe_float


class AnalysisError(ValueError):
    pass


def quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _table_sql(path: Path) -> str:
    path_text = path.as_posix().replace("'", "''")
    return f"read_parquet('{path_text}')"


def _column_map(dataset: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {column["name"]: column for column in dataset["profile"]["columns_detail"]}


def _get_column(dataset: dict[str, Any], name: str | None) -> dict[str, Any] | None:
    if not name:
        return None
    column = _column_map(dataset).get(name)
    if column is None:
        raise AnalysisError(f"字段不存在：{name}")
    return column


def _validate_spec(dataset: dict[str, Any], spec: AnalysisSpec) -> dict[str, dict[str, Any]]:
    columns = _column_map(dataset)
    x = _get_column(dataset, spec.x)
    y = _get_column(dataset, spec.y)
    group = _get_column(dataset, spec.group_by)

    if spec.chart_type == "scatter":
        if not x or x["kind"] != "number" or not y or y["kind"] != "number":
            raise AnalysisError("散点图需要两个数值字段。")
    elif spec.chart_type == "histogram":
        if not x or x["kind"] != "number":
            raise AnalysisError("直方图需要一个数值字段。")
    elif spec.chart_type in {"line", "bar", "table"}:
        if spec.aggregation != "count" and (not y or y["kind"] != "number"):
            raise AnalysisError("该图表需要一个数值指标字段，或把聚合方式改为 count。")
        if spec.chart_type == "line" and x and x["kind"] not in {"datetime", "number", "string", "boolean"}:
            raise AnalysisError("折线图的 X 轴字段类型不受支持。")

    if group:
        if group["unique"] > 30:
            raise AnalysisError("分组字段的取值过多（超过 30 个），请先合并长尾。")
        if group["name"] in {spec.x, spec.y}:
            raise AnalysisError("分组字段不能与 X/Y 字段相同。")
        if spec.chart_type not in {"line", "bar"}:
            raise AnalysisError("只有折线图和柱状图支持分组。")
    if spec.x and spec.y and spec.x == spec.y and spec.aggregation != "count":
        raise AnalysisError("X 轴与指标字段不能相同。")

    if len(spec.filters) > 10:
        raise AnalysisError("筛选条件最多 10 个。")
    for item in spec.filters:
        if item.column not in columns:
            raise AnalysisError(f"筛选字段不存在：{item.column}")
    return columns


def _filter_sql(
    filters: list[Filter],
    columns: dict[str, dict[str, Any]],
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    for item in filters:
        column = columns[item.column]
        identifier = quote_identifier(item.column)
        is_time = column["kind"] == "datetime"
        if item.op == "=" and item.value is None:
            clauses.append(f"{identifier} IS NULL")
            continue
        if item.op == "!=" and item.value is None:
            clauses.append(f"{identifier} IS NOT NULL")
            continue
        if item.op == "contains":
            clauses.append(f"CAST({identifier} AS VARCHAR) ILIKE '%' || ? || '%'")
            params.append(str(item.value))
            continue
        if item.op == "in":
            values = item.value if isinstance(item.value, (list, tuple)) else [item.value]
            if not values:
                clauses.append("FALSE")
                continue
            placeholders = ", ".join("TRY_CAST(? AS TIMESTAMP)" if is_time else "?" for _ in values)
            clauses.append(f"{identifier} IN ({placeholders})")
            params.extend(values)
            continue
        if item.op == "between":
            cast = "TRY_CAST(? AS TIMESTAMP)" if is_time else "?"
            clauses.append(f"{identifier} BETWEEN {cast} AND {cast}")
            params.extend([item.value, item.value2])
            continue
        right = "TRY_CAST(? AS TIMESTAMP)" if is_time else "?"
        clauses.append(f"{identifier} {item.op} {right}")
        params.append(item.value)
    if not clauses:
        return "", []
    return " WHERE " + " AND ".join(clauses), params


def _time_grain_sql(name: str, grain: str) -> str:
    return f"CAST(date_trunc('{grain}', {quote_identifier(name)}) AS DATE)"


def _x_expression(column: dict[str, Any], spec: AnalysisSpec) -> str:
    if column["kind"] == "datetime":
        return _time_grain_sql(column["name"], spec.time_grain)
    return quote_identifier(column["name"])


def _agg_sql(aggregation: str, y: str | None) -> str:
    if aggregation == "count":
        return "COUNT(*)"
    if not y:
        raise AnalysisError("缺少指标字段。")
    identifier = quote_identifier(y)
    if aggregation == "count_distinct":
        return f"COUNT(DISTINCT {identifier})"
    if aggregation not in {"sum", "avg", "min", "max", "median"}:
        raise AnalysisError(f"不支持的聚合方式：{aggregation}")
    return f"{aggregation.upper()}({identifier})"


def _label(value: Any) -> str:
    if value is None:
        return "空值"
    try:
        if pd.isna(value):
            return "空值"
    except (TypeError, ValueError):
        pass
    if isinstance(value, (pd.Timestamp,)):
        return value.strftime("%Y-%m-%d")
    if hasattr(value, "isoformat") and not isinstance(value, str):
        return str(value.isoformat())[:19]
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _query_frame(connection: duckdb.DuckDBPyConnection, sql: str, params: list[Any]) -> pd.DataFrame:
    try:
        return connection.execute(sql, params).fetchdf()
    except Exception as exc:  # noqa: BLE001
        raise AnalysisError(f"查询失败：{exc}") from exc


def _summary_for_categories(frame: pd.DataFrame, aggregation: str, label: str) -> str:
    if frame.empty:
        return "没有匹配的数据。"
    values = pd.to_numeric(frame["value"], errors="coerce").dropna()
    if values.empty:
        return f"共 {len(frame)} 个分组。"
    top_row = frame.iloc[0]
    bottom_row = frame.iloc[-1]
    if aggregation == "avg":
        return (
            f"共 {len(frame)} 个分组；`{top_row['label']}` 的平均值最高"
            f"（{format_number(top_row['value'])}），最低为 `{bottom_row['label']}`"
            f"（{format_number(bottom_row['value'])}）。"
        )
    total = float(values.sum())
    share = float(top_row["value"]) / total if total else 0.0
    return (
        f"共 {len(frame)} 个分组；`{top_row['label']}` 最高"
        f"（{format_number(top_row['value'])}，占 {format_percent(share)}）。"
    )


def _bar_result(
    connection: duckdb.DuckDBPyConnection,
    table: str,
    spec: AnalysisSpec,
    columns: dict[str, dict[str, Any]],
    where: str,
    params: list[Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], str, int]:
    x_column = columns[spec.x]  # type: ignore[index]
    x_expr = _x_expression(x_column, spec)
    agg_expr = _agg_sql(spec.aggregation, spec.y)
    limit = min(spec.limit, 500)
    if spec.group_by:
        sql = (
            f"SELECT {x_expr} AS __label, {quote_identifier(spec.group_by)} AS __series, "
            f"{agg_expr} AS __value FROM {table}{where} "
            f"GROUP BY 1, 2 ORDER BY 1"
        )
        frame = _query_frame(connection, sql, params)
        if frame.empty:
            return empty_option(), [], "没有匹配的数据。", 0
        pivot = frame.pivot(index="__label", columns="__series", values="__value")
        totals = pivot.sum(numeric_only=True).sort_values(ascending=False)
        keep = list(totals.head(6).index)
        pivot = pivot[keep]
        pivot = pivot.fillna(0) if spec.aggregation in {"sum", "count", "count_distinct"} else pivot
        pivot = pivot.head(limit)
        labels = [_label(value) for value in pivot.index.tolist()]
        series = []
        for name in pivot.columns:
            series.append(
                {
                    "name": _label(name),
                    "data": [safe_float(value) for value in pivot[name].tolist()],
                }
            )
        chart = grouped_bar_option(labels, series, spec.y or "记录数")
        rows = [
            {"label": label, **{_label(name): safe_float(value) for name, value in zip(pivot.columns, row)}}
            for label, row in zip(labels, pivot.to_numpy().tolist())
        ]
        return chart, rows, f"按 {spec.group_by} 拆分后的分组对比。", len(labels)

    order = "2 DESC" if spec.sort == "y" else "1 ASC"
    sql = (
        f"SELECT {x_expr} AS __label, {agg_expr} AS __value FROM {table}{where} "
        f"GROUP BY 1 ORDER BY {order} LIMIT ?"
    )
    frame = _query_frame(connection, sql, [*params, limit])
    if frame.empty:
        return empty_option(), [], "没有匹配的数据。", 0
    frame = frame.rename(columns={"__label": "label", "__value": "value"})
    summary = _summary_for_categories(frame, spec.aggregation, spec.x or "")
    display = frame.iloc[::-1]
    labels = [_label(value) for value in display["label"].tolist()]
    values = [safe_float(value) for value in display["value"].tolist()]
    chart = bar_option(labels, values, spec.y or "记录数", horizontal=True)
    rows = records_from_frame(frame)
    return chart, rows, summary, len(frame)


def _line_result(
    connection: duckdb.DuckDBPyConnection,
    table: str,
    spec: AnalysisSpec,
    columns: dict[str, dict[str, Any]],
    where: str,
    params: list[Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], str, int]:
    x_column = columns[spec.x]  # type: ignore[index]
    x_expr = _x_expression(x_column, spec)
    agg_expr = _agg_sql(spec.aggregation, spec.y)
    limit = min(spec.limit, 500)
    if spec.group_by:
        sql = (
            f"SELECT {x_expr} AS __label, {quote_identifier(spec.group_by)} AS __series, "
            f"{agg_expr} AS __value FROM {table}{where} GROUP BY 1, 2 ORDER BY 1"
        )
        frame = _query_frame(connection, sql, params)
        if frame.empty:
            return empty_option(), [], "没有匹配的数据。", 0
        pivot = frame.pivot(index="__label", columns="__series", values="__value")
        pivot = pivot.sort_index().head(limit)
        labels = [_label(value) for value in pivot.index.tolist()]
        series = [
            {"name": _label(name), "data": [safe_float(value) for value in pivot[name].tolist()]}
            for name in pivot.columns
        ]
        chart = line_option(labels, series, spec.x or "", spec.y or "")
        return chart, [], "按分组拆分的趋势对比。", len(labels)

    sql = (
        f"SELECT {x_expr} AS __label, {agg_expr} AS __value FROM {table}{where} "
        f"GROUP BY 1 ORDER BY 1 LIMIT ?"
    )
    frame = _query_frame(connection, sql, [*params, limit])
    if frame.empty:
        return empty_option(), [], "没有匹配的数据。", 0
    frame = frame.rename(columns={"__label": "label", "__value": "value"})
    labels = [_label(value) for value in frame["label"].tolist()]
    values = [safe_float(value) for value in frame["value"].tolist()]
    chart = line_option(labels, [{"name": spec.y or "记录数", "data": values}], spec.x or "", spec.y or "")
    clean = [value for value in values if value is not None]
    if len(clean) >= 2 and clean[0] != 0:
        change = (clean[-1] - clean[0]) / abs(clean[0])
        summary = f"从 {labels[0]} 到 {labels[-1]}，变化 {change:+.1%}。"
    else:
        summary = f"共 {len(labels)} 个时间点。"
    rows = records_from_frame(frame)
    return chart, rows, summary, len(labels)


def _scatter_result(
    connection: duckdb.DuckDBPyConnection,
    table: str,
    spec: AnalysisSpec,
    columns: dict[str, dict[str, Any]],
    where: str,
    params: list[Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], str, int]:
    x = quote_identifier(spec.x)  # type: ignore[arg-type]
    y = quote_identifier(spec.y)  # type: ignore[arg-type]
    limit = min(spec.limit, 2000)
    sql = (
        f"SELECT {x} AS __x, {y} AS __y FROM {table}{where} "
        f"AND {x} IS NOT NULL AND {y} IS NOT NULL LIMIT ?"
        if where
        else f"SELECT {x} AS __x, {y} AS __y FROM {table} "
        f"WHERE {x} IS NOT NULL AND {y} IS NOT NULL LIMIT ?"
    )
    frame = _query_frame(connection, sql, [*params, limit])
    if frame.empty:
        return empty_option(), [], "没有可用的数值对。", 0
    x_values = pd.to_numeric(frame["__x"], errors="coerce")
    y_values = pd.to_numeric(frame["__y"], errors="coerce")
    valid = pd.DataFrame({"x": x_values, "y": y_values}).dropna()
    if len(valid) < 2:
        return empty_option(), [], "有效样本不足，无法计算相关性。", len(valid)
    correlation = float(valid["x"].corr(valid["y"]))
    points = [
        [safe_float(x_value), safe_float(y_value)]
        for x_value, y_value in zip(valid["x"].tolist(), valid["y"].tolist())
        if safe_float(x_value) is not None and safe_float(y_value) is not None
    ]
    slope, intercept = np.polyfit(valid["x"].to_numpy(), valid["y"].to_numpy(), 1)
    x0, x1 = float(valid["x"].min()), float(valid["x"].max())
    regression = (x0, slope * x0 + intercept, x1, slope * x1 + intercept, correlation) if not math.isnan(correlation) else None
    chart = scatter_option(points, spec.x or "", spec.y or "", regression)
    if math.isnan(correlation):
        summary = f"共 {len(valid):,} 个有效样本；无法计算相关系数。"
    else:
        summary = f"共 {len(valid):,} 个有效样本；Pearson r={correlation:.2f}。"
    rows = records_from_frame(valid.rename(columns={"x": spec.x, "y": spec.y}).head(200))
    return chart, rows, summary, len(valid)


def _histogram_result(
    connection: duckdb.DuckDBPyConnection,
    table: str,
    spec: AnalysisSpec,
    columns: dict[str, dict[str, Any]],
    where: str,
    params: list[Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], str, int]:
    x = quote_identifier(spec.x)  # type: ignore[arg-type]
    stats_sql = f"SELECT MIN({x}) AS __min, MAX({x}) AS __max, COUNT(*) AS __n, AVG({x}) AS __mean, MEDIAN({x}) AS __median FROM {table}{where}"
    stats = _query_frame(connection, stats_sql, params)
    if stats.empty:
        return empty_option(), [], "没有匹配的数据。", 0
    row = stats.iloc[0]
    minimum, maximum = safe_float(row["__min"]), safe_float(row["__max"])
    count = int(row["__n"] or 0)
    mean, median = safe_float(row["__mean"]), safe_float(row["__median"])
    if minimum is None or maximum is None or count == 0:
        return empty_option(), [], "没有可用的数值。", 0
    if minimum == maximum:
        return empty_option("该字段只有一个取值"), [], "该字段只有一个取值，无法绘制分布。", count
    bins = min(30, max(5, int(math.sqrt(count))))
    width = (maximum - minimum) / bins
    bin_sql = (
        f"SELECT LEAST(CAST(FLOOR(({x} - ?) / ?) AS INTEGER), ?) AS __bin, COUNT(*) AS __count "
        f"FROM {table}{where} AND {x} IS NOT NULL GROUP BY 1 ORDER BY 1"
        if where
        else f"SELECT LEAST(CAST(FLOOR(({x} - ?) / ?) AS INTEGER), ?) AS __bin, COUNT(*) AS __count "
        f"FROM {table} WHERE {x} IS NOT NULL GROUP BY 1 ORDER BY 1"
    )
    frame = _query_frame(connection, bin_sql, [*params, minimum, width, bins - 1])
    counts = [0] * bins
    for bin_value, count_value in zip(frame["__bin"].tolist(), frame["__count"].tolist()):
        index = max(0, min(bins - 1, int(bin_value)))
        counts[index] = int(count_value)
    edges = [minimum + width * index for index in range(bins)] + [maximum]
    chart = histogram_option(edges, counts, spec.x or "", marks=[value for value in (mean, median) if value is not None])
    summary = f"共 {count:,} 个样本；均值 {format_number(mean)}，中位数 {format_number(median)}。"
    rows = [
        {"bin_start": safe_float(edges[index]), "bin_end": safe_float(edges[index + 1]), "count": counts[index]}
        for index in range(bins)
    ]
    return chart, rows, summary, count


def _table_result(
    connection: duckdb.DuckDBPyConnection,
    table: str,
    spec: AnalysisSpec,
    columns: dict[str, dict[str, Any]],
    where: str,
    params: list[Any],
) -> tuple[None, list[dict[str, Any]], str, int]:
    limit = min(spec.limit, 500)
    if spec.x:
        x_expr = _x_expression(columns[spec.x], spec)
        agg_expr = _agg_sql(spec.aggregation, spec.y)
        order = "2 DESC" if spec.sort == "y" else "1 ASC"
        sql = (
            f"SELECT {x_expr} AS {quote_identifier(spec.x)}, {agg_expr} AS "
            f"{quote_identifier(spec.y or ('记录数'))} FROM {table}{where} GROUP BY 1 ORDER BY {order} LIMIT ?"
        )
    else:
        sql = f"SELECT * FROM {table}{where} LIMIT ?"
    frame = _query_frame(connection, sql, [*params, limit])
    rows = records_from_frame(frame)
    return None, rows, f"返回 {len(rows):,} 行结果。", len(rows)


def execute_analysis(dataset: dict[str, Any], spec: AnalysisSpec) -> AnalysisResult:
    columns = _validate_spec(dataset, spec)
    path = dataset_path(dataset["id"])
    if not path.exists():
        raise AnalysisError("数据集文件已丢失，请重新上传。")
    table = _table_sql(path)
    where, params = _filter_sql(spec.filters, columns)
    start = time.perf_counter()
    connection = duckdb.connect()
    try:
        if spec.chart_type == "bar":
            chart, rows, summary, count = _bar_result(connection, table, spec, columns, where, params)
        elif spec.chart_type == "line":
            chart, rows, summary, count = _line_result(connection, table, spec, columns, where, params)
        elif spec.chart_type == "scatter":
            chart, rows, summary, count = _scatter_result(connection, table, spec, columns, where, params)
        elif spec.chart_type == "histogram":
            chart, rows, summary, count = _histogram_result(connection, table, spec, columns, where, params)
        else:
            chart, rows, summary, count = _table_result(connection, table, spec, columns, where, params)
    finally:
        connection.close()
    elapsed = (time.perf_counter() - start) * 1000
    return AnalysisResult(
        spec=spec,
        chart=chart,
        columns=[],
        rows=rows,
        summary=summary,
        query_ms=round(elapsed, 1),
        row_count=count,
    )


def preview_rows(dataset: dict[str, Any], limit: int = 100, offset: int = 0) -> dict[str, Any]:
    path = dataset_path(dataset["id"])
    connection = duckdb.connect()
    try:
        frame = _query_frame(
            connection,
            f"SELECT * FROM {_table_sql(path)} LIMIT ? OFFSET ?",
            [min(max(limit, 1), 500), max(offset, 0)],
        )
    finally:
        connection.close()
    columns = [
        {"name": column["name"], "kind": column["kind"], "dtype": column["dtype"]}
        for column in dataset["profile"]["columns_detail"]
    ]
    return {"columns": columns, "rows": records_from_frame(frame), "limit": limit, "offset": offset}

