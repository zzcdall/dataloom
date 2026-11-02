from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


ChartType = Literal["line", "bar", "scatter", "histogram", "table"]
Aggregation = Literal["sum", "avg", "count", "min", "max", "median", "count_distinct"]
FilterOp = Literal["=", "!=", ">", ">=", "<", "<=", "in", "contains", "between"]
TimeGrain = Literal["day", "week", "month", "quarter", "year"]


class Filter(BaseModel):
    column: str
    op: FilterOp
    value: Any = None
    value2: Any = None


class AnalysisSpec(BaseModel):
    chart_type: ChartType = "bar"
    x: str | None = None
    y: str | None = None
    aggregation: Aggregation = "sum"
    group_by: str | None = None
    time_grain: TimeGrain = "month"
    filters: list[Filter] = Field(default_factory=list)
    sort: Literal["x", "y", "none"] = "x"
    limit: int = Field(default=50, ge=1, le=2000)

    @field_validator("limit")
    @classmethod
    def cap_limit(cls, value: int) -> int:
        return min(value, 2000)

    @model_validator(mode="after")
    def require_columns(self) -> "AnalysisSpec":
        if self.chart_type in {"line", "bar", "scatter", "histogram"} and not self.x:
            raise ValueError("x is required for this chart type")
        if self.chart_type in {"line", "bar", "table"} and self.aggregation != "count" and not self.y:
            raise ValueError("y is required unless aggregation is count")
        if self.chart_type == "scatter" and not self.y:
            raise ValueError("y is required for scatter charts")
        return self


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class ColumnProfile(BaseModel):
    name: str
    kind: Literal["number", "string", "datetime", "boolean"]
    dtype: str
    missing: int
    missing_rate: float
    unique: int
    is_measure: bool
    is_dimension: bool
    is_time: bool
    semantic: Literal["measure", "dimension", "time", "id", "flag"]
    examples: list[str] = Field(default_factory=list)
    top_values: list[dict[str, Any]] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)


class QualityReport(BaseModel):
    completeness: float
    duplicate_rows: int
    duplicate_rate: float
    health_score: int
    constant_columns: list[str] = Field(default_factory=list)
    high_cardinality_columns: list[str] = Field(default_factory=list)
    dropped_empty_rows: int = 0
    dropped_empty_columns: int = 0


class Profile(BaseModel):
    rows: int
    columns: int
    columns_detail: list[ColumnProfile]
    quality: QualityReport
    ingest: dict[str, Any] = Field(default_factory=dict)


class Insight(BaseModel):
    id: str
    kind: str
    tag: str
    title: str
    summary: str
    detail: str = ""
    confidence: Literal["high", "medium", "low"] = "medium"
    score: float = 0
    chart: dict[str, Any] | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    columns: list[str] = Field(default_factory=list)
    spec: AnalysisSpec | None = None


class DatasetDetail(BaseModel):
    id: str
    name: str
    source_filename: str
    rows: int
    columns: int
    size_bytes: int
    created_at: str
    profile: Profile
    insights: list[Insight]
    suggestions: list[str] = Field(default_factory=list)


class DatasetListItem(BaseModel):
    id: str
    name: str
    source_filename: str
    rows: int
    columns: int
    size_bytes: int
    created_at: str
    health_score: int


class AnalysisResult(BaseModel):
    spec: AnalysisSpec
    chart: dict[str, Any] | None = None
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    summary: str = ""
    query_ms: float = 0
    row_count: int = 0


class AskResponse(BaseModel):
    question: str
    answer: str
    intent: str
    spec: AnalysisSpec | None = None
    result: AnalysisResult | None = None
    used_llm: bool = False

