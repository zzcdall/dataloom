from __future__ import annotations

from typing import Any, Iterable, Sequence


PALETTE = [
    "#5b5bd6",
    "#12b76a",
    "#f79009",
    "#f04438",
    "#06aed4",
    "#9e77ed",
    "#ee46bc",
    "#84cc16",
]

AXIS_LABEL = {"color": "#667085", "fontSize": 11}
AXIS_LINE = {"lineStyle": {"color": "#d0d5dd"}}
SPLIT_LINE = {"lineStyle": {"color": "#eaecf0", "type": "dashed"}}


def _base() -> dict[str, Any]:
    return {
        "animationDuration": 450,
        "color": PALETTE,
        "textStyle": {
            "fontFamily": "Inter, 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif",
            "color": "#344054",
        },
        "tooltip": {
            "backgroundColor": "#ffffff",
            "borderColor": "#eaecf0",
            "borderWidth": 1,
            "textStyle": {"color": "#101828", "fontSize": 12},
            "extraCssText": "box-shadow:0 10px 28px rgba(16,24,40,.12);border-radius:10px;padding:10px 12px;",
        },
        "grid": {"left": 10, "right": 18, "top": 26, "bottom": 10, "containLabel": True},
    }


def line_option(
    labels: Sequence[str],
    series: Sequence[dict[str, Any]],
    x_label: str = "",
    y_label: str = "",
) -> dict[str, Any]:
    option = _base()
    option.update(
        {
            "tooltip": {**option["tooltip"], "trigger": "axis"},
            "legend": {
                "show": len(series) > 1,
                "top": 0,
                "right": 0,
                "icon": "circle",
                "itemWidth": 8,
                "itemHeight": 8,
                "textStyle": {"color": "#667085", "fontSize": 11},
            },
            "xAxis": {
                "type": "category",
                "data": list(labels),
                "boundaryGap": False,
                "axisLabel": {**AXIS_LABEL, "hideOverlap": True},
                "axisLine": AXIS_LINE,
                "axisTick": {"show": False},
                "name": x_label,
                "nameTextStyle": {"color": "#98a2b3", "fontSize": 10},
            },
            "yAxis": {
                "type": "value",
                "axisLabel": AXIS_LABEL,
                "splitLine": SPLIT_LINE,
                "axisLine": {"show": False},
                "name": y_label,
                "nameTextStyle": {"color": "#98a2b3", "fontSize": 10},
            },
            "series": [],
        }
    )
    for index, item in enumerate(series):
        option["series"].append(
            {
                "name": item.get("name", "值"),
                "type": "line",
                "data": item.get("data", []),
                "smooth": 0.25,
                "showSymbol": len(labels) <= 40,
                "symbol": "circle",
                "symbolSize": 6,
                "lineStyle": {"width": 2.4, "color": PALETTE[index % len(PALETTE)]},
                "itemStyle": {"color": PALETTE[index % len(PALETTE)]},
                "areaStyle": {"opacity": 0.07},
                "connectNulls": True,
            }
        )
    return option


def bar_option(
    labels: Sequence[str],
    values: Sequence[float | None],
    value_name: str = "值",
    horizontal: bool = True,
) -> dict[str, Any]:
    option = _base()
    category_axis = {
        "type": "category",
        "data": list(labels),
        "axisLabel": {**AXIS_LABEL, "interval": 0, "hideOverlap": True},
        "axisLine": AXIS_LINE,
        "axisTick": {"show": False},
    }
    value_axis = {
        "type": "value",
        "axisLabel": AXIS_LABEL,
        "splitLine": SPLIT_LINE,
        "axisLine": {"show": False},
    }
    option.update(
        {
            "tooltip": {
                **option["tooltip"],
                "trigger": "axis",
                "axisPointer": {"type": "shadow", "shadowStyle": {"color": "rgba(91,91,214,.06)"}},
            },
            "xAxis": value_axis if horizontal else category_axis,
            "yAxis": category_axis if horizontal else value_axis,
            "series": [
                {
                    "name": value_name,
                    "type": "bar",
                    "data": list(values),
                    "barMaxWidth": 26,
                    "itemStyle": {
                        "color": PALETTE[0],
                        "borderRadius": [0, 6, 6, 0] if horizontal else [6, 6, 0, 0],
                    },
                    "label": {
                        "show": len(values) <= 14,
                        "position": "right" if horizontal else "top",
                        "color": "#475467",
                        "fontSize": 10,
                        "formatter": "{c}",
                    },
                }
            ],
        }
    )
    return option


def grouped_bar_option(
    labels: Sequence[str],
    series: Sequence[dict[str, Any]],
    value_name: str = "值",
) -> dict[str, Any]:
    option = _base()
    option.update(
        {
            "tooltip": {
                **option["tooltip"],
                "trigger": "axis",
                "axisPointer": {"type": "shadow", "shadowStyle": {"color": "rgba(91,91,214,.06)"}},
            },
            "legend": {
                "show": True,
                "top": 0,
                "right": 0,
                "icon": "circle",
                "itemWidth": 8,
                "itemHeight": 8,
                "textStyle": {"color": "#667085", "fontSize": 11},
            },
            "xAxis": {
                "type": "category",
                "data": list(labels),
                "axisLabel": {**AXIS_LABEL, "interval": 0, "hideOverlap": True},
                "axisLine": AXIS_LINE,
                "axisTick": {"show": False},
            },
            "yAxis": {
                "type": "value",
                "axisLabel": AXIS_LABEL,
                "splitLine": SPLIT_LINE,
                "axisLine": {"show": False},
            },
            "series": [
                {
                    "name": item.get("name", "值"),
                    "type": "bar",
                    "data": item.get("data", []),
                    "barMaxWidth": 22,
                    "itemStyle": {
                        "color": PALETTE[index % len(PALETTE)],
                        "borderRadius": [4, 4, 0, 0],
                    },
                }
                for index, item in enumerate(series)
            ],
        }
    )
    return option


