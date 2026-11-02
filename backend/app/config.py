from __future__ import annotations

import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("DATALOOM_DATA_DIR", str(ROOT_DIR / "data"))).resolve()
DATASETS_DIR = DATA_DIR / "datasets"
DB_PATH = DATA_DIR / "dataloom.db"
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"
EXAMPLES_DIR = ROOT_DIR / "examples"

MAX_UPLOAD_MB = int(os.getenv("DATALOOM_MAX_UPLOAD_MB", "100"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

LLM_BASE_URL = os.getenv("DATALOOM_LLM_BASE_URL", "").strip()
LLM_API_KEY = os.getenv("DATALOOM_LLM_API_KEY", "").strip()
LLM_MODEL = os.getenv("DATALOOM_LLM_MODEL", "").strip()

ALLOWED_EXTENSIONS = {".csv", ".tsv", ".xlsx"}


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)

