import { Search } from "lucide-react";
import { useMemo, useState } from "react";
import type { DatasetDetail, Preview } from "../types";
import { formatNumber, formatPercent, kindLabel } from "../format";
import { DataTable } from "./DataTable";

export function DataPanel({ dataset, preview }: { dataset: DatasetDetail; preview: Preview | null }) {
  const [query, setQuery] = useState("");
  const columns = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return dataset.profile.columns_detail;
    return dataset.profile.columns_detail.filter(
      (column) =>
        column.name.toLowerCase().includes(term) ||
        column.examples.some((example) => example.toLowerCase().includes(term)),
    );
  }, [dataset.profile.columns_detail, query]);

  return (
    <div className="panel-stack">
      <div className="section-heading">
        <div>
          <h2>数据预览</h2>
          <p>{preview ? `展示前 ${preview.rows.length} 行，原始数据不会被修改。` : "正在读取数据…"}</p>
        </div>
        <span className="section-count">{dataset.rows.toLocaleString("zh-CN")} 行</span>
      </div>
      {preview ? <DataTable columns={preview.columns} rows={preview.rows} maxHeight={480} /> : null}

      <div className="section-heading spaced">
        <div>
          <h2>字段画像</h2>
          <p>自动识别的类型、缺失率、唯一值与示例。</p>
        </div>
        <div className="search-box">
          <Search size={14} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="搜索字段或示例值"
            aria-label="搜索字段"
          />
        </div>
      </div>

      <div className="column-grid">
        {columns.map((column) => (
          <article className="column-card" key={column.name}>
            <div className="column-head">
              <h3>{column.name}</h3>
              <span className={`type-pill kind-${column.kind}`}>{kindLabel(column.kind)}</span>
            </div>
            <div className="column-stats">
              <div><span>缺失率</span><strong>{formatPercent(column.missing_rate)}</strong></div>
              <div><span>唯一值</span><strong>{formatNumber(column.unique)}</strong></div>
              <div><span>语义</span><strong>{column.semantic === "measure" ? "指标" : column.semantic === "time" ? "时间" : column.semantic === "id" ? "ID" : "维度"}</strong></div>
            </div>
            <div className="column-examples">
              {column.examples.length ? column.examples.map((example) => (
                <span key={example} className="example-chip">{example || "空值"}</span>
              )) : <span className="muted">暂无示例</span>}
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

