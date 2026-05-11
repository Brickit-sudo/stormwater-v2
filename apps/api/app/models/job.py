from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import (
    ArchivedMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Job(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_organization_id_client_id", "organization_id", "client_id"),
        Index("ix_jobs_organization_id_site_id", "organization_id", "site_id"),
        Index("ix_jobs_organization_id_status", "organization_id", "status"),
        Index("ix_jobs_organization_id_due_date", "organization_id", "due_date"),
        Index("ix_jobs_organization_id_scheduled_date", "organization_id", "scheduled_date"),
        Index("ix_jobs_organization_id_legacy_id", "organization_id", "legacy_id"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("clients.id"),
        nullable=False,
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sites.id"),
        nullable=False,
    )
    job_code: Mapped[str | None] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    service_type: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id"),
    )
    scheduled_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    completed_date: Mapped[date | None] = mapped_column(Date)
    scope: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    drive_folder_id: Mapped[str | None] = mapped_column(String(255))
    drive_folder_url: Mapped[str | None] = mapped_column(Text)
    legacy_source: Mapped[str | None] = mapped_column(String(64))
    legacy_id: Mapped[str | None] = mapped_column(String(128))

    organization: Mapped["Organization"] = relationship(back_populates="jobs")
    client: Mapped["Client"] = relationship(back_populates="jobs")
    site: Mapped["Site"] = relationship(back_populates="jobs")
    assignee: Mapped["User | None"] = relationship(back_populates="assigned_jobs")
    observations: Mapped[list["Observation"]] = relationship(back_populates="job")
    evidence_files: Mapped[list["EvidenceFile"]] = relationship(back_populates="job")
    reports: Mapped[list["Report"]] = relationship(back_populates="job")
