from __future__ import annotations

import html
import json
from datetime import datetime
from typing import Any

from .engine import preview_rows
from .utils import format_number, format_percent


def _rich(text: str) -> str:
    escaped = html.escape(text or "")
    escaped = escaped.replace("\n", "<br/>")
    while "`" in escaped:
        first = escaped.find("`")
        second = escaped.find("`", first + 1)
        if second == -1:
            break
        escaped = escaped[:first] + "<code>" + escaped[first + 1 : second] + "</code>" + escaped[second + 1 :]
    return escaped


def _kind_label(kind: str) -> str:
    return {
        "number": "数值",
        "string": "文本",
        "datetime": "日期",
        "boolean": "布尔",
    }.get(kind, kind)


def _metric_block(insight: dict[str, Any]) -> str:
    metrics = insight.get("metrics") or {}
    items: list[tuple[str, str]] = []
    if isinstance(metrics.get("health_score"), (int, float)):
        items.append((format_number(metrics["health_score"]), "健康分"))
    if isinstance(metrics.get("rows"), (int, float)):
        items.append((format_number(metrics["rows"]), "行"))
    if isinstance(metrics.get("columns"), (int, float)):
        items.append((format_number(metrics["columns"]), "列"))
    if isinstance(metrics.get("duplicate_rows"), (int, float)):
        items.append((format_number(metrics["duplicate_rows"]), "重复行"))
    if isinstance(metrics.get("completeness"), (int, float)):
        items.append((format_percent(metrics["completeness"]), "完整度"))
    if not items:
        columns = insight.get("columns") or []
        if columns:
            chips = "".join(f"<span class='mini-chip'>{html.escape(str(name))}</span>" for name in columns[:6])
            return f"<div class='metric-quote'>{chips}</div>"
        return ""
    cells = "".join(
        f"<div class='metric-item'><strong>{html.escape(value)}</strong><span>{html.escape(label)}</span></div>"
        for value, label in items[:3]
    )
    return f"<div class='metric-grid'>{cells}</div>"


