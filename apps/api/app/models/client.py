from __future__ import annotations

from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import (
    ArchivedMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Client(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "clients"
    __table_args__ = (
        Index("ix_clients_organization_id_name", "organization_id", "name"),
        Index("ix_clients_organization_id_status", "organization_id", "status"),
        Index("ix_clients_organization_id_legacy_id", "organization_id", "legacy_id"),
    )

    client_code: Mapped[str | None] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    primary_contact_name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(64))
    billing_address: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    drive_folder_id: Mapped[str | None] = mapped_column(String(255))
    drive_folder_url: Mapped[str | None] = mapped_column(Text)
    legacy_source: Mapped[str | None] = mapped_column(String(64))
    legacy_id: Mapped[str | None] = mapped_column(String(128))

    organization: Mapped["Organization"] = relationship(back_populates="clients")
    contacts: Mapped[list["Contact"]] = relationship(back_populates="client")
    sites: Mapped[list["Site"]] = relationship(back_populates="client")
    jobs: Mapped[list["Job"]] = relationship(back_populates="client")
    evidence_files: Mapped[list["EvidenceFile"]] = relationship(back_populates="client")
    reminders: Mapped[list["Reminder"]] = relationship(back_populates="client")
    aliases: Mapped[list["ClientAlias"]] = relationship(back_populates="client")
    site_aliases: Mapped[list["SiteAlias"]] = relationship(back_populates="client")
