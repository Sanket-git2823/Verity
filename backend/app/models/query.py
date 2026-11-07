"""Query, answer, citation, and retrieval result models."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime,
    ForeignKey, Index, JSON, Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Query(Base):
    __tablename__ = "queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_query = Column(Text, nullable=False)
    normalized_query = Column(Text, nullable=True)
    extracted_keywords = Column(JSON, nullable=True)
    metadata_filters = Column(JSON, nullable=True)
    retrieval_config = Column(JSON, nullable=True)  # bm25_weight, vector_weight, top_k, etc.
    total_chunks_retrieved = Column(Integer, default=0)
    retrieval_time_ms = Column(Float, nullable=True)
    generation_time_ms = Column(Float, nullable=True)
    total_time_ms = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    answer = relationship("GeneratedAnswer", back_populates="query", uselist=False, cascade="all, delete-orphan")
    retrieval_results = relationship("RetrievalResult", back_populates="query", cascade="all, delete-orphan")


class GeneratedAnswer(Base):
    __tablename__ = "generated_answers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id = Column(UUID(as_uuid=True), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False, unique=True)
    answer_text = Column(Text, nullable=False)
    evidence_summary = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)
    evidence_coverage = Column(Float, nullable=True)  # fraction of answer backed by evidence
    model_used = Column(String(128), nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    is_insufficient_evidence = Column(Boolean, default=False)
    raw_llm_response = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    query = relationship("Query", back_populates="answer")
    citations = relationship("Citation", back_populates="answer", cascade="all, delete-orphan")


class Citation(Base):
    __tablename__ = "citations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    answer_id = Column(UUID(as_uuid=True), ForeignKey("generated_answers.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    citation_index = Column(Integer, nullable=False)  # [1], [2], etc.
    cited_text = Column(Text, nullable=True)  # the quoted passage
    source_filename = Column(String(512), nullable=True)
    page_number = Column(Integer, nullable=True)
    relevance_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    answer = relationship("GeneratedAnswer", back_populates="citations")


class RetrievalResult(Base):
    __tablename__ = "retrieval_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id = Column(UUID(as_uuid=True), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(UUID(as_uuid=True), ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    retrieval_stage = Column(String(32), nullable=False)  # bm25, vector, rrf, reranked
    rank = Column(Integer, nullable=False)
    score = Column(Float, nullable=True)
    chunk_content_preview = Column(Text, nullable=True)
    source_filename = Column(String(512), nullable=True)
    page_number = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    query = relationship("Query", back_populates="retrieval_results")

    __table_args__ = (
        Index("ix_retrieval_query_stage", "query_id", "retrieval_stage"),
    )
