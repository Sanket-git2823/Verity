"""
Information Retrieval (IR) and RAG evaluation metric algorithms.
Provides standard implementations for Recall@K, Precision@K, MRR, NDCG@K,
Reciprocal Rank Fusion (RRF), and Answer Faithfulness.
"""

import math
import re
from typing import Any, Dict, List, Optional, Set


def compute_recall_at_k(
    retrieved: List[str],
    relevant: Set[str],
    k: int = 10,
) -> float:
    """
    Recall@K = |retrieved_top_k ∩ relevant| / |relevant|
    Measures the fraction of relevant documents that were successfully retrieved.
    """
    if not relevant:
        return 1.0
    if k <= 0 or not retrieved:
        return 0.0
    retrieved_top_k = set(retrieved[:k])
    return len(retrieved_top_k & relevant) / len(relevant)


def compute_precision_at_k(
    retrieved: List[str],
    relevant: Set[str],
    k: int = 10,
) -> float:
    """
    Precision@K = |retrieved_top_k ∩ relevant| / K
    Measures the fraction of retrieved top-K documents that are truly relevant.
    """
    if k <= 0:
        return 0.0
    if not retrieved:
        return 0.0
    retrieved_top_k = set(retrieved[:k])
    return len(retrieved_top_k & relevant) / k


def compute_reciprocal_rank(
    retrieved: List[str],
    relevant: Set[str],
) -> float:
    """
    Reciprocal Rank (RR) = 1 / rank_of_first_relevant
    Returns 0.0 if no relevant chunk is retrieved.
    """
    for rank, item in enumerate(retrieved, start=1):
        if item in relevant:
            return 1.0 / rank
    return 0.0


def compute_ndcg_at_k(
    retrieved: List[str],
    relevant: Set[str],
    relevance_labels: Optional[Dict[str, float]] = None,
    k: int = 10,
) -> float:
    """
    Normalized Discounted Cumulative Gain (NDCG@K).
    Supports graded relevance labels (e.g. 0.0 to 3.0).
    DCG@K = sum_{i=1}^K (2^{rel_i} - 1) / log2(i + 1)
    """
    if not retrieved or not relevant or k <= 0:
        return 0.0

    # Compute Discounted Cumulative Gain (DCG)
    dcg = 0.0
    for i, item in enumerate(retrieved[:k], start=1):
        if relevance_labels and item in relevance_labels:
            rel = float(relevance_labels[item])
        elif item in relevant:
            rel = 1.0
        else:
            rel = 0.0
        dcg += (math.pow(2, rel) - 1.0) / math.log2(i + 1)

    # Compute Ideal DCG (IDCG)
    if relevance_labels:
        ideal_rels = sorted(
            [float(relevance_labels.get(cid, 1.0)) for cid in relevant],
            reverse=True,
        )
    else:
        ideal_rels = [1.0] * len(relevant)

    idcg = 0.0
    for i, rel in enumerate(ideal_rels[:k], start=1):
        idcg += (math.pow(2, rel) - 1.0) / math.log2(i + 1)

    if idcg <= 0.0:
        return 0.0

    return min(max(dcg / idcg, 0.0), 1.0)


def compute_rrf_score(
    rank_bm25: Optional[int],
    rank_vector: Optional[int],
    k: int = 60,
    w_bm25: float = 0.4,
    w_vector: float = 0.6,
) -> float:
    """
    Reciprocal Rank Fusion formula:
    RRF_score = w_bm25 * (1 / (k + rank_bm25)) + w_vector * (1 / (k + rank_vector))
    """
    score = 0.0
    if rank_bm25 is not None and rank_bm25 > 0:
        score += w_bm25 * (1.0 / (k + rank_bm25))
    if rank_vector is not None and rank_vector > 0:
        score += w_vector * (1.0 / (k + rank_vector))
    return score


def compute_faithfulness(
    answer: str,
    evidence_passages: List[str],
) -> float:
    """
    Empirical faithfulness metric: measures the proportion of key assertions
    in the generated answer that are lexically/semantically grounded in the evidence.
    """
    if not answer or not evidence_passages:
        return 0.0

    # Extract claims / sentences from answer
    sentences = [s.strip() for s in re.split(r"[.!?]+", answer) if len(s.strip()) > 10]
    if not sentences:
        return 0.5

    corpus_text = " ".join(evidence_passages).lower()
    grounded_count = 0

    for sentence in sentences:
        # Check token overlap of significant words
        words = [w.lower() for w in re.findall(r"\b[a-zA-Z]{4,}\b", sentence)]
        if not words:
            continue
        matches = sum(1 for w in words if w in corpus_text)
        overlap_ratio = matches / len(words)
        if overlap_ratio >= 0.5:
            grounded_count += 1

    return min(max(grounded_count / len(sentences), 0.0), 1.0)


def compute_citation_correctness(
    citations: List[Dict[str, Any]],
    chunk_map: Dict[str, str],
) -> float:
    """
    Validates that cited passage indices reference chunks containing the claimed content.
    """
    if not citations:
        return 1.0

    valid = 0
    for c in citations:
        chunk_id = str(c.get("chunk_id", ""))
        cited_text = c.get("cited_text", "").strip().lower()
        if chunk_id in chunk_map:
            actual_content = chunk_map[chunk_id].lower()
            if cited_text[:50] in actual_content or not cited_text:
                valid += 1

    return valid / len(citations)
