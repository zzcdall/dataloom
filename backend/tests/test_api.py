from __future__ import annotations

import json

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_upload_and_profile(client: TestClient, uploaded_dataset: dict) -> None:
    assert uploaded_dataset["rows"] == 1808
    assert uploaded_dataset["columns"] == 12
    assert uploaded_dataset["profile"]["quality"]["health_score"] <= 100
    assert uploaded_dataset["insights"]
    kinds = {insight["kind"] for insight in uploaded_dataset["insights"]}
    assert "overview" in kinds
    assert "trend" in kinds
    assert "category" in kinds
    assert uploaded_dataset["suggestions"]
    columns = {column["name"]: column for column in uploaded_dataset["profile"]["columns_detail"]}
    assert columns["订单日期"]["kind"] == "datetime"
    assert columns["销售额"]["kind"] == "number"
    assert columns["客户ID"]["semantic"] == "id"


def test_preview(client: TestClient, uploaded_dataset: dict) -> None:
    response = client.get(f"/api/datasets/{uploaded_dataset['id']}/preview?limit=7")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["rows"]) == 7
    assert len(payload["columns"]) == 12


def test_bar_analysis(client: TestClient, uploaded_dataset: dict) -> None:
    response = client.post(
        f"/api/datasets/{uploaded_dataset['id']}/analyze",
        json={
            "chart_type": "bar",
            "x": "地区",
            "y": "销售额",
            "aggregation": "sum",
            "sort": "y",
            "limit": 10,
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["chart"]["series"][0]["type"] == "bar"
    assert payload["row_count"] >= 4
    assert "华东" in response.text


def test_line_analysis(client: TestClient, uploaded_dataset: dict) -> None:
    response = client.post(
        f"/api/datasets/{uploaded_dataset['id']}/analyze",
        json={
            "chart_type": "line",
            "x": "订单日期",
            "y": "销售额",
            "aggregation": "sum",
            "time_grain": "month",
            "limit": 100,
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["chart"]["series"][0]["type"] == "line"
    assert len(payload["chart"]["xAxis"]["data"]) >= 20


def test_scatter_analysis(client: TestClient, uploaded_dataset: dict) -> None:
    response = client.post(
        f"/api/datasets/{uploaded_dataset['id']}/analyze",
        json={
            "chart_type": "scatter",
            "x": "销售额",
            "y": "利润",
            "aggregation": "sum",
            "limit": 500,
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["chart"]["series"][0]["type"] == "scatter"
    assert payload["row_count"] > 100


def test_histogram_analysis(client: TestClient, uploaded_dataset: dict) -> None:
    response = client.post(
        f"/api/datasets/{uploaded_dataset['id']}/analyze",
        json={
            "chart_type": "histogram",
            "x": "销售额",
            "aggregation": "count",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["chart"]["series"][0]["type"] == "bar"
    assert payload["row_count"] == uploaded_dataset["rows"]


def test_invalid_column_is_rejected(client: TestClient, uploaded_dataset: dict) -> None:
    response = client.post(
        f"/api/datasets/{uploaded_dataset['id']}/analyze",
        json={"chart_type": "bar", "x": "不存在的字段", "y": "销售额"},
    )
    assert response.status_code == 400
    assert "字段不存在" in response.json()["detail"]


def test_ask_trend(client: TestClient, uploaded_dataset: dict) -> None:
    response = client.post(
        f"/api/datasets/{uploaded_dataset['id']}/ask",
        json={"question": "销售额随时间的趋势如何？"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["intent"] == "trend"
    assert payload["spec"]["chart_type"] == "line"
    assert payload["result"]["chart"]


def test_ask_rank(client: TestClient, uploaded_dataset: dict) -> None:
    response = client.post(
        f"/api/datasets/{uploaded_dataset['id']}/ask",
        json={"question": "按地区看，销售额排名前几的是谁？"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["spec"]["chart_type"] == "bar"
    assert payload["spec"]["x"] == "地区"


def test_export_html(client: TestClient, uploaded_dataset: dict) -> None:
    response = client.get(f"/api/datasets/{uploaded_dataset['id']}/export.html")
    assert response.status_code == 200
    assert "DataLoom" in response.text
    assert "关键发现" in response.text
    assert "attachment" in response.headers["content-disposition"]


def test_demo_endpoint(client: TestClient) -> None:
    response = client.post("/api/demo")
    assert response.status_code == 200, response.text
    assert response.json()["rows"] == 1808


def test_dataset_list(client: TestClient, uploaded_dataset: dict) -> None:
    response = client.get("/api/datasets")
    assert response.status_code == 200
    payload = response.json()
    assert any(item["id"] == uploaded_dataset["id"] for item in payload)


def test_insights_are_json_safe(uploaded_dataset: dict) -> None:
    json.dumps(uploaded_dataset, ensure_ascii=False)

