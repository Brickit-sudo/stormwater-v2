from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductIdeaBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category: str = Field(default="UX", min_length=1, max_length=64)
    lane: str = Field(default="V2", min_length=1, max_length=64)
    status: str = Field(default="new", min_length=1, max_length=32)
    priority: str = Field(default="medium", min_length=1, max_length=32)
    source: str | None = Field(default=None, max_length=128)
    owner: str | None = Field(default=None, max_length=128)
    target_version: str | None = Field(default=None, max_length=64)
    effort: str | None = Field(default=None, max_length=64)
    risk: str | None = Field(default=None, max_length=64)
    boss_demo_relevant: bool = False


class ProductIdeaCreate(ProductIdeaBase):
    organization_id: uuid.UUID


class ProductIdeaUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category: str | None = Field(default=None, min_length=1, max_length=64)
    lane: str | None = Field(default=None, min_length=1, max_length=64)
    status: str | None = Field(default=None, min_length=1, max_length=32)
    priority: str | None = Field(default=None, min_length=1, max_length=32)
    source: str | None = Field(default=None, max_length=128)
    owner: str | None = Field(default=None, max_length=128)
    target_version: str | None = Field(default=None, max_length=64)
    effort: str | None = Field(default=None, max_length=64)
    risk: str | None = Field(default=None, max_length=64)
    boss_demo_relevant: bool | None = None


class ProductIdeaRead(ProductIdeaBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class ProductIdeaListResponse(BaseModel):
    items: list[ProductIdeaRead]
    total: int
    limit: int
    offset: int


class ProductDecisionBase(BaseModel):
    related_idea_id: uuid.UUID | None = None
    decision_title: str = Field(min_length=1, max_length=255)
    decision_summary: str | None = None
    decision_reason: str | None = None
    alternatives_considered: str | None = None
    status: str = Field(default="proposed", min_length=1, max_length=32)
    decided_at: datetime | None = None


class ProductDecisionCreate(ProductDecisionBase):
    organization_id: uuid.UUID


class ProductDecisionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    related_idea_id: uuid.UUID | None = None
    decision_title: str | None = Field(default=None, min_length=1, max_length=255)
    decision_summary: str | None = None
    decision_reason: str | None = None
    alternatives_considered: str | None = None
    status: str | None = Field(default=None, min_length=1, max_length=32)
    decided_at: datetime | None = None


class ProductDecisionRead(ProductDecisionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class ProductDecisionListResponse(BaseModel):
    items: list[ProductDecisionRead]
    total: int
    limit: int
    offset: int
