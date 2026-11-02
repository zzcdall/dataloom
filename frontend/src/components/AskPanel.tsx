import { ArrowUpRight, Bot, Loader2, MessageSquareText, Send, Sparkles } from "lucide-react";
import type { AnalysisSpec, AskResponse, DatasetDetail } from "../types";
import { Chart } from "./Chart";
import { RichText } from "./RichText";

interface AskPanelProps {
  dataset: DatasetDetail;
  value: string;
  onChange: (value: string) => void;
  onSubmit: (question?: string) => void;
  response: AskResponse | null;
  loading: boolean;
  onExplore: (spec: AnalysisSpec) => void;
}

const INTENT_LABELS: Record<string, string> = {
  trend: "趋势分析",
  rank: "排名对比",
  correlation: "相关性",
  distribution: "分布",
  compare: "分组对比",
  count: "计数",
  overview: "整体概览",
  line: "折线分析",
  bar: "分组分析",
  scatter: "散点分析",
  histogram: "分布分析",
  table: "数据表",
};

export function AskPanel({ dataset, value, onChange, onSubmit, response, loading, onExplore }: AskPanelProps) {
  return (
    <div className="panel-stack">
      <section className="ask-hero">
        <div className="ask-icon"><Sparkles size={22} /></div>
        <div>
          <h2>直接问这份数据</h2>
          <p>本地规则引擎会把问题翻译成可复现的分析；配置模型后也可以用 LLM 规划。</p>
        </div>
      </section>

      <section className="suggestion-row">
        {dataset.suggestions.map((suggestion) => (
          <button type="button" key={suggestion} className="suggestion-chip" onClick={() => onSubmit(suggestion)} disabled={loading}>
            {suggestion}
          </button>
        ))}
      </section>

      <form
        className="ask-form"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <MessageSquareText size={18} className="ask-form-icon" />
        <input
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="例如：销售额随时间的趋势如何？"
          aria-label="向数据提问"
        />
        <button type="submit" className="btn btn-primary" disabled={loading || !value.trim()}>
          {loading ? <Loader2 size={15} className="spin" /> : <Send size={15} />}
          提问
        </button>
      </form>

      {response ? (
        <section className="answer-card">
          <div className="answer-head">
            <div className="answer-badges">
              <span className="tag tag-violet"><Bot size={12} /> {response.used_llm ? "LLM 辅助" : "本地规则引擎"}</span>
              <span className="tag tag-blue">{INTENT_LABELS[response.intent] ?? response.intent}</span>
            </div>
            <span className="answer-question">{response.question}</span>
          </div>
          <div className="answer-text"><RichText text={response.answer} /></div>
          {response.result?.chart ? <Chart option={response.result.chart} height={340} /> : null}
          <div className="answer-actions">
            {response.spec ? (
              <button type="button" className="btn btn-secondary" onClick={() => onExplore(response.spec!)}>
                在探索中打开
                <ArrowUpRight size={14} />
              </button>
            ) : null}
            {response.spec ? (
              <details className="spec-details">
                <summary>查看分析定义</summary>
                <pre>{JSON.stringify(response.spec, null, 2)}</pre>
              </details>
            ) : null}
          </div>
        </section>
      ) : (
        <section className="ask-empty">
          <MessageSquareText size={24} />
          <p>试试上面的示例问题，或输入一个你关心的业务问题。</p>
        </section>
      )}
    </div>
  );
}

