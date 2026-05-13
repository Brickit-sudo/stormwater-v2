from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ai_draft import AiDraftRead


class AiStatusResponse(BaseModel):
    configured: bool
    enabled: bool
    provider: str = "openai"
    model: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
    message: str


class AiRequestBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: uuid.UUID
    email_message_id: uuid.UUID | None = None
    client_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    user_context: str | None = None
    save_draft: bool = False


class EmailSummaryRequest(AiRequestBase):
    pass


class EmailActionItemsRequest(AiRequestBase):
    pass


class ExtractFileLinksRequest(AiRequestBase):
    text: str | None = None


class SuggestRecordLinksRequest(AiRequestBase):
    text: str | None = None


class DraftReplyRequest(AiRequestBase):
    tone: str = Field(default="professional", max_length=64)


class ReportSectionDraftRequest(AiRequestBase):
    section_heading: str = Field(default="Inspection Findings", max_length=120)


class MaintenanceRecommendationDraftRequest(AiRequestBase):
    system_type: str | None = Field(default=None, max_length=120)


class ClientSummaryDraftRequest(AiRequestBase):
    audience: str = Field(default="client", max_length=64)


class SavedDraftRef(BaseModel):
    id: uuid.UUID
    draft_type: str
    title: str
    status: str


class AiOperationResponse(BaseModel):
    available: bool
    source: str
    model: str | None = None
    error_code: str | None = None
    message: str
    saved_draft: SavedDraftRef | None = None


class EmailSummaryResult(BaseModel):
    summary: str
    key_points: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    recommended_next_step: str


class EmailSummaryResponse(AiOperationResponse):
    result: EmailSummaryResult | None = None


class ActionItemSuggestion(BaseModel):
    title: str
    priority: str = "medium"
    due_hint: str | None = None
    reason: str
    suggested_owner: str | None = None


class EmailActionItemsResponse(AiOperationResponse):
    items: list[ActionItemSuggestion] = Field(default_factory=list)


class FileLinkCandidate(BaseModel):
    url: str
    link_type: str
    label: str
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractFileLinksResponse(AiOperationResponse):
    links: list[FileLinkCandidate] = Field(default_factory=list)


class RecordLinkSuggestion(BaseModel):
    target_type: str
    target_id: uuid.UUID
    target_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class SuggestRecordLinksResponse(AiOperationResponse):
    suggestions: list[RecordLinkSuggestion] = Field(default_factory=list)


class DraftReplyResult(BaseModel):
    subject: str
    body: str
    tone: str
    review_note: str


class DraftReplyResponse(AiOperationResponse):
    result: DraftReplyResult | None = None
    saved_ai_draft: AiDraftRead | None = None


class ReportSectionDraftResult(BaseModel):
    heading: str
    draft_text: str
    cautions: list[str] = Field(default_factory=list)


class ReportSectionDraftResponse(AiOperationResponse):
    result: ReportSectionDraftResult | None = None
    saved_ai_draft: AiDraftRead | None = None
