from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import (
    ArchivedMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class ProductIdea(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "product_ideas"
    __table_args__ = (
        Index("ix_product_ideas_organization_id_status", "organization_id", "status"),
        Index("ix_product_ideas_organization_id_category", "organization_id", "category"),
        Index("ix_product_ideas_organization_id_lane", "organization_id", "lane"),
        Index("ix_product_ideas_organization_id_priority", "organization_id", "priority"),
        Index(
            "ix_product_ideas_organization_id_boss_demo_relevant",
            "organization_id",
            "boss_demo_relevant",
        ),
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="UX")
    lane: Mapped[str] = mapped_column(String(64), nullable=False, default="V2")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="new")
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    source: Mapped[str | None] = mapped_column(String(128))
    owner: Mapped[str | None] = mapped_column(String(128))
    target_version: Mapped[str | None] = mapped_column(String(64))
    effort: Mapped[str | None] = mapped_column(String(64))
    risk: Mapped[str | None] = mapped_column(String(64))
    boss_demo_relevant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    organization: Mapped["Organization"] = relationship(back_populates="product_ideas")
    decisions: Mapped[list["ProductDecision"]] = relationship(back_populates="related_idea")


class ProductDecision(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "product_decisions"
    __table_args__ = (
        Index("ix_product_decisions_organization_id_status", "organization_id", "status"),
        Index(
            "ix_product_decisions_organization_id_related_idea_id",
            "organization_id",
            "related_idea_id",
        ),
    )

    related_idea_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("product_ideas.id"),
    )
    decision_title: Mapped[str] = mapped_column(String(255), nullable=False)
    decision_summary: Mapped[str | None] = mapped_column(Text)
    decision_reason: Mapped[str | None] = mapped_column(Text)
    alternatives_considered: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="proposed")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    organization: Mapped["Organization"] = relationship(back_populates="product_decisions")
    related_idea: Mapped["ProductIdea | None"] = relationship(back_populates="decisions")
