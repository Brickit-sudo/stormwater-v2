from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SiteBase(BaseModel):
    site_code: str | None = Field(default=None, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    address: str | None = None
    city: str | None = Field(default=None, max_length=128)
    state: str | None = Field(default=None, max_length=64)
    zip: str | None = Field(default=None, max_length=20)
    latitude: Decimal | None = Field(default=None, ge=Decimal("-90"), le=Decimal("90"))
    longitude: Decimal | None = Field(default=None, ge=Decimal("-180"), le=Decimal("180"))
    status: str = Field(default="active", min_length=1, max_length=32)
    notes: str | None = None
    drive_folder_url: str | None = None


class SiteCreate(SiteBase):
    organization_id: uuid.UUID
    client_id: uuid.UUID


class SiteUpdate(BaseModel):
    client_id: uuid.UUID | None = None
    site_code: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = None
    city: str | None = Field(default=None, max_length=128)
    state: str | None = Field(default=None, max_length=64)
    zip: str | None = Field(default=None, max_length=20)
    latitude: Decimal | None = Field(default=None, ge=Decimal("-90"), le=Decimal("90"))
    longitude: Decimal | None = Field(default=None, ge=Decimal("-180"), le=Decimal("180"))
    status: str | None = Field(default=None, min_length=1, max_length=32)
    notes: str | None = None
    drive_folder_url: str | None = None


class SiteRead(SiteBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    client_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class SiteListResponse(BaseModel):
    items: list[SiteRead]
    total: int
    limit: int
    offset: int


class SiteMapRead(BaseModel):
    id: uuid.UUID
    name: str
    client_id: uuid.UUID
    client_name: str | None = None
    status: str
    address: str | None = None
    city: str | None = None
    state: str | None = None
    latitude: Decimal = Field(ge=Decimal("-90"), le=Decimal("90"))
    longitude: Decimal = Field(ge=Decimal("-180"), le=Decimal("180"))


class SiteMapListResponse(BaseModel):
    items: list[SiteMapRead]
    total: int
    limit: int
    offset: int
