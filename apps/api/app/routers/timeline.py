from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import TimelineListResponse
from app.services import timeline_service
from app.services.common import CRMNotFoundError, CRMValidationError


router = APIRouter(prefix="/v1/timeline", tags=["timeline"])
SessionDep = Annotated[Session, Depends(get_db)]
OrgQuery = Annotated[
    uuid.UUID,
    Query(description="Temporary organization scope until auth is added."),
]
LimitQuery = Annotated[int, Query(ge=1, le=timeline_service.MAX_LIMIT)]


def _raise_http_error(error: Exception) -> None:
    if isinstance(error, CRMNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if isinstance(error, CRMValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    raise error


@router.get("", response_model=TimelineListResponse)
def list_timeline(
    db: SessionDep,
    organization_id: OrgQuery,
    client_id: uuid.UUID | None = None,
    site_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    limit: LimitQuery = timeline_service.DEFAULT_LIMIT,
) -> TimelineListResponse:
    try:
        return timeline_service.list_timeline(
            db,
            organization_id=organization_id,
            client_id=client_id,
            site_id=site_id,
            job_id=job_id,
            limit=limit,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
