from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    subtitle: str | None = None
    description: str | None = None
    status: str | None = None
    href: str | None = None
    matched_fields: list[str] = Field(default_factory=list)
    occurred_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchGroup(BaseModel):
    type: str
    label: str
    count: int
    results: list[SearchResult] = Field(default_factory=list)


class SearchResponse(BaseModel):
    query: str
    groups: list[SearchGroup] = Field(default_factory=list)
    total_count: int
