import { AlertTriangle, ArrowRight, Check, Loader2, Sparkles, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";
import { AskPanel } from "./components/AskPanel";
import { DataPanel } from "./components/DataPanel";
import { ExplorePanel, type ExploreState } from "./components/ExplorePanel";
import { Header, type TabKey } from "./components/Header";
import { InsightsPanel } from "./components/InsightsPanel";
import { Sidebar } from "./components/Sidebar";
import { UploadZone } from "./components/UploadZone";
import type {
  Aggregation,
  AnalysisResult,
  AnalysisSpec,
  AskResponse,
  DatasetDetail,
  DatasetListItem,
  Preview,
  TimeGrain,
} from "./types";

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "发生未知错误，请重试。";
}

function defaultExplore(dataset: DatasetDetail): ExploreState {
  const columns = dataset.profile.columns_detail;
  const measure = columns.find((column) => column.is_measure) ?? columns.find((column) => column.kind === "number");
  const dimension =
    columns.find((column) => column.is_dimension && column.unique > 1 && column.unique <= 30) ??
    columns.find((column) => column.kind !== "number");
  const time = columns.find((column) => column.is_time);
  if (dimension && measure) {
    return {
      chartType: "bar",
      x: dimension.name,
      y: measure.name,
      aggregation: "sum",
      groupBy: "",
      timeGrain: "month",
      sort: "y",
      limit: 12,
    };
  }
  if (time && measure) {
    return {
      chartType: "line",
      x: time.name,
      y: measure.name,
      aggregation: "sum",
      groupBy: "",
      timeGrain: "month",
      sort: "x",
      limit: 200,
    };
  }
  if (measure) {
    return {
      chartType: "histogram",
      x: measure.name,
      y: "",
      aggregation: "count",
      groupBy: "",
      timeGrain: "month",
      sort: "x",
      limit: 30,
    };
  }
  return {
    chartType: "table",
    x: columns[0]?.name ?? "",
    y: "",
    aggregation: "count",
    groupBy: "",
    timeGrain: "month",
    sort: "x",
    limit: 100,
  };
}

function specFromState(state: ExploreState): AnalysisSpec {
  const isCount = state.aggregation === "count" || state.chartType === "histogram";
  return {
    chart_type: state.chartType,
    x: state.x || null,
    y: isCount ? null : state.y || null,
    aggregation: state.chartType === "histogram" ? "count" : state.aggregation,
    group_by: ["bar", "line"].includes(state.chartType) && state.groupBy ? state.groupBy : null,
    time_grain: state.timeGrain,
    filters: [],
    sort: state.chartType === "line" ? "x" : state.sort,
    limit: state.limit,
  };
}

function validateSpec(spec: AnalysisSpec): string | null {
  if (!spec.x) return "请先选择 X 轴或分组字段。";
  if (spec.chart_type === "scatter" && !spec.y) return "散点图需要选择一个数值指标。";
  if (["bar", "line", "table"].includes(spec.chart_type) && spec.aggregation !== "count" && !spec.y) {
    return "请选择一个指标，或把聚合方式改为记录数。";
  }
  return null;
}

function stateFromSpec(spec: AnalysisSpec, fallback: ExploreState): ExploreState {
  return {
    chartType: spec.chart_type,
    x: spec.x ?? fallback.x,
    y: spec.y ?? "",
    aggregation: (spec.aggregation as Aggregation) ?? fallback.aggregation,
    groupBy: spec.group_by ?? "",
    timeGrain: (spec.time_grain as TimeGrain) ?? fallback.timeGrain,
    sort: spec.sort ?? "x",
    limit: spec.limit ?? fallback.limit,
  };
}

function EmptyState({
  onFile,
  onDemo,
  loading,
}: {
  onFile: (file: File) => void;
  onDemo: () => void;
  loading: boolean;
}) {
  return (
    <main className="workspace empty-workspace">
      <div className="landing">
        <div className="landing-grid" aria-hidden="true" />
        <div className="landing-kicker"><span className="pulse-dot" /> LOCAL-FIRST DATA ANALYSIS</div>
        <h1>把表格，<em>织</em>成洞察。</h1>
        <p className="landing-lead">
          上传 CSV 或 Excel，DataLoom 自动完成数据体检、关键发现、交互探索和报告导出。
          默认本地运行，原始数据不离开这台机器。
        </p>
        <UploadZone onFile={onFile} onDemo={onDemo} loading={loading} />
        <div className="feature-row">
          <div className="feature-card">
            <span className="feature-icon"><Sparkles size={17} /></span>
            <h3>自动分析</h3>
            <p>趋势、异常、相关性和分组差异，不用先写 SQL。</p>
          </div>
          <div className="feature-card">
            <span className="feature-icon"><Check size={17} /></span>
            <h3>结论可追溯</h3>
            <p>每条洞察都有计算口径、样本量和置信度。</p>
          </div>
          <div className="feature-card">
            <span className="feature-icon"><ArrowRight size={17} /></span>
            <h3>继续追问</h3>
            <p>用自然语言提问，再一键回到交互探索。</p>
          </div>
        </div>
        <div className="landing-foot">
          <span>CSV · TSV · XLSX</span>
          <span>最大 100 MB</span>
          <span>Apache-2.0</span>
        </div>
      </div>
    </main>
  );
}

