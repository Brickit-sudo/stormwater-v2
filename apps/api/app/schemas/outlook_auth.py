from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class OutlookAuthStatusResponse(BaseModel):
    configured: bool
    configured_fields: list[str]
    missing_fields: list[str]
    graph_base_url: str
    auth_mode: str = "stored_oauth"
    connection_status: str = "disconnected"
    connected: bool = False
    email_address: str | None = None
    display_name: str | None = None
    scopes: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None
    connected_at: datetime | None = None
    last_used_at: datetime | None = None
    token_storage_mode: str
    message: str


class OutlookAuthStartResponse(BaseModel):
    configured: bool
    auth_url: str
    state: str
    message: str


class OutlookAuthCallbackResponse(BaseModel):
    connected: bool
    connection_status: str
    email_address: str | None = None
    display_name: str | None = None
    message: str


class OutlookDisconnectRequest(BaseModel):
    organization_id: uuid.UUID


class OutlookDisconnectResponse(BaseModel):
    disconnected: bool
    connection_status: str
    message: str
