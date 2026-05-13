from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


TimelineEntryType = Literal[
    "record",
    "job",
    "reminder",
    "file",
    "email",
    "email_link",
    "ai_draft",
    "import_batch",
    "outlook_draft",
]


class TimelineEntry(BaseModel):
    id: str
    type: TimelineEntryType
    title: str
    description: str | None = None
    occurred_at: datetime
    source_table: str
    source_id: uuid.UUID
    status: str | None = None
    priority: str | None = None
    related_client_id: uuid.UUID | None = None
    related_site_id: uuid.UUID | None = None
    related_job_id: uuid.UUID | None = None
    href: str | None = None
    metadata: dict[str, Any] | None = None


class TimelineListResponse(BaseModel):
    items: list[TimelineEntry]
    total: int
    limit: int
    offset: int = 0
