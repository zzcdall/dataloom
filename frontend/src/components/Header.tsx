import {
  BarChart3,
  Download,
  LineChart,
  MessageSquareText,
  Sparkles,
  Table2,
  Trash2,
} from "lucide-react";
import type { DatasetDetail } from "../types";
import { formatBytes, formatDate, formatNumber, formatPercent } from "../format";

export type TabKey = "insights" | "data" | "explore" | "ask";

interface HeaderProps {
  dataset: DatasetDetail;
  tab: TabKey;
  onTab: (tab: TabKey) => void;
  onDelete: () => void;
  exportUrl: string;
}

const TABS: { key: TabKey; label: string; icon: typeof BarChart3 }[] = [
  { key: "insights", label: "关键发现", icon: Sparkles },
  { key: "data", label: "数据与字段", icon: Table2 },
  { key: "explore", label: "交互探索", icon: BarChart3 },
  { key: "ask", label: "提问", icon: MessageSquareText },
];

export function Header({ dataset, tab, onTab, onDelete, exportUrl }: HeaderProps) {
  const quality = dataset.profile.quality;
  return (
    <header className="workspace-header">
      <div className="breadcrumb">工作区 <span>/</span> {dataset.name}</div>
      <div className="header-row">
        <div className="header-title">
          <h1>{dataset.name}</h1>
          <div className="header-meta">
            <span>{formatNumber(dataset.rows)} 行</span>
            <span>{dataset.columns} 列</span>
            <span>{formatBytes(dataset.size_bytes)}</span>
            <span className="quality-inline">完整度 {formatPercent(quality.completeness)}</span>
            <span className="source-name">{dataset.source_filename}</span>
            <span>{formatDate(dataset.created_at)}</span>
          </div>
        </div>
        <div className="header-actions">
          <a className="btn btn-secondary" href={exportUrl} download>
            <Download size={15} />
            导出报告
          </a>
          <button type="button" className="icon-btn danger" onClick={onDelete} aria-label="删除数据集" title="删除数据集">
            <Trash2 size={16} />
          </button>
        </div>
      </div>
      <nav className="tabs" aria-label="工作区导航">
        {TABS.map((item) => {
          const Icon = item.icon;
          return (
            <button
              type="button"
              key={item.key}
              className={`tab ${tab === item.key ? "active" : ""}`}
              onClick={() => onTab(item.key)}
            >
              <Icon size={15} />
              {item.label}
            </button>
          );
        })}
      </nav>
    </header>
  );
}

