from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import (
    ArchivedMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class EmailMessage(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "email_messages"
    __table_args__ = (
        Index("ix_email_messages_organization_id_received_at", "organization_id", "received_at"),
        Index("ix_email_messages_organization_id_status", "organization_id", "status"),
        Index(
            "ix_email_messages_organization_id_provider_message_id",
            "organization_id",
            "provider_message_id",
        ),
        Index("ix_email_messages_organization_id_client_id", "organization_id", "client_id"),
        Index("ix_email_messages_organization_id_site_id", "organization_id", "site_id"),
        Index("ix_email_messages_organization_id_job_id", "organization_id", "job_id"),
    )

    import_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("email_import_batches.id"),
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
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(255))
    provider_conversation_id: Mapped[str | None] = mapped_column(String(255))
    internet_message_id: Mapped[str | None] = mapped_column(String(512))
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    sender: Mapped[str] = mapped_column(String(320), nullable=False)
    recipients_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    snippet: Mapped[str | None] = mapped_column(Text)
    body_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    body_html: Mapped[str | None] = mapped_column(Text)
    attachments_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    links_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    web_link: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="unlinked")

    import_batch: Mapped["EmailImportBatch | None"] = relationship(back_populates="email_messages")
    record_links: Mapped[list["EmailRecordLink"]] = relationship(
        back_populates="email_message",
        cascade="all, delete-orphan",
    )
    ai_drafts: Mapped[list["AiDraft"]] = relationship(back_populates="email_message")
