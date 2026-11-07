"""
Text processing utilities for the Verity RAG platform.
Provides normalization, keyword extraction, token counting, and hashing.
"""

import hashlib
import re
import unicodedata
from typing import List


STOPWORDS: set[str] = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
    "be", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "need", "must",
    "not", "no", "nor", "so", "if", "then", "than", "too", "very",
    "just", "about", "above", "after", "again", "all", "also", "am",
    "any", "because", "before", "below", "between", "both", "during",
    "each", "few", "further", "get", "got", "here", "how", "i", "into",
    "it", "its", "itself", "me", "more", "most", "my", "myself", "now",
    "only", "other", "our", "out", "over", "own", "same", "she", "he",
    "her", "him", "his", "hers", "some", "such", "that", "their", "them",
    "themselves", "these", "they", "this", "those", "through", "under",
    "until", "up", "we", "what", "when", "where", "which", "while",
    "who", "whom", "why", "you", "your", "yours", "yourself", "being",
    "having", "doing", "s", "t", "d", "ll", "ve", "re", "m",
    "don", "didn", "doesn", "isn", "wasn", "aren", "weren", "won",
    "wouldn", "couldn", "shouldn", "hasn", "haven", "hadn",
}


def normalize_text(text: str) -> str:
    """
    Normalize unicode characters, collapse whitespace, and strip leading/trailing space.
    """
    if not text:
        return ""
    # Normalize unicode to NFC form
    text = unicodedata.normalize("NFC", text)
    # Replace various unicode whitespace characters with standard space
    text = re.sub(r"[\u00a0\u2000-\u200b\u2028\u2029\u3000\ufeff]", " ", text)
    # Replace carriage returns with newlines
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse multiple consecutive blank lines into a single blank line
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse multiple spaces (not newlines) into a single space
    text = re.sub(r"[^\S\n]+", " ", text)
    # Strip leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)
    # Final strip
    return text.strip()


def extract_keywords(text: str) -> List[str]:
    """
    Simple keyword extraction: tokenize, lowercase, remove stopwords and
    short/numeric-only tokens, deduplicate while preserving order.
    """
    if not text:
        return []
    # Tokenize on non-alphanumeric boundaries
    tokens = re.findall(r"[a-zA-Z0-9]+(?:'[a-zA-Z]+)?", text.lower())
    seen: set[str] = set()
    keywords: List[str] = []
    for token in tokens:
        # Skip stopwords, very short tokens, and pure numbers
        if token in STOPWORDS:
            continue
        if len(token) < 2:
            continue
        if token.isdigit():
            continue
        if token not in seen:
            seen.add(token)
            keywords.append(token)
    return keywords


def count_tokens(text: str) -> int:
    """
    Approximate token count using word count * 1.3 heuristic.
    This is a fast approximation that avoids loading a tokenizer.
    """
    if not text:
        return 0
    word_count = len(text.split())
    return int(word_count * 1.3)


def compute_hash(content: bytes) -> str:
    """
    Compute SHA-256 hex digest of the given byte content.
    """
    return hashlib.sha256(content).hexdigest()
