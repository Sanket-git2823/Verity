"""Unit tests for sentence-aware chunking service."""

import pytest
from app.services.chunking import ChunkingService


def test_chunking_basic():
    service = ChunkingService()
    text = (
        "Retrieval-augmented generation improves language models by retrieving relevant evidence. "
        "Dense vectors capture semantic meaning effectively. "
        "BM25 keyword search ensures lexical fidelity. "
        "Hybrid search merges the strengths of both approaches using reciprocal rank fusion."
    )
    chunks = service.chunk_text(text, doc_id="test-doc-1")
    assert len(chunks) >= 1
    assert "content" in chunks[0]
    assert "content_hash" in chunks[0]
    assert "token_count" in chunks[0]
    assert chunks[0]["chunk_index"] == 0


def test_chunking_with_pages():
    service = ChunkingService(chunk_size=10)
    pages = [
        (1, "Page one discusses dense embeddings and neural search architectures in deep learning."),
        (2, "Page two discusses cross-encoder rerankers and score distributions in information retrieval."),
    ]
    chunks = service.chunk_pages(pages, doc_id="test-doc-2")
    assert len(chunks) >= 2
    assert chunks[0]["page_number"] == 1
    assert "dense embeddings" in chunks[0]["content"]


def test_chunking_empty_text():
    service = ChunkingService()
    chunks = service.chunk_text("", doc_id="empty-doc")
    assert len(chunks) == 0


def test_chunk_hash_deterministic():
    service = ChunkingService()
    text = "Deterministic chunk content hashing verification."
    c1 = service.chunk_text(text, doc_id="d1")
    c2 = service.chunk_text(text, doc_id="d2")
    assert c1[0]["content_hash"] == c2[0]["content_hash"]
