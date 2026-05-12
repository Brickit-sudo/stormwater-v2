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


class Reminder(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "reminders"
    __table_args__ = (
        Index("ix_reminders_organization_id_due_at", "organization_id", "due_at"),
        Index("ix_reminders_organization_id_status", "organization_id", "status"),
        Index("ix_reminders_organization_id_priority", "organization_id", "priority"),
        Index("ix_reminders_organization_id_job_id", "organization_id", "job_id"),
        Index("ix_reminders_organization_id_site_id", "organization_id", "site_id"),
        Index("ix_reminders_organization_id_client_id", "organization_id", "client_id"),
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
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id"),
    )
    source_type: Mapped[str | None] = mapped_column(String(64))
    source_id: Mapped[str | None] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reminder_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    organization: Mapped["Organization"] = relationship(back_populates="reminders")
    client: Mapped["Client | None"] = relationship(back_populates="reminders")
    site: Mapped["Site | None"] = relationship(back_populates="reminders")
    job: Mapped["Job | None"] = relationship(back_populates="reminders")
    assignee: Mapped["User | None"] = relationship(back_populates="assigned_reminders")
