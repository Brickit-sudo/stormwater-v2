"""add ai draft provider metadata

Revision ID: 0005_ai_draft_provider_metadata
Revises: 0004_outlook_connections
Create Date: 2026-05-13 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0005_ai_draft_provider_metadata"
down_revision: str | None = "0004_outlook_connections"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ai_drafts", sa.Column("provider", sa.String(length=64), nullable=True))
    op.add_column("ai_drafts", sa.Column("provider_draft_id", sa.String(length=255), nullable=True))
    op.add_column("ai_drafts", sa.Column("provider_web_link", sa.Text(), nullable=True))
    op.add_column("ai_drafts", sa.Column("provider_status", sa.String(length=32), nullable=True))
    op.add_column("ai_drafts", sa.Column("pushed_to_provider_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ai_drafts", sa.Column("provider_error", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_drafts", "provider_error")
    op.drop_column("ai_drafts", "pushed_to_provider_at")
    op.drop_column("ai_drafts", "provider_status")
    op.drop_column("ai_drafts", "provider_web_link")
    op.drop_column("ai_drafts", "provider_draft_id")
    op.drop_column("ai_drafts", "provider")
