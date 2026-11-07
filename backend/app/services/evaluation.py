"""
Evaluation service for the Verity RAG platform.
Runs evaluation datasets through the retrieval + generation pipeline,
computes IR and generation quality metrics, and stores results.
"""

import logging
import math
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models.evaluation import (
    EvaluationDataset,
    EvaluationDatasetItem,
    EvaluationRun,
    EvaluationRunResult,
)
from app.services.retrieval import RetrievalService
from app.services.generation import GenerationService

logger = logging.getLogger(__name__)


class EvaluationService:
    """Create evaluation datasets, run evaluations, and compare runs."""

    def __init__(self) -> None:
        self.retrieval_service = RetrievalService()
        self.generation_service = GenerationService()

    # ------------------------------------------------------------------
    # Dataset management
    # ------------------------------------------------------------------

    async def create_dataset(
        self,
        db: AsyncSession,
        name: str,
        description: str,
        items: List[dict],
    ) -> EvaluationDataset:
        """
        Create an evaluation dataset with items.

        Args:
            db: Database session.
            name: Dataset name.
            description: Dataset description.
            items: List of dicts with keys:
                query_text (str), relevant_chunk_ids (List[str]),
                expected_answer (str, optional), relevance_labels (dict, optional)

        Returns:
            The created EvaluationDataset.
        """
        dataset = EvaluationDataset(
            name=name,
            description=description,
        )
        db.add(dataset)
        await db.commit()
        await db.refresh(dataset)

        for item_data in items:
            item = EvaluationDatasetItem(
                dataset_id=dataset.id,
                query_text=item_data["query_text"],
                relevant_chunk_ids=item_data.get("relevant_chunk_ids", []),
                expected_answer=item_data.get("expected_answer", ""),
                relevance_labels=item_data.get("relevance_labels", {}),
            )
            db.add(item)

        await db.commit()
        logger.info("Created evaluation dataset '%s' with %d items", name, len(items))
        return dataset

    # ------------------------------------------------------------------
    # Run evaluation
    # ------------------------------------------------------------------

    async def run_evaluation(self, run_id: uuid.UUID, db: Optional[AsyncSession] = None) -> EvaluationRun:
        """
        Execute an evaluation run: for each dataset item, run the retrieval
        + generation pipeline, compute per-query metrics, then aggregate.
        """
        if db is not None:
            return await self._do_run_evaluation(run_id, db)
        async with async_session() as session:
            return await self._do_run_evaluation(run_id, session)

    async def _do_run_evaluation(self, run_id: uuid.UUID, db: AsyncSession) -> EvaluationRun:
            # Load the run
            result = await db.execute(
                select(EvaluationRun).where(EvaluationRun.id == run_id)
            )
            run = result.scalar_one_or_none()
            if run is None:
                raise ValueError(f"Evaluation run {run_id} not found")

            # Mark as running
            run.status = "running"
            run.started_at = datetime.now(timezone.utc)
            await db.commit()

            # Load dataset items
            items_result = await db.execute(
                select(EvaluationDatasetItem).where(
                    EvaluationDatasetItem.dataset_id == run.dataset_id
                )
            )
            items = items_result.scalars().all()

            if not items:
                run.status = "failed"
                run.error_count = 0
                await db.commit()
                raise ValueError("Evaluation dataset has no items")

            # Per-query results
            per_query_results: List[EvaluationRunResult] = []
            latencies: List[float] = []
            error_count = 0

            k_values = [1, 3, 5, 10]  # Evaluation at these K values
            recall_at_k_accum: Dict[int, List[float]] = {k: [] for k in k_values}
            precision_at_k_accum: Dict[int, List[float]] = {k: [] for k in k_values}
            rr_values: List[float] = []
            ndcg_values: Dict[int, List[float]] = {k: [] for k in k_values}
            faithfulness_values: List[float] = []
            citation_correctness_values: List[float] = []

            for item in items:
                try:
                    t_start = time.perf_counter()

                    # Run retrieval
                    pipeline_result = await self.retrieval_service.retrieve(
                        query=item.query_text,
                        db=db,
                    )

                    # Run generation
                    context_chunks = [
                        {
                            "id": c.id,
                            "document_id": c.document_id,
                            "content": c.content,
                            "page_number": c.page_number,
                            "source_filename": c.source_filename,
                            "chunk_index": c.chunk_index,
                            "score": c.score,
                        }
                        for c in pipeline_result.final_chunks
                    ]
                    gen_result = await self.generation_service.generate_answer(
                        query=item.query_text,
                        context_chunks=context_chunks,
                        query_id=pipeline_result.query_id,
                        db=db,
                    )

                    t_end = time.perf_counter()
                    latency_ms = round((t_end - t_start) * 1000, 2)
                    latencies.append(latency_ms)

                    # Retrieved chunk IDs
                    retrieved_ids = [str(c.id) for c in pipeline_result.final_chunks]
                    relevant_ids = set(item.relevant_chunk_ids or [])

                    # Compute per-query metrics
                    recall = self._compute_recall(retrieved_ids, relevant_ids, max(k_values))
                    precision = self._compute_precision(retrieved_ids, relevant_ids, max(k_values))
                    reciprocal_rank = self._compute_reciprocal_rank(retrieved_ids, relevant_ids)
                    ndcg = self._compute_ndcg(
                        retrieved_ids, relevant_ids,
                        item.relevance_labels or {},
                        max(k_values),
                    )

                    # Accumulate at different K values
                    for k in k_values:
                        recall_at_k_accum[k].append(
                            self._compute_recall(retrieved_ids, relevant_ids, k)
                        )
                        precision_at_k_accum[k].append(
                            self._compute_precision(retrieved_ids, relevant_ids, k)
                        )
                        ndcg_values[k].append(
                            self._compute_ndcg(retrieved_ids, relevant_ids, item.relevance_labels or {}, k)
                        )

                    rr_values.append(reciprocal_rank)

                    # Faithfulness: simple heuristic based on citation coverage
                    faithfulness = self._compute_faithfulness(
                        gen_result.answer_text, context_chunks
                    )
                    faithfulness_values.append(faithfulness)

                    # Citation correctness
                    citation_correct = self._compute_citation_correctness(
                        gen_result.citations, relevant_ids
                    )
                    citation_correctness_values.append(citation_correct)

                    # Store per-query result
                    run_result = EvaluationRunResult(
                        run_id=run_id,
                        dataset_item_id=item.id,
                        query_text=item.query_text,
                        generated_answer=gen_result.answer_text,
                        retrieved_chunk_ids=retrieved_ids,
                        relevant_chunk_ids=list(relevant_ids),
                        recall=recall,
                        precision=precision,
                        reciprocal_rank=reciprocal_rank,
                        ndcg=ndcg,
                        faithfulness=faithfulness,
                        citation_correctness=citation_correct,
                        latency_ms=latency_ms,
                    )
                    db.add(run_result)
                    per_query_results.append(run_result)

                except Exception as exc:
                    error_count += 1
                    logger.error(
                        "Evaluation error for item %s: %s", item.id, exc
                    )
                    run_result = EvaluationRunResult(
                        run_id=run_id,
                        dataset_item_id=item.id,
                        query_text=item.query_text,
                        generated_answer="",
                        retrieved_chunk_ids=[],
                        relevant_chunk_ids=list(item.relevant_chunk_ids or []),
                        recall=0.0,
                        precision=0.0,
                        reciprocal_rank=0.0,
                        ndcg=0.0,
                        faithfulness=0.0,
                        citation_correctness=0.0,
                        latency_ms=0.0,
                        error_message=str(exc)[:1000],
                    )
                    db.add(run_result)

            await db.commit()

            # Compute aggregate metrics
            recall_at_k = {str(k): self._safe_mean(recall_at_k_accum[k]) for k in k_values}
            precision_at_k = {str(k): self._safe_mean(precision_at_k_accum[k]) for k in k_values}
            mrr = self._safe_mean(rr_values)
            ndcg_at_k = {str(k): self._safe_mean(ndcg_values[k]) for k in k_values}
            avg_faithfulness = self._safe_mean(faithfulness_values)
            avg_citation_correctness = self._safe_mean(citation_correctness_values)
            avg_latency = self._safe_mean(latencies)
            p50_latency = float(np.percentile(latencies, 50)) if latencies else 0.0
            p95_latency = float(np.percentile(latencies, 95)) if latencies else 0.0

            # Update run record
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            run.recall_at_k = recall_at_k
            run.precision_at_k = precision_at_k
            run.mrr = mrr
            run.ndcg_at_k = ndcg_at_k
            run.avg_faithfulness = avg_faithfulness
            run.avg_citation_correctness = avg_citation_correctness
            run.avg_latency_ms = avg_latency
            run.p50_latency_ms = p50_latency
            run.p95_latency_ms = p95_latency
            run.total_queries = len(items)
            run.error_count = error_count
            await db.commit()

            logger.info(
                "Evaluation run %s completed: %d queries, %d errors, MRR=%.3f",
                run_id, len(items), error_count, mrr,
            )
            return run

    # ------------------------------------------------------------------
    # Compare runs
    # ------------------------------------------------------------------

    async def compare_runs(
        self, run_ids: List[uuid.UUID], db: AsyncSession
    ) -> List[dict]:
        """
        Compare metrics across multiple evaluation runs.
        Returns a list of run summary dicts for side-by-side comparison.
        """
        comparisons: List[dict] = []

        for run_id in run_ids:
            result = await db.execute(
                select(EvaluationRun).where(EvaluationRun.id == run_id)
            )
            run = result.scalar_one_or_none()
            if run is None:
                logger.warning("Run %s not found for comparison", run_id)
                continue

            comparisons.append({
                "run_id": str(run.id),
                "name": run.name,
                "status": run.status,
                "config": run.config,
                "recall_at_k": run.recall_at_k,
                "precision_at_k": run.precision_at_k,
                "mrr": run.mrr,
                "ndcg_at_k": run.ndcg_at_k,
                "avg_faithfulness": run.avg_faithfulness,
                "avg_citation_correctness": run.avg_citation_correctness,
                "avg_latency_ms": run.avg_latency_ms,
                "p50_latency_ms": run.p50_latency_ms,
                "p95_latency_ms": run.p95_latency_ms,
                "total_queries": run.total_queries,
                "error_count": run.error_count,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            })

        return comparisons

    # ------------------------------------------------------------------
    # Metric computation (Delegates to app.utils.metrics)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_recall(
        retrieved: List[str], relevant: set, k: int
    ) -> float:
        from app.utils.metrics import compute_recall_at_k
        return compute_recall_at_k(retrieved, relevant, k)

    @staticmethod
    def _compute_precision(
        retrieved: List[str], relevant: set, k: int
    ) -> float:
        from app.utils.metrics import compute_precision_at_k
        return compute_precision_at_k(retrieved, relevant, k)

    @staticmethod
    def _compute_reciprocal_rank(
        retrieved: List[str], relevant: set
    ) -> float:
        from app.utils.metrics import compute_reciprocal_rank
        return compute_reciprocal_rank(retrieved, relevant)

    @staticmethod
    def _compute_ndcg(
        retrieved: List[str],
        relevant: set,
        relevance_labels: Dict[str, Any],
        k: int,
    ) -> float:
        from app.utils.metrics import compute_ndcg_at_k
        return compute_ndcg_at_k(retrieved, relevant, relevance_labels, k)

        return dcg / idcg

    @staticmethod
    def _compute_faithfulness(
        answer_text: str, context_chunks: List[dict]
    ) -> float:
        """
        Heuristic faithfulness score: fraction of sentences in the answer that
        contain a citation reference [N].
        """
        import re
        if not answer_text.strip():
            return 0.0

        sentences = re.split(r"[.!?]+", answer_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if not sentences:
            return 0.0

        cited_sentences = sum(
            1 for s in sentences if re.search(r"\[\d+\]", s)
        )
        return cited_sentences / len(sentences)

    @staticmethod
    def _compute_citation_correctness(
        citations: list, relevant_ids: set
    ) -> float:
        """
        Fraction of citations that reference relevant chunks.
        """
        if not citations:
            return 0.0

        correct = sum(
            1 for c in citations
            if str(getattr(c, "chunk_id", "")) in relevant_ids
        )
        return correct / len(citations)

    @staticmethod
    def _safe_mean(values: List[float]) -> float:
        """Mean that handles empty lists."""
        if not values:
            return 0.0
        return sum(values) / len(values)
