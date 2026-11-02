import { Database, FileSpreadsheet, Loader2, Plus, Sparkles } from "lucide-react";
import { useRef } from "react";
import type { DatasetListItem } from "../types";
import { formatBytes, formatNumber } from "../format";
import { Logo } from "./Logo";

interface SidebarProps {
  datasets: DatasetListItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onFile: (file: File) => void;
  onDemo: () => void;
  uploading: boolean;
}

function healthTone(score: number): string {
  if (score >= 92) return "good";
  if (score >= 75) return "ok";
  return "warn";
}

export function Sidebar({ datasets, selectedId, onSelect, onFile, onDemo, uploading }: SidebarProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <Logo size={36} />
        <div>
          <div className="brand-name">DataLoom</div>
          <div className="brand-cn">数织 · 自动分析工作台</div>
        </div>
      </div>

      <div className="sidebar-actions">
        <button
          type="button"
          className="btn btn-primary btn-block"
          disabled={uploading}
          onClick={() => inputRef.current?.click()}
        >
          {uploading ? <Loader2 size={16} className="spin" /> : <Plus size={16} />}
          {uploading ? "正在导入…" : "上传数据"}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.tsv,.xlsx"
          hidden
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) onFile(file);
            event.target.value = "";
          }}
        />
        <button type="button" className="btn btn-subtle btn-block" onClick={onDemo} disabled={uploading}>
          <Sparkles size={15} />
          体验示例数据
        </button>
      </div>

      <div className="sidebar-section-head">
        <span><Database size={13} /> 数据集</span>
        <span className="count">{datasets.length}</span>
      </div>

      <div className="dataset-list">
        {datasets.map((dataset) => (
          <button
            type="button"
            key={dataset.id}
            className={`dataset-item ${dataset.id === selectedId ? "active" : ""}`}
            onClick={() => onSelect(dataset.id)}
          >
            <span className="dataset-icon"><FileSpreadsheet size={16} /></span>
            <span className="dataset-copy">
              <span className="dataset-name">{dataset.name}</span>
              <span className="dataset-meta">
                {formatNumber(dataset.rows)} 行 · {dataset.columns} 列 · {formatBytes(dataset.size_bytes)}
              </span>
            </span>
            <span className={`health-dot ${healthTone(dataset.health_score)}`} title={`健康分 ${dataset.health_score}`} />
          </button>
        ))}
        {!datasets.length ? (
          <div className="sidebar-empty">
            <span>还没有数据集</span>
            <small>上传 CSV 或 Excel 开始</small>
          </div>
        ) : null}
      </div>

      <div className="sidebar-footer">
        <div className="local-badge"><span className="pulse-dot" /> 本地优先 · 数据不出机器</div>
        <div className="version">DataLoom v0.1.0</div>
      </div>
    </aside>
  );
}

