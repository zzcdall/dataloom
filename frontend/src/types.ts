export type ColumnKind = "number" | "string" | "datetime" | "boolean";

export type Semantic = "measure" | "dimension" | "time" | "id" | "flag";

export interface ColumnProfile {
  name: string;
  kind: ColumnKind;
  dtype: string;
  missing: number;
  missing_rate: number;
  unique: number;
  is_measure: boolean;
  is_dimension: boolean;
  is_time: boolean;
  semantic: Semantic;
  examples: string[];
  top_values: { value: string; count: number }[];
  stats: Record<string, number | string | null>;
}

export interface QualityReport {
  completeness: number;
  duplicate_rows: number;
  duplicate_rate: number;
  health_score: number;
  constant_columns: string[];
  high_cardinality_columns: string[];
  dropped_empty_rows: number;
  dropped_empty_columns: number;
}

export interface Profile {
  rows: number;
  columns: number;
  columns_detail: ColumnProfile[];
  quality: QualityReport;
  ingest: Record<string, unknown>;
}

export type ChartType = "line" | "bar" | "scatter" | "histogram" | "table";
export type Aggregation = "sum" | "avg" | "count" | "min" | "max" | "median" | "count_distinct";
export type TimeGrain = "day" | "week" | "month" | "quarter" | "year";

export interface Filter {
  column: string;
  op: "=" | "!=" | ">" | ">=" | "<" | "<=" | "in" | "contains" | "between";
  value?: unknown;
  value2?: unknown;
}

export interface AnalysisSpec {
  chart_type: ChartType;
  x?: string | null;
  y?: string | null;
  aggregation: Aggregation;
  group_by?: string | null;
  time_grain?: TimeGrain;
  filters?: Filter[];
  sort?: "x" | "y" | "none";
  limit?: number;
}

export interface Insight {
  id: string;
  kind: string;
  tag: string;
  title: string;
  summary: string;
  detail: string;
  confidence: "high" | "medium" | "low";
  score: number;
  chart: Record<string, unknown> | null;
  metrics: Record<string, unknown>;
  columns: string[];
  spec: AnalysisSpec | null;
}

export interface DatasetDetail {
  id: string;
  name: string;
  source_filename: string;
  rows: number;
  columns: number;
  size_bytes: number;
  created_at: string;
  profile: Profile;
  insights: Insight[];
  suggestions: string[];
}

export interface DatasetListItem {
  id: string;
  name: string;
  source_filename: string;
  rows: number;
  columns: number;
  size_bytes: number;
  created_at: string;
  health_score: number;
}

export interface AnalysisResult {
  spec: AnalysisSpec;
  chart: Record<string, unknown> | null;
  columns: string[];
  rows: Record<string, unknown>[];
  summary: string;
  query_ms: number;
  row_count: number;
}

export interface AskResponse {
  question: string;
  answer: string;
  intent: string;
  spec: AnalysisSpec | null;
  result: AnalysisResult | null;
  used_llm: boolean;
}

export interface PreviewColumn {
  name: string;
  kind: ColumnKind;
  dtype: string;
}

export interface Preview {
  columns: PreviewColumn[];
  rows: Record<string, unknown>[];
  limit: number;
  offset: number;
}

