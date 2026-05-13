from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import auth
from app.db import get_db
from app.schemas import (
    EvidenceFileCreate,
    EvidenceFileListResponse,
    EvidenceFileRead,
    EvidenceFileUpdate,
)
from app.services import evidence_files_service
from app.services.common import CRMNotFoundError, CRMValidationError


router = APIRouter(prefix="/v1/files", tags=["files"])
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


@router.get("", response_model=EvidenceFileListResponse)
def list_files(
    db: SessionDep,
    organization_id: OrgQuery,
    client_id: uuid.UUID | None = None,
    site_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> EvidenceFileListResponse:
    page = evidence_files_service.list_evidence_files(
        db,
        organization_id=organization_id,
        client_id=client_id,
        site_id=site_id,
        job_id=job_id,
        limit=limit,
        offset=offset,
    )
    return EvidenceFileListResponse(
        items=page.items,
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post("", response_model=EvidenceFileRead, status_code=status.HTTP_201_CREATED)
def create_file(
    payload: EvidenceFileCreate,
    db: SessionDep,
    current_user: auth.CurrentUserDep,
) -> EvidenceFileRead:
    auth.require_organization_access(db, current_user, payload.organization_id)
    try:
        return evidence_files_service.create_evidence_file(db, data=payload.model_dump())
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.get("/{file_id}", response_model=EvidenceFileRead)
def get_file(file_id: uuid.UUID, db: SessionDep, organization_id: OrgQuery) -> EvidenceFileRead:
    record = evidence_files_service.get_evidence_file(
        db, organization_id=organization_id, file_id=file_id,
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    return record


@router.patch("/{file_id}", response_model=EvidenceFileRead)
def update_file(
    file_id: uuid.UUID,
    payload: EvidenceFileUpdate,
    db: SessionDep,
    organization_id: OrgQuery,
) -> EvidenceFileRead:
    try:
        return evidence_files_service.update_evidence_file(
            db,
            organization_id=organization_id,
            file_id=file_id,
            data=payload.model_dump(exclude_unset=True),
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.delete("/{file_id}", response_model=EvidenceFileRead)
def archive_file(
    file_id: uuid.UUID,
    db: SessionDep,
    organization_id: OrgQuery,
) -> EvidenceFileRead:
    try:
        return evidence_files_service.archive_evidence_file(
            db,
            organization_id=organization_id,
            file_id=file_id,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