def build_html_report(dataset: dict[str, Any]) -> str:
    profile = dataset["profile"]
    quality = profile["quality"]
    preview = preview_rows(dataset, limit=20)
    chart_payload: list[dict[str, Any]] = []
    insight_cards: list[str] = []
    for index, insight in enumerate(dataset["insights"]):
        chart_html = ""
        if insight.get("chart"):
            chart_id = f"chart-{index}"
            chart_html = f'<div class="chart" id="{chart_id}"></div>'
            chart_payload.append({"id": chart_id, "option": insight["chart"]})
        metric_html = "" if insight.get("chart") else _metric_block(insight)
        confidence = {"high": "高", "medium": "中", "low": "低"}.get(insight.get("confidence", "medium"), "中")
        insight_cards.append(
            f"""
            <article class="insight">
              <div class="insight-head">
                <span class="tag">{html.escape(insight.get('tag', '洞察'))}</span>
                <span class="confidence">置信度 {confidence}</span>
              </div>
              <h3>{_rich(insight.get('title', ''))}</h3>
              <p class="summary">{_rich(insight.get('summary', ''))}</p>
              {chart_html}
              {metric_html}
              <p class="detail">{_rich(insight.get('detail', ''))}</p>
            </article>
            """
        )

    column_rows = "\n".join(
        f"""
        <tr>
          <td><strong>{html.escape(column['name'])}</strong></td>
          <td><span class="pill">{_kind_label(column['kind'])}</span></td>
          <td>{format_percent(column['missing_rate'])}</td>
          <td>{column['unique']:,}</td>
          <td>{html.escape(', '.join(column.get('examples', [])))}</td>
        </tr>
        """
        for column in profile["columns_detail"]
    )

    preview_header = "".join(f"<th>{html.escape(column['name'])}</th>" for column in preview["columns"])
    preview_rows_html = []
    for row in preview["rows"]:
        cells = []
        for column in preview["columns"]:
            value = row.get(column["name"])
            text = "—" if value is None else str(value)
            cells.append(f"<td>{html.escape(text[:120])}</td>")
        preview_rows_html.append("<tr>" + "".join(cells) + "</tr>")

    chart_json = json.dumps(chart_payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    generated = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    title = f"{dataset['name']} · DataLoom 分析报告"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{html.escape(title)}</title>
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>
  <style>
    :root {{
      --ink: #101828; --muted: #667085; --line: #eaecf0; --panel: #ffffff;
      --bg: #f6f7fb; --accent: #5b5bd6; --soft: #eef0ff;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: var(--bg); color: var(--ink);
      font-family: Inter, "PingFang SC", "Microsoft YaHei", system-ui, sans-serif; line-height: 1.6; }}
    .page {{ max-width: 1180px; margin: 0 auto; padding: 40px 28px 64px; }}
    header.hero {{ background: linear-gradient(135deg, #15153d 0%, #2b2b76 55%, #4f46b8 100%);
      color: #fff; border-radius: 24px; padding: 34px 36px; position: relative; overflow: hidden; }}
    header.hero::after {{ content: ""; position: absolute; width: 320px; height: 320px; right: -80px; top: -140px;
      border: 1px solid rgba(255,255,255,.18); border-radius: 50%; box-shadow: 0 0 0 42px rgba(255,255,255,.04),
      0 0 0 84px rgba(255,255,255,.03); }}
    .brand {{ display: flex; align-items: center; gap: 10px; font-size: 13px; letter-spacing: .12em;
      text-transform: uppercase; color: rgba(255,255,255,.72); }}
    .mark {{ width: 30px; height: 30px; border-radius: 9px; background: #fff; color: #2b2b76;
      display: grid; place-items: center; font-weight: 800; letter-spacing: 0; }}
    h1 {{ font-size: 34px; line-height: 1.2; margin: 18px 0 8px; font-weight: 720; letter-spacing: -.02em; }}
    .hero p {{ margin: 0; color: rgba(255,255,255,.72); }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 22px; }}
    .chip {{ border: 1px solid rgba(255,255,255,.2); background: rgba(255,255,255,.08);
      padding: 5px 11px; border-radius: 999px; font-size: 12px; }}
    .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: 18px 0 30px; }}
    .stat {{ background: var(--panel); border: 1px solid var(--line); border-radius: 16px; padding: 18px 20px; }}
    .stat .label {{ color: var(--muted); font-size: 12px; }}
    .stat .value {{ font-size: 26px; font-weight: 700; letter-spacing: -.02em; margin-top: 4px; }}
    h2 {{ font-size: 20px; margin: 34px 0 14px; letter-spacing: -.01em; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
    .insight {{ background: var(--panel); border: 1px solid var(--line); border-radius: 18px; padding: 20px; break-inside: avoid; }}
    .insight-head {{ display: flex; align-items: center; justify-content: space-between; gap: 8px; }}
    .tag {{ color: var(--accent); background: var(--soft); border-radius: 999px; padding: 3px 9px; font-size: 11px; font-weight: 650; }}
    .confidence {{ color: #98a2b3; font-size: 11px; }}
    .insight h3 {{ font-size: 16px; line-height: 1.45; margin: 12px 0 6px; }}
    .summary {{ color: #344054; font-size: 13px; margin: 0 0 8px; }}
    .detail {{ color: var(--muted); font-size: 12px; margin: 8px 0 0; }}
    .chart {{ height: 240px; margin: 10px 0 2px; }}
    .chart-fallback {{ display: grid; place-items: center; min-height: 160px; padding: 20px;
      border: 1px dashed #d0d5dd; border-radius: 12px; color: var(--muted); font-size: 13px;
      text-align: center; background: #fafbff; }}
    .metric-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 16px 0 4px; }}
    .metric-item {{ border: 1px solid var(--line); border-radius: 12px; padding: 14px; background: #fbfbff; }}
    .metric-item strong {{ display: block; font-size: 22px; letter-spacing: -.03em; }}
    .metric-item span {{ color: var(--muted); font-size: 11px; }}
    .metric-quote {{ margin: 16px 0 4px; display: flex; flex-wrap: wrap; gap: 6px; }}
    .mini-chip {{ border: 1px solid var(--line); border-radius: 999px; padding: 3px 8px; color: var(--muted); font-size: 11px; }}
    code {{ background: #f2f4f7; border-radius: 5px; padding: 1px 5px; font-size: .92em; color: #3538cd; }}
    table {{ width: 100%; border-collapse: collapse; background: var(--panel); border: 1px solid var(--line);
      border-radius: 16px; overflow: hidden; font-size: 12px; }}
    th, td {{ text-align: left; padding: 11px 13px; border-bottom: 1px solid var(--line); vertical-align: top; }}
    th {{ background: #f9fafb; color: var(--muted); font-weight: 600; white-space: nowrap; }}
    tr:last-child td {{ border-bottom: none; }}
    .pill {{ border: 1px solid var(--line); border-radius: 999px; padding: 2px 7px; color: var(--muted); }}
    .scroll {{ overflow-x: auto; border-radius: 16px; }}
    footer {{ color: #98a2b3; font-size: 11px; margin-top: 40px; display: flex; justify-content: space-between; gap: 20px; }}
    @media (max-width: 800px) {{
      .page {{ padding: 20px 14px 40px; }}
      header.hero {{ padding: 26px 22px; border-radius: 18px; }}
      h1 {{ font-size: 26px; }}
      .stats, .grid {{ grid-template-columns: 1fr; }}
      .stats {{ grid-template-columns: repeat(2, 1fr); }}
    }}
    @media print {{
      body {{ background: #fff; }}
      .page {{ max-width: none; padding: 0; }}
      header.hero {{ border-radius: 0; }}
      .insight, .stat, table {{ break-inside: avoid; }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <header class="hero">
      <div class="brand"><span class="mark">DL</span> DataLoom · 数织</div>
      <h1>{html.escape(dataset['name'])}</h1>
      <p>自动生成的数据分析报告</p>
      <div class="chips">
        <span class="chip">{profile['rows']:,} 行</span>
        <span class="chip">{profile['columns']} 列</span>
        <span class="chip">完整度 {format_percent(quality['completeness'])}</span>
        <span class="chip">生成于 {generated}</span>
      </div>
    </header>

    <section class="stats">
      <div class="stat"><div class="label">数据健康分</div><div class="value">{quality['health_score']}</div></div>
      <div class="stat"><div class="label">完整度</div><div class="value">{format_percent(quality['completeness'])}</div></div>
      <div class="stat"><div class="label">重复行</div><div class="value">{quality['duplicate_rows']:,}</div></div>
      <div class="stat"><div class="label">字段数</div><div class="value">{profile['columns']}</div></div>
    </section>

    <h2>关键发现</h2>
    <section class="grid">{''.join(insight_cards)}</section>

    <h2>字段概览</h2>
    <div class="scroll"><table>
      <thead><tr><th>字段</th><th>类型</th><th>缺失率</th><th>唯一值</th><th>示例</th></tr></thead>
      <tbody>{column_rows}</tbody>
    </table></div>

    <h2>数据预览</h2>
    <div class="scroll"><table>
      <thead><tr>{preview_header}</tr></thead>
      <tbody>{''.join(preview_rows_html)}</tbody>
    </table></div>

    <footer>
      <span>由 DataLoom 本地生成 · 数据未离开这台机器</span>
      <span>DataLoom v0.1.0</span>
    </footer>
  </main>
  <script id="chart-data" type="application/json">{chart_json}</script>
  <script>
    (function () {{
      if (typeof echarts === 'undefined') {{
        document.querySelectorAll('.chart').forEach(function (element) {{
          element.innerHTML = '<div class="chart-fallback">图表组件未能加载。请联网后重新打开此文件；文字结论、字段画像与数据预览不受影响。</div>';
          element.style.height = 'auto';
        }});
        return;
      }}
      try {{
        var charts = JSON.parse(document.getElementById('chart-data').textContent);
        charts.forEach(function (item) {{
          var element = document.getElementById(item.id);
          if (element) echarts.init(element).setOption(item.option);
        }});
      }} catch (error) {{ console.error(error); }}
    }})();
  </script>
</body>
</html>"""

