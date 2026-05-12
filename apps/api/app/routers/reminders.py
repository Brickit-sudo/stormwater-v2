from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    ReminderCreate,
    ReminderListResponse,
    ReminderRead,
    ReminderUpdate,
)
from app.services import reminders_service
from app.services.common import CRMNotFoundError, CRMValidationError


router = APIRouter(prefix="/v1/reminders", tags=["reminders"])
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


@router.get("", response_model=ReminderListResponse)
def list_reminders(
    db: SessionDep,
    organization_id: OrgQuery,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    priority: str | None = None,
    client_id: uuid.UUID | None = None,
    site_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    due_before: datetime | None = None,
    due_after: datetime | None = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> ReminderListResponse:
    try:
        page = reminders_service.list_reminders(
            db,
            organization_id=organization_id,
            status=status_filter,
            priority=priority,
            client_id=client_id,
            site_id=site_id,
            job_id=job_id,
            due_before=due_before,
            due_after=due_after,
            limit=limit,
            offset=offset,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
    return ReminderListResponse(items=page.items, total=page.total, limit=page.limit, offset=page.offset)


@router.post("", response_model=ReminderRead, status_code=status.HTTP_201_CREATED)
def create_reminder(payload: ReminderCreate, db: SessionDep) -> ReminderRead:
    try:
        return reminders_service.create_reminder(db, data=payload.model_dump())
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.get("/{reminder_id}", response_model=ReminderRead)
def get_reminder(
    reminder_id: uuid.UUID,
    db: SessionDep,
    organization_id: OrgQuery,
) -> ReminderRead:
    reminder = reminders_service.get_reminder(
        db,
        organization_id=organization_id,
        reminder_id=reminder_id,
    )
    if reminder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found.")
    return reminder


@router.patch("/{reminder_id}", response_model=ReminderRead)
def update_reminder(
    reminder_id: uuid.UUID,
    payload: ReminderUpdate,
    db: SessionDep,
    organization_id: OrgQuery,
) -> ReminderRead:
    try:
        return reminders_service.update_reminder(
            db,
            organization_id=organization_id,
            reminder_id=reminder_id,
            data=payload.model_dump(exclude_unset=True),
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.delete("/{reminder_id}", response_model=ReminderRead)
def archive_reminder(
    reminder_id: uuid.UUID,
    db: SessionDep,
    organization_id: OrgQuery,
) -> ReminderRead:
    try:
        return reminders_service.archive_reminder(
            db,
            organization_id=organization_id,
            reminder_id=reminder_id,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
