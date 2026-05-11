"""create v2 core crm schema

Revision ID: 0001_v2_core_schema
Revises:
Create Date: 2026-05-11 15:10:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_v2_core_schema"
down_revision: str | None = None
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


def legacy_columns() -> list[sa.Column]:
    return [
        sa.Column("legacy_source", sa.String(length=64), nullable=True),
        sa.Column("legacy_id", sa.String(length=128), nullable=True),
    ]


def drive_folder_columns() -> list[sa.Column]:
    return [
        sa.Column("drive_folder_id", sa.String(length=255), nullable=True),
        sa.Column("drive_folder_url", sa.Text(), nullable=True),
    ]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "organizations",
        uuid_pk(),
        sa.Column("name", sa.String(length=255), nullable=False),
        created_at(),
        updated_at(),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "users",
        uuid_pk(),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        created_at(),
        updated_at(),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "organization_memberships",
        uuid_pk(),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=64), nullable=False),
        created_at(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "user_id",
            name="uq_organization_memberships_organization_id_user_id",
        ),
    )

    op.create_table(
        "clients",
        uuid_pk(),
        org_id(),
        sa.Column("client_code", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("primary_contact_name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("billing_address", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *drive_folder_columns(),
        *legacy_columns(),
        created_at(),
        updated_at(),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clients_organization_id_name", "clients", ["organization_id", "name"])
    op.create_index("ix_clients_organization_id_status", "clients", ["organization_id", "status"])
    op.create_index("ix_clients_organization_id_legacy_id", "clients", ["organization_id", "legacy_id"])

    op.create_table(
        "sites",
        uuid_pk(),
        org_id(),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id"),
            nullable=False,
        ),
        sa.Column("site_code", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("state", sa.String(length=64), nullable=True),
        sa.Column("zip", sa.String(length=20), nullable=True),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        *drive_folder_columns(),
        *legacy_columns(),
        created_at(),
        updated_at(),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sites_organization_id_client_id", "sites", ["organization_id", "client_id"])
    op.create_index("ix_sites_organization_id_name", "sites", ["organization_id", "name"])
    op.create_index("ix_sites_organization_id_city", "sites", ["organization_id", "city"])
    op.create_index("ix_sites_organization_id_state", "sites", ["organization_id", "state"])
    op.create_index("ix_sites_organization_id_status", "sites", ["organization_id", "status"])
    op.create_index("ix_sites_organization_id_legacy_id", "sites", ["organization_id", "legacy_id"])

    op.create_table(
        "contacts",
        uuid_pk(),
        org_id(),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id"),
            nullable=True,
        ),
        sa.Column(
            "site_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sites.id"),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("role", sa.String(length=128), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *legacy_columns(),
        created_at(),
        updated_at(),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "jobs",
        uuid_pk(),
        org_id(),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id"),
            nullable=False,
        ),
        sa.Column(
            "site_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sites.id"),
            nullable=False,
        ),
        sa.Column("job_code", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("service_type", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "assigned_to",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("scheduled_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("completed_date", sa.Date(), nullable=True),
        sa.Column("scope", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *drive_folder_columns(),
        *legacy_columns(),
        created_at(),
        updated_at(),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jobs_organization_id_client_id", "jobs", ["organization_id", "client_id"])
    op.create_index("ix_jobs_organization_id_site_id", "jobs", ["organization_id", "site_id"])
    op.create_index("ix_jobs_organization_id_status", "jobs", ["organization_id", "status"])
    op.create_index("ix_jobs_organization_id_due_date", "jobs", ["organization_id", "due_date"])
    op.create_index("ix_jobs_organization_id_scheduled_date", "jobs", ["organization_id", "scheduled_date"])
    op.create_index("ix_jobs_organization_id_legacy_id", "jobs", ["organization_id", "legacy_id"])

    op.create_table(
        "bmp_systems",
        uuid_pk(),
        org_id(),
        sa.Column(
            "site_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sites.id"),
            nullable=False,
        ),
        sa.Column("system_code", sa.String(length=64), nullable=True),
        sa.Column("system_type", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("location_description", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *legacy_columns(),
        created_at(),
        updated_at(),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bmp_systems_organization_id_site_id", "bmp_systems", ["organization_id", "site_id"])
    op.create_index(
        "ix_bmp_systems_organization_id_system_type",
        "bmp_systems",
        ["organization_id", "system_type"],
    )

    op.create_table(
        "observations",
        uuid_pk(),
        org_id(),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id"),
            nullable=False,
        ),
        sa.Column(
            "system_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bmp_systems.id"),
            nullable=True,
        ),
        sa.Column("observation_type", sa.String(length=128), nullable=True),
        sa.Column("finding", sa.Text(), nullable=True),
        sa.Column("recommendation", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(length=64), nullable=True),
        sa.Column("maintenance_needed", sa.Boolean(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        created_at(),
        updated_at(),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_observations_organization_id_job_id", "observations", ["organization_id", "job_id"])
    op.create_index(
        "ix_observations_organization_id_system_id",
        "observations",
        ["organization_id", "system_id"],
    )

    op.create_table(
        "evidence_files",
        uuid_pk(),
        org_id(),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("clients.id"),
            nullable=True,
        ),
        sa.Column(
            "site_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sites.id"),
            nullable=True,
        ),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id"),
            nullable=True,
        ),
        sa.Column(
            "observation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("observations.id"),
            nullable=True,
        ),
        sa.Column(
            "system_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bmp_systems.id"),
            nullable=True,
        ),
        sa.Column("source", sa.String(length=64), nullable=True),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("drive_file_id", sa.String(length=255), nullable=True),
        sa.Column("drive_folder_id", sa.String(length=255), nullable=True),
        sa.Column("storage_bucket", sa.String(length=128), nullable=True),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("public_url", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("caption", sa.Text(), nullable=True),
        *legacy_columns(),
        created_at(),
        updated_at(),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidence_files_organization_id_job_id", "evidence_files", ["organization_id", "job_id"])
    op.create_index("ix_evidence_files_organization_id_site_id", "evidence_files", ["organization_id", "site_id"])
    op.create_index(
        "ix_evidence_files_organization_id_drive_file_id",
        "evidence_files",
        ["organization_id", "drive_file_id"],
    )

    op.create_table(
        "reports",
        uuid_pk(),
        org_id(),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id"),
            nullable=True,
        ),
        sa.Column(
            "site_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sites.id"),
            nullable=True,
        ),
        sa.Column("report_type", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("template_version", sa.String(length=64), nullable=True),
        sa.Column(
            "generated_docx_file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evidence_files.id"),
            nullable=True,
        ),
        sa.Column(
            "generated_pdf_file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evidence_files.id"),
            nullable=True,
        ),
        *legacy_columns(),
        created_at(),
        updated_at(),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_organization_id_job_id", "reports", ["organization_id", "job_id"])
    op.create_index("ix_reports_organization_id_site_id", "reports", ["organization_id", "site_id"])
    op.create_index("ix_reports_organization_id_status", "reports", ["organization_id", "status"])

    op.create_table(
        "activity_log",
        uuid_pk(),
        org_id(),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("entity_type", sa.String(length=128), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        created_at(),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("activity_log")
    op.drop_table("reports")
    op.drop_table("evidence_files")
    op.drop_table("observations")
    op.drop_table("bmp_systems")
    op.drop_table("jobs")
    op.drop_table("contacts")
    op.drop_table("sites")
    op.drop_table("clients")
    op.drop_table("organization_memberships")
    op.drop_table("users")
    op.drop_table("organizations")
