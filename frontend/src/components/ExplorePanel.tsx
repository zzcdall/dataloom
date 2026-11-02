import {
  Activity,
  BarChart3,
  LineChart,
  Loader2,
  Play,
  RotateCcw,
  ScatterChart,
  Table2,
} from "lucide-react";
import type { ReactNode } from "react";
import type { Aggregation, AnalysisResult, ChartType, DatasetDetail, TimeGrain } from "../types";
import { DataTable } from "./DataTable";
import { Chart } from "./Chart";

export interface ExploreState {
  chartType: ChartType;
  x: string;
  y: string;
  aggregation: Aggregation;
  groupBy: string;
  timeGrain: TimeGrain;
  sort: "x" | "y" | "none";
  limit: number;
}

interface ExplorePanelProps {
  dataset: DatasetDetail;
  state: ExploreState;
  onChange: (patch: Partial<ExploreState>) => void;
  onRun: () => void;
  onReset: () => void;
  result: AnalysisResult | null;
  loading: boolean;
}

const CHART_TYPES: { key: ChartType; label: string; icon: typeof BarChart3 }[] = [
  { key: "bar", label: "柱状图", icon: BarChart3 },
  { key: "line", label: "折线图", icon: LineChart },
  { key: "scatter", label: "散点图", icon: ScatterChart },
  { key: "histogram", label: "直方图", icon: Activity },
  { key: "table", label: "数据表", icon: Table2 },
];

const AGGREGATIONS: { value: Aggregation; label: string }[] = [
  { value: "sum", label: "求和" },
  { value: "avg", label: "平均值" },
  { value: "count", label: "记录数" },
  { value: "median", label: "中位数" },
  { value: "min", label: "最小值" },
  { value: "max", label: "最大值" },
  { value: "count_distinct", label: "去重计数" },
];

function SelectField({
  label,
  value,
  onChange,
  children,
  disabled,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  children: ReactNode;
  disabled?: boolean;
}) {
  return (
    <label className="control-field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)} disabled={disabled}>
        {children}
      </select>
    </label>
  );
}

