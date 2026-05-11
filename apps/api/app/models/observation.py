from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import (
    ArchivedMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Observation(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "observations"
    __table_args__ = (
        Index("ix_observations_organization_id_job_id", "organization_id", "job_id"),
        Index("ix_observations_organization_id_system_id", "organization_id", "system_id"),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobs.id"),
        nullable=False,
    )
    system_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bmp_systems.id"),
    )
    observation_type: Mapped[str | None] = mapped_column(String(128))
    finding: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str | None] = mapped_column(String(64))
    maintenance_needed: Mapped[bool | None] = mapped_column(Boolean)
    notes: Mapped[str | None] = mapped_column(Text)

    organization: Mapped["Organization"] = relationship(back_populates="observations")
    job: Mapped["Job"] = relationship(back_populates="observations")
    system: Mapped["BmpSystem | None"] = relationship(back_populates="observations")
    evidence_files: Mapped[list["EvidenceFile"]] = relationship(back_populates="observation")
