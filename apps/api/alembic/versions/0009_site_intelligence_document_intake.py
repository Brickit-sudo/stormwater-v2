"""Add site intelligence and document intake foundation.

Revision ID: 0009_site_intel_docs
Revises: 0008_user_auth_fields
Create Date: 2026-05-14
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0009_site_intel_docs"
down_revision: str | None = "0008_user_auth_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def uuid_pk() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )


def org_id() -> sa.Column:
    return sa.Column(
        "organization_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("organizations.id"),
        nullable=False,
    )


def created_at() -> sa.Column:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def updated_at() -> sa.Column:
    return sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def archived_at() -> sa.Column:
    return sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True)


def upgrade() -> None:
    op.create_table(
        "record_links",
        uuid_pk(),
        org_id(),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_type", sa.String(length=64), nullable=False, server_default="related"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("link_reason", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        created_at(),
        updated_at(),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_record_links_organization_id_source", "record_links", ["organization_id", "source_type", "source_id"])
    op.create_index("ix_record_links_organization_id_target", "record_links", ["organization_id", "target_type", "target_id"])
    op.create_index("ix_record_links_organization_id_relationship_type", "record_links", ["organization_id", "relationship_type"])

    op.create_table(
        "record_notes",
        uuid_pk(),
        org_id(),
        sa.Column("parent_type", sa.String(length=64), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("note_type", sa.String(length=64), nullable=False, server_default="general"),
        sa.Column("visibility", sa.String(length=64), nullable=False, server_default="internal"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        created_at(),
        updated_at(),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_record_notes_organization_id_parent", "record_notes", ["organization_id", "parent_type", "parent_id"])
    op.create_index("ix_record_notes_organization_id_note_type", "record_notes", ["organization_id", "note_type"])

    op.create_table(
        "knowledge_items",
        uuid_pk(),
        org_id(),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=True),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("knowledge_type", sa.String(length=64), nullable=False),
        sa.Column("tags_json", sa.JSON(), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        created_at(),
        updated_at(),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_items_organization_id_client_id", "knowledge_items", ["organization_id", "client_id"])
    op.create_index("ix_knowledge_items_organization_id_site_id", "knowledge_items", ["organization_id", "site_id"])
    op.create_index("ix_knowledge_items_organization_id_job_id", "knowledge_items", ["organization_id", "job_id"])
    op.create_index("ix_knowledge_items_organization_id_knowledge_type", "knowledge_items", ["organization_id", "knowledge_type"])

    op.create_table(
        "document_records",
        uuid_pk(),
        org_id(),
        sa.Column("evidence_file_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("evidence_files.id"), nullable=True),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="manual"),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=True),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("document_type", sa.String(length=64), nullable=False, server_default="unknown"),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=True),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("extraction_status", sa.String(length=32), nullable=False, server_default="not_started"),
        created_at(),
        updated_at(),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_records_organization_id_status", "document_records", ["organization_id", "status"])
    op.create_index("ix_document_records_organization_id_document_type", "document_records", ["organization_id", "document_type"])
    op.create_index("ix_document_records_organization_id_client_id", "document_records", ["organization_id", "client_id"])
    op.create_index("ix_document_records_organization_id_site_id", "document_records", ["organization_id", "site_id"])
    op.create_index("ix_document_records_organization_id_job_id", "document_records", ["organization_id", "job_id"])
    op.create_index("ix_document_records_organization_id_evidence_file_id", "document_records", ["organization_id", "evidence_file_id"])

    op.create_table(
        "document_text_chunks",
        uuid_pk(),
        org_id(),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_records.id"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("heading", sa.String(length=255), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        created_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_text_chunks_organization_id_document_id",
        "document_text_chunks",
        ["organization_id", "document_id", "chunk_index"],
    )

    op.create_table(
        "document_extracted_fields",
        uuid_pk(),
        org_id(),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_records.id"), nullable=False),
        sa.Column("field_name", sa.String(length=128), nullable=False),
        sa.Column("field_value", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("review_status", sa.String(length=32), nullable=False, server_default="pending"),
        created_at(),
        updated_at(),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_extracted_fields_organization_id_document_id",
        "document_extracted_fields",
        ["organization_id", "document_id"],
    )
    op.create_index(
        "ix_document_extracted_fields_organization_id_review_status",
        "document_extracted_fields",
        ["organization_id", "review_status"],
    )

    op.create_table(
        "document_link_suggestions",
        uuid_pk(),
        org_id(),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("document_records.id"), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_label", sa.String(length=255), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("review_status", sa.String(length=32), nullable=False, server_default="pending"),
        created_at(),
        updated_at(),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_link_suggestions_organization_id_document_id",
        "document_link_suggestions",
        ["organization_id", "document_id"],
    )
    op.create_index(
        "ix_document_link_suggestions_organization_id_review_status",
        "document_link_suggestions",
        ["organization_id", "review_status"],
    )
    op.create_index(
        "ix_document_link_suggestions_organization_id_target",
        "document_link_suggestions",
        ["organization_id", "target_type", "target_id"],
    )


def downgrade() -> None:
    op.drop_table("document_link_suggestions")
    op.drop_table("document_extracted_fields")
    op.drop_table("document_text_chunks")
    op.drop_table("document_records")
    op.drop_table("knowledge_items")
    op.drop_table("record_notes")
    op.drop_table("record_links")