export function ExplorePanel({ dataset, state, onChange, onRun, onReset, result, loading }: ExplorePanelProps) {
  const columns = dataset.profile.columns_detail;
  const numeric = columns.filter((column) => column.kind === "number");
  const dimensions = columns.filter((column) => column.kind !== "number" || column.unique <= 30);
  const xColumn = columns.find((column) => column.name === state.x);
  const showTimeGrain = state.chartType === "line" && xColumn?.kind === "datetime";
  const needsY = !["histogram"].includes(state.chartType);
  const showAggregation = ["bar", "line", "table"].includes(state.chartType);
  const showGroup = ["bar", "line"].includes(state.chartType);
  const showSort = ["bar", "table"].includes(state.chartType);
  const xOptions = state.chartType === "scatter" || state.chartType === "histogram" ? numeric : columns;

  return (
    <div className="panel-stack">
      <section className="explore-controls">
        <div className="control-head">
          <div>
            <h2>交互探索</h2>
            <p>选择字段和聚合方式，分析会实时重新计算。</p>
          </div>
          <div className="chart-type-switch" role="group" aria-label="图表类型">
            {CHART_TYPES.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  type="button"
                  key={item.key}
                  className={state.chartType === item.key ? "active" : ""}
                  onClick={() => onChange({ chartType: item.key })}
                  title={item.label}
                >
                  <Icon size={15} />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="control-grid">
          <SelectField label={state.chartType === "histogram" ? "数值字段" : "X 轴 / 分组"} value={state.x} onChange={(value) => onChange({ x: value })}>
            {xOptions.map((column) => (
              <option key={column.name} value={column.name}>{column.name}</option>
            ))}
          </SelectField>

          {needsY ? (
            <SelectField
              label="指标"
              value={state.aggregation === "count" ? "" : state.y}
              onChange={(value) =>
                onChange({
                  y: value,
                  aggregation: value ? (state.aggregation === "count" ? "sum" : state.aggregation) : "count",
                })
              }
              disabled={state.aggregation === "count"}
            >
              <option value="">{state.aggregation === "count" ? "记录数（自动）" : "选择指标"}</option>
              {numeric.map((column) => (
                <option key={column.name} value={column.name}>{column.name}</option>
              ))}
            </SelectField>
          ) : null}

          {showAggregation ? (
            <SelectField label="聚合方式" value={state.aggregation} onChange={(value) => onChange({ aggregation: value as Aggregation })}>
              {AGGREGATIONS.map((item) => (
                <option key={item.value} value={item.value}>{item.label}</option>
              ))}
            </SelectField>
          ) : null}

          {showGroup ? (
            <SelectField label="按…拆分" value={state.groupBy} onChange={(value) => onChange({ groupBy: value })}>
              <option value="">不拆分</option>
              {dimensions.filter((column) => column.name !== state.x && column.unique <= 30).map((column) => (
                <option key={column.name} value={column.name}>{column.name}</option>
              ))}
            </SelectField>
          ) : null}

          {showTimeGrain ? (
            <SelectField label="时间粒度" value={state.timeGrain} onChange={(value) => onChange({ timeGrain: value as TimeGrain })}>
              <option value="day">按日</option>
              <option value="week">按周</option>
              <option value="month">按月</option>
              <option value="quarter">按季度</option>
              <option value="year">按年</option>
            </SelectField>
          ) : null}

          {showSort ? (
            <SelectField label="排序" value={state.sort} onChange={(value) => onChange({ sort: value as "x" | "y" | "none" })}>
              <option value="y">按指标降序</option>
              <option value="x">按维度升序</option>
              <option value="none">不排序</option>
            </SelectField>
          ) : null}

          <label className="control-field">
            <span>返回行数</span>
            <input
              type="number"
              min={1}
              max={500}
              value={state.limit}
              onChange={(event) => onChange({ limit: Math.max(1, Math.min(500, Number(event.target.value) || 1)) })}
            />
          </label>
        </div>

        <div className="control-actions">
          <button type="button" className="btn btn-primary" onClick={onRun} disabled={loading || !state.x}>
            {loading ? <Loader2 size={15} className="spin" /> : <Play size={15} />}
            {loading ? "计算中…" : "运行分析"}
          </button>
          <button type="button" className="btn btn-ghost" onClick={onReset} disabled={loading}>
            <RotateCcw size={14} />
            重置
          </button>
          <span className="control-hint">结果由 DuckDB 直接查询 Parquet 生成</span>
        </div>
      </section>

      {result ? (
        <section className="result-card">
          <div className="result-head">
            <div>
              <span className="eyebrow">分析结果</span>
              <h3>{result.summary}</h3>
            </div>
            <div className="result-meta">
              <span>{result.row_count.toLocaleString("zh-CN")} 组 / 行</span>
              <span>{result.query_ms.toFixed(0)} ms</span>
            </div>
          </div>
          {result.chart ? <Chart option={result.chart} height={390} /> : null}
          {!result.chart && result.rows.length ? (
            <DataTable
              columns={Object.keys(result.rows[0]).map((name) => ({ name }))}
              rows={result.rows}
              maxHeight={440}
            />
          ) : null}
          {result.chart && result.rows.length ? (
            <details className="result-details">
              <summary>查看结果数据</summary>
              <DataTable
                columns={Object.keys(result.rows[0]).map((name) => ({ name }))}
                rows={result.rows}
                maxHeight={320}
                dense
              />
            </details>
          ) : null}
        </section>
      ) : (
        <section className="empty-result">
          <div className="empty-icon"><BarChart3 size={26} /></div>
          <h3>{loading ? "正在计算…" : "选择字段，开始探索"}</h3>
          <p>支持趋势、排名、相关性、分布和数据表五种分析方式。</p>
        </section>
      )}
    </div>
  );
}

