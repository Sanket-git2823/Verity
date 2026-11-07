"""Query, answer, and retrieval schemas."""

from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    metadata_filters: Optional[Dict[str, Any]] = None
    bm25_weight: Optional[float] = None
    vector_weight: Optional[float] = None
    top_k: Optional[int] = None
    rerank: bool = True
    generate_answer: bool = True


class CitationResponse(BaseModel):
    citation_index: int
    cited_text: Optional[str] = None
    content: Optional[str] = None
    source_filename: Optional[str] = None
    filename: Optional[str] = None
    page_number: Optional[int] = None
    document_id: Optional[UUID] = None
    chunk_id: Optional[UUID] = None
    relevance_score: Optional[float] = None
    score: Optional[float] = None

    @model_validator(mode="before")
    @classmethod
    def populate_citation_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "content" not in data and "cited_text" in data:
                data["content"] = data["cited_text"]
            if "cited_text" not in data and "content" in data:
                data["cited_text"] = data["content"]
            if "filename" not in data and "source_filename" in data:
                data["filename"] = data["source_filename"]
            if "source_filename" not in data and "filename" in data:
                data["source_filename"] = data["filename"]
            if "score" not in data and "relevance_score" in data:
                data["score"] = data["relevance_score"]
            if "relevance_score" not in data and "score" in data:
                data["relevance_score"] = data["score"]
        elif hasattr(data, "__dict__"):
            c = getattr(data, "cited_text", None)
            if c and not getattr(data, "content", None):
                setattr(data, "content", c)
            f = getattr(data, "source_filename", None)
            if f and not getattr(data, "filename", None):
                setattr(data, "filename", f)
            s = getattr(data, "relevance_score", None)
            if s and not getattr(data, "score", None):
                setattr(data, "score", s)
        return data

    class Config:
        from_attributes = True


class AnswerResponse(BaseModel):
    answer_text: str
    text: Optional[str] = None
    evidence_summary: Optional[str] = None
    confidence_score: Optional[float] = None
    confidence: Optional[float] = None
    evidence_coverage: Optional[float] = None
    is_insufficient_evidence: bool = False
    insufficient_evidence: Optional[bool] = None
    model_used: Optional[str] = None
    model: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    citations: List[CitationResponse] = []

    @model_validator(mode="before")
    @classmethod
    def populate_answer_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "text" not in data and "answer_text" in data:
                data["text"] = data["answer_text"]
            if "answer_text" not in data and "text" in data:
                data["answer_text"] = data["text"]
            if "confidence" not in data and "confidence_score" in data:
                data["confidence"] = data["confidence_score"]
            if "confidence_score" not in data and "confidence" in data:
                data["confidence_score"] = data["confidence"]
            if "model" not in data and "model_used" in data:
                data["model"] = data["model_used"]
            if "model_used" not in data and "model" in data:
                data["model_used"] = data["model"]
            if "insufficient_evidence" not in data and "is_insufficient_evidence" in data:
                data["insufficient_evidence"] = data["is_insufficient_evidence"]
            if "is_insufficient_evidence" not in data and "insufficient_evidence" in data:
                data["is_insufficient_evidence"] = data["insufficient_evidence"]
        elif hasattr(data, "__dict__"):
            t = getattr(data, "answer_text", None)
            if t and not getattr(data, "text", None):
                setattr(data, "text", t)
            c = getattr(data, "confidence_score", None)
            if c is not None and not getattr(data, "confidence", None):
                setattr(data, "confidence", c)
            m = getattr(data, "model_used", None)
            if m and not getattr(data, "model", None):
                setattr(data, "model", m)
            ie = getattr(data, "is_insufficient_evidence", None)
            if ie is not None and getattr(data, "insufficient_evidence", None) is None:
                setattr(data, "insufficient_evidence", ie)
        return data

    class Config:
        from_attributes = True


