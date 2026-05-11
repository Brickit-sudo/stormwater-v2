from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ClientBase(BaseModel):
    client_code: str | None = Field(default=None, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    status: str = Field(default="active", min_length=1, max_length=32)
    primary_contact_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=64)
    billing_address: str | None = None
    notes: str | None = None
    drive_folder_url: str | None = None


class ClientCreate(ClientBase):
    organization_id: uuid.UUID


class ClientUpdate(BaseModel):
    client_code: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    status: str | None = Field(default=None, min_length=1, max_length=32)
    primary_contact_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=64)
    billing_address: str | None = None
    notes: str | None = None
    drive_folder_url: str | None = None


class ClientRead(ClientBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class ClientListResponse(BaseModel):
    items: list[ClientRead]
    total: int
    limit: int
    offset: int
