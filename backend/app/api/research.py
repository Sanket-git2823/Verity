"""Research API routes – query execution and history."""

import time
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.query import Query as QueryModel, GeneratedAnswer, RetrievalResult
from app.schemas.query import (
    QueryRequest,
    QueryResponse,
    QueryHistoryResponse,
    AnswerResponse,
    CitationResponse,
    RetrievalResultResponse,
)
from app.services.retrieval import RetrievalService
from app.services.generation import GenerationService

logger = logging.getLogger("verity.api.research")

router = APIRouter(prefix="/api/research", tags=["Research"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_query_response(query_row: QueryModel) -> QueryResponse:
    """Construct a full QueryResponse from an ORM Query row."""
    answer_resp: Optional[AnswerResponse] = None
    if query_row.answer:
        a = query_row.answer
        citations = [
            CitationResponse.model_validate(c)
            for c in sorted(a.citations, key=lambda c: c.citation_index)
        ]
        answer_resp = AnswerResponse(
            answer_text=a.answer_text,
            evidence_summary=a.evidence_summary,
            confidence_score=a.confidence_score,
            evidence_coverage=a.evidence_coverage,
            is_insufficient_evidence=a.is_insufficient_evidence,
            model_used=a.model_used,
            prompt_tokens=a.prompt_tokens,
            completion_tokens=a.completion_tokens,
            citations=citations,
        )

    retrieval_results = [
        RetrievalResultResponse.model_validate(r)
        for r in sorted(query_row.retrieval_results, key=lambda r: (r.retrieval_stage, r.rank))
    ]

    return QueryResponse(
        id=query_row.id,
        original_query=query_row.original_query,
        normalized_query=query_row.normalized_query,
        extracted_keywords=query_row.extracted_keywords,
        retrieval_config=query_row.retrieval_config,
        total_chunks_retrieved=query_row.total_chunks_retrieved,
        retrieval_time_ms=query_row.retrieval_time_ms,
        generation_time_ms=query_row.generation_time_ms,
        total_time_ms=query_row.total_time_ms,
        answer=answer_resp,
        retrieval_results=retrieval_results,
        created_at=query_row.created_at,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/query", response_model=QueryResponse, status_code=200)
async def execute_query(
    body: QueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """Run a full retrieval (and optionally generation) pipeline."""
    total_start = time.perf_counter()

    # --- Retrieval ---
    retrieval_start = time.perf_counter()
    retrieval_service = RetrievalService()
    retrieval_output = await retrieval_service.retrieve(
        query=body.query,
        top_k=body.top_k,
        bm25_weight=body.bm25_weight,
        vector_weight=body.vector_weight,
        metadata_filters=body.metadata_filters,
        rerank=body.rerank,
        db=db,
    )
    retrieval_time_ms = (time.perf_counter() - retrieval_start) * 1000

    # retrieval_output is expected to have: chunks, results_by_stage, normalized_query, keywords
    context_chunks = retrieval_output.get("chunks", [])
    results_by_stage = retrieval_output.get("results_by_stage", {})
    normalized_query = retrieval_output.get("normalized_query")
    extracted_keywords = retrieval_output.get("keywords")

    # --- Create Query record ---
    query_record = QueryModel(
        original_query=body.query,
        normalized_query=normalized_query,
        extracted_keywords=extracted_keywords,
        metadata_filters=body.metadata_filters,
        retrieval_config={
            "bm25_weight": body.bm25_weight,
            "vector_weight": body.vector_weight,
            "top_k": body.top_k,
            "rerank": body.rerank,
        },
        total_chunks_retrieved=len(context_chunks),
        retrieval_time_ms=round(retrieval_time_ms, 2),
    )
    db.add(query_record)
    await db.flush()

    # --- Store retrieval results ---
    for stage_name, stage_results in results_by_stage.items():
        for rank_idx, sr in enumerate(stage_results, start=1):
            rr = RetrievalResult(
                query_id=query_record.id,
                chunk_id=sr.get("chunk_id"),
                document_id=sr.get("document_id"),
                retrieval_stage=stage_name,
                rank=rank_idx,
                score=sr.get("score"),
                chunk_content_preview=sr.get("content", "")[:500] if sr.get("content") else None,
                source_filename=sr.get("source_filename"),
                page_number=sr.get("page_number"),
            )
            db.add(rr)

    # --- Generation (optional) ---
    generation_time_ms: Optional[float] = None
    if body.generate_answer and context_chunks:
        gen_start = time.perf_counter()
        generation_service = GenerationService()
        await generation_service.generate_answer(
            query=body.query,
            context_chunks=context_chunks,
            query_id=query_record.id,
            db=db,
        )
        generation_time_ms = (time.perf_counter() - gen_start) * 1000
        query_record.generation_time_ms = round(generation_time_ms, 2)

    total_time_ms = (time.perf_counter() - total_start) * 1000
    query_record.total_time_ms = round(total_time_ms, 2)
    await db.flush()

    # --- Reload with relationships ---
    await db.refresh(query_record)
    stmt = (
        select(QueryModel)
        .options(
            selectinload(QueryModel.answer).selectinload(GeneratedAnswer.citations),
            selectinload(QueryModel.retrieval_results),
        )
        .where(QueryModel.id == query_record.id)
    )
    row = (await db.execute(stmt)).scalar_one()

    logger.info(
        "Query %s completed in %.0f ms (retrieval=%.0f ms, generation=%s ms)",
        row.id, total_time_ms, retrieval_time_ms,
        f"{generation_time_ms:.0f}" if generation_time_ms else "N/A",
    )
    return _build_query_response(row)


@router.get("/history", response_model=QueryHistoryResponse)
async def query_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List past queries ordered by most recent first."""
    count_stmt = select(func.count()).select_from(QueryModel)
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = (
        select(QueryModel)
        .options(
            selectinload(QueryModel.answer).selectinload(GeneratedAnswer.citations),
            selectinload(QueryModel.retrieval_results),
        )
        .order_by(desc(QueryModel.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).scalars().all()

    return QueryHistoryResponse(
        queries=[_build_query_response(q) for q in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/query/{query_id}", response_model=QueryResponse)
async def get_query(query_id: UUID, db: AsyncSession = Depends(get_db)):
    """Return a single query with all retrieval results and answer."""
    stmt = (
        select(QueryModel)
        .options(
            selectinload(QueryModel.answer).selectinload(GeneratedAnswer.citations),
            selectinload(QueryModel.retrieval_results),
        )
        .where(QueryModel.id == query_id)
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Query not found.")

    return _build_query_response(row)
