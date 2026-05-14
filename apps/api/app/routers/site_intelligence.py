from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import auth
from app.db import get_db
from app.schemas import (
    BmpSystemListResponse,
    BmpSystemRead,
    DocumentExtractedFieldCreate,
    DocumentExtractedFieldListResponse,
    DocumentExtractedFieldRead,
    DocumentExtractedFieldUpdate,
    DocumentLinkSuggestionCreate,
    DocumentLinkSuggestionListResponse,
    DocumentLinkSuggestionRead,
    DocumentLinkSuggestionUpdate,
    DocumentRecordCreate,
    DocumentRecordListResponse,
    DocumentRecordRead,
    DocumentRecordUpdate,
    DocumentTextChunkCreate,
    DocumentTextChunkListResponse,
    DocumentTextChunkRead,
    KnowledgeItemCreate,
    KnowledgeItemListResponse,
    KnowledgeItemRead,
    KnowledgeItemUpdate,
    ObservationListResponse,
    ObservationRead,
    RecordLinkCreate,
    RecordLinkListResponse,
    RecordLinkRead,
    RecordLinkUpdate,
    RecordNoteCreate,
    RecordNoteListResponse,
    RecordNoteRead,
    RecordNoteUpdate,
)
from app.services import site_intelligence_service
from app.services.common import CRMNotFoundError, CRMValidationError


router = APIRouter(tags=["site-intelligence"])
SessionDep = Annotated[Session, Depends(get_db)]
OrgQuery = auth.OrgQueryDep
LimitQuery = Annotated[int, Query(ge=1, le=500)]
OffsetQuery = Annotated[int, Query(ge=0)]


