from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import AiDraftCreate, AiDraftListResponse, AiDraftRead, AiDraftUpdate
from app.services import ai_drafts_service
from app.services.common import CRMNotFoundError, CRMValidationError


router = APIRouter(prefix="/v1/ai-drafts", tags=["ai-drafts"])
SessionDep = Annotated[Session, Depends(get_db)]
OrgQuery = Annotated[
    uuid.UUID,
    Query(description="Temporary organization scope until auth is added."),
]
LimitQuery = Annotated[int, Query(ge=1, le=500)]
OffsetQuery = Annotated[int, Query(ge=0)]


def _raise_http_error(error: Exception) -> None:
    if isinstance(error, CRMNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if isinstance(error, CRMValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    raise error


@router.get("", response_model=AiDraftListResponse)
def list_ai_drafts(
    db: SessionDep,
    organization_id: OrgQuery,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    draft_type: str | None = None,
    client_id: uuid.UUID | None = None,
    site_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    email_message_id: uuid.UUID | None = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> AiDraftListResponse:
    try:
        page = ai_drafts_service.list_ai_drafts(
            db,
            organization_id=organization_id,
            status=status_filter,
            draft_type=draft_type,
            client_id=client_id,
            site_id=site_id,
            job_id=job_id,
            email_message_id=email_message_id,
            limit=limit,
            offset=offset,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
    return AiDraftListResponse(items=page.items, total=page.total, limit=page.limit, offset=page.offset)


@router.post("", response_model=AiDraftRead, status_code=status.HTTP_201_CREATED)
def create_ai_draft(payload: AiDraftCreate, db: SessionDep) -> AiDraftRead:
    try:
        return ai_drafts_service.create_ai_draft(db, data=payload.model_dump())
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.get("/{draft_id}", response_model=AiDraftRead)
def get_ai_draft(
    draft_id: uuid.UUID,
    db: SessionDep,
    organization_id: OrgQuery,
) -> AiDraftRead:
    draft = ai_drafts_service.get_ai_draft(
        db,
        organization_id=organization_id,
        draft_id=draft_id,
    )
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI draft not found.")
    return draft


@router.patch("/{draft_id}", response_model=AiDraftRead)
def update_ai_draft(
    draft_id: uuid.UUID,
    payload: AiDraftUpdate,
    db: SessionDep,
    organization_id: OrgQuery,
) -> AiDraftRead:
    try:
        return ai_drafts_service.update_ai_draft(
            db,
            organization_id=organization_id,
            draft_id=draft_id,
            data=payload.model_dump(exclude_unset=True),
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.delete("/{draft_id}", response_model=AiDraftRead)
def archive_ai_draft(
    draft_id: uuid.UUID,
    db: SessionDep,
    organization_id: OrgQuery,
) -> AiDraftRead:
    try:
        return ai_drafts_service.archive_ai_draft(
            db,
            organization_id=organization_id,
            draft_id=draft_id,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
