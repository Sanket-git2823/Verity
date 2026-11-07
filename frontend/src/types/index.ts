// ─── Document Types ──────────────────────────────────────────────

export interface Document {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  page_count: number | null;
  chunk_count: number;
  status: "pending" | "processing" | "completed" | "failed";
  error_message: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  page_number: number | null;
  token_count: number;
  metadata: Record<string, unknown>;
}

export interface DocumentDetail extends Document {
  chunks: DocumentChunk[];
}

export interface DocumentListResponse {
  items: Document[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// ─── Research / Query Types ──────────────────────────────────────

export interface QueryRequest {
  query: string;
  metadata_filters?: Record<string, unknown>;
  bm25_weight?: number;
  vector_weight?: number;
  top_k?: number;
  rerank?: boolean;
  generate_answer?: boolean;
}

export interface Citation {
  citation_index: number;
  chunk_id: string;
  document_id: string;
  filename: string;
  page_number: number | null;
  content: string;
  score: number;
}

export interface Answer {
  text: string;
  citations: Citation[];
  confidence: number;
  model: string;
  insufficient_evidence: boolean;
}

export interface RetrievalResult {
  chunk_id: string;
  document_id: string;
  filename: string;
  page_number: number | null;
  content: string;
  score: number;
  rank: number;
  stage: "bm25" | "vector" | "rrf_fusion" | "reranked";
}

export interface QueryResponse {
  id?: string;
  query_id: string;
  query: string;
  original_query?: string;
  normalized_query?: string;
  extracted_keywords?: string[];
  retrieval_config?: Record<string, unknown>;
  total_chunks_retrieved?: number;
  retrieval_time_ms?: number;
  generation_time_ms?: number;
  total_time_ms?: number;
  answer: Answer | null;
  retrieval_results: RetrievalResult[];
  bm25_results: RetrievalResult[];
  vector_results: RetrievalResult[];
  rrf_results: RetrievalResult[];
  reranked_results: RetrievalResult[];
  latency_ms: number;
  created_at: string;
}

export interface QueryHistoryItem {
  query_id: string;
  id?: string;
  query: string;
  original_query?: string;
  latency_ms: number;
  total_time_ms?: number;
  result_count: number;
  has_answer: boolean;
  created_at: string;
}

export interface QueryHistoryResponse {
  items: QueryHistoryItem[];
  queries?: any[];
  total: number;
  page: number;
  page_size: number;
}

// ─── Evaluation Types ────────────────────────────────────────────

export interface EvaluationDatasetItem {
  query_text: string;
  expected_answer?: string;
  relevant_document_ids?: string[];
}

export interface EvaluationDataset {
  id: string;
  name: string;
  description: string;
  item_count: number;
  items?: EvaluationDatasetItem[];
  created_at: string;
}

export interface EvaluationRunConfig {
  bm25_weight: number;
  vector_weight: number;
  top_k: number;
  rerank: boolean;
  k_values: number[];
}

export interface EvaluationMetrics {
  recall_at_k: Record<string, number>;
  precision_at_k: Record<string, number>;
  mrr: number;
  ndcg_at_k: Record<string, number>;
  avg_faithfulness: number;
  citation_correctness: number;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
}

export interface EvaluationQueryResult {
  query_text: string;
  expected_answer: string;
  generated_answer: string;
  retrieval_results: RetrievalResult[];
  recall: number;
  precision: number;
  faithfulness: number;
  latency_ms: number;
}

export interface EvaluationRun {
  id: string;
  name: string;
  description: string;
  dataset_id: string;
  dataset_name?: string;
  status: "pending" | "running" | "completed" | "failed";
  config: EvaluationRunConfig;
  metrics: EvaluationMetrics | null;
  query_results: EvaluationQueryResult[];
  total_queries?: number;
  error_count?: number;
  created_at: string;
  completed_at: string | null;
}

export interface EvaluationCompareResponse {
  runs: EvaluationRun[];
  metric_comparison: Record<string, Record<string, number>>;
}

// ─── System Types ────────────────────────────────────────────────

export interface ServiceHealth {
  status: "healthy" | "degraded" | "unhealthy";
  latency_ms: number | null;
  message: string | null;
}

export interface SystemHealth {
  status: "healthy" | "degraded" | "unhealthy";
  services: {
    database: ServiceHealth;
    redis: ServiceHealth;
    api: ServiceHealth;
  };
  uptime_seconds: number;
  version: string;
}

export interface SystemMetrics {
  total_documents: number;
  total_chunks: number;
  total_embeddings: number;
  total_queries: number;
  avg_latency_ms: number;
  failed_ingestions: number;
  documents_by_status: Record<string, number>;
  documents_by_type: Record<string, number>;
  query_latency: {
    avg: number;
    p50: number;
    p95: number;
  };
}