def scatter_option(
    points: Sequence[Sequence[float]],
    x_label: str = "",
    y_label: str = "",
    regression: tuple[float, float, float, float, float] | None = None,
) -> dict[str, Any]:
    option = _base()
    option.update(
        {
            "tooltip": {
                **option["tooltip"],
                "trigger": "item",
                "formatter": "{a}<br/>{c}",
            },
            "xAxis": {
                "type": "value",
                "scale": True,
                "axisLabel": AXIS_LABEL,
                "splitLine": SPLIT_LINE,
                "axisLine": AXIS_LINE,
                "name": x_label,
                "nameLocation": "middle",
                "nameGap": 24,
                "nameTextStyle": {"color": "#98a2b3", "fontSize": 10},
            },
            "yAxis": {
                "type": "value",
                "scale": True,
                "axisLabel": AXIS_LABEL,
                "splitLine": SPLIT_LINE,
                "axisLine": {"show": False},
                "name": y_label,
                "nameTextStyle": {"color": "#98a2b3", "fontSize": 10},
            },
            "series": [
                {
                    "name": f"{x_label} vs {y_label}",
                    "type": "scatter",
                    "data": [list(point) for point in points],
                    "symbolSize": 7,
                    "itemStyle": {"color": PALETTE[0], "opacity": 0.55},
                    "emphasis": {"itemStyle": {"opacity": 1}},
                }
            ],
        }
    )
    if regression:
        x0, y0, x1, y1, r = regression
        option["series"].append(
            {
                "name": f"拟合线 (r={r:.2f})",
                "type": "line",
                "data": [[x0, y0], [x1, y1]],
                "showSymbol": False,
                "silent": True,
                "lineStyle": {"width": 2, "type": "dashed", "color": PALETTE[3]},
                "tooltip": {"show": False},
            }
        )
    return option


def histogram_option(
    edges: Sequence[float],
    counts: Sequence[int],
    label: str = "值",
    marks: Sequence[float] = (),
) -> dict[str, Any]:
    option = _base()
    centers = [
        round((float(edges[index]) + float(edges[index + 1])) / 2, 4)
        for index in range(len(edges) - 1)
    ]
    mark_lines = [
        {
            "xAxis": mark,
            "label": {"formatter": f"{mark:.2f}", "color": "#f04438", "fontSize": 10},
            "lineStyle": {"color": "#f04438", "type": "dashed", "width": 1.2},
        }
        for mark in marks
    ]
    option.update(
        {
            "tooltip": {**option["tooltip"], "trigger": "item"},
            "xAxis": {
                "type": "value",
                "min": edges[0],
                "max": edges[-1],
                "axisLabel": AXIS_LABEL,
                "splitLine": {"show": False},
                "axisLine": AXIS_LINE,
                "name": label,
                "nameLocation": "middle",
                "nameGap": 24,
                "nameTextStyle": {"color": "#98a2b3", "fontSize": 10},
            },
            "yAxis": {
                "type": "value",
                "axisLabel": AXIS_LABEL,
                "splitLine": SPLIT_LINE,
                "axisLine": {"show": False},
            },
            "series": [
                {
                    "name": "样本数",
                    "type": "bar",
                    "data": [[centers[index], counts[index]] for index in range(len(counts))],
                    "barWidth": "94%",
                    "itemStyle": {"color": PALETTE[0], "borderRadius": [3, 3, 0, 0]},
                    "markLine": {"silent": True, "symbol": "none", "data": mark_lines}
                    if mark_lines
                    else {"data": []},
                }
            ],
        }
    )
    return option


def box_option(
    label: str,
    box: Sequence[float],
    outliers: Sequence[float],
) -> dict[str, Any]:
    option = _base()
    option.update(
        {
            "tooltip": {**option["tooltip"], "trigger": "item"},
            "xAxis": {
                "type": "category",
                "data": [label],
                "axisLabel": AXIS_LABEL,
                "axisLine": AXIS_LINE,
                "axisTick": {"show": False},
            },
            "yAxis": {
                "type": "value",
                "scale": True,
                "axisLabel": AXIS_LABEL,
                "splitLine": SPLIT_LINE,
                "axisLine": {"show": False},
            },
            "series": [
                {
                    "name": label,
                    "type": "boxplot",
                    "data": [list(box)],
                    "itemStyle": {"color": "rgba(91,91,214,.12)", "borderColor": PALETTE[0]},
                },
                {
                    "name": "异常值",
                    "type": "scatter",
                    "data": [[0, value] for value in outliers[:400]],
                    "symbolSize": 5,
                    "itemStyle": {"color": PALETTE[3], "opacity": 0.7},
                },
            ],
        }
    )
    return option


def empty_option(message: str = "没有可展示的数据") -> dict[str, Any]:
    return {
        "title": {
            "text": message,
            "left": "center",
            "top": "middle",
            "textStyle": {"color": "#98a2b3", "fontSize": 13, "fontWeight": 400},
        }
    }


def series_from_rows(
    labels: Iterable[str],
    groups: dict[str, Sequence[float | None]],
) -> list[dict[str, Any]]:
    return [{"name": name, "data": list(values)} for name, values in groups.items()]

