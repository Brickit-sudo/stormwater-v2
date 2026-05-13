"""add outlook connections

Revision ID: 0004_outlook_connections
Revises: 0003_work_hub_email
Create Date: 2026-05-13 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_outlook_connections"
down_revision: str | None = "0003_work_hub_email"
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


def timestamp(name: str, *, nullable: bool = False) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=nullable)


def upgrade() -> None:
    op.create_table(
        "outlook_connections",
        uuid_pk(),
        org_id(),
        sa.Column("provider", sa.String(length=64), nullable=False, server_default="outlook"),
        sa.Column("email_address", sa.String(length=320), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("tenant_id", sa.String(length=255), nullable=True),
        sa.Column("scopes_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("access_token_encrypted", sa.Text(), nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text(), nullable=True),
        timestamp("expires_at", nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="connected"),
        timestamp("connected_at", nullable=False),
        timestamp("last_used_at", nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        timestamp("archived_at", nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_outlook_connections_organization_id_status",
        "outlook_connections",
        ["organization_id", "status"],
    )
    op.create_index(
        "ix_outlook_connections_organization_id_email_address",
        "outlook_connections",
        ["organization_id", "email_address"],
    )


def downgrade() -> None:
    op.drop_table("outlook_connections")
