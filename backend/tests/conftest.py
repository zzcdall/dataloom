from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest


os.environ["DATALOOM_DATA_DIR"] = tempfile.mkdtemp(prefix="dataloom-tests-")
BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def sample_csv() -> bytes:
    return (REPO_DIR / "examples" / "sample_sales.csv").read_bytes()


@pytest.fixture(scope="session")
def uploaded_dataset(client: TestClient, sample_csv: bytes) -> dict:
    response = client.post(
        "/api/datasets",
        files={"file": ("sample_sales.csv", sample_csv, "text/csv")},
    )
    assert response.status_code == 200, response.text
    return response.json()

