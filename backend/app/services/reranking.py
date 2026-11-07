"""
Cross-encoder reranking service for the Verity RAG platform.
Lazy-loads a sentence-transformers CrossEncoder model and scores
(query, chunk) pairs for relevance reranking.
"""

import logging
from typing import List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class RerankingService:
    """Rerank retrieval candidates using a cross-encoder model."""

    _model = None
    _model_name: Optional[str] = None

    def __init__(self) -> None:
        self.model_name = settings.RERANKER_MODEL
        self.top_k = settings.RERANKER_TOP_K

    # ------------------------------------------------------------------
    # Model lifecycle
    # ------------------------------------------------------------------

    @classmethod
    def _load_model(cls, model_name: str):
        """Lazy-load the cross-encoder model. Cached at class level."""
        if cls._model is not None and cls._model_name == model_name:
            return cls._model

        try:
            from sentence_transformers import CrossEncoder
            logger.info("Loading reranker model: %s", model_name)
            cls._model = CrossEncoder(model_name)
            cls._model_name = model_name
            logger.info("Reranker model loaded successfully.")
            return cls._model
        except Exception as exc:
            logger.error("Failed to load reranker model %s: %s", model_name, exc)
            cls._model = None
            cls._model_name = None
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def rerank(
        self,
        query: str,
        chunks: List[dict],
        top_k: Optional[int] = None,
    ) -> List[dict]:
        """
        Rerank chunks by cross-encoder relevance to the query.

        Args:
            query: The search query.
            chunks: List of chunk dicts, each with at least ``id`` and ``content``.
            top_k: Number of top results to return. Defaults to settings.RERANKER_TOP_K.

        Returns:
            Reranked list of chunk dicts (top_k items), each augmented with
            a ``rerank_score`` key.
        """
        if not chunks:
            return []

        top_k = top_k or self.top_k
        top_k = min(top_k, len(chunks))

        model = self._load_model(self.model_name)
        if model is None:
            logger.warning("Reranker unavailable; returning original ranking.")
            return chunks[:top_k]

        try:
            # Build (query, passage) pairs
            pairs = [(query, chunk["content"]) for chunk in chunks]
            scores = model.predict(pairs)

            # Attach scores
            scored_chunks: List[dict] = []
            for chunk, score in zip(chunks, scores):
                enriched = {**chunk, "rerank_score": float(score)}
                scored_chunks.append(enriched)

            # Sort descending by rerank score
            scored_chunks.sort(key=lambda c: c["rerank_score"], reverse=True)
            return scored_chunks[:top_k]

        except Exception as exc:
            logger.error("Reranking failed: %s. Falling back to original ranking.", exc)
            return chunks[:top_k]
