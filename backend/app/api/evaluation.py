"""Evaluation API routes – datasets, runs, comparison."""

import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db, async_session
from app.models.evaluation import (
    EvaluationDataset,
    EvaluationDatasetItem,
    EvaluationRun,
    EvaluationRunResult,
)
from app.schemas.evaluation import (
    EvaluationDatasetCreate,
    EvaluationDatasetResponse,
    EvaluationRunCreate,
    EvaluationRunResponse,
    EvaluationRunDetailResponse,
    EvaluationResultItemResponse,
    EvaluationCompareResponse,
)
from app.services.evaluation import EvaluationService

logger = logging.getLogger("verity.api.evaluation")

router = APIRouter(prefix="/api/evaluation", tags=["Evaluation"])


# ---------------------------------------------------------------------------
# Background runner
# ---------------------------------------------------------------------------

async def _background_run_evaluation(run_id: UUID) -> None:
    """Execute evaluation asynchronously in its own DB session."""
    async with async_session() as db:
        try:
            service = EvaluationService()
            await service.run_evaluation(run_id, db)
            await db.commit()
        except Exception as exc:
            logger.exception("Background evaluation failed for run %s: %s", run_id, exc)
            await db.rollback()
            run = await db.get(EvaluationRun, run_id)
            if run:
                run.status = "failed"
                run.error_count = (run.error_count or 0) + 1
                await db.commit()


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------

@router.post("/datasets", response_model=EvaluationDatasetResponse, status_code=201)
async def create_dataset(
    body: EvaluationDatasetCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create an evaluation dataset with its items."""
    dataset = EvaluationDataset(
        name=body.name,
        description=body.description,
        item_count=len(body.items),
    )
    db.add(dataset)
    await db.flush()

    for item_data in body.items:
        item = EvaluationDatasetItem(
            dataset_id=dataset.id,
            query_text=item_data.query_text,
            expected_answer=item_data.expected_answer,
            relevant_document_ids=item_data.relevant_document_ids,
            relevant_chunk_ids=item_data.relevant_chunk_ids,
            relevance_labels=item_data.relevance_labels,
        )
        db.add(item)

    await db.flush()
    logger.info("Created evaluation dataset '%s' (%s) with %d items", body.name, dataset.id, len(body.items))

    return EvaluationDatasetResponse(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        item_count=dataset.item_count,
        created_at=dataset.created_at,
    )


@router.get("/datasets", response_model=List[EvaluationDatasetResponse])
async def list_datasets(db: AsyncSession = Depends(get_db)):
    """Return all evaluation datasets."""
    stmt = select(EvaluationDataset).order_by(EvaluationDataset.created_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return [EvaluationDatasetResponse.model_validate(d) for d in rows]


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

@router.post("/run", response_model=EvaluationRunResponse, status_code=202)
async def start_evaluation_run(
    body: EvaluationRunCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Create and queue an evaluation run."""
    # Verify dataset exists
    dataset = await db.get(EvaluationDataset, body.dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Evaluation dataset not found.")

    run = EvaluationRun(
        dataset_id=body.dataset_id,
        name=body.name,
        description=body.description,
        config=body.config.model_dump(),
        status="pending",
        total_queries=dataset.item_count,
    )
    db.add(run)
    await db.flush()
    await db.commit()

    background_tasks.add_task(_background_run_evaluation, run.id)

    logger.info("Queued evaluation run '%s' (%s) on dataset %s", body.name, run.id, body.dataset_id)
    return EvaluationRunResponse.model_validate(run)


@router.get("/runs", response_model=List[EvaluationRunResponse])
async def list_runs(
    dataset_id: Optional[UUID] = Query(None, description="Filter by dataset"),
    db: AsyncSession = Depends(get_db),
):
    """List evaluation runs, optionally filtered by dataset."""
    stmt = select(EvaluationRun).order_by(EvaluationRun.created_at.desc())
    if dataset_id:
        stmt = stmt.where(EvaluationRun.dataset_id == dataset_id)

    rows = (await db.execute(stmt)).scalars().all()
    return [EvaluationRunResponse.model_validate(r) for r in rows]


@router.get("/runs/{run_id}", response_model=EvaluationRunDetailResponse)
async def get_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a single evaluation run with all result items."""
    stmt = (
        select(EvaluationRun)
        .options(selectinload(EvaluationRun.results))
        .where(EvaluationRun.id == run_id)
    )
    run = (await db.execute(stmt)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Evaluation run not found.")

    result_items = [
        EvaluationResultItemResponse.model_validate(r)
        for r in run.results
    ]

    resp = EvaluationRunDetailResponse.model_validate(run)
    resp.results = result_items
    return resp


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------

@router.get("/compare", response_model=EvaluationCompareResponse)
async def compare_runs(
    run_ids: str = Query(..., description="Comma-separated run UUIDs"),
    db: AsyncSession = Depends(get_db),
):
    """Compare aggregate metrics across multiple evaluation runs."""
    try:
        id_list = [UUID(rid.strip()) for rid in run_ids.split(",") if rid.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID in run_ids.")

    if len(id_list) < 2:
        raise HTTPException(status_code=400, detail="At least two run IDs are required for comparison.")

    stmt = select(EvaluationRun).where(EvaluationRun.id.in_(id_list))
    rows = (await db.execute(stmt)).scalars().all()

    if len(rows) != len(id_list):
        found = {r.id for r in rows}
        missing = [str(rid) for rid in id_list if rid not in found]
        raise HTTPException(status_code=404, detail=f"Runs not found: {', '.join(missing)}")

    run_responses = [EvaluationRunResponse.model_validate(r) for r in rows]

    # Build a comparison matrix
    metric_keys = [
        "mrr", "avg_faithfulness", "avg_citation_correctness",
        "avg_latency_ms", "p50_latency_ms", "p95_latency_ms",
    ]
    metrics_comparison: dict = {}

    for key in metric_keys:
        values = {}
        for r in rows:
            val = getattr(r, key, None)
            values[str(r.id)] = val
        metrics_comparison[key] = values

    # Include recall_at_k, precision_at_k, ndcg_at_k as nested dicts
    for composite_key in ["recall_at_k", "precision_at_k", "ndcg_at_k"]:
        composite = {}
        for r in rows:
            val = getattr(r, composite_key, None)
            composite[str(r.id)] = val
        metrics_comparison[composite_key] = composite

    return EvaluationCompareResponse(
        runs=run_responses,
        metrics_comparison=metrics_comparison,
    )
