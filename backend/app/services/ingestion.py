"""
Document ingestion service for the Verity RAG platform.
Handles file upload, text extraction, normalization, hashing, and
orchestrates the full document processing pipeline.
"""

import asyncio
import hashlib
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from fastapi import UploadFile
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.services.chunking import ChunkingService
from app.services.embedding import EmbeddingService
from app.utils.text import compute_hash, normalize_text

logger = logging.getLogger(__name__)


class IngestionService:
    """Orchestrates document ingestion: upload, extraction, chunking, embedding, indexing."""

    def __init__(self) -> None:
        self.chunking_service = ChunkingService()
        self.embedding_service = EmbeddingService()
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # File I/O helpers
    # ------------------------------------------------------------------

    async def save_upload(self, upload: UploadFile) -> Tuple[Path, bytes]:
        """Read uploaded file contents and persist to UPLOAD_DIR. Returns (path, raw_bytes)."""
        raw_bytes = await upload.read()
        file_id = uuid.uuid4().hex[:16]
        safe_name = f"{file_id}_{upload.filename}"
        dest = self.upload_dir / safe_name
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, dest.write_bytes, raw_bytes)
        logger.info("Saved upload %s (%d bytes) to %s", upload.filename, len(raw_bytes), dest)
        return dest, raw_bytes

    # ------------------------------------------------------------------
    # Text extraction
    # ------------------------------------------------------------------

    async def extract_text(self, file_path: Path, file_type: str, raw_bytes: bytes) -> Tuple[str, List[Tuple[int, str]], dict]:
        """
        Extract text from a file.

        Returns:
            (full_text, pages_list, metadata_dict)
            pages_list is a list of (page_number, page_text) tuples.
            metadata_dict may contain title, author, page_count.
        """
        loop = asyncio.get_running_loop()
        ext = file_type.lower().lstrip(".")
        if ext == "pdf":
            return await loop.run_in_executor(None, self._extract_pdf, file_path, raw_bytes)
        elif ext == "docx":
            return await loop.run_in_executor(None, self._extract_docx, file_path, raw_bytes)
        elif ext in ("txt", "text"):
            return await loop.run_in_executor(None, self._extract_txt, raw_bytes)
        elif ext in ("md", "markdown"):
            return await loop.run_in_executor(None, self._extract_txt, raw_bytes)
        elif ext == "csv":
            return await loop.run_in_executor(None, self._extract_csv, raw_bytes)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    @staticmethod
    def _extract_pdf(file_path: Path, raw_bytes: bytes) -> Tuple[str, List[Tuple[int, str]], dict]:
        import io
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(raw_bytes))
        metadata: dict = {}
        if reader.metadata:
            metadata["title"] = reader.metadata.get("/Title") or reader.metadata.get("title") or ""
            metadata["author"] = reader.metadata.get("/Author") or reader.metadata.get("author") or ""
        metadata["page_count"] = len(reader.pages)

        pages: List[Tuple[int, str]] = []
        full_parts: List[str] = []
        for idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            pages.append((idx + 1, text))
            full_parts.append(text)

        full_text = "\n\n".join(full_parts)
        return full_text, pages, metadata

    @staticmethod
    def _extract_docx(file_path: Path, raw_bytes: bytes) -> Tuple[str, List[Tuple[int, str]], dict]:
        import io
        from docx import Document as DocxDocument

        doc = DocxDocument(io.BytesIO(raw_bytes))
        metadata: dict = {}
        core = doc.core_properties
        metadata["title"] = core.title or ""
        metadata["author"] = core.author or ""

        paragraphs: List[str] = []
        for para in doc.paragraphs:
            if para.text.strip():
                paragraphs.append(para.text)

        full_text = "\n\n".join(paragraphs)
        # DOCX doesn't have explicit pages; treat entire doc as page 1
        pages: List[Tuple[int, str]] = [(1, full_text)]
        metadata["page_count"] = 1
        return full_text, pages, metadata

    @staticmethod
    def _extract_txt(raw_bytes: bytes) -> Tuple[str, List[Tuple[int, str]], dict]:
        text = raw_bytes.decode("utf-8", errors="replace")
        pages: List[Tuple[int, str]] = [(1, text)]
        metadata: dict = {"page_count": 1}
        return text, pages, metadata

    @staticmethod
    def _extract_csv(raw_bytes: bytes) -> Tuple[str, List[Tuple[int, str]], dict]:
        import csv
        import io

        text = raw_bytes.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        rows: List[str] = []
        for row in reader:
            rows.append(" | ".join(row))
        full_text = "\n".join(rows)
        pages: List[Tuple[int, str]] = [(1, full_text)]
        metadata: dict = {"page_count": 1}
        return full_text, pages, metadata

    # ------------------------------------------------------------------
    # Duplicate detection
    # ------------------------------------------------------------------

    async def check_duplicate(self, db: AsyncSession, file_hash: str) -> Optional[Document]:
        """Return an existing document with the same hash, or None."""
        result = await db.execute(
            select(Document).where(Document.file_hash == file_hash).limit(1)
        )
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    @staticmethod
    async def _set_status(
        db: AsyncSession,
        doc_id: uuid.UUID,
        status: DocumentStatus,
        error_message: Optional[str] = None,
    ) -> None:
        values: dict = {"status": status}
        if error_message is not None:
            values["error_message"] = error_message
        if status == DocumentStatus.completed:
            values["processed_at"] = datetime.now(timezone.utc)
        await db.execute(update(Document).where(Document.id == doc_id).values(**values))
        await db.commit()

    # ------------------------------------------------------------------
    # Single-file processing pipeline
    # ------------------------------------------------------------------

    async def ingest_upload(self, upload: UploadFile, db: AsyncSession, source: str = "upload") -> Document:
        """
        Accept a single UploadFile, save it, create a Document record, and
        kick off the async processing pipeline.  Returns the Document immediately.
        """
        file_path, raw_bytes = await self.save_upload(upload)
        file_hash = compute_hash(raw_bytes)

        # Duplicate check
        existing = await self.check_duplicate(db, file_hash)
        if existing is not None:
            logger.info("Duplicate detected: %s matches document %s", upload.filename, existing.id)
            doc = Document(
                filename=file_path.name,
                original_filename=upload.filename,
                file_type=Path(upload.filename).suffix.lstrip(".").lower(),
                file_size=len(raw_bytes),
                file_hash=file_hash,
                source=source,
                status=DocumentStatus.duplicate,
                error_message=f"Duplicate of document {existing.id}",
            )
            db.add(doc)
            await db.commit()
            await db.refresh(doc)
            return doc

        file_type = Path(upload.filename).suffix.lstrip(".").lower()
        doc = Document(
            filename=file_path.name,
            original_filename=upload.filename,
            file_type=file_type,
            file_size=len(raw_bytes),
            file_hash=file_hash,
            source=source,
            status=DocumentStatus.pending,
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        # Launch background processing
        asyncio.create_task(self.process_document(doc.id, file_path, raw_bytes, file_type))
        return doc

    async def process_document(
        self,
        document_id: uuid.UUID,
        file_path: Path,
        raw_bytes: bytes,
        file_type: str,
    ) -> None:
        """
        Full processing pipeline for a single document:
        PENDING → PROCESSING → CHUNKING → EMBEDDING → INDEXING → COMPLETED
        """
        async with async_session() as db:
            try:
                # --- PROCESSING: extract text ---
                await self._set_status(db, document_id, DocumentStatus.processing)
                full_text, pages, metadata = await self.extract_text(file_path, file_type, raw_bytes)
                normalized_text = normalize_text(full_text)

                if not normalized_text.strip():
                    await self._set_status(db, document_id, DocumentStatus.failed, "No text could be extracted from the document.")
                    return

                word_count = len(normalized_text.split())
                page_count = metadata.get("page_count", 1)
                title = metadata.get("title", "")
                author = metadata.get("author", "")

                await db.execute(
                    update(Document)
                    .where(Document.id == document_id)
                    .values(
                        title=title or None,
                        author=author or None,
                        page_count=page_count,
                        word_count=word_count,
                    )
                )
                await db.commit()

                # --- CHUNKING ---
                await self._set_status(db, document_id, DocumentStatus.chunking)
                chunks = self.chunking_service.chunk_document(pages)

                if not chunks:
                    await self._set_status(db, document_id, DocumentStatus.failed, "Document produced zero chunks after splitting.")
                    return

                # --- EMBEDDING ---
                await self._set_status(db, document_id, DocumentStatus.embedding)
                chunk_texts = [c["content"] for c in chunks]
                embeddings = await self.embedding_service.embed_texts(chunk_texts)

                # --- INDEXING: store chunks ---
                await self._set_status(db, document_id, DocumentStatus.indexing)
                chunk_records: List[DocumentChunk] = []
                for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    record = DocumentChunk(
                        document_id=document_id,
                        chunk_index=idx,
                        content=chunk["content"],
                        content_hash=chunk["content_hash"],
                        page_number=chunk["page_number"],
                        start_char=chunk["start_char"],
                        end_char=chunk["end_char"],
                        token_count=chunk["token_count"],
                        word_count=chunk["word_count"],
                        embedding=embedding,
                    )
                    chunk_records.append(record)

                db.add_all(chunk_records)
                await db.commit()

                # Update chunk_count on the document
                await db.execute(
                    update(Document)
                    .where(Document.id == document_id)
                    .values(chunk_count=len(chunk_records))
                )
                await db.commit()

                # --- COMPLETED ---
                await self._set_status(db, document_id, DocumentStatus.completed)
                logger.info(
                    "Document %s processed successfully: %d chunks, %d words",
                    document_id, len(chunk_records), word_count,
                )

            except Exception as exc:
                logger.exception("Failed to process document %s: %s", document_id, exc)
                try:
                    await self._set_status(db, document_id, DocumentStatus.failed, str(exc)[:1000])
                except Exception:
                    logger.exception("Failed to set FAILED status for document %s", document_id)

    # ------------------------------------------------------------------
    # Batch processing
    # ------------------------------------------------------------------

    async def process_batch(
        self, uploads: List[UploadFile], db: AsyncSession, source: str = "batch_upload"
    ) -> List[Document]:
        """
        Process multiple file uploads concurrently, using a semaphore to
        limit parallelism to BATCH_INGESTION_WORKERS.
        """
        semaphore = asyncio.Semaphore(settings.BATCH_INGESTION_WORKERS)
        documents: List[Document] = []

        async def _ingest_one(upload: UploadFile) -> Document:
            async with semaphore:
                return await self.ingest_upload(upload, db, source=source)

        tasks = [_ingest_one(upload) for upload in uploads]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Batch ingestion failed for file %s: %s", uploads[i].filename, result)
            else:
                documents.append(result)

        logger.info("Batch ingestion complete: %d/%d files accepted", len(documents), len(uploads))
        return documents
