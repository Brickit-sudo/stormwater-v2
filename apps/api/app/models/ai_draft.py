from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import (
    ArchivedMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class AiDraft(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "ai_drafts"
    __table_args__ = (
        Index("ix_ai_drafts_organization_id_status", "organization_id", "status"),
        Index("ix_ai_drafts_organization_id_draft_type", "organization_id", "draft_type"),
    )

    client_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("clients.id"),
    )
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sites.id"),
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobs.id"),
    )
    email_message_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("email_messages.id"),
    )
    draft_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt_context: Mapped[str | None] = mapped_column(Text)
    draft_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    provider: Mapped[str | None] = mapped_column(String(64))
    provider_draft_id: Mapped[str | None] = mapped_column(String(255))
    provider_web_link: Mapped[str | None] = mapped_column(Text)
    provider_status: Mapped[str | None] = mapped_column(String(32))
    pushed_to_provider_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_error: Mapped[str | None] = mapped_column(Text)

    email_message: Mapped["EmailMessage | None"] = relationship(back_populates="ai_drafts")
