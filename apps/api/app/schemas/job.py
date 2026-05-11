from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class JobBase(BaseModel):
    job_code: str | None = Field(default=None, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    service_type: str | None = Field(default=None, max_length=128)
    status: str = Field(default="draft", min_length=1, max_length=32)
    assigned_to: uuid.UUID | None = None
    scheduled_date: date | None = None
    due_date: date | None = None
    completed_date: date | None = None
    scope: str | None = None
    notes: str | None = None
    drive_folder_url: str | None = None


class JobCreate(JobBase):
    organization_id: uuid.UUID
    client_id: uuid.UUID
    site_id: uuid.UUID


class JobUpdate(BaseModel):
    client_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    job_code: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    service_type: str | None = Field(default=None, max_length=128)
    status: str | None = Field(default=None, min_length=1, max_length=32)
    assigned_to: uuid.UUID | None = None
    scheduled_date: date | None = None
    due_date: date | None = None
    completed_date: date | None = None
    scope: str | None = None
    notes: str | None = None
    drive_folder_url: str | None = None


class JobRead(JobBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    client_id: uuid.UUID
    site_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class JobListResponse(BaseModel):
    items: list[JobRead]
    total: int
    limit: int
    offset: int
