from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OutlookDraftFromAiDraftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: uuid.UUID
    ai_draft_id: uuid.UUID
    to_recipients: list[str] = Field(default_factory=list)
    subject: str | None = Field(default=None, max_length=500)
    body_override: str | None = None


class OutlookDraftFromAiDraftResponse(BaseModel):
    ai_draft_id: uuid.UUID
    provider: str
    provider_draft_id: str
    provider_web_link: str | None = None
    provider_status: str
    pushed_to_provider_at: datetime
