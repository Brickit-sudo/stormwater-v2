from __future__ import annotations

from pydantic import BaseModel, Field


class IntegrationProviderStatus(BaseModel):
    provider: str
    label: str
    configured: bool
    status: str = Field(description="configured, missing, or deferred")
    missing_fields: list[str] = Field(default_factory=list)
    enabled_capabilities: list[str] = Field(default_factory=list)
    deferred_capabilities: list[str] = Field(default_factory=list)
    message: str
    model: str | None = None


class IntegrationsStatusResponse(BaseModel):
    outlook: IntegrationProviderStatus
    gmail: IntegrationProviderStatus
    google_drive: IntegrationProviderStatus
    onedrive: IntegrationProviderStatus
    ai: IntegrationProviderStatus
