from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EmailMessageBase(BaseModel):
    import_batch_id: uuid.UUID | None = None
    client_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    provider: str = Field(default="outlook", min_length=1, max_length=64)
    provider_message_id: str | None = Field(default=None, max_length=255)
    provider_conversation_id: str | None = Field(default=None, max_length=255)
    internet_message_id: str | None = Field(default=None, max_length=512)
    subject: str = Field(min_length=1, max_length=500)
    sender: str = Field(min_length=1, max_length=320)
    recipients_json: list[dict[str, Any]] = Field(default_factory=list)
    received_at: datetime | None = None
    snippet: str | None = None
    body_text: str = ""
    body_html: str | None = None
    attachments_json: list[dict[str, Any]] = Field(default_factory=list)
    links_json: list[dict[str, Any]] = Field(default_factory=list)
    web_link: str | None = None
    status: str = Field(default="unlinked", min_length=1, max_length=32)


class EmailMessageCreate(EmailMessageBase):
    organization_id: uuid.UUID


class EmailMessageUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    import_batch_id: uuid.UUID | None = None
    client_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    provider: str | None = Field(default=None, min_length=1, max_length=64)
    provider_message_id: str | None = Field(default=None, max_length=255)
    provider_conversation_id: str | None = Field(default=None, max_length=255)
    internet_message_id: str | None = Field(default=None, max_length=512)
    subject: str | None = Field(default=None, min_length=1, max_length=500)
    sender: str | None = Field(default=None, min_length=1, max_length=320)
    recipients_json: list[dict[str, Any]] | None = None
    received_at: datetime | None = None
    snippet: str | None = None
    body_text: str | None = None
    body_html: str | None = None
    attachments_json: list[dict[str, Any]] | None = None
    links_json: list[dict[str, Any]] | None = None
    web_link: str | None = None
    status: str | None = Field(default=None, min_length=1, max_length=32)


class EmailMessageRead(EmailMessageBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class EmailMessageListResponse(BaseModel):
    items: list[EmailMessageRead]
    total: int
    limit: int
    offset: int
