from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.email_import_batch import EmailImportBatchRead
from app.schemas.email_message import EmailMessageRead


class OutlookStatusResponse(BaseModel):
    configured: bool
    configured_fields: list[str]
    missing_fields: list[str]
    graph_base_url: str
    auth_mode: str = "stored_oauth_or_request_token"
    message: str


class OutlookPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: uuid.UUID
    search_query: str | None = None
    folder_id: str | None = Field(default=None, max_length=255)
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = Field(default=25, ge=1)
    access_token: str | None = Field(default=None, min_length=1)


class OutlookPreviewMessage(BaseModel):
    provider_message_id: str = Field(min_length=1)
    provider_conversation_id: str | None = None
    internet_message_id: str | None = None
    subject: str
    sender: str
    recipients: list[dict[str, Any]] = Field(default_factory=list)
    received_at: datetime | None = None
    snippet: str | None = None
    body_preview: str | None = None
    body_text: str | None = None
    has_attachments: bool = False
    web_link: str | None = None


class OutlookPreviewResponse(BaseModel):
    items: list[OutlookPreviewMessage]
    count: int
    limit: int
    capped: bool = False


class OutlookImportSelectedRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: uuid.UUID
    search_query: str | None = None
    folder_id: str | None = Field(default=None, max_length=255)
    date_from: datetime | None = None
    date_to: datetime | None = None
    limit: int = Field(default=25, ge=1)
    selected_messages: list[OutlookPreviewMessage] = Field(default_factory=list)
    access_token: str | None = Field(default=None, min_length=1)


class OutlookImportSelectedResponse(BaseModel):
    batch: EmailImportBatchRead
    imported_messages: list[EmailMessageRead]
    imported_count: int
    skipped_count: int
    duplicate_count: int
    error_count: int
    capped: bool = False
