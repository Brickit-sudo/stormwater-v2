from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReminderBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: str = Field(default="open", min_length=1, max_length=32)
    priority: str = Field(default="medium", min_length=1, max_length=32)
    due_at: datetime | None = None
    reminder_at: datetime | None = None
    completed_at: datetime | None = None
    assigned_to: uuid.UUID | None = None
    source_type: str | None = Field(default=None, max_length=64)
    source_id: str | None = Field(default=None, max_length=128)


class ReminderCreate(ReminderBase):
    organization_id: uuid.UUID
    client_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None


class ReminderUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    assigned_to: uuid.UUID | None = None
    source_type: str | None = Field(default=None, max_length=64)
    source_id: str | None = Field(default=None, max_length=128)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: str | None = Field(default=None, min_length=1, max_length=32)
    priority: str | None = Field(default=None, min_length=1, max_length=32)
    due_at: datetime | None = None
    reminder_at: datetime | None = None
    completed_at: datetime | None = None


class ReminderRead(ReminderBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    client_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class ReminderListResponse(BaseModel):
    items: list[ReminderRead]
    total: int
    limit: int
    offset: int
