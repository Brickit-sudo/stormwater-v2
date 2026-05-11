from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import (
    ArchivedMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class BmpSystem(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "bmp_systems"
    __table_args__ = (
        Index("ix_bmp_systems_organization_id_site_id", "organization_id", "site_id"),
        Index("ix_bmp_systems_organization_id_system_type", "organization_id", "system_type"),
    )

    site_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sites.id"),
        nullable=False,
    )
    system_code: Mapped[str | None] = mapped_column(String(64))
    system_type: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    location_description: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    legacy_source: Mapped[str | None] = mapped_column(String(64))
    legacy_id: Mapped[str | None] = mapped_column(String(128))

    organization: Mapped["Organization"] = relationship(back_populates="bmp_systems")
    site: Mapped["Site"] = relationship(back_populates="bmp_systems")
    observations: Mapped[list["Observation"]] = relationship(back_populates="system")
    evidence_files: Mapped[list["EvidenceFile"]] = relationship(back_populates="system")
