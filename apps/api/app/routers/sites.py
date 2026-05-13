from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    JobListResponse,
    SiteCreate,
    SiteListResponse,
    SiteMapListResponse,
    SiteRead,
    SiteUpdate,
)
from app.services import sites_service
from app.services.common import CRMNotFoundError, CRMValidationError


router = APIRouter(prefix="/v1/sites", tags=["sites"])
SessionDep = Annotated[Session, Depends(get_db)]
OrgQuery = Annotated[
    uuid.UUID,
    Query(description="Temporary organization scope until auth is added."),
]
LimitQuery = Annotated[int, Query(ge=1, le=500)]
MapLimitQuery = Annotated[int, Query(ge=1, le=5000)]
OffsetQuery = Annotated[int, Query(ge=0)]
LatitudeBoundQuery = Annotated[Decimal | None, Query(ge=Decimal("-90"), le=Decimal("90"))]
LongitudeBoundQuery = Annotated[Decimal | None, Query(ge=Decimal("-180"), le=Decimal("180"))]


def _raise_http_error(error: Exception) -> None:
    if isinstance(error, CRMNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if isinstance(error, CRMValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    raise error


@router.get("", response_model=SiteListResponse)
def list_sites(
    db: SessionDep,
    organization_id: OrgQuery,
    search: str | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    client_id: uuid.UUID | None = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> SiteListResponse:
    page = sites_service.list_sites(
        db,
        organization_id=organization_id,
        search=search,
        status=status_filter,
        client_id=client_id,
        limit=limit,
        offset=offset,
    )
    return SiteListResponse(items=page.items, total=page.total, limit=page.limit, offset=page.offset)


@router.get("/map", response_model=SiteMapListResponse)
def list_site_map(
    db: SessionDep,
    organization_id: OrgQuery,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    client_id: uuid.UUID | None = None,
    north: LatitudeBoundQuery = None,
    south: LatitudeBoundQuery = None,
    east: LongitudeBoundQuery = None,
    west: LongitudeBoundQuery = None,
    limit: MapLimitQuery = sites_service.MAP_DEFAULT_LIMIT,
    offset: OffsetQuery = 0,
) -> SiteMapListResponse:
    page = sites_service.list_map_sites(
        db,
        organization_id=organization_id,
        status=status_filter,
        client_id=client_id,
        north=north,
        south=south,
        east=east,
        west=west,
        limit=limit,
        offset=offset,
    )
    return SiteMapListResponse(items=page.items, total=page.total, limit=page.limit, offset=page.offset)


@router.post("", response_model=SiteRead, status_code=status.HTTP_201_CREATED)
def create_site(payload: SiteCreate, db: SessionDep) -> SiteRead:
    try:
        return sites_service.create_site(db, data=payload.model_dump())
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.get("/{site_id}", response_model=SiteRead)
def get_site(site_id: uuid.UUID, db: SessionDep, organization_id: OrgQuery) -> SiteRead:
    site = sites_service.get_site(db, organization_id=organization_id, site_id=site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found.")
    return site


@router.patch("/{site_id}", response_model=SiteRead)
def update_site(
    site_id: uuid.UUID,
    payload: SiteUpdate,
    db: SessionDep,
    organization_id: OrgQuery,
) -> SiteRead:
    try:
        return sites_service.update_site(
            db,
            organization_id=organization_id,
            site_id=site_id,
            data=payload.model_dump(exclude_unset=True),
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.delete("/{site_id}", response_model=SiteRead)
def archive_site(site_id: uuid.UUID, db: SessionDep, organization_id: OrgQuery) -> SiteRead:
    try:
        return sites_service.archive_site(db, organization_id=organization_id, site_id=site_id)
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.get("/{site_id}/jobs", response_model=JobListResponse)
def list_site_jobs(
    site_id: uuid.UUID,
    db: SessionDep,
    organization_id: OrgQuery,
    search: str | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> JobListResponse:
    try:
        page = sites_service.list_site_jobs(
            db,
            organization_id=organization_id,
            site_id=site_id,
            search=search,
            status=status_filter,
            limit=limit,
            offset=offset,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
    return JobListResponse(items=page.items, total=page.total, limit=page.limit, offset=page.offset)
