"""
Embedding service for the Verity RAG platform.
Calls an OpenAI-compatible embedding API with batching, retries, and
exponential backoff.
"""

import asyncio
import logging
from typing import List

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate vector embeddings via an OpenAI-compatible API."""

    MAX_RETRIES: int = 3
    BACKOFF_BASE: float = 1.0  # seconds

    def __init__(self) -> None:
        self.api_base = settings.EMBEDDING_API_BASE.rstrip("/")
        self.api_key = settings.EMBEDDING_API_KEY
        self.model = settings.EMBEDDING_MODEL
        self.dimensions = settings.EMBEDDING_DIMENSIONS
        self.batch_size = settings.EMBEDDING_BATCH_SIZE

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of texts in batches.  Returns a list of embedding vectors
        in the same order as the input texts.
        """
        if not texts:
            return []

        all_embeddings: List[List[float]] = []

        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            batch_embeddings = await self._embed_batch(batch)
            all_embeddings.extend(batch_embeddings)
            logger.debug(
                "Embedded batch %d-%d / %d",
                start, start + len(batch), len(texts),
            )

        return all_embeddings

    async def embed_query(self, text: str) -> List[float]:
        """Embed a single query string."""
        results = await self._embed_batch([text])
        return results[0]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Call the embedding API for a batch of texts with retry logic and offline fallback."""
        if not self.api_key:
            import hashlib
            import math
            results = []
            for t in texts:
                vec = []
                for i in range(self.dimensions):
                    h = hashlib.sha256(f"{t}_{i}".encode()).hexdigest()
                    val = (int(h[:8], 16) / 0xffffffff) * 2.0 - 1.0
                    vec.append(val)
                norm = math.sqrt(sum(x * x for x in vec)) or 1.0
                results.append([x / norm for x in vec])
            return results

        url = f"{self.api_base}/embeddings"
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload: dict = {
            "model": self.model,
            "input": texts,
        }
        if self.dimensions:
            payload["dimensions"] = self.dimensions

        last_exc: Exception | None = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()

                data = response.json()
                # Sort by index to ensure correct order
                sorted_data = sorted(data["data"], key=lambda d: d["index"])
                embeddings = [item["embedding"] for item in sorted_data]
                return embeddings

            except (httpx.HTTPStatusError, httpx.RequestError, KeyError) as exc:
                last_exc = exc
                wait = self.BACKOFF_BASE * (2 ** (attempt - 1))
                logger.warning(
                    "Embedding API attempt %d/%d failed: %s. Retrying in %.1fs",
                    attempt, self.MAX_RETRIES, exc, wait,
                )
                if attempt < self.MAX_RETRIES:
                    await asyncio.sleep(wait)

        raise RuntimeError(
            f"Embedding API failed after {self.MAX_RETRIES} attempts: {last_exc}"
        ) from last_exc
