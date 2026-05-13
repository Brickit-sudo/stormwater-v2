"""add product roadmap tracker

Revision ID: 0007_product_roadmap
Revises: 0006_import_foundation
Create Date: 2026-05-13 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0007_product_roadmap"
down_revision: str | None = "0006_import_foundation"
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
        "product_ideas",
        uuid_pk(),
        org_id(),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=False, server_default="UX"),
        sa.Column("lane", sa.String(length=64), nullable=False, server_default="V2"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="new"),
        sa.Column("priority", sa.String(length=32), nullable=False, server_default="medium"),
        sa.Column("source", sa.String(length=128), nullable=True),
        sa.Column("owner", sa.String(length=128), nullable=True),
        sa.Column("target_version", sa.String(length=64), nullable=True),
        sa.Column("effort", sa.String(length=64), nullable=True),
        sa.Column("risk", sa.String(length=64), nullable=True),
        sa.Column("boss_demo_relevant", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        created_at(),
        updated_at(),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_product_ideas_organization_id_status",
        "product_ideas",
        ["organization_id", "status"],
    )
    op.create_index(
        "ix_product_ideas_organization_id_category",
        "product_ideas",
        ["organization_id", "category"],
    )
    op.create_index(
        "ix_product_ideas_organization_id_lane",
        "product_ideas",
        ["organization_id", "lane"],
    )
    op.create_index(
        "ix_product_ideas_organization_id_priority",
        "product_ideas",
        ["organization_id", "priority"],
    )
    op.create_index(
        "ix_product_ideas_organization_id_boss_demo_relevant",
        "product_ideas",
        ["organization_id", "boss_demo_relevant"],
    )

    op.create_table(
        "product_decisions",
        uuid_pk(),
        org_id(),
        sa.Column(
            "related_idea_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("product_ideas.id"),
            nullable=True,
        ),
        sa.Column("decision_title", sa.String(length=255), nullable=False),
        sa.Column("decision_summary", sa.Text(), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("alternatives_considered", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="proposed"),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        created_at(),
        updated_at(),
        archived_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_product_decisions_organization_id_status",
        "product_decisions",
        ["organization_id", "status"],
    )
    op.create_index(
        "ix_product_decisions_organization_id_related_idea_id",
        "product_decisions",
        ["organization_id", "related_idea_id"],
    )


def downgrade() -> None:
    op.drop_table("product_decisions")
    op.drop_table("product_ideas")
