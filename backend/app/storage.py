from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import DB_PATH, ensure_dirs


SCHEMA = """
CREATE TABLE IF NOT EXISTS datasets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source_filename TEXT NOT NULL,
    rows INTEGER NOT NULL,
    columns INTEGER NOT NULL,
    size_bytes INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    profile_json TEXT NOT NULL,
    insights_json TEXT NOT NULL,
    suggestions_json TEXT NOT NULL DEFAULT '[]'
);
"""


def connect() -> sqlite3.Connection:
    ensure_dirs()
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    return connection


def init_db() -> None:
    with connect() as connection:
        connection.executescript(SCHEMA)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def create_dataset(
    *,
    dataset_id: str,
    name: str,
    source_filename: str,
    rows: int,
    columns: int,
    size_bytes: int,
    profile: dict[str, Any],
    insights: list[dict[str, Any]],
    suggestions: list[str],
) -> dict[str, Any]:
    created_at = utc_now()
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO datasets
            (id, name, source_filename, rows, columns, size_bytes, created_at,
             profile_json, insights_json, suggestions_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dataset_id,
                name,
                source_filename,
                rows,
                columns,
                size_bytes,
                created_at,
                json.dumps(profile, ensure_ascii=False),
                json.dumps(insights, ensure_ascii=False),
                json.dumps(suggestions, ensure_ascii=False),
            ),
        )
    return get_dataset(dataset_id)  # type: ignore[return-value]


def _row_to_record(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "source_filename": row["source_filename"],
        "rows": row["rows"],
        "columns": row["columns"],
        "size_bytes": row["size_bytes"],
        "created_at": row["created_at"],
        "profile": json.loads(row["profile_json"]),
        "insights": json.loads(row["insights_json"]),
        "suggestions": json.loads(row["suggestions_json"]),
    }


def get_dataset(dataset_id: str) -> dict[str, Any] | None:
    with connect() as connection:
        row = connection.execute("SELECT * FROM datasets WHERE id = ?", (dataset_id,)).fetchone()
    return _row_to_record(row) if row else None


def list_datasets() -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM datasets ORDER BY created_at DESC, rowid DESC"
        ).fetchall()
    records = [_row_to_record(dict(row)) for row in rows]
    return [
        {
            "id": record["id"],
            "name": record["name"],
            "source_filename": record["source_filename"],
            "rows": record["rows"],
            "columns": record["columns"],
            "size_bytes": record["size_bytes"],
            "created_at": record["created_at"],
            "health_score": record["profile"]["quality"]["health_score"],
        }
        for record in records
    ]


def delete_dataset(dataset_id: str) -> bool:
    with connect() as connection:
        cursor = connection.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))
    return cursor.rowcount > 0


def dataset_path(dataset_id: str) -> Path:
    from .config import DATASETS_DIR

    return DATASETS_DIR / f"{dataset_id}.parquet"

