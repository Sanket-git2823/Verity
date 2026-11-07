"""System schemas."""

from pydantic import BaseModel, model_validator
from typing import Optional, Dict, Any
from datetime import datetime


class ServiceHealth(BaseModel):
    status: str = "healthy"
    latency_ms: Optional[float] = None
    message: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str = "healthy"
    redis: str = "healthy"
    uptime_seconds: float
    services: Dict[str, ServiceHealth] = {}

    @model_validator(mode="before")
    @classmethod
    def populate_services(cls, data: Any) -> Any:
        if isinstance(data, dict) and not data.get("services"):
            data["services"] = {
                "database": {"status": data.get("database", "healthy"), "latency_ms": None, "message": None},
                "redis": {"status": data.get("redis", "healthy"), "latency_ms": None, "message": None},
                "api": {"status": "healthy", "latency_ms": None, "message": None},
            }
        return data


class QueryLatencyStats(BaseModel):
    avg: float = 0.0
    p50: float = 0.0
    p95: float = 0.0


class SystemMetrics(BaseModel):
    total_documents: int = 0
    total_chunks: int = 0
    total_embeddings: int = 0
    total_queries: int = 0
    documents_by_status: Dict[str, int] = {}
    documents_by_type: Dict[str, int] = {}
    avg_query_latency_ms: Optional[float] = None
    avg_latency_ms: Optional[float] = None
    p50_query_latency_ms: Optional[float] = None
    p95_query_latency_ms: Optional[float] = None
    failed_ingestions: int = 0
    storage_used_bytes: int = 0
    query_latency: QueryLatencyStats = QueryLatencyStats()

    @model_validator(mode="before")
    @classmethod
    def populate_latency(cls, data: Any) -> Any:
        if isinstance(data, dict):
            avg = data.get("avg_query_latency_ms") or data.get("avg_latency_ms") or 0.0
            p50 = data.get("p50_query_latency_ms") or avg
            p95 = data.get("p95_query_latency_ms") or avg
            data["avg_latency_ms"] = avg
            data["avg_query_latency_ms"] = avg
            if not data.get("query_latency"):
                data["query_latency"] = {
                    "avg": avg or 0.0,
                    "p50": p50 or 0.0,
                    "p95": p95 or 0.0,
                }
        return data


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime
