"""Capture README screenshots from a running DataLoom instance.

Usage:
    python scripts/capture_screenshots.py http://127.0.0.1:8000
"""

from __future__ import annotations

import sys
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright


def main() -> None:
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    output = Path(__file__).resolve().parents[1] / "docs"
    output.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1020}, device_scale_factor=1)
        page.on("console", lambda message: errors.append(f"console: {message.text}") if message.type == "error" else None)
        page.on("pageerror", lambda error: errors.append(f"pageerror: {error}"))
        page.goto(base_url, wait_until="networkidle")
        page.wait_for_timeout(1200)

        if page.locator(".dataset-item").count() == 0:
            page.screenshot(path=str(output / "landing.png"))
            page.locator(".landing .upload-demo").click()
            page.wait_for_selector(".insight-card", timeout=30000)

        page.wait_for_timeout(2200)
        page.screenshot(path=str(output / "screenshot.png"))

        tabs = page.locator(".tab")
        if tabs.count() >= 4:
            tabs.nth(2).click()
            page.wait_for_timeout(1800)
            page.screenshot(path=str(output / "explore.png"))
            tabs.nth(3).click()
            page.wait_for_timeout(600)
            suggestions = page.locator(".suggestion-chip")
            if suggestions.count() > 0:
                suggestions.first.click()
                page.wait_for_selector(".answer-card", timeout=30000)
            page.wait_for_timeout(1600)
            page.screenshot(path=str(output / "ask.png"))

        mobile = browser.new_page(viewport={"width": 430, "height": 900}, device_scale_factor=1)
        mobile.goto(base_url, wait_until="networkidle")
        mobile.wait_for_timeout(1800)
        mobile.screenshot(path=str(output / "mobile.png"))

        datasets = requests.get(f"{base_url.rstrip('/')}/api/datasets", timeout=30).json()
        if datasets:
            report = requests.get(
                f"{base_url.rstrip('/')}/api/datasets/{datasets[0]['id']}/export.html",
                timeout=60,
            )
            report.raise_for_status()
            report_path = output / "sample-report.html"
            report_path.write_text(report.text, encoding="utf-8")
            report_page = browser.new_page(viewport={"width": 1280, "height": 1000}, device_scale_factor=1)
            report_page.goto(report_path.as_uri(), wait_until="networkidle")
            report_page.wait_for_timeout(1800)
            report_page.screenshot(path=str(output / "report.png"))

        browser.close()
    if errors:
        print("Browser errors:")
        for error in errors:
            print(f"  {error}")
        raise SystemExit(1)
    print(f"Screenshots written to {output}")


if __name__ == "__main__":
    main()

