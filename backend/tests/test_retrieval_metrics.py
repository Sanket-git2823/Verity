"""Unit tests for information retrieval evaluation metrics."""

import pytest
from app.utils.metrics import (
    compute_recall_at_k,
    compute_precision_at_k,
    compute_reciprocal_rank,
    compute_ndcg_at_k,
    compute_rrf_score,
    compute_faithfulness,
)


def test_recall_at_k():
    retrieved = ["chunk-1", "chunk-2", "chunk-3", "chunk-4", "chunk-5"]
    relevant = {"chunk-2", "chunk-5", "chunk-8"}

    # At K=3: retrieved = [chunk-1, chunk-2, chunk-3], relevant in top 3 is {chunk-2}
    recall_3 = compute_recall_at_k(retrieved, relevant, k=3)
    assert recall_3 == pytest.approx(1 / 3, 0.01)

    # At K=5: retrieved has chunk-2 and chunk-5
    recall_5 = compute_recall_at_k(retrieved, relevant, k=5)
    assert recall_5 == pytest.approx(2 / 3, 0.01)


def test_precision_at_k():
    retrieved = ["chunk-1", "chunk-2", "chunk-3", "chunk-4", "chunk-5"]
    relevant = {"chunk-2", "chunk-5"}

    prec_2 = compute_precision_at_k(retrieved, relevant, k=2)
    assert prec_2 == pytest.approx(1 / 2, 0.01)

    prec_5 = compute_precision_at_k(retrieved, relevant, k=5)
    assert prec_5 == pytest.approx(2 / 5, 0.01)


def test_reciprocal_rank():
    retrieved = ["chunk-a", "chunk-b", "chunk-c"]
    relevant = {"chunk-b"}

    # First relevant chunk is at rank 2
    rr = compute_reciprocal_rank(retrieved, relevant)
    assert rr == pytest.approx(1 / 2, 0.001)

    # If first result is relevant
    rr_first = compute_reciprocal_rank(["chunk-b"], relevant)
    assert rr_first == 1.0

    # If not found
    rr_none = compute_reciprocal_rank(["chunk-x", "chunk-y"], relevant)
    assert rr_none == 0.0


def test_ndcg_at_k():
    retrieved = ["c1", "c2", "c3"]
    relevant = {"c1", "c2", "c3"}
    # Graded relevance: c1 is 2.0, c2 is 0.0, c3 is 3.0
    labels = {"c1": 2.0, "c2": 0.0, "c3": 3.0}

    ndcg = compute_ndcg_at_k(retrieved, relevant, relevance_labels=labels, k=3)
    assert 0.0 <= ndcg <= 1.0


def test_rrf_scoring():
    # Item ranked 1 in BM25, 2 in Vector
    score = compute_rrf_score(rank_bm25=1, rank_vector=2, k=60, w_bm25=0.4, w_vector=0.6)
    expected = 0.4 * (1.0 / 61.0) + 0.6 * (1.0 / 62.0)
    assert score == pytest.approx(expected, 0.0001)


def test_faithfulness_metric():
    evidence = ["Supervised fine-tuning aligns language models with human preferences."]
    grounded_answer = "Supervised fine-tuning effectively aligns language models."
    faithfulness = compute_faithfulness(grounded_answer, evidence)
    assert faithfulness > 0.5


def test_empty_retrieval_handles_gracefully():
    assert compute_recall_at_k([], {"c1"}, k=5) == 0.0
    assert compute_precision_at_k([], {"c1"}, k=5) == 0.0
    assert compute_reciprocal_rank([], {"c1"}) == 0.0
