from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.mixins import ArchivedMixin, OrganizationOwnedMixin, UUIDPrimaryKeyMixin


class EmailImportBatch(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "email_import_batches"
    __table_args__ = (
        Index("ix_email_import_batches_organization_id_created_at", "organization_id", "created_at"),
    )

    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    import_mode: Mapped[str] = mapped_column(String(64), nullable=False)
    folder_id: Mapped[str | None] = mapped_column(String(255))
    search_query: Mapped[str | None] = mapped_column(Text)
    date_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    date_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="previewed")
    preview_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    imported_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    result_summary_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    email_messages: Mapped[list["EmailMessage"]] = relationship(back_populates="import_batch")
