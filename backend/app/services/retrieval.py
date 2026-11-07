"""
Hybrid retrieval service for the Verity RAG platform.
Combines BM25 full-text search and pgvector cosine similarity via
Reciprocal Rank Fusion, with optional cross-encoder reranking.
"""

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models.query import Query, RetrievalResult
from app.services.embedding import EmbeddingService
from app.services.reranking import RerankingService
from app.utils.text import count_tokens, extract_keywords, normalize_text

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Result dataclasses
# ------------------------------------------------------------------

@dataclass
class ChunkResult:
    """A single retrieved chunk with its metadata."""
    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    content: str
    page_number: Optional[int]
    source_filename: Optional[str]
    score: float
    stage: str  # bm25 | vector | rrf | reranked


@dataclass
class RetrievalPipelineResult:
    """Full output of the retrieval pipeline."""
    query_id: uuid.UUID
    original_query: str
    normalized_query: str
    extracted_keywords: List[str]
    bm25_results: List[ChunkResult] = field(default_factory=list)
    vector_results: List[ChunkResult] = field(default_factory=list)
    rrf_results: List[ChunkResult] = field(default_factory=list)
    reranked_results: List[ChunkResult] = field(default_factory=list)
    final_chunks: List[ChunkResult] = field(default_factory=list)
    total_chunks_retrieved: int = 0
    retrieval_time_ms: float = 0.0


