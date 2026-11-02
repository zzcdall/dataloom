import type {
  AnalysisResult,
  AnalysisSpec,
  AskResponse,
  DatasetDetail,
  DatasetListItem,
  Preview,
} from "./types";

const BASE = import.meta.env.VITE_API_BASE ?? "";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE}${path}`, options);
  if (!response.ok) {
    let message = `请求失败（${response.status}）`;
    try {
      const payload = (await response.json()) as { detail?: string | { msg?: string }[] };
      if (typeof payload.detail === "string") {
        message = payload.detail;
      } else if (Array.isArray(payload.detail)) {
        message = payload.detail.map((item) => item.msg ?? "参数错误").join("；");
      }
    } catch {
      // Keep the status message when the body is not JSON.
    }
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const api = {
  listDatasets: () => request<DatasetListItem[]>("/api/datasets"),
  getDataset: (id: string) => request<DatasetDetail>(`/api/datasets/${id}`),
  uploadDataset: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<DatasetDetail>("/api/datasets", { method: "POST", body: form });
  },
  loadDemo: () => request<DatasetDetail>("/api/demo", { method: "POST" }),
  deleteDataset: (id: string) => request<void>(`/api/datasets/${id}`, { method: "DELETE" }),
  preview: (id: string, limit = 100) =>
    request<Preview>(`/api/datasets/${id}/preview?limit=${limit}`),
  analyze: (id: string, spec: AnalysisSpec) =>
    request<AnalysisResult>(`/api/datasets/${id}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(spec),
    }),
  ask: (id: string, question: string) =>
    request<AskResponse>(`/api/datasets/${id}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    }),
  exportUrl: (id: string) => `${BASE}/api/datasets/${id}/export.html`,
};

