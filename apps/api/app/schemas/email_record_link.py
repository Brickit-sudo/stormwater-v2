from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EmailRecordLinkBase(BaseModel):
    email_message_id: uuid.UUID
    client_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    link_reason: str = Field(default="manual", min_length=1, max_length=255)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class EmailRecordLinkCreate(EmailRecordLinkBase):
    organization_id: uuid.UUID


class EmailRecordLinkRead(EmailRecordLinkBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime


class EmailRecordLinkListResponse(BaseModel):
    items: list[EmailRecordLinkRead]
    total: int
    limit: int
    offset: int