export default function App() {
  const [datasets, setDatasets] = useState<DatasetListItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [dataset, setDataset] = useState<DatasetDetail | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [tab, setTab] = useState<TabKey>("insights");
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exploreState, setExploreState] = useState<ExploreState>({
    chartType: "bar",
    x: "",
    y: "",
    aggregation: "sum",
    groupBy: "",
    timeGrain: "month",
    sort: "y",
    limit: 12,
  });
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [analysisBusy, setAnalysisBusy] = useState(false);
  const [exploreDirty, setExploreDirty] = useState(false);
  const [askText, setAskText] = useState("");
  const [askResponse, setAskResponse] = useState<AskResponse | null>(null);
  const [asking, setAsking] = useState(false);
  const autoRan = useRef<string | null>(null);

  const loadDataset = useCallback(async (id: string) => {
    setBusy(true);
    setError(null);
    try {
      const [detail, previewData] = await Promise.all([api.getDataset(id), api.preview(id, 100)]);
      setDataset(detail);
      setPreview(previewData);
      setExploreState(defaultExplore(detail));
      setAnalysis(null);
      setAskResponse(null);
      setAskText("");
      setExploreDirty(false);
      setTab("insights");
      autoRan.current = null;
    } catch (loadError) {
      setError(errorMessage(loadError));
      setDataset(null);
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    api
      .listDatasets()
      .then((items) => {
        if (!active) return;
        setDatasets(items);
        if (items.length) setSelectedId(items[0].id);
      })
      .catch((loadError) => setError(errorMessage(loadError)));
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setDataset(null);
      setPreview(null);
      return;
    }
    if (dataset?.id === selectedId) return;
    void loadDataset(selectedId);
  }, [selectedId, dataset?.id, loadDataset]);

  const refreshList = useCallback(async () => {
    const items = await api.listDatasets();
    setDatasets(items);
    return items;
  }, []);

  const handleUpload = useCallback(
    async (file: File) => {
      setUploading(true);
      setError(null);
      try {
        const detail = await api.uploadDataset(file);
        await refreshList();
        setSelectedId(detail.id);
        setDataset(detail);
        setPreview(await api.preview(detail.id, 100));
        setExploreState(defaultExplore(detail));
        setAnalysis(null);
        setAskResponse(null);
        setAskText("");
        setExploreDirty(false);
        setTab("insights");
        autoRan.current = null;
      } catch (uploadError) {
        setError(errorMessage(uploadError));
      } finally {
        setUploading(false);
      }
    },
    [refreshList],
  );

  const handleDemo = useCallback(async () => {
    setUploading(true);
    setError(null);
    try {
      const detail = await api.loadDemo();
      await refreshList();
      setSelectedId(detail.id);
      setDataset(detail);
      setPreview(await api.preview(detail.id, 100));
      setExploreState(defaultExplore(detail));
      setAnalysis(null);
      setAskResponse(null);
      setAskText("");
      setExploreDirty(false);
      setTab("insights");
      autoRan.current = null;
    } catch (demoError) {
      setError(errorMessage(demoError));
    } finally {
      setUploading(false);
    }
  }, [refreshList]);

  const handleDelete = useCallback(async () => {
    if (!dataset) return;
    const confirmed = window.confirm(`确定删除「${dataset.name}」？原始文件与分析记录都会被删除。`);
    if (!confirmed) return;
    setBusy(true);
    setError(null);
    try {
      await api.deleteDataset(dataset.id);
      const items = await refreshList();
      setDataset(null);
      setPreview(null);
      setAnalysis(null);
      setAskResponse(null);
      setSelectedId(items[0]?.id ?? null);
    } catch (deleteError) {
      setError(errorMessage(deleteError));
    } finally {
      setBusy(false);
    }
  }, [dataset, refreshList]);

  const runExplore = useCallback(
    async (override?: AnalysisSpec) => {
      if (!dataset) return;
      const spec = override ?? specFromState(exploreState);
      const validation = validateSpec(spec);
      if (validation) {
        setError(validation);
        return;
      }
      setAnalysisBusy(true);
      setError(null);
      try {
        const result = await api.analyze(dataset.id, spec);
        setAnalysis(result);
        setExploreDirty(false);
      } catch (analysisError) {
        setError(errorMessage(analysisError));
      } finally {
        setAnalysisBusy(false);
      }
    },
    [dataset, exploreState],
  );

  const changeExplore = useCallback((patch: Partial<ExploreState>) => {
    setExploreDirty(true);
    setExploreState((previous) => {
      const next = { ...previous, ...patch };
      const columns = dataset?.profile.columns_detail ?? [];
      const numeric = columns.filter((column) => column.kind === "number");
      if (patch.chartType) {
        if (["scatter", "histogram"].includes(next.chartType) && !numeric.some((column) => column.name === next.x)) {
          next.x = numeric[0]?.name ?? "";
        }
        if (next.chartType === "histogram") {
          next.aggregation = "count";
          next.y = "";
        }
        if (next.chartType === "scatter" && !numeric.some((column) => column.name === next.y)) {
          next.y = numeric.find((column) => column.name !== next.x)?.name ?? numeric[0]?.name ?? "";
        }
        if (next.chartType === "line" && !next.x) {
          next.x = columns.find((column) => column.is_time)?.name ?? "";
        }
        if (["bar", "line", "table"].includes(next.chartType) && !next.y && next.aggregation !== "count") {
          next.y = numeric[0]?.name ?? "";
        }
      }
      if (patch.aggregation && patch.aggregation !== "count" && !next.y) {
        next.y = numeric[0]?.name ?? "";
      }
      return next;
    });
  }, [dataset]);

  const resetExplore = useCallback(() => {
    if (dataset) {
      setExploreState(defaultExplore(dataset));
      setExploreDirty(true);
    }
  }, [dataset]);

  const openExplore = useCallback(
    (spec: AnalysisSpec) => {
      const next = stateFromSpec(spec, exploreState);
      if (dataset) autoRan.current = dataset.id;
      setExploreState(next);
      setTab("explore");
      setExploreDirty(false);
      void runExplore(spec);
    },
    [dataset, exploreState, runExplore],
  );

  const submitAsk = useCallback(
    async (question?: string) => {
      if (!dataset) return;
      const text = (question ?? askText).trim();
      if (!text) return;
      setAskText(text);
      setAsking(true);
      setError(null);
      try {
        setAskResponse(await api.ask(dataset.id, text));
      } catch (askError) {
        setError(errorMessage(askError));
      } finally {
        setAsking(false);
      }
    },
    [askText, dataset],
  );

  useEffect(() => {
    if (tab !== "explore" || !dataset || analysis || analysisBusy) return;
    if (autoRan.current === dataset.id) return;
    autoRan.current = dataset.id;
    void runExplore();
  }, [tab, dataset, analysis, analysisBusy, runExplore]);

  const selected = datasets.find((item) => item.id === selectedId) ?? null;
  const showEmpty = !dataset && !busy && !uploading && !selectedId;

  return (
    <div className="app-shell">
      <Sidebar
        datasets={datasets}
        selectedId={selectedId}
        onSelect={setSelectedId}
        onFile={handleUpload}
        onDemo={handleDemo}
        uploading={uploading}
      />
      <div className="workspace-wrap">
        {(busy || uploading || analysisBusy) && <div className="top-progress" />}
        {error ? (
          <div className="error-banner" role="alert">
            <AlertTriangle size={16} />
            <span>{error}</span>
            <button type="button" onClick={() => setError(null)} aria-label="关闭错误提示"><X size={15} /></button>
          </div>
        ) : null}

        {showEmpty ? <EmptyState onFile={handleUpload} onDemo={handleDemo} loading={uploading} /> : null}

        {!showEmpty && !dataset && !error && (busy || selectedId) ? (
          <main className="workspace loading-workspace">
            <div className="loading-card">
              <Loader2 size={24} className="spin" />
              <span>正在读取数据集…</span>
            </div>
          </main>
        ) : null}

        {dataset ? (
          <main className="workspace">
            <Header
              dataset={dataset}
              tab={tab}
              onTab={setTab}
              onDelete={handleDelete}
              exportUrl={api.exportUrl(dataset.id)}
            />
            <div className="workspace-body">
              {tab === "insights" ? (
                <InsightsPanel dataset={dataset} onExplore={openExplore} onOpenData={() => setTab("data")} />
              ) : null}
              {tab === "data" ? <DataPanel dataset={dataset} preview={preview} /> : null}
              {tab === "explore" ? (
                <ExplorePanel
                  dataset={dataset}
                  state={exploreState}
                  onChange={changeExplore}
                  onRun={() => void runExplore()}
                  onReset={resetExplore}
                  result={analysis}
                  loading={analysisBusy}
                />
              ) : null}
              {tab === "ask" ? (
                <AskPanel
                  dataset={dataset}
                  value={askText}
                  onChange={setAskText}
                  onSubmit={submitAsk}
                  response={askResponse}
                  loading={asking}
                  onExplore={openExplore}
                />
              ) : null}
              {tab === "explore" && exploreDirty && analysis ? (
                <div className="stale-hint">配置已修改，点击「运行分析」刷新结果。</div>
              ) : null}
            </div>
          </main>
        ) : null}

        {selected && !dataset && !busy && !uploading && error ? (
          <div className="workspace-error-state">
            <AlertTriangle size={22} />
            <p>无法打开「{selected.name}」，请重试或重新上传。</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}

