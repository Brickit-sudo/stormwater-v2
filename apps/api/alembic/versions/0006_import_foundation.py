"""add import readiness foundation

Revision ID: 0006_import_foundation
Revises: 0005_ai_draft_provider_metadata
Create Date: 2026-05-13 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006_import_foundation"
down_revision: str | None = "0005_ai_draft_provider_metadata"
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
        "external_record_ids",
        uuid_pk(),
        org_id(),
        sa.Column("source_system", sa.String(length=64), nullable=False),
        sa.Column("source_table", sa.String(length=128), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("legacy_label", sa.String(length=255), nullable=True),
        created_at(),
        updated_at(),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "source_system",
            "source_table",
            "source_id",
            name="uq_external_record_ids_organization_source_record",
        ),
    )
    op.create_index(
        "ix_external_record_ids_organization_id_entity",
        "external_record_ids",
        ["organization_id", "entity_type", "entity_id"],
    )

    op.create_table(
        "client_aliases",
        uuid_pk(),
        org_id(),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=True),
        sa.Column("alias_value", sa.String(length=255), nullable=False),
        sa.Column("alias_type", sa.String(length=64), nullable=False),
        sa.Column("source_system", sa.String(length=64), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        created_at(),
        updated_at(),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "alias_value",
            "alias_type",
            name="uq_client_aliases_organization_alias_type",
        ),
    )
    op.create_index(
        "ix_client_aliases_organization_id_client_id",
        "client_aliases",
        ["organization_id", "client_id"],
    )
    op.create_index(
        "ix_client_aliases_organization_id_source_system",
        "client_aliases",
        ["organization_id", "source_system"],
    )

    op.create_table(
        "site_aliases",
        uuid_pk(),
        org_id(),
        sa.Column("site_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sites.id"), nullable=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id"), nullable=True),
        sa.Column("alias_value", sa.String(length=255), nullable=False),
        sa.Column("alias_type", sa.String(length=64), nullable=False),
        sa.Column("source_system", sa.String(length=64), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        created_at(),
        updated_at(),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "alias_value",
            "alias_type",
            name="uq_site_aliases_organization_alias_type",
        ),
    )
    op.create_index(
        "ix_site_aliases_organization_id_site_id",
        "site_aliases",
        ["organization_id", "site_id"],
    )
    op.create_index(
        "ix_site_aliases_organization_id_client_id",
        "site_aliases",
        ["organization_id", "client_id"],
    )
    op.create_index(
        "ix_site_aliases_organization_id_source_system",
        "site_aliases",
        ["organization_id", "source_system"],
    )

    op.create_table(
        "service_catalog",
        uuid_pk(),
        org_id(),
        sa.Column("service_code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_frequency", sa.String(length=64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        created_at(),
        updated_at(),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "service_code",
            name="uq_service_catalog_organization_service_code",
        ),
    )
    op.create_index(
        "ix_service_catalog_organization_id_category",
        "service_catalog",
        ["organization_id", "category"],
    )
    op.create_index(
        "ix_service_catalog_organization_id_is_active",
        "service_catalog",
        ["organization_id", "is_active"],
    )

    op.create_table(
        "file_categories",
        uuid_pk(),
        org_id(),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("allowed_parent_types_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        created_at(),
        updated_at(),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "code",
            name="uq_file_categories_organization_code",
        ),
    )
    op.create_index(
        "ix_file_categories_organization_id_is_active",
        "file_categories",
        ["organization_id", "is_active"],
    )

    op.create_table(
        "import_batches",
        uuid_pk(),
        org_id(),
        sa.Column("import_type", sa.String(length=64), nullable=False),
        sa.Column("source_file_name", sa.String(length=255), nullable=False),
        sa.Column("source_system", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("valid_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("invalid_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("duplicate_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("unmatched_rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        created_at(),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_import_batches_organization_id_created_at",
        "import_batches",
        ["organization_id", "created_at"],
    )
    op.create_index(
        "ix_import_batches_organization_id_import_type",
        "import_batches",
        ["organization_id", "import_type"],
    )
    op.create_index(
        "ix_import_batches_organization_id_status",
        "import_batches",
        ["organization_id", "status"],
    )

    op.create_table(
        "import_rows",
        uuid_pk(),
        org_id(),
        sa.Column(
            "import_batch_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("import_batches.id"),
            nullable=False,
        ),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("import_type", sa.String(length=64), nullable=False),
        sa.Column("raw_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("normalized_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("validation_errors_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("duplicate_key", sa.String(length=255), nullable=True),
        sa.Column("matched_entity_type", sa.String(length=64), nullable=True),
        sa.Column("matched_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        created_at(),
        updated_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_import_rows_organization_id_import_batch_id",
        "import_rows",
        ["organization_id", "import_batch_id"],
    )
    op.create_index(
        "ix_import_rows_organization_id_status",
        "import_rows",
        ["organization_id", "status"],
    )
    op.create_index(
        "ix_import_rows_organization_id_duplicate_key",
        "import_rows",
        ["organization_id", "duplicate_key"],
    )
    op.create_index(
        "ix_import_rows_organization_id_matched_entity",
        "import_rows",
        ["organization_id", "matched_entity_type", "matched_entity_id"],
    )


def downgrade() -> None:
    op.drop_table("import_rows")
    op.drop_table("import_batches")
    op.drop_table("file_categories")
    op.drop_table("service_catalog")
    op.drop_table("site_aliases")
    op.drop_table("client_aliases")
    op.drop_table("external_record_ids")
