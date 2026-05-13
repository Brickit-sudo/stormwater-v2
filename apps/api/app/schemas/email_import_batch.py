from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EmailImportBatchBase(BaseModel):
    provider: str = Field(default="outlook", min_length=1, max_length=64)
    import_mode: str = Field(default="manual_seed", min_length=1, max_length=64)
    folder_id: str | None = Field(default=None, max_length=255)
    search_query: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    status: str = Field(default="previewed", min_length=1, max_length=32)
    preview_count: int = Field(default=0, ge=0)
    imported_count: int = Field(default=0, ge=0)
    skipped_count: int = Field(default=0, ge=0)
    duplicate_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    request_json: dict[str, Any] | None = None
    result_summary_json: dict[str, Any] | None = None
    completed_at: datetime | None = None


class EmailImportBatchCreate(EmailImportBatchBase):
    organization_id: uuid.UUID


class EmailImportBatchRead(EmailImportBatchBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime
    archived_at: datetime | None = None


class EmailImportBatchListResponse(BaseModel):
    items: list[EmailImportBatchRead]
    total: int
    limit: int
    offset: int
