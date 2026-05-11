from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EvidenceFileBase(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    source: str | None = Field(default="drive_link", max_length=64)
    public_url: str | None = None
    drive_file_id: str | None = Field(default=None, max_length=255)
    mime_type: str | None = Field(default=None, max_length=128)
    size_bytes: int | None = Field(default=None, ge=0)
    caption: str | None = None
    sort_order: int = Field(default=0)


class EvidenceFileCreate(EvidenceFileBase):
    organization_id: uuid.UUID
    client_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None


class EvidenceFileUpdate(BaseModel):
    file_name: str | None = Field(default=None, min_length=1, max_length=255)
    source: str | None = Field(default=None, max_length=64)
    public_url: str | None = None
    drive_file_id: str | None = Field(default=None, max_length=255)
    mime_type: str | None = Field(default=None, max_length=128)
    size_bytes: int | None = Field(default=None, ge=0)
    caption: str | None = None
    sort_order: int | None = None


class EvidenceFileRead(EvidenceFileBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    client_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    observation_id: uuid.UUID | None = None
    system_id: uuid.UUID | None = None
    drive_folder_id: str | None = None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class EvidenceFileListResponse(BaseModel):
    items: list[EvidenceFileRead]
    total: int
    limit: int
    offset: int
