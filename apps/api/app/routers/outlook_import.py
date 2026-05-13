from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    OutlookImportSelectedRequest,
    OutlookImportSelectedResponse,
    OutlookPreviewRequest,
    OutlookPreviewResponse,
    OutlookStatusResponse,
)
from app.services import outlook_import_service
from app.services.common import CRMNotFoundError, CRMValidationError
from app.services.email_messages_service import require_organization


router = APIRouter(prefix="/v1/outlook", tags=["outlook-import"])
SessionDep = Annotated[Session, Depends(get_db)]


def _raise_http_error(error: Exception) -> None:
    if isinstance(error, CRMNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if isinstance(error, CRMValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    if isinstance(error, httpx.HTTPStatusError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Microsoft Graph request failed: {error.response.status_code} {error.response.reason_phrase}.",
        ) from error
    if isinstance(error, httpx.HTTPError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Microsoft Graph request failed before a response was received.",
        ) from error
    raise error


@router.get("/status", response_model=OutlookStatusResponse)
def get_outlook_status() -> OutlookStatusResponse:
    return outlook_import_service.get_outlook_config_status()


@router.post("/preview", response_model=OutlookPreviewResponse)
def preview_outlook_messages(
    payload: OutlookPreviewRequest,
    db: SessionDep,
) -> OutlookPreviewResponse:
    try:
        require_organization(db, payload.organization_id)
        return outlook_import_service.preview_outlook_messages(payload, db=db)
    except (CRMNotFoundError, CRMValidationError, httpx.HTTPError) as error:
        _raise_http_error(error)


@router.post("/import-selected", response_model=OutlookImportSelectedResponse)
def import_selected_outlook_messages(
    payload: OutlookImportSelectedRequest,
    db: SessionDep,
) -> OutlookImportSelectedResponse:
    try:
        return outlook_import_service.import_selected_outlook_messages(db, payload=payload)
    except (CRMNotFoundError, CRMValidationError, httpx.HTTPError) as error:
        _raise_http_error(error)