class RetrievalResultResponse(BaseModel):
    chunk_id: Optional[UUID] = None
    document_id: Optional[UUID] = None
    retrieval_stage: str
    stage: Optional[str] = None
    rank: int
    score: Optional[float] = None
    chunk_content_preview: Optional[str] = None
    content: Optional[str] = None
    source_filename: Optional[str] = None
    filename: Optional[str] = None
    page_number: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def populate_retrieval_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "stage" not in data and "retrieval_stage" in data:
                data["stage"] = data["retrieval_stage"]
            if "retrieval_stage" not in data and "stage" in data:
                data["retrieval_stage"] = data["stage"]
            if "content" not in data and "chunk_content_preview" in data:
                data["content"] = data["chunk_content_preview"]
            if "chunk_content_preview" not in data and "content" in data:
                data["chunk_content_preview"] = data["content"]
            if "filename" not in data and "source_filename" in data:
                data["filename"] = data["source_filename"]
            if "source_filename" not in data and "filename" in data:
                data["source_filename"] = data["filename"]
        elif hasattr(data, "__dict__"):
            s = getattr(data, "retrieval_stage", None)
            if s and not getattr(data, "stage", None):
                setattr(data, "stage", s)
            c = getattr(data, "chunk_content_preview", None)
            if c and not getattr(data, "content", None):
                setattr(data, "content", c)
            f = getattr(data, "source_filename", None)
            if f and not getattr(data, "filename", None):
                setattr(data, "filename", f)
        return data

    class Config:
        from_attributes = True


class QueryResponse(BaseModel):
    id: UUID
    query_id: Optional[UUID] = None
    original_query: str
    query: Optional[str] = None
    normalized_query: Optional[str] = None
    extracted_keywords: Optional[List[str]] = None
    retrieval_config: Optional[dict] = None
    total_chunks_retrieved: int = 0
    retrieval_time_ms: Optional[float] = None
    generation_time_ms: Optional[float] = None
    total_time_ms: Optional[float] = None
    latency_ms: Optional[float] = None
    answer: Optional[AnswerResponse] = None
    retrieval_results: List[RetrievalResultResponse] = []
    bm25_results: List[RetrievalResultResponse] = []
    vector_results: List[RetrievalResultResponse] = []
    rrf_results: List[RetrievalResultResponse] = []
    reranked_results: List[RetrievalResultResponse] = []
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def populate_query_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            qid = data.get("id") or data.get("query_id")
            data["id"] = qid
            data["query_id"] = qid
            q = data.get("original_query") or data.get("query")
            data["original_query"] = q
            data["query"] = q
            lat = data.get("total_time_ms") or data.get("latency_ms") or 0.0
            data["total_time_ms"] = lat
            data["latency_ms"] = lat
            results = data.get("retrieval_results") or []
            if not data.get("bm25_results"):
                data["bm25_results"] = [r for r in results if getattr(r, "retrieval_stage", None) == "bm25" or (isinstance(r, dict) and r.get("retrieval_stage") == "bm25")]
            if not data.get("vector_results"):
                data["vector_results"] = [r for r in results if getattr(r, "retrieval_stage", None) == "vector" or (isinstance(r, dict) and r.get("retrieval_stage") == "vector")]
            if not data.get("rrf_results"):
                data["rrf_results"] = [r for r in results if getattr(r, "retrieval_stage", None) in ("rrf", "rrf_fusion") or (isinstance(r, dict) and r.get("retrieval_stage") in ("rrf", "rrf_fusion"))]
            if not data.get("reranked_results"):
                data["reranked_results"] = [r for r in results if getattr(r, "retrieval_stage", None) == "reranked" or (isinstance(r, dict) and r.get("retrieval_stage") == "reranked")]
        return data

    class Config:
        from_attributes = True


class QueryHistoryItem(BaseModel):
    query_id: UUID
    query: str
    latency_ms: float = 0.0
    result_count: int = 0
    has_answer: bool = False
    created_at: datetime


class QueryHistoryResponse(BaseModel):
    items: List[QueryHistoryItem] = []
    queries: List[QueryResponse] = []
    total: int
    page: int
    page_size: int

    @model_validator(mode="before")
    @classmethod
    def populate_history_items(cls, data: Any) -> Any:
        if isinstance(data, dict) and "queries" in data and not data.get("items"):
            items = []
            for q in data["queries"]:
                if isinstance(q, dict):
                    items.append({
                        "query_id": q.get("id"),
                        "query": q.get("original_query", ""),
                        "latency_ms": q.get("total_time_ms") or 0.0,
                        "result_count": q.get("total_chunks_retrieved", 0),
                        "has_answer": bool(q.get("answer")),
                        "created_at": q.get("created_at"),
                    })
                elif hasattr(q, "id"):
                    items.append({
                        "query_id": q.id,
                        "query": q.original_query,
                        "latency_ms": q.total_time_ms or 0.0,
                        "result_count": q.total_chunks_retrieved or 0,
                        "has_answer": bool(q.answer),
                        "created_at": q.created_at,
                    })
            data["items"] = items
        return data
