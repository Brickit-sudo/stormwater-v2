from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.db import get_db
from app.schemas import EmailRecordLinkCreate, EmailRecordLinkListResponse, EmailRecordLinkRead
from app.services import email_record_links_service
from app.services.common import CRMNotFoundError, CRMValidationError


router = APIRouter(prefix="/v1/email-record-links", tags=["email-record-links"])
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


@router.post("", response_model=EmailRecordLinkRead, status_code=status.HTTP_201_CREATED)
def create_email_record_link(payload: EmailRecordLinkCreate, db: SessionDep) -> EmailRecordLinkRead:
    try:
        return email_record_links_service.create_email_record_link(db, data=payload.model_dump())
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.get("", response_model=EmailRecordLinkListResponse)
def list_email_record_links(
    db: SessionDep,
    organization_id: OrgQuery,
    email_message_id: uuid.UUID,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> EmailRecordLinkListResponse:
    try:
        page = email_record_links_service.list_email_record_links(
            db,
            organization_id=organization_id,
            email_message_id=email_message_id,
            limit=limit,
            offset=offset,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
    return EmailRecordLinkListResponse(items=page.items, total=page.total, limit=page.limit, offset=page.offset)


@router.delete("/{link_id}", response_model=EmailRecordLinkRead)
def delete_email_record_link(
    link_id: uuid.UUID,
    db: SessionDep,
    organization_id: OrgQuery,
) -> EmailRecordLinkRead:
    try:
        return email_record_links_service.delete_email_record_link(
            db,
            organization_id=organization_id,
            link_id=link_id,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
