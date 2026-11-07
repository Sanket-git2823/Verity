"""
Text chunking service for the Verity RAG platform.
Provides sentence-aware text splitting with configurable chunk size and overlap,
page number tracking, and per-chunk metadata.
"""

import hashlib
import re
from typing import List, Optional, Tuple

from app.config import settings
from app.utils.text import count_tokens


class ChunkingService:
    """Split documents into overlapping, sentence-aware chunks."""

    # Regex to split on sentence boundaries while keeping the delimiter
    _SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"\'\u201c\u2018(])|(?<=[.!?])\s+")

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> None:
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chunk_document(
        self,
        pages: List[Tuple[int, str]],
    ) -> List[dict]:
        """
        Split a document into chunks.

        Args:
            pages: List of (page_number, page_text) tuples.

        Returns:
            List of chunk dicts with keys:
              content, chunk_index, page_number, start_char, end_char,
              token_count, word_count, content_hash
        """
        if not pages:
            return []

        # Build a flat list of sentences annotated with page numbers
        annotated_sentences = self._split_into_sentences(pages)
        if not annotated_sentences:
            return []

        chunks = self._merge_sentences_into_chunks(annotated_sentences)
        return chunks

    def chunk_pages(self, pages: List[Tuple[int, str]], doc_id: Optional[str] = None) -> List[dict]:
        return self.chunk_document(pages)

    def chunk_text(self, text: str, doc_id: Optional[str] = None) -> List[dict]:
        if not text:
            return []
        return self.chunk_document([(1, text)])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _split_into_sentences(
        self, pages: List[Tuple[int, str]]
    ) -> List[dict]:
        """
        Split page texts into individual sentences, keeping track of the
        page number and character offset within the concatenated document.
        """
        sentences: List[dict] = []
        global_offset = 0

        for page_num, page_text in pages:
            if not page_text or not page_text.strip():
                # Account for the page separator even if empty
                global_offset += len(page_text) + 2  # +2 for the \n\n separator
                continue

            # Split the page text into sentences
            raw_sentences = self._SENTENCE_SPLIT_RE.split(page_text)
            local_offset = 0

            for sent in raw_sentences:
                stripped = sent.strip()
                if not stripped:
                    local_offset += len(sent)
                    continue

                sentences.append({
                    "text": stripped,
                    "page_number": page_num,
                    "start_char": global_offset + local_offset,
                    "end_char": global_offset + local_offset + len(stripped),
                })
                local_offset += len(sent)

            # Add separator offset between pages
            global_offset += len(page_text) + 2

        return sentences

    def _merge_sentences_into_chunks(
        self,
        sentences: List[dict],
    ) -> List[dict]:
        """
        Greedily merge sentences into chunks that respect chunk_size (in characters),
        adding overlap from previous sentences.
        """
        chunks: List[dict] = []
        chunk_index = 0
        i = 0
        total = len(sentences)

        while i < total:
            current_text_parts: List[str] = []
            current_length = 0
            current_page = sentences[i]["page_number"]
            start_char = sentences[i]["start_char"]
            end_char = sentences[i]["end_char"]
            first_idx = i

            # Greedily add sentences until we hit chunk_size
            while i < total:
                sent_text = sentences[i]["text"]
                addition_length = len(sent_text) + (1 if current_text_parts else 0)
                if current_length + addition_length > self.chunk_size and current_text_parts:
                    break
                current_text_parts.append(sent_text)
                current_length += addition_length
                end_char = sentences[i]["end_char"]
                # Use the first sentence's page as the chunk page
                i += 1

            content = " ".join(current_text_parts)

            if not content.strip():
                continue

            chunks.append(self._build_chunk_dict(
                content=content,
                chunk_index=chunk_index,
                page_number=current_page,
                start_char=start_char,
                end_char=end_char,
            ))
            chunk_index += 1

            # Handle overlap: rewind so the next chunk starts with some
            # sentences from the end of this chunk
            if self.chunk_overlap > 0 and i < total:
                overlap_chars = 0
                rewind = 0
                # Walk backwards from the last sentence included
                for j in range(i - 1, first_idx, -1):
                    overlap_chars += len(sentences[j]["text"]) + 1
                    rewind += 1
                    if overlap_chars >= self.chunk_overlap:
                        break
                i = i - rewind

        return chunks

    @staticmethod
    def _build_chunk_dict(
        content: str,
        chunk_index: int,
        page_number: int,
        start_char: int,
        end_char: int,
    ) -> dict:
        """Construct the chunk metadata dict."""
        word_count = len(content.split())
        return {
            "content": content,
            "chunk_index": chunk_index,
            "page_number": page_number,
            "start_char": start_char,
            "end_char": end_char,
            "token_count": count_tokens(content),
            "word_count": word_count,
            "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        }
