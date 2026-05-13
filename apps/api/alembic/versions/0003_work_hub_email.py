"""add work hub email foundation

Revision ID: 0003_work_hub_email
Revises: 0002_reminders
Create Date: 2026-05-12 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_work_hub_email"
down_revision: str | None = "0002_reminders"
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


def nullable_uuid_fk(name: str, table: str) -> sa.Column:
    return sa.Column(
        name,
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey(f"{table}.id"),
        nullable=True,
    )


def upgrade() -> None:
    op.create_table(
        "email_import_batches",
        uuid_pk(),
        org_id(),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("import_mode", sa.String(length=64), nullable=False),
        sa.Column("folder_id", sa.String(length=255), nullable=True),
        sa.Column("search_query", sa.Text(), nullable=True),
        sa.Column("date_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("date_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("preview_count", sa.Integer(), nullable=False),
        sa.Column("imported_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("request_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result_summary_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        created_at(),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_email_import_batches_organization_id_created_at",
        "email_import_batches",
        ["organization_id", "created_at"],
    )

    op.create_table(
        "email_messages",
        uuid_pk(),
        org_id(),
        nullable_uuid_fk("import_batch_id", "email_import_batches"),
        nullable_uuid_fk("client_id", "clients"),
        nullable_uuid_fk("site_id", "sites"),
        nullable_uuid_fk("job_id", "jobs"),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True),
        sa.Column("provider_conversation_id", sa.String(length=255), nullable=True),
        sa.Column("internet_message_id", sa.String(length=512), nullable=True),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("sender", sa.String(length=320), nullable=False),
        sa.Column("recipients_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("attachments_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("links_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("web_link", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        created_at(),
        updated_at(),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_email_messages_organization_id_received_at",
        "email_messages",
        ["organization_id", "received_at"],
    )
    op.create_index("ix_email_messages_organization_id_status", "email_messages", ["organization_id", "status"])
    op.create_index(
        "ix_email_messages_organization_id_provider_message_id",
        "email_messages",
        ["organization_id", "provider_message_id"],
    )
    op.create_index("ix_email_messages_organization_id_client_id", "email_messages", ["organization_id", "client_id"])
    op.create_index("ix_email_messages_organization_id_site_id", "email_messages", ["organization_id", "site_id"])
    op.create_index("ix_email_messages_organization_id_job_id", "email_messages", ["organization_id", "job_id"])

    op.create_table(
        "email_record_links",
        uuid_pk(),
        org_id(),
        sa.Column(
            "email_message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("email_messages.id"),
            nullable=False,
        ),
        nullable_uuid_fk("client_id", "clients"),
        nullable_uuid_fk("site_id", "sites"),
        nullable_uuid_fk("job_id", "jobs"),
        sa.Column("link_reason", sa.String(length=255), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        created_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_email_record_links_organization_id_email_message_id",
        "email_record_links",
        ["organization_id", "email_message_id"],
    )

    op.create_table(
        "ai_drafts",
        uuid_pk(),
        org_id(),
        nullable_uuid_fk("client_id", "clients"),
        nullable_uuid_fk("site_id", "sites"),
        nullable_uuid_fk("job_id", "jobs"),
        nullable_uuid_fk("email_message_id", "email_messages"),
        sa.Column("draft_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("prompt_context", sa.Text(), nullable=True),
        sa.Column("draft_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        created_at(),
        updated_at(),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_drafts_organization_id_status", "ai_drafts", ["organization_id", "status"])
    op.create_index("ix_ai_drafts_organization_id_draft_type", "ai_drafts", ["organization_id", "draft_type"])


def downgrade() -> None:
    op.drop_table("ai_drafts")
    op.drop_table("email_record_links")
    op.drop_table("email_messages")
    op.drop_table("email_import_batches")
