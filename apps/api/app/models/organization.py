from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    memberships: Mapped[list["OrganizationMembership"]] = relationship(
        back_populates="organization",
    )
    clients: Mapped[list["Client"]] = relationship(back_populates="organization")
    contacts: Mapped[list["Contact"]] = relationship(back_populates="organization")
    sites: Mapped[list["Site"]] = relationship(back_populates="organization")
    jobs: Mapped[list["Job"]] = relationship(back_populates="organization")
    bmp_systems: Mapped[list["BmpSystem"]] = relationship(back_populates="organization")
    observations: Mapped[list["Observation"]] = relationship(back_populates="organization")
    evidence_files: Mapped[list["EvidenceFile"]] = relationship(back_populates="organization")
    reports: Mapped[list["Report"]] = relationship(back_populates="organization")
    activity_logs: Mapped[list["ActivityLog"]] = relationship(back_populates="organization")
    reminders: Mapped[list["Reminder"]] = relationship(back_populates="organization")
    email_import_batches: Mapped[list["EmailImportBatch"]] = relationship()
    email_messages: Mapped[list["EmailMessage"]] = relationship()
    email_record_links: Mapped[list["EmailRecordLink"]] = relationship()
    ai_drafts: Mapped[list["AiDraft"]] = relationship()
    external_record_ids: Mapped[list["ExternalRecordId"]] = relationship(back_populates="organization")
    client_aliases: Mapped[list["ClientAlias"]] = relationship(back_populates="organization")
    site_aliases: Mapped[list["SiteAlias"]] = relationship(back_populates="organization")
    service_catalog: Mapped[list["ServiceCatalog"]] = relationship(back_populates="organization")
    file_categories: Mapped[list["FileCategory"]] = relationship(back_populates="organization")
    import_batches: Mapped[list["ImportBatch"]] = relationship(back_populates="organization")
