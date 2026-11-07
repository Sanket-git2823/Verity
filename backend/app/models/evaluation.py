"""Evaluation dataset and run models."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime,
    ForeignKey, Index, JSON, Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class EvaluationDataset(Base):
    __tablename__ = "evaluation_datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(256), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    item_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    items = relationship("EvaluationDatasetItem", back_populates="dataset", cascade="all, delete-orphan")
    runs = relationship("EvaluationRun", back_populates="dataset", cascade="all, delete-orphan")


class EvaluationDatasetItem(Base):
    __tablename__ = "evaluation_dataset_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    query_text = Column(Text, nullable=False)
    expected_answer = Column(Text, nullable=True)
    relevant_document_ids = Column(JSON, nullable=True)  # list of document UUIDs
    relevant_chunk_ids = Column(JSON, nullable=True)  # list of chunk UUIDs
    relevance_labels = Column(JSON, nullable=True)  # {chunk_id: relevance_grade}
    metadata_extra = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    dataset = relationship("EvaluationDataset", back_populates="items")


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_datasets.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    config = Column(JSON, nullable=False)  # retrieval config used
    status = Column(String(32), default="pending")  # pending, running, completed, failed
    # Aggregate metrics
    recall_at_k = Column(JSON, nullable=True)  # {5: 0.72, 10: 0.85, ...}
    precision_at_k = Column(JSON, nullable=True)
    mrr = Column(Float, nullable=True)
    ndcg_at_k = Column(JSON, nullable=True)
    avg_faithfulness = Column(Float, nullable=True)
    avg_citation_correctness = Column(Float, nullable=True)
    avg_latency_ms = Column(Float, nullable=True)
    p50_latency_ms = Column(Float, nullable=True)
    p95_latency_ms = Column(Float, nullable=True)
    total_queries = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    dataset = relationship("EvaluationDataset", back_populates="runs")
    results = relationship("EvaluationRunResult", back_populates="run", cascade="all, delete-orphan")


class EvaluationRunResult(Base):
    __tablename__ = "evaluation_run_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    dataset_item_id = Column(UUID(as_uuid=True), ForeignKey("evaluation_dataset_items.id", ondelete="SET NULL"), nullable=True)
    query_text = Column(Text, nullable=False)
    generated_answer = Column(Text, nullable=True)
    retrieved_chunk_ids = Column(JSON, nullable=True)
    relevant_chunk_ids = Column(JSON, nullable=True)  # ground truth
    recall = Column(Float, nullable=True)
    precision = Column(Float, nullable=True)
    reciprocal_rank = Column(Float, nullable=True)
    ndcg = Column(Float, nullable=True)
    faithfulness = Column(Float, nullable=True)
    citation_correctness = Column(Float, nullable=True)
    latency_ms = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    run = relationship("EvaluationRun", back_populates="results")
