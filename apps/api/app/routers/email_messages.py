from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import auth
from app.db import get_db
from app.schemas import EmailMessageCreate, EmailMessageListResponse, EmailMessageRead, EmailMessageUpdate
from app.services import email_messages_service
from app.services.common import CRMNotFoundError, CRMValidationError


router = APIRouter(prefix="/v1/email-messages", tags=["email-messages"])
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


@router.get("", response_model=EmailMessageListResponse)
def list_email_messages(
    db: SessionDep,
    organization_id: OrgQuery,
    search: str | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    client_id: uuid.UUID | None = None,
    site_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    provider: str | None = None,
    received_before: datetime | None = None,
    received_after: datetime | None = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> EmailMessageListResponse:
    try:
        page = email_messages_service.list_email_messages(
            db,
            organization_id=organization_id,
            search=search,
            status=status_filter,
            client_id=client_id,
            site_id=site_id,
            job_id=job_id,
            provider=provider,
            received_before=received_before,
            received_after=received_after,
            limit=limit,
            offset=offset,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
    return EmailMessageListResponse(items=page.items, total=page.total, limit=page.limit, offset=page.offset)


@router.post("", response_model=EmailMessageRead, status_code=status.HTTP_201_CREATED)
def create_email_message(
    payload: EmailMessageCreate,
    db: SessionDep,
    current_user: auth.CurrentUserDep,
) -> EmailMessageRead:
    auth.require_organization_access(db, current_user, payload.organization_id)
    try:
        return email_messages_service.create_email_message(db, data=payload.model_dump())
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.get("/{email_message_id}", response_model=EmailMessageRead)
def get_email_message(
    email_message_id: uuid.UUID,
    db: SessionDep,
    organization_id: OrgQuery,
) -> EmailMessageRead:
    message = email_messages_service.get_email_message(
        db,
        organization_id=organization_id,
        email_message_id=email_message_id,
    )
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email message not found.")
    return message


@router.patch("/{email_message_id}", response_model=EmailMessageRead)
def update_email_message(
    email_message_id: uuid.UUID,
    payload: EmailMessageUpdate,
    db: SessionDep,
    organization_id: OrgQuery,
) -> EmailMessageRead:
    try:
        return email_messages_service.update_email_message(
            db,
            organization_id=organization_id,
            email_message_id=email_message_id,
            data=payload.model_dump(exclude_unset=True),
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.delete("/{email_message_id}", response_model=EmailMessageRead)
def archive_email_message(
    email_message_id: uuid.UUID,
    db: SessionDep,
    organization_id: OrgQuery,
) -> EmailMessageRead:
    try:
        return email_messages_service.archive_email_message(
            db,
            organization_id=organization_id,
            email_message_id=email_message_id,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
