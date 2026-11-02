from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from typing import Any

import pandas as pd

from .config import ALLOWED_EXTENSIONS
from .profiling import RATE_KEYWORDS, TIME_KEYWORDS, is_id_like, name_matches


ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "gbk", "big5", "latin-1")
BOOLEAN_TRUE = {"true", "yes", "y", "是", "有", "1"}
BOOLEAN_FALSE = {"false", "no", "n", "否", "无", "0"}


class IngestError(ValueError):
    pass


def detect_encoding(content: bytes) -> str:
    sample = content[:131072]
    for encoding in ENCODINGS:
        try:
            sample.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    return "latin-1"


def detect_delimiter(sample: str, extension: str) -> str:
    if extension == ".tsv":
        return "\t"
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except csv.Error:
        return ","


def _clean_columns(columns: list[Any]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for index, column in enumerate(columns):
        text = re.sub(r"\s+", " ", str(column).replace("\n", " ")).strip()
        if not text or text.lower().startswith("unnamed:"):
            text = f"column_{index + 1}"
        base = text
        suffix = 2
        while text in seen:
            text = f"{base}_{suffix}"
            suffix += 1
        seen.add(text)
        cleaned.append(text)
    return cleaned


def _datetime_candidate(series: pd.Series, name: str) -> pd.Series | None:
    non_null = series.dropna()
    if non_null.empty:
        return None
    text = non_null.astype("string").head(80)
    hinted = name_matches(name, TIME_KEYWORDS)
    looks_like_date = bool(
        text.str.contains(r"\d{4}[-/年]\d{1,2}|\d{1,2}:\d{2}", regex=True).mean() >= 0.6
    )
    if not (hinted or looks_like_date):
        return None
    try:
        converted = pd.to_datetime(series, errors="coerce", format="mixed")
    except (TypeError, ValueError):
        return None
    valid_rate = converted.notna().sum() / max(series.notna().sum(), 1)
    if valid_rate < 0.8:
        return None
    if isinstance(converted.dtype, pd.DatetimeTZDtype):
        converted = converted.dt.tz_localize(None)
    return converted


def _numeric_candidate(series: pd.Series, name: str) -> pd.Series | None:
    if is_id_like(name, series):
        return None
    text = series.astype("string").str.strip()
    non_null = int(text.notna().sum())
    if non_null == 0:
        return None
    cleaned = text.str.replace(r"[,，\s￥¥$€£]", "", regex=True)
    has_percent = cleaned.str.endswith("%").fillna(False)
    cleaned = cleaned.str.replace("%", "", regex=False)
    converted = pd.to_numeric(cleaned, errors="coerce")
    if converted.notna().sum() / non_null < 0.9:
        return None
    sample = text.dropna().head(50)
    if sample.str.fullmatch(r"0\d+").any():
        return None
    if has_percent.mean() > 0.8 and name_matches(name, RATE_KEYWORDS):
        converted = converted / 100
    return converted


def _boolean_candidate(series: pd.Series) -> pd.Series | None:
    normalized = series.astype("string").str.strip().str.lower()
    values = set(normalized.dropna().unique().tolist())
    if not values or len(values) > 2:
        return None
    if not values.issubset(BOOLEAN_TRUE | BOOLEAN_FALSE):
        return None
    mapping = {**{value: True for value in BOOLEAN_TRUE}, **{value: False for value in BOOLEAN_FALSE}}
    return normalized.map(mapping).astype("boolean")


def prepare_dataframe(frame: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    if frame is None or frame.empty:
        raise IngestError("表格中没有可读取的数据。")
    frame = frame.copy()
    frame.columns = _clean_columns(list(frame.columns))

    dropped_empty_rows = int(frame.isna().all(axis=1).sum())
    dropped_empty_columns = int(frame.isna().all(axis=0).sum())
    if dropped_empty_rows:
        frame = frame.dropna(axis=0, how="all")
    if dropped_empty_columns:
        frame = frame.dropna(axis=1, how="all")
    if frame.empty or len(frame.columns) == 0:
        raise IngestError("清洗空行空列后没有剩余数据。")

    for name in list(frame.columns):
        series = frame[name]
        if pd.api.types.is_datetime64_any_dtype(series) or pd.api.types.is_numeric_dtype(series):
            continue
        if not (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series) or isinstance(series.dtype, pd.CategoricalDtype)):
            continue

        datetime_values = _datetime_candidate(series, name)
        if datetime_values is not None:
            frame[name] = datetime_values
            continue
        boolean_values = _boolean_candidate(series)
        if boolean_values is not None:
            frame[name] = boolean_values
            continue
        numeric_values = _numeric_candidate(series, name)
        if numeric_values is not None:
            frame[name] = numeric_values
            continue
        frame[name] = series.astype("string")

    for name in frame.columns:
        if isinstance(frame[name].dtype, pd.DatetimeTZDtype):
            frame[name] = frame[name].dt.tz_localize(None)

    frame = frame.reset_index(drop=True)
    return frame, dropped_empty_rows, dropped_empty_columns


def parse_upload(filename: str, content: bytes) -> tuple[pd.DataFrame, dict[str, Any]]:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise IngestError(f"不支持的文件类型 {suffix or '(无扩展名)'}。支持：{allowed}")
    if not content:
        raise IngestError("上传的文件为空。")

    if suffix == ".xlsx":
        try:
            frame = pd.read_excel(io.BytesIO(content), sheet_name=0, engine="openpyxl")
        except Exception as exc:  # noqa: BLE001
            raise IngestError(f"无法读取 Excel 文件：{exc}") from exc
        meta = {"encoding": "xlsx", "delimiter": None, "sheet": 0}
    else:
        encoding = detect_encoding(content)
        sample = content[:131072].decode(encoding, errors="replace")
        delimiter = detect_delimiter(sample, suffix)
        try:
            frame = pd.read_csv(io.BytesIO(content), encoding=encoding, sep=delimiter)
        except Exception as exc:  # noqa: BLE001
            try:
                frame = pd.read_csv(io.BytesIO(content), encoding=encoding, sep=None, engine="python")
            except Exception as fallback_exc:  # noqa: BLE001
                raise IngestError(f"无法读取 CSV 文件：{exc}") from fallback_exc
        meta = {"encoding": encoding, "delimiter": delimiter, "sheet": None}

    frame, dropped_rows, dropped_columns = prepare_dataframe(frame)
    meta.update(
        {
            "dropped_empty_rows": dropped_rows,
            "dropped_empty_columns": dropped_columns,
        }
    )
    return frame, meta


def save_frame(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False, engine="pyarrow")


def load_frame(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path)

