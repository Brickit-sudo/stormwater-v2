from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    EmailImportBatchCreate,
    EmailImportBatchListResponse,
    EmailImportBatchRead,
)
from app.services import email_import_batches_service
from app.services.common import CRMNotFoundError, CRMValidationError


router = APIRouter(prefix="/v1/email-import-batches", tags=["email-import-batches"])
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


@router.get("", response_model=EmailImportBatchListResponse)
def list_import_batches(
    db: SessionDep,
    organization_id: OrgQuery,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    provider: str | None = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> EmailImportBatchListResponse:
    try:
        page = email_import_batches_service.list_import_batches(
            db,
            organization_id=organization_id,
            status=status_filter,
            provider=provider,
            limit=limit,
            offset=offset,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
    return EmailImportBatchListResponse(items=page.items, total=page.total, limit=page.limit, offset=page.offset)


@router.post("", response_model=EmailImportBatchRead, status_code=status.HTTP_201_CREATED)
def create_import_batch(payload: EmailImportBatchCreate, db: SessionDep) -> EmailImportBatchRead:
    try:
        return email_import_batches_service.create_import_batch(db, data=payload.model_dump())
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.get("/{batch_id}", response_model=EmailImportBatchRead)
def get_import_batch(
    batch_id: uuid.UUID,
    db: SessionDep,
    organization_id: OrgQuery,
) -> EmailImportBatchRead:
    batch = email_import_batches_service.get_import_batch(
        db,
        organization_id=organization_id,
        batch_id=batch_id,
    )
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email import batch not found.")
    return batch
