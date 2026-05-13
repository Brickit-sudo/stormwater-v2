from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import SearchResponse
from app.services import search_service
from app.services.common import CRMValidationError


router = APIRouter(prefix="/v1/search", tags=["search"])
SessionDep = Annotated[Session, Depends(get_db)]
OrgQuery = Annotated[
    uuid.UUID,
    Query(description="Temporary organization scope until auth is added."),
]
SearchQuery = Annotated[str, Query(min_length=2)]
LimitQuery = Annotated[int, Query(ge=1)]


@router.get("", response_model=SearchResponse)
def global_search(
    db: SessionDep,
    organization_id: OrgQuery,
    q: SearchQuery,
    types: str | None = None,
    limit: LimitQuery = search_service.DEFAULT_LIMIT,
) -> SearchResponse:
    try:
        return search_service.search(
            db,
            organization_id=organization_id,
            q=q,
            types=types,
            limit=limit,
        )
    except CRMValidationError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
