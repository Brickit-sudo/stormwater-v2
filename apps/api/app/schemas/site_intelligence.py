from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BmpSystemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    site_id: uuid.UUID
    system_code: str | None = None
    system_type: str
    name: str | None = None
    location_description: str | None = None
    notes: str | None = None
    legacy_source: str | None = None
    legacy_id: str | None = None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class BmpSystemListResponse(BaseModel):
    items: list[BmpSystemRead]
    total: int
    limit: int
    offset: int


class ObservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    job_id: uuid.UUID
    system_id: uuid.UUID | None = None
    observation_type: str | None = None
    finding: str | None = None
    recommendation: str | None = None
    severity: str | None = None
    maintenance_needed: bool | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class ObservationListResponse(BaseModel):
    items: list[ObservationRead]
    total: int
    limit: int
    offset: int


class RecordLinkBase(BaseModel):
    source_type: str = Field(min_length=1, max_length=64)
    source_id: uuid.UUID
    target_type: str = Field(min_length=1, max_length=64)
    target_id: uuid.UUID
    relationship_type: str = Field(default="related", min_length=1, max_length=64)
    confidence: float | None = Field(default=None, ge=0, le=1)
    link_reason: str | None = None


class RecordLinkCreate(RecordLinkBase):
    organization_id: uuid.UUID


class RecordLinkUpdate(BaseModel):
    relationship_type: str | None = Field(default=None, min_length=1, max_length=64)
    confidence: float | None = Field(default=None, ge=0, le=1)
    link_reason: str | None = None


class RecordLinkRead(RecordLinkBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    created_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class RecordLinkListResponse(BaseModel):
    items: list[RecordLinkRead]
    total: int
    limit: int
    offset: int


class RecordNoteBase(BaseModel):
    parent_type: str = Field(min_length=1, max_length=64)
    parent_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)
    note_type: str = Field(default="general", min_length=1, max_length=64)
    visibility: str = Field(default="internal", min_length=1, max_length=64)


class RecordNoteCreate(RecordNoteBase):
    organization_id: uuid.UUID


class RecordNoteUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    body: str | None = Field(default=None, min_length=1)
    note_type: str | None = Field(default=None, min_length=1, max_length=64)
    visibility: str | None = Field(default=None, min_length=1, max_length=64)


class RecordNoteRead(RecordNoteBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    created_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class RecordNoteListResponse(BaseModel):
    items: list[RecordNoteRead]
    total: int
    limit: int
    offset: int


class KnowledgeItemBase(BaseModel):
    client_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    knowledge_type: str = Field(min_length=1, max_length=64)
    tags_json: list[str] | None = None
    source_type: str | None = Field(default=None, max_length=64)
    source_id: uuid.UUID | None = None


class KnowledgeItemCreate(KnowledgeItemBase):
    organization_id: uuid.UUID


class KnowledgeItemUpdate(BaseModel):
    client_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content: str | None = Field(default=None, min_length=1)
    knowledge_type: str | None = Field(default=None, min_length=1, max_length=64)
    tags_json: list[str] | None = None
    source_type: str | None = Field(default=None, max_length=64)
    source_id: uuid.UUID | None = None


class KnowledgeItemRead(KnowledgeItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class KnowledgeItemListResponse(BaseModel):
    items: list[KnowledgeItemRead]
    total: int
    limit: int
    offset: int


class DocumentRecordBase(BaseModel):
    evidence_file_id: uuid.UUID | None = None
    source: str = Field(default="manual", min_length=1, max_length=64)
    file_name: str = Field(min_length=1, max_length=255)
    file_url: str | None = None
    storage_path: str | None = None
    mime_type: str | None = Field(default=None, max_length=128)
    document_type: str = Field(default="unknown", min_length=1, max_length=64)
    client_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    status: str = Field(default="queued", min_length=1, max_length=32)
    extraction_status: str = Field(default="not_started", min_length=1, max_length=32)


class DocumentRecordCreate(DocumentRecordBase):
    organization_id: uuid.UUID


class DocumentRecordUpdate(BaseModel):
    evidence_file_id: uuid.UUID | None = None
    source: str | None = Field(default=None, min_length=1, max_length=64)
    file_name: str | None = Field(default=None, min_length=1, max_length=255)
    file_url: str | None = None
    storage_path: str | None = None
    mime_type: str | None = Field(default=None, max_length=128)
    document_type: str | None = Field(default=None, min_length=1, max_length=64)
    client_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    status: str | None = Field(default=None, min_length=1, max_length=32)
    extraction_status: str | None = Field(default=None, min_length=1, max_length=32)


class DocumentRecordRead(DocumentRecordBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class DocumentRecordListResponse(BaseModel):
    items: list[DocumentRecordRead]
    total: int
    limit: int
    offset: int


class DocumentTextChunkBase(BaseModel):
    chunk_index: int = Field(ge=0)
    page_number: int | None = Field(default=None, ge=1)
    heading: str | None = Field(default=None, max_length=255)
    text: str = Field(min_length=1)
    token_count: int | None = Field(default=None, ge=0)


class DocumentTextChunkCreate(DocumentTextChunkBase):
    organization_id: uuid.UUID


class DocumentTextChunkRead(DocumentTextChunkBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    document_id: uuid.UUID
    created_at: datetime


class DocumentTextChunkListResponse(BaseModel):
    items: list[DocumentTextChunkRead]
    total: int
    limit: int
    offset: int


class DocumentExtractedFieldBase(BaseModel):
    field_name: str = Field(min_length=1, max_length=128)
    field_value: str = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_page: int | None = Field(default=None, ge=1)
    review_status: str = Field(default="pending", min_length=1, max_length=32)


class DocumentExtractedFieldCreate(DocumentExtractedFieldBase):
    organization_id: uuid.UUID


class DocumentExtractedFieldUpdate(BaseModel):
    field_name: str | None = Field(default=None, min_length=1, max_length=128)
    field_value: str | None = Field(default=None, min_length=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    source_page: int | None = Field(default=None, ge=1)
    review_status: str | None = Field(default=None, min_length=1, max_length=32)


class DocumentExtractedFieldRead(DocumentExtractedFieldBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    document_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class DocumentExtractedFieldListResponse(BaseModel):
    items: list[DocumentExtractedFieldRead]
    total: int
    limit: int
    offset: int


class DocumentLinkSuggestionBase(BaseModel):
    target_type: str = Field(min_length=1, max_length=64)
    target_id: uuid.UUID | None = None
    target_label: str | None = Field(default=None, max_length=255)
    confidence: float | None = Field(default=None, ge=0, le=1)
    reason: str | None = None
    review_status: str = Field(default="pending", min_length=1, max_length=32)


class DocumentLinkSuggestionCreate(DocumentLinkSuggestionBase):
    organization_id: uuid.UUID


class DocumentLinkSuggestionUpdate(BaseModel):
    target_type: str | None = Field(default=None, min_length=1, max_length=64)
    target_id: uuid.UUID | None = None
    target_label: str | None = Field(default=None, max_length=255)
    confidence: float | None = Field(default=None, ge=0, le=1)
    reason: str | None = None
    review_status: str | None = Field(default=None, min_length=1, max_length=32)


class DocumentLinkSuggestionRead(DocumentLinkSuggestionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    document_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class DocumentLinkSuggestionListResponse(BaseModel):
    items: list[DocumentLinkSuggestionRead]
    total: int
    limit: int
    offset: int
