"""Unit tests for text processing utilities."""

import pytest
from app.utils.text import (
    normalize_text,
    extract_keywords,
    count_tokens,
    compute_hash,
)


def test_normalize_text():
    raw = "   Grounded   \n\t RAG   Evaluation \u00a0 Platform \r\n  "
    cleaned = normalize_text(raw)
    assert cleaned == "Grounded\nRAG Evaluation Platform"


def test_extract_keywords():
    query = "What is the computational complexity of transformer self-attention?"
    keywords = extract_keywords(query)
    assert "complexity" in keywords or "transformer" in keywords
    # Stopwords should be filtered
    assert "what" not in keywords
    assert "is" not in keywords
    assert "the" not in keywords
    assert "of" not in keywords


def test_count_tokens():
    text = "Dense retrieval uses vector representations."
    count = count_tokens(text)
    assert count > 0
    assert count >= len(text.split())


def test_compute_hash():
    data = b"Verity Research Intelligence"
    h1 = compute_hash(data)
    h2 = compute_hash(data)
    assert len(h1) == 64  # SHA-256 hex string
    assert h1 == h2
