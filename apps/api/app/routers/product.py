from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import auth
from app.db import get_db
from app.schemas import (
    ProductDecisionCreate,
    ProductDecisionListResponse,
    ProductDecisionRead,
    ProductDecisionUpdate,
    ProductIdeaCreate,
    ProductIdeaListResponse,
    ProductIdeaRead,
    ProductIdeaUpdate,
)
from app.services import product_service
from app.services.common import CRMNotFoundError, CRMValidationError


ideas_router = APIRouter(prefix="/v1/product-ideas", tags=["product-roadmap"])
decisions_router = APIRouter(prefix="/v1/product-decisions", tags=["product-roadmap"])
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


@ideas_router.get("", response_model=ProductIdeaListResponse)
def list_product_ideas(
    db: SessionDep,
    organization_id: OrgQuery,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    priority: str | None = None,
    category: str | None = None,
    lane: str | None = None,
    boss_demo_relevant: bool | None = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> ProductIdeaListResponse:
    try:
        page = product_service.list_product_ideas(
            db,
            organization_id=organization_id,
            status=status_filter,
            priority=priority,
            category=category,
            lane=lane,
            boss_demo_relevant=boss_demo_relevant,
            limit=limit,
            offset=offset,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
    return ProductIdeaListResponse(items=page.items, total=page.total, limit=page.limit, offset=page.offset)


@ideas_router.post("", response_model=ProductIdeaRead, status_code=status.HTTP_201_CREATED)
def create_product_idea(
    payload: ProductIdeaCreate,
    db: SessionDep,
    current_user: auth.CurrentUserDep,
) -> ProductIdeaRead:
    auth.require_organization_access(db, current_user, payload.organization_id)
    try:
        return product_service.create_product_idea(db, data=payload.model_dump())
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@ideas_router.get("/{idea_id}", response_model=ProductIdeaRead)
def get_product_idea(
    idea_id: uuid.UUID,
    db: SessionDep,
    organization_id: OrgQuery,
) -> ProductIdeaRead:
    idea = product_service.get_product_idea(
        db,
        organization_id=organization_id,
        idea_id=idea_id,
    )
    if idea is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product idea not found.")
    return idea


@ideas_router.patch("/{idea_id}", response_model=ProductIdeaRead)
def update_product_idea(
    idea_id: uuid.UUID,
    payload: ProductIdeaUpdate,
    db: SessionDep,
    organization_id: OrgQuery,
) -> ProductIdeaRead:
    try:
        return product_service.update_product_idea(
            db,
            organization_id=organization_id,
            idea_id=idea_id,
            data=payload.model_dump(exclude_unset=True),
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@ideas_router.delete("/{idea_id}", response_model=ProductIdeaRead)
def archive_product_idea(
    idea_id: uuid.UUID,
    db: SessionDep,
    organization_id: OrgQuery,
) -> ProductIdeaRead:
    try:
        return product_service.archive_product_idea(
            db,
            organization_id=organization_id,
            idea_id=idea_id,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@decisions_router.get("", response_model=ProductDecisionListResponse)
def list_product_decisions(
    db: SessionDep,
    organization_id: OrgQuery,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    related_idea_id: uuid.UUID | None = None,
    limit: LimitQuery = 50,
    offset: OffsetQuery = 0,
) -> ProductDecisionListResponse:
    try:
        page = product_service.list_product_decisions(
            db,
            organization_id=organization_id,
            status=status_filter,
            related_idea_id=related_idea_id,
            limit=limit,
            offset=offset,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
    return ProductDecisionListResponse(
        items=page.items,
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@decisions_router.post("", response_model=ProductDecisionRead, status_code=status.HTTP_201_CREATED)
def create_product_decision(
    payload: ProductDecisionCreate,
    db: SessionDep,
    current_user: auth.CurrentUserDep,
) -> ProductDecisionRead:
    auth.require_organization_access(db, current_user, payload.organization_id)
    try:
        return product_service.create_product_decision(db, data=payload.model_dump())
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@decisions_router.patch("/{decision_id}", response_model=ProductDecisionRead)
def update_product_decision(
    decision_id: uuid.UUID,
    payload: ProductDecisionUpdate,
    db: SessionDep,
    organization_id: OrgQuery,
) -> ProductDecisionRead:
    try:
        return product_service.update_product_decision(
            db,
            organization_id=organization_id,
            decision_id=decision_id,
            data=payload.model_dump(exclude_unset=True),
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)


@decisions_router.delete("/{decision_id}", response_model=ProductDecisionRead)
def archive_product_decision(
    decision_id: uuid.UUID,
    db: SessionDep,
    organization_id: OrgQuery,
) -> ProductDecisionRead:
    try:
        return product_service.archive_product_decision(
            db,
            organization_id=organization_id,
            decision_id=decision_id,
        )
    except (CRMNotFoundError, CRMValidationError) as error:
        _raise_http_error(error)
