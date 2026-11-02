from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import (
    ALLOWED_EXTENSIONS,
    EXAMPLES_DIR,
    FRONTEND_DIST,
    MAX_UPLOAD_BYTES,
    MAX_UPLOAD_MB,
    ensure_dirs,
)
from .engine import AnalysisError, execute_analysis, preview_rows
from .export import build_html_report
from .ingest import IngestError, parse_upload, save_frame
from .insights import build_suggestions, generate_insights
from .planner import answer_question
from .profiling import profile_dataframe
from .schemas import (
    AnalysisResult,
    AnalysisSpec,
    AskRequest,
    AskResponse,
    DatasetDetail,
    DatasetListItem,
)
from .storage import create_dataset, dataset_path, delete_dataset, get_dataset, init_db, list_datasets


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_dirs()
    init_db()
    yield


app = FastAPI(
    title="DataLoom API",
    version=__version__,
    description="Local-first, auditable automated data analysis.",
    lifespan=lifespan,
)

origins = [
    origin.strip()
    for origin in os.getenv(
        "DATALOOM_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _safe_name(filename: str, requested: str | None) -> str:
    name = (requested or "").strip() or Path(filename).stem or "未命名数据集"
    return name[:120]


def _ingest_bytes(filename: str, content: bytes, requested_name: str | None = None) -> dict[str, Any]:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型。请上传 {', '.join(sorted(ALLOWED_EXTENSIONS))} 文件。",
        )
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"文件超过 {MAX_UPLOAD_MB} MB 上限。")
    try:
        frame, meta = parse_upload(filename, content)
        profile = profile_dataframe(
            frame,
            dropped_empty_rows=meta.get("dropped_empty_rows", 0),
            dropped_empty_columns=meta.get("dropped_empty_columns", 0),
        )
        profile["ingest"] = meta
        insights = generate_insights(frame, profile)
        suggestions = build_suggestions(profile)
    except (IngestError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    dataset_id = uuid.uuid4().hex
    path = dataset_path(dataset_id)
    try:
        save_frame(frame, path)
        record = create_dataset(
            dataset_id=dataset_id,
            name=_safe_name(filename, requested_name),
            source_filename=Path(filename).name,
            rows=profile["rows"],
            columns=profile["columns"],
            size_bytes=len(content),
            profile=profile,
            insights=insights,
            suggestions=suggestions,
        )
    except Exception as exc:  # noqa: BLE001
        if path.exists():
            path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"保存数据集失败：{exc}") from exc
    return record


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "version": __version__, "max_upload_mb": MAX_UPLOAD_MB}


@app.get("/api/datasets", response_model=list[DatasetListItem])
def datasets() -> list[dict[str, Any]]:
    return list_datasets()


@app.post("/api/datasets", response_model=DatasetDetail)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
) -> dict[str, Any]:
    filename = file.filename or "upload.csv"
    chunks = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        chunks.extend(chunk)
        if len(chunks) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail=f"文件超过 {MAX_UPLOAD_MB} MB 上限。")
    return _ingest_bytes(filename, bytes(chunks), name)


@app.post("/api/demo", response_model=DatasetDetail)
def load_demo() -> dict[str, Any]:
    demo_path = EXAMPLES_DIR / "sample_sales.csv"
    if not demo_path.exists():
        raise HTTPException(status_code=404, detail="示例数据不存在，请先运行 examples/generate_sample.py。")
    return _ingest_bytes("sample_sales.csv", demo_path.read_bytes(), "示例：零售销售数据")


@app.get("/api/datasets/{dataset_id}", response_model=DatasetDetail)
def dataset_detail(dataset_id: str) -> dict[str, Any]:
    record = get_dataset(dataset_id)
    if not record:
        raise HTTPException(status_code=404, detail="数据集不存在。")
    return record


@app.delete("/api/datasets/{dataset_id}", status_code=204)
def remove_dataset(dataset_id: str) -> Response:
    record = get_dataset(dataset_id)
    if not record:
        raise HTTPException(status_code=404, detail="数据集不存在。")
    path = dataset_path(dataset_id)
    if path.exists():
        path.unlink(missing_ok=True)
    delete_dataset(dataset_id)
    return Response(status_code=204)


@app.get("/api/datasets/{dataset_id}/preview")
def dataset_preview(dataset_id: str, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    record = get_dataset(dataset_id)
    if not record:
        raise HTTPException(status_code=404, detail="数据集不存在。")
    try:
        return preview_rows(record, limit=limit, offset=offset)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"读取数据失败：{exc}") from exc


@app.post("/api/datasets/{dataset_id}/analyze", response_model=AnalysisResult)
def analyze(dataset_id: str, spec: AnalysisSpec) -> AnalysisResult:
    record = get_dataset(dataset_id)
    if not record:
        raise HTTPException(status_code=404, detail="数据集不存在。")
    try:
        return execute_analysis(record, spec)
    except AnalysisError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/datasets/{dataset_id}/ask", response_model=AskResponse)
def ask(dataset_id: str, request: AskRequest) -> AskResponse:
    record = get_dataset(dataset_id)
    if not record:
        raise HTTPException(status_code=404, detail="数据集不存在。")
    try:
        return answer_question(record, request)
    except AnalysisError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/datasets/{dataset_id}/export.html")
def export_report(dataset_id: str) -> HTMLResponse:
    record = get_dataset(dataset_id)
    if not record:
        raise HTTPException(status_code=404, detail="数据集不存在。")
    html = build_html_report(record)
    return HTMLResponse(
        content=html,
        headers={
            "Content-Disposition": f'attachment; filename="dataloom-report-{dataset_id[:8]}.html"',
            "Cache-Control": "no-store",
        },
    )


@app.get("/", include_in_schema=False)
def index() -> Response:
    index_path = FRONTEND_DIST / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse(
        """
        <!doctype html><html lang="zh-CN"><head><meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width,initial-scale=1"/>
        <title>DataLoom API</title>
        <style>body{font-family:system-ui,sans-serif;background:#f6f7fb;color:#101828;display:grid;place-items:center;min-height:100vh;margin:0}
        .card{background:#fff;border:1px solid #eaecf0;border-radius:18px;padding:32px;max-width:560px;box-shadow:0 12px 40px rgba(16,24,40,.08)}
        code{background:#f2f4f7;padding:2px 6px;border-radius:6px}a{color:#5b5bd6}</style></head>
        <body><div class="card"><h1>DataLoom API is running</h1>
        <p>前端还没有构建。开发模式请运行 <code>cd frontend &amp;&amp; npm run dev</code>，
        或执行 <code>npm run build</code> 后刷新本页。</p>
        <p>API 文档：<a href="/docs">/docs</a></p></div></body></html>
        """
    )


if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str) -> Response:
    if full_path.startswith("api/") or full_path == "api":
        raise HTTPException(status_code=404, detail="API 路径不存在。")
    candidate = FRONTEND_DIST / full_path
    if candidate.is_file():
        return FileResponse(candidate)
    index_path = FRONTEND_DIST / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="前端尚未构建。")

