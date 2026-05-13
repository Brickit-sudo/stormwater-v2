from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import OrganizationOwnedMixin, UUIDPrimaryKeyMixin


class EmailRecordLink(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    Base,
):
    __tablename__ = "email_record_links"
    __table_args__ = (
        Index(
            "ix_email_record_links_organization_id_email_message_id",
            "organization_id",
            "email_message_id",
        ),
    )

    email_message_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("email_messages.id"),
        nullable=False,
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
    link_reason: Mapped[str] = mapped_column(String(255), nullable=False, default="manual")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    email_message: Mapped["EmailMessage"] = relationship(back_populates="record_links")