def _raise_http_error(error: Exception) -> None:
    if isinstance(error, CRMNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if isinstance(error, CRMValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    raise error


@router.get("/v1/bmp-systems", response_model=BmpSystemListResponse)
def list_bmp_systems(
    db: SessionDep,
    organization_id: OrgQuery,
    site_id: uuid.UUID | None = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> BmpSystemListResponse:
    page = site_intelligence_service.list_bmp_systems(
        db,
        organization_id=organization_id,
        site_id=site_id,
        limit=limit,
        offset=offset,
    )
    return BmpSystemListResponse(items=page.items, total=page.total, limit=page.limit, offset=page.offset)


@router.get("/v1/bmp-systems/{system_id}", response_model=BmpSystemRead)
def get_bmp_system(system_id: uuid.UUID, db: SessionDep, organization_id: OrgQuery) -> BmpSystemRead:
    record = site_intelligence_service.get_bmp_system(
        db,
        organization_id=organization_id,
        system_id=system_id,
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BMP system not found.")
    return record


@router.get("/v1/observations", response_model=ObservationListResponse)
def list_observations(
    db: SessionDep,
    organization_id: OrgQuery,
    job_id: uuid.UUID | None = None,
    site_id: uuid.UUID | None = None,
    system_id: uuid.UUID | None = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> ObservationListResponse:
    page = site_intelligence_service.list_observations(
        db,
        organization_id=organization_id,
        job_id=job_id,
        site_id=site_id,
        system_id=system_id,
        limit=limit,
        offset=offset,
    )
    return ObservationListResponse(items=page.items, total=page.total, limit=page.limit, offset=page.offset)


@router.get("/v1/observations/{observation_id}", response_model=ObservationRead)
def get_observation(
    observation_id: uuid.UUID,
    db: SessionDep,
    organization_id: OrgQuery,
) -> ObservationRead:
    record = site_intelligence_service.get_observation(
        db,
        organization_id=organization_id,
        observation_id=observation_id,
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Observation not found.")
    return record


@router.get("/v1/record-links", response_model=RecordLinkListResponse)
def list_record_links(
    db: SessionDep,
    organization_id: OrgQuery,
    source_type: str | None = None,
    source_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
    relationship_type: str | None = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> RecordLinkListResponse:
    try:
        page = site_intelligence_service.list_record_links(
            db,
            organization_id=organization_id,
            source_type=source_type,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            relationship_type=relationship_type,
            limit=limit,
            offset=offset,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
    return RecordLinkListResponse(items=page.items, total=page.total, limit=page.limit, offset=page.offset)


@router.post("/v1/record-links", response_model=RecordLinkRead, status_code=status.HTTP_201_CREATED)
def create_record_link(
    payload: RecordLinkCreate,
    db: SessionDep,
    current_user: auth.CurrentUserDep,
) -> RecordLinkRead:
    auth.require_organization_access(db, current_user, payload.organization_id)
    try:
        return site_intelligence_service.create_record_link(
            db,
            data=payload.model_dump(),
            created_by=current_user.id if current_user else None,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.patch("/v1/record-links/{link_id}", response_model=RecordLinkRead)
def update_record_link(
    link_id: uuid.UUID,
    payload: RecordLinkUpdate,
    db: SessionDep,
    organization_id: OrgQuery,
) -> RecordLinkRead:
    try:
        return site_intelligence_service.update_record_link(
            db,
            organization_id=organization_id,
            link_id=link_id,
            data=payload.model_dump(exclude_unset=True),
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.delete("/v1/record-links/{link_id}", response_model=RecordLinkRead)
def archive_record_link(link_id: uuid.UUID, db: SessionDep, organization_id: OrgQuery) -> RecordLinkRead:
    try:
        return site_intelligence_service.archive_record_link(
            db,
            organization_id=organization_id,
            link_id=link_id,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.get("/v1/record-notes", response_model=RecordNoteListResponse)
def list_record_notes(
    db: SessionDep,
    organization_id: OrgQuery,
    parent_type: str | None = None,
    parent_id: uuid.UUID | None = None,
    note_type: str | None = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> RecordNoteListResponse:
    try:
        page = site_intelligence_service.list_record_notes(
            db,
            organization_id=organization_id,
            parent_type=parent_type,
            parent_id=parent_id,
            note_type=note_type,
            limit=limit,
            offset=offset,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
    return RecordNoteListResponse(items=page.items, total=page.total, limit=page.limit, offset=page.offset)


@router.post("/v1/record-notes", response_model=RecordNoteRead, status_code=status.HTTP_201_CREATED)
def create_record_note(
    payload: RecordNoteCreate,
    db: SessionDep,
    current_user: auth.CurrentUserDep,
) -> RecordNoteRead:
    auth.require_organization_access(db, current_user, payload.organization_id)
    try:
        return site_intelligence_service.create_record_note(
            db,
            data=payload.model_dump(),
            created_by=current_user.id if current_user else None,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.patch("/v1/record-notes/{note_id}", response_model=RecordNoteRead)
def update_record_note(
    note_id: uuid.UUID,
    payload: RecordNoteUpdate,
    db: SessionDep,
    organization_id: OrgQuery,
) -> RecordNoteRead:
    try:
        return site_intelligence_service.update_record_note(
            db,
            organization_id=organization_id,
            note_id=note_id,
            data=payload.model_dump(exclude_unset=True),
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.delete("/v1/record-notes/{note_id}", response_model=RecordNoteRead)
def archive_record_note(note_id: uuid.UUID, db: SessionDep, organization_id: OrgQuery) -> RecordNoteRead:
    try:
        return site_intelligence_service.archive_record_note(
            db,
            organization_id=organization_id,
            note_id=note_id,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.get("/v1/knowledge-items", response_model=KnowledgeItemListResponse)
def list_knowledge_items(
    db: SessionDep,
    organization_id: OrgQuery,
    client_id: uuid.UUID | None = None,
    site_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    knowledge_type: str | None = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> KnowledgeItemListResponse:
    try:
        page = site_intelligence_service.list_knowledge_items(
            db,
            organization_id=organization_id,
            client_id=client_id,
            site_id=site_id,
            job_id=job_id,
            knowledge_type=knowledge_type,
            limit=limit,
            offset=offset,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
    return KnowledgeItemListResponse(items=page.items, total=page.total, limit=page.limit, offset=page.offset)


@router.post("/v1/knowledge-items", response_model=KnowledgeItemRead, status_code=status.HTTP_201_CREATED)
def create_knowledge_item(
    payload: KnowledgeItemCreate,
    db: SessionDep,
    current_user: auth.CurrentUserDep,
) -> KnowledgeItemRead:
    auth.require_organization_access(db, current_user, payload.organization_id)
    try:
        return site_intelligence_service.create_knowledge_item(db, data=payload.model_dump())
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.patch("/v1/knowledge-items/{item_id}", response_model=KnowledgeItemRead)
def update_knowledge_item(
    item_id: uuid.UUID,
    payload: KnowledgeItemUpdate,
    db: SessionDep,
    organization_id: OrgQuery,
) -> KnowledgeItemRead:
    try:
        return site_intelligence_service.update_knowledge_item(
            db,
            organization_id=organization_id,
            item_id=item_id,
            data=payload.model_dump(exclude_unset=True),
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.delete("/v1/knowledge-items/{item_id}", response_model=KnowledgeItemRead)
def archive_knowledge_item(item_id: uuid.UUID, db: SessionDep, organization_id: OrgQuery) -> KnowledgeItemRead:
    try:
        return site_intelligence_service.archive_knowledge_item(
            db,
            organization_id=organization_id,
            item_id=item_id,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.get("/v1/documents", response_model=DocumentRecordListResponse)
def list_documents(
    db: SessionDep,
    organization_id: OrgQuery,
    client_id: uuid.UUID | None = None,
    site_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    document_type: str | None = None,
    extraction_status: str | None = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> DocumentRecordListResponse:
    try:
        page = site_intelligence_service.list_documents(
            db,
            organization_id=organization_id,
            client_id=client_id,
            site_id=site_id,
            job_id=job_id,
            status=status_filter,
            document_type=document_type,
            extraction_status=extraction_status,
            limit=limit,
            offset=offset,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
    return DocumentRecordListResponse(items=page.items, total=page.total, limit=page.limit, offset=page.offset)


@router.post("/v1/documents", response_model=DocumentRecordRead, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: DocumentRecordCreate,
    db: SessionDep,
    current_user: auth.CurrentUserDep,
) -> DocumentRecordRead:
    auth.require_organization_access(db, current_user, payload.organization_id)
    try:
        return site_intelligence_service.create_document(db, data=payload.model_dump())
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.get("/v1/documents/{document_id}", response_model=DocumentRecordRead)
def get_document(document_id: uuid.UUID, db: SessionDep, organization_id: OrgQuery) -> DocumentRecordRead:
    record = site_intelligence_service.get_document(
        db,
        organization_id=organization_id,
        document_id=document_id,
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return record


@router.patch("/v1/documents/{document_id}", response_model=DocumentRecordRead)
def update_document(
    document_id: uuid.UUID,
    payload: DocumentRecordUpdate,
    db: SessionDep,
    organization_id: OrgQuery,
) -> DocumentRecordRead:
    try:
        return site_intelligence_service.update_document(
            db,
            organization_id=organization_id,
            document_id=document_id,
            data=payload.model_dump(exclude_unset=True),
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.delete("/v1/documents/{document_id}", response_model=DocumentRecordRead)
def archive_document(document_id: uuid.UUID, db: SessionDep, organization_id: OrgQuery) -> DocumentRecordRead:
    try:
        return site_intelligence_service.archive_document(
            db,
            organization_id=organization_id,
            document_id=document_id,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.get("/v1/documents/{document_id}/chunks", response_model=DocumentTextChunkListResponse)
def list_document_chunks(
    document_id: uuid.UUID,
    db: SessionDep,
    organization_id: OrgQuery,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> DocumentTextChunkListResponse:
    try:
        page = site_intelligence_service.list_document_chunks(
            db,
            organization_id=organization_id,
            document_id=document_id,
            limit=limit,
            offset=offset,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
    return DocumentTextChunkListResponse(items=page.items, total=page.total, limit=page.limit, offset=page.offset)


@router.post("/v1/documents/{document_id}/chunks", response_model=DocumentTextChunkRead, status_code=status.HTTP_201_CREATED)
def create_document_chunk(
    document_id: uuid.UUID,
    payload: DocumentTextChunkCreate,
    db: SessionDep,
    current_user: auth.CurrentUserDep,
) -> DocumentTextChunkRead:
    auth.require_organization_access(db, current_user, payload.organization_id)
    try:
        return site_intelligence_service.create_document_chunk(
            db,
            organization_id=payload.organization_id,
            document_id=document_id,
            data=payload.model_dump(exclude={"organization_id"}),
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.get("/v1/documents/{document_id}/extracted-fields", response_model=DocumentExtractedFieldListResponse)
def list_document_extracted_fields(
    document_id: uuid.UUID,
    db: SessionDep,
    organization_id: OrgQuery,
    review_status: str | None = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> DocumentExtractedFieldListResponse:
    try:
        page = site_intelligence_service.list_document_extracted_fields(
            db,
            organization_id=organization_id,
            document_id=document_id,
            review_status=review_status,
            limit=limit,
            offset=offset,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
    return DocumentExtractedFieldListResponse(items=page.items, total=page.total, limit=page.limit, offset=page.offset)


@router.post(
    "/v1/documents/{document_id}/extracted-fields",
    response_model=DocumentExtractedFieldRead,
    status_code=status.HTTP_201_CREATED,
)
def create_document_extracted_field(
    document_id: uuid.UUID,
    payload: DocumentExtractedFieldCreate,
    db: SessionDep,
    current_user: auth.CurrentUserDep,
) -> DocumentExtractedFieldRead:
    auth.require_organization_access(db, current_user, payload.organization_id)
    try:
        return site_intelligence_service.create_document_extracted_field(
            db,
            organization_id=payload.organization_id,
            document_id=document_id,
            data=payload.model_dump(exclude={"organization_id"}),
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.patch("/v1/documents/{document_id}/extracted-fields/{field_id}", response_model=DocumentExtractedFieldRead)
def update_document_extracted_field(
    document_id: uuid.UUID,
    field_id: uuid.UUID,
    payload: DocumentExtractedFieldUpdate,
    db: SessionDep,
    organization_id: OrgQuery,
) -> DocumentExtractedFieldRead:
    try:
        return site_intelligence_service.update_document_extracted_field(
            db,
            organization_id=organization_id,
            document_id=document_id,
            field_id=field_id,
            data=payload.model_dump(exclude_unset=True),
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.delete("/v1/documents/{document_id}/extracted-fields/{field_id}", response_model=DocumentExtractedFieldRead)
def archive_document_extracted_field(
    document_id: uuid.UUID,
    field_id: uuid.UUID,
    db: SessionDep,
    organization_id: OrgQuery,
) -> DocumentExtractedFieldRead:
    try:
        return site_intelligence_service.archive_document_extracted_field(
            db,
            organization_id=organization_id,
            document_id=document_id,
            field_id=field_id,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.get("/v1/documents/{document_id}/link-suggestions", response_model=DocumentLinkSuggestionListResponse)
def list_document_link_suggestions(
    document_id: uuid.UUID,
    db: SessionDep,
    organization_id: OrgQuery,
    review_status: str | None = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> DocumentLinkSuggestionListResponse:
    try:
        page = site_intelligence_service.list_document_link_suggestions(
            db,
            organization_id=organization_id,
            document_id=document_id,
            review_status=review_status,
            limit=limit,
            offset=offset,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
    return DocumentLinkSuggestionListResponse(items=page.items, total=page.total, limit=page.limit, offset=page.offset)


@router.post(
    "/v1/documents/{document_id}/link-suggestions",
    response_model=DocumentLinkSuggestionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_document_link_suggestion(
    document_id: uuid.UUID,
    payload: DocumentLinkSuggestionCreate,
    db: SessionDep,
    current_user: auth.CurrentUserDep,
) -> DocumentLinkSuggestionRead:
    auth.require_organization_access(db, current_user, payload.organization_id)
    try:
        return site_intelligence_service.create_document_link_suggestion(
            db,
            organization_id=payload.organization_id,
            document_id=document_id,
            data=payload.model_dump(exclude={"organization_id"}),
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.patch("/v1/documents/{document_id}/link-suggestions/{suggestion_id}", response_model=DocumentLinkSuggestionRead)
def update_document_link_suggestion(
    document_id: uuid.UUID,
    suggestion_id: uuid.UUID,
    payload: DocumentLinkSuggestionUpdate,
    db: SessionDep,
    organization_id: OrgQuery,
) -> DocumentLinkSuggestionRead:
    try:
        return site_intelligence_service.update_document_link_suggestion(
            db,
            organization_id=organization_id,
            document_id=document_id,
            suggestion_id=suggestion_id,
            data=payload.model_dump(exclude_unset=True),
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.delete("/v1/documents/{document_id}/link-suggestions/{suggestion_id}", response_model=DocumentLinkSuggestionRead)
def archive_document_link_suggestion(
    document_id: uuid.UUID,
    suggestion_id: uuid.UUID,
    db: SessionDep,
    organization_id: OrgQuery,
) -> DocumentLinkSuggestionRead:
    try:
        return site_intelligence_service.archive_document_link_suggestion(
            db,
            organization_id=organization_id,
            document_id=document_id,
            suggestion_id=suggestion_id,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
