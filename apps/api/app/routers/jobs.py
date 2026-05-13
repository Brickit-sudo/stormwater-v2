from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import auth
from app.db import get_db
from app.schemas import JobCreate, JobListResponse, JobRead, JobUpdate, ReportReadinessResponse
from app.services import jobs_service, report_readiness_service
from app.services.common import CRMNotFoundError, CRMValidationError


router = APIRouter(prefix="/v1/jobs", tags=["jobs"])
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


@router.get("", response_model=JobListResponse)
def list_jobs(
    db: SessionDep,
    organization_id: OrgQuery,
    search: str | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    client_id: uuid.UUID | None = None,
    site_id: uuid.UUID | None = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> JobListResponse:
    page = jobs_service.list_jobs(
        db,
        organization_id=organization_id,
        search=search,
        status=status_filter,
        client_id=client_id,
        site_id=site_id,
        limit=limit,
        offset=offset,
    )
    return JobListResponse(items=page.items, total=page.total, limit=page.limit, offset=page.offset)


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobCreate,
    db: SessionDep,
    current_user: auth.CurrentUserDep,
) -> JobRead:
    auth.require_organization_access(db, current_user, payload.organization_id)
    try:
        return jobs_service.create_job(db, data=payload.model_dump())
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: uuid.UUID, db: SessionDep, organization_id: OrgQuery) -> JobRead:
    job = jobs_service.get_job(db, organization_id=organization_id, job_id=job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return job


@router.get("/{job_id}/report-readiness", response_model=ReportReadinessResponse)
def get_job_report_readiness(
    job_id: uuid.UUID,
    db: SessionDep,
    organization_id: OrgQuery,
) -> ReportReadinessResponse:
    try:
        return report_readiness_service.get_report_readiness(
            db,
            organization_id=organization_id,
            job_id=job_id,
        )
    except CRMNotFoundError as error:
        _raise_http_error(error)


@router.patch("/{job_id}", response_model=JobRead)
def update_job(
    job_id: uuid.UUID,
    payload: JobUpdate,
    db: SessionDep,
    organization_id: OrgQuery,
) -> JobRead:
    try:
        return jobs_service.update_job(
            db,
            organization_id=organization_id,
            job_id=job_id,
            data=payload.model_dump(exclude_unset=True),
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.delete("/{job_id}", response_model=JobRead)
def archive_job(job_id: uuid.UUID, db: SessionDep, organization_id: OrgQuery) -> JobRead:
    try:
        return jobs_service.archive_job(db, organization_id=organization_id, job_id=job_id)
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
