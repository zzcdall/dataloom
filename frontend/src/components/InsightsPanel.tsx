import { AlertTriangle, ArrowUpRight, CheckCircle2, CircleDashed, Sparkles } from "lucide-react";
import type { CSSProperties } from "react";
import type { AnalysisSpec, DatasetDetail, Insight } from "../types";
import { formatPercent } from "../format";
import { InsightCard } from "./InsightCard";
import { RichText } from "./RichText";

interface InsightsPanelProps {
  dataset: DatasetDetail;
  onExplore: (spec: AnalysisSpec) => void;
  onOpenData: () => void;
}

function Stat({ label, value, hint, tone }: { label: string; value: string; hint: string; tone?: string }) {
  return (
    <div className={`stat-card ${tone ?? ""}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      <div className="stat-hint">{hint}</div>
    </div>
  );
}

export function InsightsPanel({ dataset, onExplore, onOpenData }: InsightsPanelProps) {
  const quality = dataset.profile.quality;
  const overview = dataset.insights.find((insight) => insight.kind === "overview");
  const insights = dataset.insights.filter((insight) => insight.kind !== "overview");
  const score = quality.health_score;
  const scoreTone = score >= 92 ? "good" : score >= 75 ? "ok" : "warn";
  return (
    <div className="panel-stack">
      <section className="overview-hero">
        <div className="overview-copy">
          <div className="eyebrow"><Sparkles size={14} /> 自动分析完成</div>
          <h2>{overview?.title ?? `${dataset.rows.toLocaleString("zh-CN")} 行数据`}</h2>
          <p className="overview-summary">
            <RichText text={overview?.summary ?? "已读取字段并生成数据画像。"} />
          </p>
          <div className="overview-meta">
            <span><CheckCircle2 size={14} /> {insights.length} 条关键发现</span>
            <span><CircleDashed size={14} /> 完整度 {formatPercent(quality.completeness)}</span>
            {quality.duplicate_rows ? <span><AlertTriangle size={14} /> {quality.duplicate_rows} 行重复</span> : null}
          </div>
        </div>
        <div className={`score-ring ${scoreTone}`} style={{ "--score": `${score * 3.6}deg` } as CSSProperties}>
          <div className="score-inner">
            <strong>{score}</strong>
            <span>健康分</span>
          </div>
        </div>
      </section>

      <section className="stats-row">
        <Stat label="数据完整度" value={formatPercent(quality.completeness)} hint="非空单元格占比" />
        <Stat label="重复记录" value={quality.duplicate_rows.toLocaleString("zh-CN")} hint="完全相同的行" tone={quality.duplicate_rows ? "warn" : ""} />
        <Stat label="字段数量" value={`${dataset.columns}`} hint={`${dataset.profile.columns_detail.filter((column) => column.is_measure).length} 个数值字段`} />
        <Stat label="时间字段" value={`${dataset.profile.columns_detail.filter((column) => column.is_time).length}`} hint="可用于趋势分析" />
      </section>

      <div className="section-heading">
        <div>
          <h2>关键发现</h2>
          <p>每条结论都来自确定性统计计算，可点开查看原始分析。</p>
        </div>
        <span className="section-count">{insights.length} 条</span>
      </div>

      <section className="insight-grid">
        {insights.map((insight: Insight) => (
          <InsightCard key={insight.id} insight={insight} onExplore={onExplore} />
        ))}
      </section>

      <section className="quality-strip">
        <div>
          <h3>数据质量提示</h3>
          <p>
            导出报告前建议确认缺失值、重复行和异常值是否符合业务实际。DataLoom 不会自动修改你的原始数据。
          </p>
        </div>
        <button type="button" className="btn btn-secondary" onClick={onOpenData}>
          查看字段画像
          <ArrowUpRight size={14} />
        </button>
      </section>
    </div>
  );
}

