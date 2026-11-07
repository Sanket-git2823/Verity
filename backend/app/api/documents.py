"""Document API routes – upload, list, detail, delete."""

import os
import hashlib
import logging
import uuid as uuid_mod
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Query
from sqlalchemy import select, func, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.database import get_db, async_session
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    DocumentDetailResponse,
    DocumentUploadResponse,
    BatchUploadResponse,
    ChunkResponse,
)
from app.services.ingestion import IngestionService

logger = logging.getLogger("verity.api.documents")

router = APIRouter(prefix="/api/documents", tags=["Documents"])

SUPPORTED_EXTENSIONS: list[str] = [
    ext.strip().lower() for ext in settings.SUPPORTED_EXTENSIONS.split(",") if ext.strip()
]
MAX_FILE_BYTES: int = settings.MAX_FILE_SIZE_MB * 1024 * 1024


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_file(upload: UploadFile) -> None:
    """Raise HTTPException if the file is not acceptable."""
    if not upload.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")
    ext = os.path.splitext(upload.filename)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Supported: {', '.join(SUPPORTED_EXTENSIONS)}",
        )


async def _read_and_validate_size(upload: UploadFile) -> bytes:
    """Read the full file body and enforce size limit."""
    content = await upload.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {settings.MAX_FILE_SIZE_MB} MB.",
        )
    return content


async def _save_upload(filename: str, content: bytes) -> Path:
    """Persist the raw uploaded file to disk."""
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / filename
    dest.write_bytes(content)
    return dest


async def _create_document_record(
    db: AsyncSession,
    original_filename: str,
    content: bytes,
    source: Optional[str],
    title: Optional[str],
    author: Optional[str],
) -> Document:
    """Create a pending Document row and flush to get its id."""
    ext = os.path.splitext(original_filename)[1].lower()
    file_hash = hashlib.sha256(content).hexdigest()

    # Check for duplicate
    existing = await db.execute(select(Document).where(Document.file_hash == file_hash))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A document with identical content already exists.")

    stored_filename = f"{uuid_mod.uuid4().hex}{ext}"
    await _save_upload(stored_filename, content)

    doc = Document(
        filename=stored_filename,
        original_filename=original_filename,
        file_type=ext.lstrip("."),
        file_size=len(content),
        file_hash=file_hash,
        source=source,
        title=title,
        author=author,
        status=DocumentStatus.PENDING,
    )
    db.add(doc)
    await db.flush()
    return doc


async def _background_process(document_id, file_path: str) -> None:
    """Run ingestion in a new DB session (background task)."""
    async with async_session() as db:
        try:
            service = IngestionService()
            await service.process_document(document_id, file_path, db)
            await db.commit()
        except Exception as exc:
            logger.exception("Background ingestion failed for %s: %s", document_id, exc)
            await db.rollback()
            # Mark document as failed
            doc = await db.get(Document, document_id)
            if doc:
                doc.status = DocumentStatus.FAILED
                doc.error_message = str(exc)[:2000]
                await db.commit()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=DocumentUploadResponse, status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    source: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload a single document for ingestion."""
    _validate_file(file)
    content = await _read_and_validate_size(file)

    doc = await _create_document_record(db, file.filename, content, source, title, author)
    await db.commit()

    file_path = str(Path(settings.UPLOAD_DIR) / doc.filename)
    background_tasks.add_task(_background_process, doc.id, file_path)

    logger.info("Accepted document %s (%s)", doc.id, file.filename)
    return DocumentUploadResponse(
        id=doc.id,
        filename=doc.original_filename,
        status=doc.status.value,
        message="Document accepted for processing.",
    )


@router.post("/batch", response_model=BatchUploadResponse, status_code=202)
async def batch_upload(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload multiple documents at once."""
    results: list[DocumentUploadResponse] = []
    accepted = 0
    rejected = 0

    for upload in files:
        try:
            _validate_file(upload)
            content = await _read_and_validate_size(upload)
            doc = await _create_document_record(db, upload.filename, content, None, None, None)
            await db.flush()

            file_path = str(Path(settings.UPLOAD_DIR) / doc.filename)
            background_tasks.add_task(_background_process, doc.id, file_path)

            results.append(DocumentUploadResponse(
                id=doc.id,
                filename=doc.original_filename,
                status=doc.status.value,
                message="Accepted for processing.",
            ))
            accepted += 1
        except HTTPException as exc:
            results.append(DocumentUploadResponse(
                id=uuid_mod.UUID(int=0),
                filename=upload.filename or "unknown",
                status="rejected",
                message=exc.detail,
            ))
            rejected += 1

    await db.commit()
    return BatchUploadResponse(
        total_files=len(files),
        accepted=accepted,
        rejected=rejected,
        results=results,
    )


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    status: Optional[str] = Query(None, description="Filter by document status"),
    file_type: Optional[str] = Query(None, description="Filter by file type (pdf, docx, …)"),
    search: Optional[str] = Query(None, description="Full-text search on filename / title"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at", description="Column to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
):
    """List documents with filtering, search, and pagination."""
    stmt = select(Document)

    # Filters
    if status:
        try:
            status_enum = DocumentStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status '{status}'.")
        stmt = stmt.where(Document.status == status_enum)

    if file_type:
        stmt = stmt.where(Document.file_type == file_type.lower().lstrip("."))

    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Document.filename.ilike(pattern),
                Document.original_filename.ilike(pattern),
                Document.title.ilike(pattern),
            )
        )

    # Total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Sorting
    sort_column = getattr(Document, sort_by, Document.created_at)
    order_func = desc if sort_order == "desc" else asc
    stmt = stmt.order_by(order_func(sort_column))

    # Pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    rows = (await db.execute(stmt)).scalars().all()
    total_pages = max(1, -(-total // page_size))  # ceil division

    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in rows],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(document_id: uuid_mod.UUID, db: AsyncSession = Depends(get_db)):
    """Get a single document with its chunks (embedding vectors excluded)."""
    stmt = (
        select(Document)
        .options(selectinload(Document.chunks))
        .where(Document.id == document_id)
    )
    doc = (await db.execute(stmt)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    chunks = [
        ChunkResponse(
            id=c.id,
            document_id=c.document_id,
            chunk_index=c.chunk_index,
            content=c.content,
            page_number=c.page_number,
            token_count=c.token_count,
            word_count=c.word_count,
            has_embedding=c.embedding is not None,
            created_at=c.created_at,
        )
        for c in sorted(doc.chunks, key=lambda c: c.chunk_index)
    ]

    resp = DocumentDetailResponse.model_validate(doc)
    resp.chunks = chunks
    return resp


@router.delete("/{document_id}")
async def delete_document(document_id: uuid_mod.UUID, db: AsyncSession = Depends(get_db)):
    """Delete a document and its chunks; remove the stored file."""
    doc = await db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Remove physical file
    file_path = Path(settings.UPLOAD_DIR) / doc.filename
    if file_path.exists():
        file_path.unlink()

    await db.delete(doc)
    await db.flush()

    logger.info("Deleted document %s", document_id)
    return {"detail": "Document deleted successfully.", "id": str(document_id)}
