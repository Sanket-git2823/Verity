import type {
  Document,
  DocumentDetail,
  DocumentListResponse,
  QueryRequest,
  QueryResponse,
  QueryHistoryResponse,
  EvaluationDataset,
  EvaluationDatasetItem,
  EvaluationRun,
  EvaluationCompareResponse,
  SystemHealth,
  SystemMetrics,
} from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "/api";

class ApiError extends Error {
  status: number;
  detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const config: RequestInit = {
    ...options,
    headers: {
      ...(options.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      ...options.headers,
    },
  };

  const response = await fetch(url, config);

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const errorBody = await response.json();
      detail = errorBody.detail || errorBody.message || detail;
    } catch {
      // ignore parse error
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}

// ─── Documents ───────────────────────────────────────────────────

export async function uploadDocument(file: File): Promise<Document> {
  const formData = new FormData();
  formData.append("file", file);
  return request<Document>("/documents/upload", {
    method: "POST",
    body: formData,
  });
}

export async function uploadDocumentsBatch(files: File[]): Promise<Document[]> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  return request<Document[]>("/documents/batch", {
    method: "POST",
    body: formData,
  });
}

export async function getDocuments(params: {
  status?: string;
  file_type?: string;
  search?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: string;
}): Promise<DocumentListResponse> {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") {
      searchParams.set(key, String(value));
    }
  });
  const qs = searchParams.toString();
  return request<DocumentListResponse>(`/documents${qs ? `?${qs}` : ""}`);
}

export async function getDocument(id: string): Promise<DocumentDetail> {
  return request<DocumentDetail>(`/documents/${id}`);
}

export async function deleteDocument(id: string): Promise<void> {
  return request<void>(`/documents/${id}`, { method: "DELETE" });
}

// ─── Research ────────────────────────────────────────────────────

export async function queryResearch(
  body: QueryRequest
): Promise<QueryResponse> {
  return request<QueryResponse>("/research/query", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getQueryHistory(params: {
  page?: number;
  page_size?: number;
}): Promise<QueryHistoryResponse> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.page_size)
    searchParams.set("page_size", String(params.page_size));
  const qs = searchParams.toString();
  return request<QueryHistoryResponse>(
    `/research/history${qs ? `?${qs}` : ""}`
  );
}

export async function getQueryDetail(queryId: string): Promise<QueryResponse> {
  return request<QueryResponse>(`/research/query/${queryId}`);
}

// ─── Evaluation ──────────────────────────────────────────────────

export async function createEvaluationDataset(body: {
  name: string;
  description: string;
  items: EvaluationDatasetItem[];
}): Promise<EvaluationDataset> {
  return request<EvaluationDataset>("/evaluation/datasets", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getEvaluationDatasets(): Promise<EvaluationDataset[]> {
  return request<EvaluationDataset[]>("/evaluation/datasets");
}

export async function createEvaluationRun(body: {
  dataset_id: string;
  name: string;
  description: string;
  config: {
    bm25_weight: number;
    vector_weight: number;
    top_k: number;
    rerank: boolean;
    k_values: number[];
  };
}): Promise<EvaluationRun> {
  return request<EvaluationRun>("/evaluation/run", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getEvaluationRuns(
  datasetId?: string
): Promise<EvaluationRun[]> {
  const qs = datasetId ? `?dataset_id=${datasetId}` : "";
  return request<EvaluationRun[]>(`/evaluation/runs${qs}`);
}

export async function getEvaluationRun(runId: string): Promise<EvaluationRun> {
  return request<EvaluationRun>(`/evaluation/runs/${runId}`);
}

export async function compareEvaluationRuns(
  runIds: string[]
): Promise<EvaluationCompareResponse> {
  return request<EvaluationCompareResponse>(
    `/evaluation/compare?run_ids=${runIds.join(",")}`
  );
}

// ─── System ──────────────────────────────────────────────────────

export async function getSystemHealth(): Promise<SystemHealth> {
  return request<SystemHealth>("/system/health");
}

export async function getSystemMetrics(): Promise<SystemMetrics> {
  return request<SystemMetrics>("/system/metrics");
}

export { ApiError };
