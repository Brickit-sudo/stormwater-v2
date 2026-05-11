from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import (
    ArchivedMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Report(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "reports"
    __table_args__ = (
        Index("ix_reports_organization_id_job_id", "organization_id", "job_id"),
        Index("ix_reports_organization_id_site_id", "organization_id", "site_id"),
        Index("ix_reports_organization_id_status", "organization_id", "status"),
    )

    job_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("jobs.id"),
    )
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("sites.id"),
    )
    report_type: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    snapshot_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    template_version: Mapped[str | None] = mapped_column(String(64))
    generated_docx_file_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("evidence_files.id"),
    )
    generated_pdf_file_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("evidence_files.id"),
    )
    legacy_source: Mapped[str | None] = mapped_column(String(64))
    legacy_id: Mapped[str | None] = mapped_column(String(128))

    organization: Mapped["Organization"] = relationship(back_populates="reports")
    job: Mapped["Job | None"] = relationship(back_populates="reports")
    site: Mapped["Site | None"] = relationship(back_populates="reports")
    generated_docx_file: Mapped["EvidenceFile | None"] = relationship(
        foreign_keys=[generated_docx_file_id],
    )
    generated_pdf_file: Mapped["EvidenceFile | None"] = relationship(
        foreign_keys=[generated_pdf_file_id],
    )