class RetrievalService:
    """Hybrid retrieval engine: BM25 + vector search + RRF + reranking."""

    def __init__(self) -> None:
        self.embedding_service = EmbeddingService()
        self.reranking_service = RerankingService()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def retrieve(
        self,
        query: str,
        db: AsyncSession,
        top_k: Optional[int] = None,
        bm25_weight: Optional[float] = None,
        vector_weight: Optional[float] = None,
        metadata_filters: Optional[Dict[str, Any]] = None,
        rerank: bool = True,
    ) -> RetrievalPipelineResult:
        """
        Execute the full hybrid retrieval pipeline:
          1. Query processing
          2a. BM25 full-text search
          2b. Vector similarity search
          3. Reciprocal Rank Fusion
          4. (Optional) Cross-encoder reranking
          5. Context construction
        """
        t_start = time.perf_counter()

        top_k = top_k or settings.HYBRID_TOP_K
        bm25_weight = bm25_weight if bm25_weight is not None else settings.BM25_WEIGHT
        vector_weight = vector_weight if vector_weight is not None else settings.VECTOR_WEIGHT

        # --- Stage 1: Query processing ---
        normalized_query = normalize_text(query).lower().strip()
        keywords = extract_keywords(query)

        # Create Query record
        query_record = Query(
            original_query=query,
            normalized_query=normalized_query,
            extracted_keywords=keywords,
            metadata_filters=metadata_filters,
            retrieval_config={
                "top_k": top_k,
                "bm25_weight": bm25_weight,
                "vector_weight": vector_weight,
                "rerank": rerank,
            },
        )
        db.add(query_record)
        await db.commit()
        await db.refresh(query_record)
        query_id = query_record.id

        pipeline_result = RetrievalPipelineResult(
            query_id=query_id,
            original_query=query,
            normalized_query=normalized_query,
            extracted_keywords=keywords,
        )

        # --- Stage 2a: BM25 retrieval ---
        bm25_results = await self._bm25_search(db, normalized_query, metadata_filters)
        pipeline_result.bm25_results = bm25_results

        # --- Stage 2b: Vector retrieval ---
        query_embedding = await self.embedding_service.embed_query(normalized_query)
        vector_results = await self._vector_search(db, query_embedding, metadata_filters)
        pipeline_result.vector_results = vector_results

        # --- Stage 3: Reciprocal Rank Fusion ---
        rrf_results = self._reciprocal_rank_fusion(
            bm25_results, vector_results,
            bm25_weight=bm25_weight,
            vector_weight=vector_weight,
            top_k=top_k,
        )
        pipeline_result.rrf_results = rrf_results

        # --- Stage 4: Reranking ---
        if rerank and rrf_results:
            reranked = self._rerank(normalized_query, rrf_results, top_k)
            pipeline_result.reranked_results = reranked
            final = reranked
        else:
            pipeline_result.reranked_results = rrf_results
            final = rrf_results

        # --- Stage 5: Context construction ---
        final_chunks = self._construct_context(final)
        pipeline_result.final_chunks = final_chunks
        pipeline_result.total_chunks_retrieved = len(final_chunks)

        t_end = time.perf_counter()
        pipeline_result.retrieval_time_ms = round((t_end - t_start) * 1000, 2)

        # Update Query record with timing
        query_record.total_chunks_retrieved = len(final_chunks)
        query_record.retrieval_time_ms = pipeline_result.retrieval_time_ms
        await db.commit()

        # Persist retrieval results for all stages
        await self._store_retrieval_results(db, query_id, pipeline_result)

        logger.info(
            "Retrieval complete for query %s: %d final chunks in %.1fms",
            query_id, len(final_chunks), pipeline_result.retrieval_time_ms,
        )
        return pipeline_result

    # ------------------------------------------------------------------
    # Stage 2a: BM25 full-text search
    # ------------------------------------------------------------------

    async def _bm25_search(
        self,
        db: AsyncSession,
        query: str,
        metadata_filters: Optional[Dict[str, Any]] = None,
    ) -> List[ChunkResult]:
        """PostgreSQL full-text search using plainto_tsquery."""
        limit = settings.BM25_TOP_K

        sql = text("""
            SELECT
                dc.id,
                dc.document_id,
                dc.chunk_index,
                dc.content,
                dc.page_number,
                d.original_filename AS source_filename,
                ts_rank(to_tsvector('english', dc.content), plainto_tsquery('english', :query)) AS score
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            WHERE to_tsvector('english', dc.content) @@ plainto_tsquery('english', :query)
            ORDER BY score DESC
            LIMIT :limit
        """)

        result = await db.execute(sql, {"query": query, "limit": limit})
        rows = result.fetchall()

        return [
            ChunkResult(
                id=row.id,
                document_id=row.document_id,
                chunk_index=row.chunk_index,
                content=row.content,
                page_number=row.page_number,
                source_filename=row.source_filename,
                score=float(row.score),
                stage="bm25",
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Stage 2b: Vector similarity search
    # ------------------------------------------------------------------

    async def _vector_search(
        self,
        db: AsyncSession,
        query_embedding: List[float],
        metadata_filters: Optional[Dict[str, Any]] = None,
    ) -> List[ChunkResult]:
        """pgvector cosine distance search."""
        limit = settings.VECTOR_TOP_K
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"

        sql = text("""
            SELECT
                dc.id,
                dc.document_id,
                dc.chunk_index,
                dc.content,
                dc.page_number,
                d.original_filename AS source_filename,
                1 - (dc.embedding <=> :query_vec) AS score
            FROM document_chunks dc
            JOIN documents d ON d.id = dc.document_id
            ORDER BY dc.embedding <=> :query_vec
            LIMIT :limit
        """)

        result = await db.execute(sql, {"query_vec": embedding_str, "limit": limit})
        rows = result.fetchall()

        return [
            ChunkResult(
                id=row.id,
                document_id=row.document_id,
                chunk_index=row.chunk_index,
                content=row.content,
                page_number=row.page_number,
                source_filename=row.source_filename,
                score=float(row.score),
                stage="vector",
            )
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Stage 3: Reciprocal Rank Fusion
    # ------------------------------------------------------------------

    def _reciprocal_rank_fusion(
        self,
        bm25_results: List[ChunkResult],
        vector_results: List[ChunkResult],
        bm25_weight: float,
        vector_weight: float,
        top_k: int,
    ) -> List[ChunkResult]:
        """
        Combine BM25 and vector results using weighted RRF.
        Score = bm25_weight * 1/(k + bm25_rank) + vector_weight * 1/(k + vector_rank)
        """
        k = settings.RRF_K
        chunk_scores: Dict[uuid.UUID, float] = {}
        chunk_map: Dict[uuid.UUID, ChunkResult] = {}

        # Score BM25 results
        for rank, cr in enumerate(bm25_results, start=1):
            rrf_score = bm25_weight * (1.0 / (k + rank))
            chunk_scores[cr.id] = chunk_scores.get(cr.id, 0.0) + rrf_score
            chunk_map[cr.id] = cr

        # Score vector results
        for rank, cr in enumerate(vector_results, start=1):
            rrf_score = vector_weight * (1.0 / (k + rank))
            chunk_scores[cr.id] = chunk_scores.get(cr.id, 0.0) + rrf_score
            if cr.id not in chunk_map:
                chunk_map[cr.id] = cr

        # Sort by fused score
        sorted_ids = sorted(chunk_scores, key=lambda cid: chunk_scores[cid], reverse=True)

        rrf_results: List[ChunkResult] = []
        for cid in sorted_ids[:top_k]:
            cr = chunk_map[cid]
            rrf_results.append(ChunkResult(
                id=cr.id,
                document_id=cr.document_id,
                chunk_index=cr.chunk_index,
                content=cr.content,
                page_number=cr.page_number,
                source_filename=cr.source_filename,
                score=chunk_scores[cid],
                stage="rrf",
            ))

        return rrf_results

    # ------------------------------------------------------------------
    # Stage 4: Reranking
    # ------------------------------------------------------------------

    def _rerank(
        self, query: str, chunks: List[ChunkResult], top_k: int
    ) -> List[ChunkResult]:
        """Run cross-encoder reranking on the RRF results."""
        chunk_dicts = [
            {
                "id": str(c.id),
                "content": c.content,
                "score": c.score,
                "document_id": str(c.document_id),
                "page_number": c.page_number,
                "source_filename": c.source_filename,
                "chunk_index": c.chunk_index,
            }
            for c in chunks
        ]

        reranked_dicts = self.reranking_service.rerank(query, chunk_dicts, top_k)

        reranked: List[ChunkResult] = []
        for d in reranked_dicts:
            reranked.append(ChunkResult(
                id=uuid.UUID(str(d["id"])),
                document_id=uuid.UUID(str(d["document_id"])),
                chunk_index=d["chunk_index"],
                content=d["content"],
                page_number=d.get("page_number"),
                source_filename=d.get("source_filename"),
                score=d.get("rerank_score", d.get("score", 0.0)),
                stage="reranked",
            ))

        return reranked

    # ------------------------------------------------------------------
    # Stage 5: Context construction
    # ------------------------------------------------------------------

    def _construct_context(self, chunks: List[ChunkResult]) -> List[ChunkResult]:
        """
        Deduplicate chunks and enforce MAX_CONTEXT_TOKENS.
        """
        seen_ids: set = set()
        deduplicated: List[ChunkResult] = []
        total_tokens = 0
        max_tokens = settings.MAX_CONTEXT_TOKENS

        for chunk in chunks:
            if chunk.id in seen_ids:
                continue
            chunk_tokens = count_tokens(chunk.content)
            if total_tokens + chunk_tokens > max_tokens:
                break
            seen_ids.add(chunk.id)
            deduplicated.append(chunk)
            total_tokens += chunk_tokens

        return deduplicated

    # ------------------------------------------------------------------
    # Persist retrieval results
    # ------------------------------------------------------------------

    async def _store_retrieval_results(
        self,
        db: AsyncSession,
        query_id: uuid.UUID,
        pipeline: RetrievalPipelineResult,
    ) -> None:
        """Save all stage results to the retrieval_results table."""
        records: List[RetrievalResult] = []

        stages = [
            ("bm25", pipeline.bm25_results),
            ("vector", pipeline.vector_results),
            ("rrf", pipeline.rrf_results),
            ("reranked", pipeline.reranked_results),
        ]

        for stage_name, stage_results in stages:
            for rank, cr in enumerate(stage_results, start=1):
                records.append(RetrievalResult(
                    query_id=query_id,
                    chunk_id=cr.id,
                    document_id=cr.document_id,
                    retrieval_stage=stage_name,
                    rank=rank,
                    score=cr.score,
                    chunk_content_preview=cr.content[:200] if cr.content else "",
                    source_filename=cr.source_filename,
                    page_number=cr.page_number,
                ))

        if records:
            db.add_all(records)
            await db.commit()
