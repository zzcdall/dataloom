"""Render the 1280x640 GitHub social preview from the current workspace screenshot.

Usage:
    python scripts/make_social_preview.py
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT = ROOT / "docs" / "screenshot.png"
OUTPUT = ROOT / "docs" / "social-preview.png"


def build_html(image_name: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8"/>
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; width: 1280px; height: 640px; overflow: hidden; }}
    body {{
      background: #0b0c1a;
      color: #fff;
      font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
      position: relative;
    }}
    .glow {{ position: absolute; border-radius: 50%; filter: blur(10px); pointer-events: none; }}
    .g1 {{ width: 620px; height: 620px; left: -220px; top: -260px;
      background: radial-gradient(circle, rgba(99,102,241,.32), transparent 68%); }}
    .g2 {{ width: 720px; height: 720px; right: -260px; bottom: -340px;
      background: radial-gradient(circle, rgba(168,85,247,.22), transparent 68%); }}
    .grid {{
      position: absolute; inset: 0; opacity: .18;
      background-image: linear-gradient(rgba(255,255,255,.06) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.06) 1px, transparent 1px);
      background-size: 48px 48px;
      mask-image: linear-gradient(120deg, #000 0%, transparent 62%);
    }}
    .copy {{ position: absolute; left: 64px; top: 58px; width: 480px; }}
    .brand {{ display: flex; align-items: center; gap: 12px; }}
    .mark {{
      width: 46px; height: 46px; border-radius: 13px; display: grid; place-items: center;
      background: linear-gradient(135deg, #6366f1, #a855f7);
      box-shadow: 0 10px 30px rgba(99,102,241,.38);
      font-weight: 800; font-size: 17px; letter-spacing: -.04em;
    }}
    .name {{ font-size: 14px; letter-spacing: .18em; color: #c7c9e8; font-weight: 600; }}
    h1 {{
      margin: 34px 0 0; font-size: 47px; line-height: 1.24; letter-spacing: -.035em;
      font-weight: 760;
    }}
    .accent {{
      background: linear-gradient(90deg, #c4b5fd, #7dd3fc);
      -webkit-background-clip: text; background-clip: text; color: transparent;
    }}
    .sub {{ margin: 22px 0 0; font-size: 17px; line-height: 1.7; color: #a8aacb; }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 9px; margin-top: 30px; width: 500px; }}
    .chip {{
      padding: 7px 13px; border-radius: 999px; font-size: 12px; color: #d9daf3;
      border: 1px solid rgba(255,255,255,.14); background: rgba(255,255,255,.06);
    }}
    .foot {{
      position: absolute; left: 66px; bottom: 44px; display: flex; align-items: center;
      gap: 9px; font-size: 13px; color: #8f92b8;
    }}
    .dot {{ width: 7px; height: 7px; border-radius: 50%; background: #34d399;
      box-shadow: 0 0 12px rgba(52,211,153,.8); }}
    .shot-wrap {{
      position: absolute; left: 552px; top: 72px; width: 700px; height: 496px;
      border-radius: 18px; padding: 1px;
      background: linear-gradient(145deg, rgba(196,181,253,.65), rgba(125,211,252,.18) 40%, rgba(255,255,255,.08));
      box-shadow: 0 42px 90px rgba(0,0,0,.58), 0 0 80px rgba(99,102,241,.18);
    }}
    .shot {{ width: 100%; height: 100%; border-radius: 17px; overflow: hidden; background: #fff; }}
    .shot img {{ display: block; width: 100%; height: 100%; object-fit: cover; object-position: top center; }}
    .badge {{
      position: absolute; right: 22px; bottom: -18px; padding: 10px 16px; border-radius: 12px;
      background: rgba(15,17,38,.92); border: 1px solid rgba(255,255,255,.14);
      box-shadow: 0 18px 40px rgba(0,0,0,.4); font-size: 12px; color: #d9daf3;
      display: flex; align-items: center; gap: 8px;
    }}
    .badge strong {{ font-size: 17px; color: #6ee7b7; }}
  </style>
</head>
<body>
  <div class="glow g1"></div>
  <div class="glow g2"></div>
  <div class="grid"></div>

  <div class="copy">
    <div class="brand"><div class="mark">DL</div><div class="name">DATALOOM · 数织</div></div>
    <h1>上传一份表格，<br/>几十秒得到<br/><span class="accent">可审计</span>的分析报告</h1>
    <p class="sub">自动字段画像 · 确定性洞察 · 交互探索<br/>自然语言追问 · 一键导出 HTML</p>
    <div class="chips">
      <span class="chip">本地优先</span>
      <span class="chip">CSV / XLSX</span>
      <span class="chip">DuckDB</span>
      <span class="chip">React + ECharts</span>
      <span class="chip">Apache-2.0</span>
    </div>
  </div>

  <div class="shot-wrap">
    <div class="shot"><img src="{image_name}" alt=""/></div>
    <div class="badge">数据健康分 <strong>99</strong></div>
  </div>

  <div class="foot"><span class="dot"></span>本地运行 · 数据不出机器 · 无需写 SQL</div>
</body>
</html>"""


def main() -> None:
    if not SCREENSHOT.exists():
        raise SystemExit(f"Missing screenshot: {SCREENSHOT}")
    temp_html = ROOT / "docs" / "_social_preview.html"
    temp_html.write_text(build_html(SCREENSHOT.name), encoding="utf-8")
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 640}, device_scale_factor=1)
            page.goto(temp_html.as_uri(), wait_until="load")
            page.wait_for_timeout(500)
            page.screenshot(path=str(OUTPUT))
            browser.close()
    finally:
        temp_html.unlink(missing_ok=True)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
