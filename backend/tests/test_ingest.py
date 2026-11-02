from __future__ import annotations

import io

import pandas as pd
from fastapi.testclient import TestClient


def test_upload_xlsx(client: TestClient) -> None:
    frame = pd.DataFrame(
        {
            "日期": ["2025-01-01", "2025-01-02", "2025-01-03"],
            "地区": ["华东", "华北", "华东"],
            "销售额": [120.5, 80.0, 200.25],
        }
    )
    buffer = io.BytesIO()
    frame.to_excel(buffer, index=False, engine="openpyxl")
    response = client.post(
        "/api/datasets",
        files={
            "file": (
                "upload.xlsx",
                buffer.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["columns"] == 3
    assert payload["rows"] == 3
    columns = {column["name"]: column for column in payload["profile"]["columns_detail"]}
    assert columns["日期"]["kind"] == "datetime"
    assert columns["销售额"]["kind"] == "number"


def test_upload_gbk_csv(client: TestClient) -> None:
    text = "日期,金额,地区\n2025-01-01,100,华东\n2025-01-02,200,华北\n"
    response = client.post(
        "/api/datasets",
        files={"file": ("gbk.csv", text.encode("gb18030"), "text/csv")},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    columns = {column["name"]: column for column in payload["profile"]["columns_detail"]}
    assert columns["日期"]["kind"] == "datetime"
    assert columns["金额"]["kind"] == "number"


def test_reject_unsupported_extension(client: TestClient) -> None:
    response = client.post(
        "/api/datasets",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400


def test_reject_empty_file(client: TestClient) -> None:
    response = client.post(
        "/api/datasets",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert response.status_code == 400

