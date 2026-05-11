from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import (
    ArchivedMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class EvidenceFile(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "evidence_files"
    __table_args__ = (
        Index("ix_evidence_files_organization_id_job_id", "organization_id", "job_id"),
        Index("ix_evidence_files_organization_id_site_id", "organization_id", "site_id"),
        Index("ix_evidence_files_organization_id_drive_file_id", "organization_id", "drive_file_id"),
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
    observation_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("observations.id"),
    )
    system_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("bmp_systems.id"),
    )
    source: Mapped[str | None] = mapped_column(String(64))
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    drive_file_id: Mapped[str | None] = mapped_column(String(255))
    drive_folder_id: Mapped[str | None] = mapped_column(String(255))
    storage_bucket: Mapped[str | None] = mapped_column(String(128))
    storage_path: Mapped[str | None] = mapped_column(Text)
    public_url: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    caption: Mapped[str | None] = mapped_column(Text)
    legacy_source: Mapped[str | None] = mapped_column(String(64))
    legacy_id: Mapped[str | None] = mapped_column(String(128))

    organization: Mapped["Organization"] = relationship(back_populates="evidence_files")
    client: Mapped["Client | None"] = relationship(back_populates="evidence_files")
    site: Mapped["Site | None"] = relationship(back_populates="evidence_files")
    job: Mapped["Job | None"] = relationship(back_populates="evidence_files")
    observation: Mapped["Observation | None"] = relationship(back_populates="evidence_files")
    system: Mapped["BmpSystem | None"] = relationship(back_populates="evidence_files")
