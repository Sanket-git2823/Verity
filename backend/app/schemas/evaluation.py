"""Evaluation schemas."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class EvaluationDatasetItemCreate(BaseModel):
    query_text: str
    expected_answer: Optional[str] = None
    relevant_document_ids: Optional[List[str]] = None
    relevant_chunk_ids: Optional[List[str]] = None
    relevance_labels: Optional[Dict[str, float]] = None


class EvaluationDatasetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None
    items: List[EvaluationDatasetItemCreate] = []


class EvaluationDatasetResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    item_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class EvaluationRunConfig(BaseModel):
    bm25_weight: float = 0.4
    vector_weight: float = 0.6
    top_k: int = 10
    rerank: bool = True
    k_values: List[int] = [5, 10, 20]


class EvaluationRunCreate(BaseModel):
    dataset_id: UUID
    name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None
    config: EvaluationRunConfig = EvaluationRunConfig()


class EvaluationRunResponse(BaseModel):
    id: UUID
    dataset_id: UUID
    name: str
    description: Optional[str] = None
    config: dict
    status: str
    recall_at_k: Optional[Dict[str, float]] = None
    precision_at_k: Optional[Dict[str, float]] = None
    mrr: Optional[float] = None
    ndcg_at_k: Optional[Dict[str, float]] = None
    avg_faithfulness: Optional[float] = None
    avg_citation_correctness: Optional[float] = None
    avg_latency_ms: Optional[float] = None
    p50_latency_ms: Optional[float] = None
    p95_latency_ms: Optional[float] = None
    total_queries: int = 0
    error_count: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class EvaluationResultItemResponse(BaseModel):
    id: UUID
    query_text: str
    generated_answer: Optional[str] = None
    recall: Optional[float] = None
    precision: Optional[float] = None
    reciprocal_rank: Optional[float] = None
    ndcg: Optional[float] = None
    faithfulness: Optional[float] = None
    citation_correctness: Optional[float] = None
    latency_ms: Optional[float] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class EvaluationRunDetailResponse(EvaluationRunResponse):
    results: List[EvaluationResultItemResponse] = []


class EvaluationCompareResponse(BaseModel):
    runs: List[EvaluationRunResponse]
    metrics_comparison: Dict[str, Any]
