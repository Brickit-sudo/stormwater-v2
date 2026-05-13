from __future__ import annotations

import uuid
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    OutlookAuthCallbackResponse,
    OutlookAuthStartResponse,
    OutlookAuthStatusResponse,
    OutlookDisconnectRequest,
    OutlookDisconnectResponse,
)
from app.services import outlook_auth_service
from app.services.common import CRMNotFoundError, CRMValidationError


router = APIRouter(prefix="/v1/outlook/auth", tags=["outlook-auth"])
SessionDep = Annotated[Session, Depends(get_db)]
OrgQuery = Annotated[
    uuid.UUID,
    Query(description="Temporary organization scope until auth is added."),
]


def _raise_http_error(error: Exception) -> None:
    if isinstance(error, CRMNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if isinstance(error, CRMValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    if isinstance(error, httpx.HTTPStatusError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Microsoft OAuth request failed: {error.response.status_code} {error.response.reason_phrase}.",
        ) from error
    if isinstance(error, httpx.HTTPError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Microsoft OAuth request failed before a response was received.",
        ) from error
    raise error


@router.get("/status", response_model=OutlookAuthStatusResponse)
def get_outlook_auth_status(
    db: SessionDep,
    organization_id: OrgQuery,
) -> OutlookAuthStatusResponse:
    try:
        return outlook_auth_service.get_outlook_connection_status(db, organization_id=organization_id)
    except (CRMNotFoundError, CRMValidationError, httpx.HTTPError) as error:
        _raise_http_error(error)


@router.get("/start", response_model=OutlookAuthStartResponse)
def start_outlook_auth(
    db: SessionDep,
    organization_id: OrgQuery,
) -> OutlookAuthStartResponse:
    try:
        return outlook_auth_service.start_authorization(db, organization_id=organization_id)
    except (CRMNotFoundError, CRMValidationError, httpx.HTTPError) as error:
        _raise_http_error(error)


@router.get("/callback", response_model=OutlookAuthCallbackResponse)
def handle_outlook_auth_callback(
    db: SessionDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> OutlookAuthCallbackResponse:
    try:
        if error:
            detail = error_description or error
            raise CRMValidationError(f"Microsoft OAuth returned an error: {detail}")
        if not code or not state:
            raise CRMValidationError("Microsoft OAuth callback requires code and state.")
        return outlook_auth_service.exchange_code_for_tokens(db, code=code, state=state)
    except (CRMNotFoundError, CRMValidationError, httpx.HTTPError) as caught:
        _raise_http_error(caught)


@router.post("/disconnect", response_model=OutlookDisconnectResponse)
def disconnect_outlook(
    payload: OutlookDisconnectRequest,
    db: SessionDep,
) -> OutlookDisconnectResponse:
    try:
        return outlook_auth_service.disconnect_connection(db, organization_id=payload.organization_id)
    except (CRMNotFoundError, CRMValidationError, httpx.HTTPError) as error:
        _raise_http_error(error)
