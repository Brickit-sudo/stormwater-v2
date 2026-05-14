from __future__ import annotations

import uuid

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.mixins import (
    ArchivedMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class RecordLink(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "record_links"
    __table_args__ = (
        Index("ix_record_links_organization_id_source", "organization_id", "source_type", "source_id"),
        Index("ix_record_links_organization_id_target", "organization_id", "target_type", "target_id"),
        Index("ix_record_links_organization_id_relationship_type", "organization_id", "relationship_type"),
    )

    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(64), nullable=False, default="related")
    confidence: Mapped[float | None] = mapped_column(Float)
    link_reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))


class RecordNote(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "record_notes"
    __table_args__ = (
        Index("ix_record_notes_organization_id_parent", "organization_id", "parent_type", "parent_id"),
        Index("ix_record_notes_organization_id_note_type", "organization_id", "note_type"),
    )

    parent_type: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    note_type: Mapped[str] = mapped_column(String(64), nullable=False, default="general")
    visibility: Mapped[str] = mapped_column(String(64), nullable=False, default="internal")
    created_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))


class KnowledgeItem(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "knowledge_items"
    __table_args__ = (
        Index("ix_knowledge_items_organization_id_client_id", "organization_id", "client_id"),
        Index("ix_knowledge_items_organization_id_site_id", "organization_id", "site_id"),
        Index("ix_knowledge_items_organization_id_job_id", "organization_id", "job_id"),
        Index("ix_knowledge_items_organization_id_knowledge_type", "organization_id", "knowledge_type"),
    )

    client_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("clients.id"))
    site_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("sites.id"))
    job_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("jobs.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    knowledge_type: Mapped[str] = mapped_column(String(64), nullable=False)
    tags_json: Mapped[list[str] | None] = mapped_column(JSON)
    source_type: Mapped[str | None] = mapped_column(String(64))
    source_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))


class DocumentRecord(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "document_records"
    __table_args__ = (
        Index("ix_document_records_organization_id_status", "organization_id", "status"),
        Index("ix_document_records_organization_id_document_type", "organization_id", "document_type"),
        Index("ix_document_records_organization_id_client_id", "organization_id", "client_id"),
        Index("ix_document_records_organization_id_site_id", "organization_id", "site_id"),
        Index("ix_document_records_organization_id_job_id", "organization_id", "job_id"),
        Index("ix_document_records_organization_id_evidence_file_id", "organization_id", "evidence_file_id"),
    )

    evidence_file_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("evidence_files.id"),
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="manual")
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str | None] = mapped_column(Text)
    storage_path: Mapped[str | None] = mapped_column(Text)
    mime_type: Mapped[str | None] = mapped_column(String(128))
    document_type: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    client_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("clients.id"))
    site_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("sites.id"))
    job_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("jobs.id"))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    extraction_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_started")


class DocumentTextChunk(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    Base,
):
    __tablename__ = "document_text_chunks"
    __table_args__ = (
        Index(
            "ix_document_text_chunks_organization_id_document_id",
            "organization_id",
            "document_id",
            "chunk_index",
        ),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("document_records.id"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer)
    heading: Mapped[str | None] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class DocumentExtractedField(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "document_extracted_fields"
    __table_args__ = (
        Index(
            "ix_document_extracted_fields_organization_id_document_id",
            "organization_id",
            "document_id",
        ),
        Index("ix_document_extracted_fields_organization_id_review_status", "organization_id", "review_status"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("document_records.id"),
        nullable=False,
    )
    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    field_value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    source_page: Mapped[int | None] = mapped_column(Integer)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")


class DocumentLinkSuggestion(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "document_link_suggestions"
    __table_args__ = (
        Index(
            "ix_document_link_suggestions_organization_id_document_id",
            "organization_id",
            "document_id",
        ),
        Index("ix_document_link_suggestions_organization_id_review_status", "organization_id", "review_status"),
        Index("ix_document_link_suggestions_organization_id_target", "organization_id", "target_type", "target_id"),
    )

    document_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("document_records.id"),
        nullable=False,
    )
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    target_label: Mapped[str | None] = mapped_column(String(255))
    confidence: Mapped[float | None] = mapped_column(Float)
    reason: Mapped[str | None] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
