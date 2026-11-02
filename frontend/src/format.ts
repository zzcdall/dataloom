import type { ColumnKind } from "./types";

const numberFormatter = new Intl.NumberFormat("zh-CN", {
  maximumFractionDigits: 2,
});

export function formatNumber(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "number" && Number.isFinite(value)) {
    if (Math.abs(value) >= 100_000_000) return `${(value / 100_000_000).toFixed(2)} 亿`;
    if (Math.abs(value) >= 10_000) return `${(value / 10_000).toFixed(2)} 万`;
    return numberFormatter.format(value);
  }
  const numeric = Number(value);
  if (!Number.isNaN(numeric) && String(value).trim() !== "") {
    return formatNumber(numeric);
  }
  return String(value);
}

export function formatPercent(value: unknown, digits = 1): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  return `${(numeric * 100).toFixed(digits)}%`;
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function kindLabel(kind: ColumnKind): string {
  return { number: "数值", string: "文本", datetime: "日期", boolean: "布尔" }[kind] ?? kind;
}

export function aggregationLabel(aggregation: string): string {
  return (
    {
      sum: "求和",
      avg: "平均值",
      count: "记录数",
      min: "最小值",
      max: "最大值",
      median: "中位数",
      count_distinct: "去重计数",
    }[aggregation] ?? aggregation
  );
}

export function confidenceLabel(confidence: string): string {
  return { high: "高", medium: "中", low: "低" }[confidence] ?? "中";
}

