import { ArrowUpRight, CircleAlert, CircleCheck, TriangleAlert } from "lucide-react";
import type { AnalysisSpec, Insight } from "../types";
import { confidenceLabel } from "../format";
import { Chart } from "./Chart";
import { RichText } from "./RichText";

interface InsightCardProps {
  insight: Insight;
  onExplore: (spec: AnalysisSpec) => void;
}

function toneFor(kind: string): string {
  if (["trend", "category"].includes(kind)) return "green";
  if (["correlation", "distribution"].includes(kind)) return "violet";
  if (["missing", "duplicate", "quality", "outlier"].includes(kind)) return "amber";
  return "blue";
}

function ConfidenceIcon({ confidence }: { confidence: Insight["confidence"] }) {
  if (confidence === "high") return <CircleCheck size={13} />;
  if (confidence === "low") return <TriangleAlert size={13} />;
  return <CircleAlert size={13} />;
}

function Spotlight({ insight }: { insight: Insight }) {
  const metrics = insight.metrics;
  let value = "—";
  let label = "关键指标";
  if (typeof metrics.health_score === "number") {
    value = `${metrics.health_score}`;
    label = "数据健康分";
  } else if (typeof metrics.duplicate_rows === "number") {
    value = metrics.duplicate_rows.toLocaleString("zh-CN");
    label = "重复行";
  } else if (typeof metrics.columns === "number") {
    value = `${metrics.columns}`;
    label = "字段数";
  }
  return (
    <div className="spotlight">
      <div className="spotlight-value">{value}</div>
      <div className="spotlight-label">{label}</div>
      <div className="spotlight-grid">
        {Array.from({ length: 16 }).map((_, index) => (
          <span key={index} style={{ opacity: 0.18 + ((index * 7) % 9) / 14 }} />
        ))}
      </div>
    </div>
  );
}

export function InsightCard({ insight, onExplore }: InsightCardProps) {
  const tone = toneFor(insight.kind);
  return (
    <article className={`insight-card tone-${tone}`}>
      <div className="insight-top">
        <span className={`tag tag-${tone}`}>{insight.tag}</span>
        <span className={`confidence confidence-${insight.confidence}`}>
          <ConfidenceIcon confidence={insight.confidence} />
          置信度 {confidenceLabel(insight.confidence)}
        </span>
      </div>
      <h3><RichText text={insight.title} /></h3>
      <p className="insight-summary"><RichText text={insight.summary} /></p>
      {insight.chart ? <Chart option={insight.chart} height={246} /> : <Spotlight insight={insight} />}
      {insight.detail ? <p className="insight-detail"><RichText text={insight.detail} /></p> : null}
      <div className="insight-foot">
        <div className="column-chips">
          {insight.columns.slice(0, 4).map((column) => (
            <span key={column} className="mini-chip">{column}</span>
          ))}
        </div>
        {insight.spec ? (
          <button type="button" className="btn btn-link" onClick={() => onExplore(insight.spec!)}>
            在探索中打开
            <ArrowUpRight size={14} />
          </button>
        ) : null}
      </div>
    </article>
  );
}

