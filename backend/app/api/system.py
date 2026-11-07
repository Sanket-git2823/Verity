"""System API routes – health check and metrics."""

import time
import logging
import platform

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, text, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.query import Query as QueryModel
from app.schemas.system import HealthResponse, SystemMetrics

logger = logging.getLogger("verity.api.system")

router = APIRouter(prefix="/api/system", tags=["System"])

_BOOT_TIME = time.time()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Check database and Redis connectivity."""

    # Database
    db_status = "healthy"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("Database health check failed: %s", exc)
        db_status = "unhealthy"

    # Redis
    redis_status = "healthy"
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.ping()
        await r.aclose()
    except Exception:
        redis_status = "unavailable"

    overall = "healthy" if db_status == "healthy" else "degraded"

    return HealthResponse(
        status=overall,
        version=settings.APP_VERSION,
        database=db_status,
        redis=redis_status,
        uptime_seconds=round(time.time() - _BOOT_TIME, 1),
    )


@router.get("/metrics", response_model=SystemMetrics)
async def system_metrics(db: AsyncSession = Depends(get_db)):
    """Aggregate system metrics across documents, chunks, and queries."""

    # --- Document counts by status ---
    status_rows = (
        await db.execute(
            select(Document.status, func.count())
            .group_by(Document.status)
        )
    ).all()
    documents_by_status = {row[0].value if hasattr(row[0], "value") else str(row[0]): row[1] for row in status_rows}
    total_documents = sum(documents_by_status.values())

    # --- Documents by type ---
    type_rows = (
        await db.execute(
            select(Document.file_type, func.count())
            .group_by(Document.file_type)
        )
    ).all()
    documents_by_type = {row[0]: row[1] for row in type_rows}

    # --- Chunks ---
    total_chunks = (await db.execute(select(func.count()).select_from(DocumentChunk))).scalar_one()

    # Chunks with embeddings
    total_embeddings = (
        await db.execute(
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.embedding.isnot(None))
        )
    ).scalar_one()

    # --- Queries ---
    total_queries = (await db.execute(select(func.count()).select_from(QueryModel))).scalar_one()

    avg_latency = None
    p50_latency = None
    p95_latency = None

    if total_queries > 0:
        avg_row = await db.execute(
            select(func.avg(QueryModel.total_time_ms))
            .where(QueryModel.total_time_ms.isnot(None))
        )
        avg_latency = avg_row.scalar_one()
        if avg_latency is not None:
            avg_latency = round(avg_latency, 2)

        # p50 / p95 via percentile_cont (PostgreSQL)
        try:
            percentile_stmt = select(
                func.percentile_cont(0.5).within_group(QueryModel.total_time_ms),
                func.percentile_cont(0.95).within_group(QueryModel.total_time_ms),
            ).where(QueryModel.total_time_ms.isnot(None))
            pct_row = (await db.execute(percentile_stmt)).one()
            p50_latency = round(pct_row[0], 2) if pct_row[0] is not None else None
            p95_latency = round(pct_row[1], 2) if pct_row[1] is not None else None
        except Exception:
            # Fallback: percentile_cont may not be available on all engines
            p50_latency = avg_latency
            p95_latency = avg_latency

    # --- Failed ingestions ---
    failed_ingestions = documents_by_status.get(DocumentStatus.FAILED.value, 0)

    # --- Approximate storage ---
    storage_result = await db.execute(select(func.coalesce(func.sum(Document.file_size), 0)))
    storage_used_bytes = storage_result.scalar_one()

    return SystemMetrics(
        total_documents=total_documents,
        total_chunks=total_chunks,
        total_embeddings=total_embeddings,
        total_queries=total_queries,
        documents_by_status=documents_by_status,
        documents_by_type=documents_by_type,
        avg_query_latency_ms=avg_latency,
        p50_query_latency_ms=p50_latency,
        p95_query_latency_ms=p95_latency,
        failed_ingestions=failed_ingestions,
        storage_used_bytes=storage_used_bytes,
    )
