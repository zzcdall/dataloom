from __future__ import annotations

import json
import re
from typing import Any

import httpx

from .config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


def is_configured() -> bool:
    return bool(LLM_BASE_URL and LLM_MODEL)


def _extract_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            return None
        try:
            value = json.loads(match.group(0))
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            return None


def plan_with_llm(dataset: dict[str, Any], question: str) -> tuple[dict[str, Any], str] | None:
    if not is_configured():
        return None
    columns = [
        {
            "name": column["name"],
            "kind": column["kind"],
            "semantic": column["semantic"],
            "unique": column["unique"],
        }
        for column in dataset["profile"]["columns_detail"]
    ]
    system = (
        "You are the planner for DataLoom, a local-first data analysis tool. "
        "Turn the user's question into a single JSON analysis spec. "
        "Never write SQL or code. Only use the column names provided. "
        "Allowed chart_type: line, bar, scatter, histogram, table. "
        "Allowed aggregation: sum, avg, count, min, max, median, count_distinct. "
        "Allowed time_grain: day, week, month, quarter, year. "
        "Return JSON only, with keys: chart_type, x, y, aggregation, group_by, "
        "time_grain, sort, limit, explanation."
    )
    user = json.dumps(
        {"question": question, "columns": columns},
        ensure_ascii=False,
    )
    headers = {"Content-Type": "application/json"}
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"
    try:
        response = httpx.post(
            f"{LLM_BASE_URL.rstrip('/')}/chat/completions",
            headers=headers,
            json={
                "model": LLM_MODEL,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=25,
        )
        response.raise_for_status()
        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
    except Exception:  # noqa: BLE001
        return None
    data = _extract_json(content)
    if not data:
        return None
    explanation = str(data.pop("explanation", "") or "由模型选择的分析方案。")
    return data, explanation

