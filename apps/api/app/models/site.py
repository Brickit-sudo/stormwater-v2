from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import (
    ArchivedMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Site(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "sites"
    __table_args__ = (
        Index("ix_sites_organization_id_client_id", "organization_id", "client_id"),
        Index("ix_sites_organization_id_name", "organization_id", "name"),
        Index("ix_sites_organization_id_city", "organization_id", "city"),
        Index("ix_sites_organization_id_state", "organization_id", "state"),
        Index("ix_sites_organization_id_status", "organization_id", "status"),
        Index("ix_sites_organization_id_legacy_id", "organization_id", "legacy_id"),
    )

    client_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("clients.id"),
        nullable=False,
    )
    site_code: Mapped[str | None] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(String(128))
    state: Mapped[str | None] = mapped_column(String(64))
    zip: Mapped[str | None] = mapped_column(String(20))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    notes: Mapped[str | None] = mapped_column(Text)
    drive_folder_id: Mapped[str | None] = mapped_column(String(255))
    drive_folder_url: Mapped[str | None] = mapped_column(Text)
    legacy_source: Mapped[str | None] = mapped_column(String(64))
    legacy_id: Mapped[str | None] = mapped_column(String(128))

    organization: Mapped["Organization"] = relationship(back_populates="sites")
    client: Mapped["Client"] = relationship(back_populates="sites")
    contacts: Mapped[list["Contact"]] = relationship(back_populates="site")
    jobs: Mapped[list["Job"]] = relationship(back_populates="site")
    bmp_systems: Mapped[list["BmpSystem"]] = relationship(back_populates="site")
    evidence_files: Mapped[list["EvidenceFile"]] = relationship(back_populates="site")
    reports: Mapped[list["Report"]] = relationship(back_populates="site")
