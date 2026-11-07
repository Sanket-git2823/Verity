"""Document and chunk schemas."""

from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID


class DocumentBase(BaseModel):
    source: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    metadata_extra: Optional[dict] = None


class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    file_hash: str
    source: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    page_count: Optional[int] = None
    chunk_count: int = 0
    word_count: int = 0
    status: str
    error_message: Optional[str] = None
    metadata_extra: Optional[dict] = None
    metadata: Optional[dict] = None
    ingested_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    @model_validator(mode="before")
    @classmethod
    def populate_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "metadata" not in data and "metadata_extra" in data:
                data["metadata"] = data["metadata_extra"]
            if "metadata_extra" not in data and "metadata" in data:
                data["metadata_extra"] = data["metadata"]
        elif hasattr(data, "__dict__"):
            extra = getattr(data, "metadata_extra", None)
            if not getattr(data, "metadata", None):
                setattr(data, "metadata", extra)
        return data

    class Config:
        from_attributes = True


class ChunkResponse(BaseModel):
    id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    page_number: Optional[int] = None
    token_count: Optional[int] = None
    word_count: Optional[int] = None
    has_embedding: bool = False
    metadata: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentDetailResponse(DocumentResponse):
    chunks: List[ChunkResponse] = []


class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse] = []
    items: List[DocumentResponse] = []
    total: int
    page: int
    page_size: int
    total_pages: int

    @model_validator(mode="before")
    @classmethod
    def sync_documents_items(cls, data: Any) -> Any:
        if isinstance(data, dict):
            docs = data.get("documents") or data.get("items") or []
            data["documents"] = docs
            data["items"] = docs
        return data


class DocumentUploadResponse(BaseModel):
    id: UUID
    filename: str
    status: str
    message: str


class BatchUploadResponse(BaseModel):
    total_files: int
    accepted: int
    rejected: int
    results: List[DocumentUploadResponse]


class DocumentFilterParams(BaseModel):
    status: Optional[str] = None
    file_type: Optional[str] = None
    search: Optional[str] = None
    page: int = 1
    page_size: int = 20
    sort_by: str = "created_at"
    sort_order: str = "desc"
