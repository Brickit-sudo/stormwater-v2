from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AiDraftBase(BaseModel):
    client_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    email_message_id: uuid.UUID | None = None
    draft_type: str = Field(default="email_reply", min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    prompt_context: str | None = None
    draft_text: str = Field(min_length=1)
    status: str = Field(default="draft", min_length=1, max_length=32)


class AiDraftCreate(AiDraftBase):
    organization_id: uuid.UUID


class AiDraftUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    email_message_id: uuid.UUID | None = None
    draft_type: str | None = Field(default=None, min_length=1, max_length=64)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    prompt_context: str | None = None
    draft_text: str | None = Field(default=None, min_length=1)
    status: str | None = Field(default=None, min_length=1, max_length=32)


class AiDraftRead(AiDraftBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    provider: str | None = None
    provider_draft_id: str | None = None
    provider_web_link: str | None = None
    provider_status: str | None = None
    pushed_to_provider_at: datetime | None = None
    provider_error: str | None = None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class AiDraftListResponse(BaseModel):
    items: list[AiDraftRead]
    total: int
    limit: int
    offset: int
