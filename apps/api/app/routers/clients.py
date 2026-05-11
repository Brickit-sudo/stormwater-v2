from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    ClientCreate,
    ClientListResponse,
    ClientRead,
    ClientUpdate,
    JobListResponse,
    SiteListResponse,
)
from app.services import clients_service
from app.services.common import CRMNotFoundError, CRMValidationError


router = APIRouter(prefix="/v1/clients", tags=["clients"])
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


@router.get("", response_model=ClientListResponse)
def list_clients(
    db: SessionDep,
    organization_id: OrgQuery,
    search: str | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> ClientListResponse:
    page = clients_service.list_clients(
        db,
        organization_id=organization_id,
        search=search,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return ClientListResponse(items=page.items, total=page.total, limit=page.limit, offset=page.offset)


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
def create_client(payload: ClientCreate, db: SessionDep) -> ClientRead:
    try:
        return clients_service.create_client(db, data=payload.model_dump())
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.get("/{client_id}", response_model=ClientRead)
def get_client(client_id: uuid.UUID, db: SessionDep, organization_id: OrgQuery) -> ClientRead:
    client = clients_service.get_client(db, organization_id=organization_id, client_id=client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found.")
    return client


@router.patch("/{client_id}", response_model=ClientRead)
def update_client(
    client_id: uuid.UUID,
    payload: ClientUpdate,
    db: SessionDep,
    organization_id: OrgQuery,
) -> ClientRead:
    try:
        return clients_service.update_client(
            db,
            organization_id=organization_id,
            client_id=client_id,
            data=payload.model_dump(exclude_unset=True),
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.delete("/{client_id}", response_model=ClientRead)
def archive_client(client_id: uuid.UUID, db: SessionDep, organization_id: OrgQuery) -> ClientRead:
    try:
        return clients_service.archive_client(
            db,
            organization_id=organization_id,
            client_id=client_id,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@router.get("/{client_id}/sites", response_model=SiteListResponse)
def list_client_sites(
    client_id: uuid.UUID,
    db: SessionDep,
    organization_id: OrgQuery,
    search: str | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> SiteListResponse:
    try:
        page = clients_service.list_client_sites(
            db,
            organization_id=organization_id,
            client_id=client_id,
            search=search,
            status=status_filter,
            limit=limit,
            offset=offset,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
    return SiteListResponse(items=page.items, total=page.total, limit=page.limit, offset=page.offset)


@router.get("/{client_id}/jobs", response_model=JobListResponse)
def list_client_jobs(
    client_id: uuid.UUID,
    db: SessionDep,
    organization_id: OrgQuery,
    search: str | None = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> JobListResponse:
    try:
        page = clients_service.list_client_jobs(
            db,
            organization_id=organization_id,
            client_id=client_id,
            search=search,
            status=status_filter,
            limit=limit,
            offset=offset,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
    return JobListResponse(items=page.items, total=page.total, limit=page.limit, offset=page.offset)
