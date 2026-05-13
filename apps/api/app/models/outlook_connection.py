from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.mixins import (
    ArchivedMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class OutlookConnection(
    UUIDPrimaryKeyMixin,
    OrganizationOwnedMixin,
    TimestampMixin,
    ArchivedMixin,
    Base,
):
    __tablename__ = "outlook_connections"
    __table_args__ = (
        Index("ix_outlook_connections_organization_id_status", "organization_id", "status"),
        Index("ix_outlook_connections_organization_id_email_address", "organization_id", "email_address"),
    )

    provider: Mapped[str] = mapped_column(String(64), nullable=False, default="outlook")
    email_address: Mapped[str | None] = mapped_column(String(320))
    display_name: Mapped[str | None] = mapped_column(String(255))
    tenant_id: Mapped[str | None] = mapped_column(String(255))
    scopes_json: Mapped[list[str] | None] = mapped_column(JSON)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="connected")
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
