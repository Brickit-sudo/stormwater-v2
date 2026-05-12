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
