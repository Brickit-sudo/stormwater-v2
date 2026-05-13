from __future__ import annotations

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import OutlookDraftFromAiDraftRequest, OutlookDraftFromAiDraftResponse
from app.services import outlook_drafts_service
from app.services.common import CRMNotFoundError, CRMValidationError


router = APIRouter(prefix="/v1/outlook/drafts", tags=["outlook-drafts"])
SessionDep = Annotated[Session, Depends(get_db)]


def _raise_http_error(error: Exception) -> None:
    if isinstance(error, CRMNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if isinstance(error, CRMValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    if isinstance(error, httpx.HTTPStatusError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Microsoft Graph draft request failed: {error.response.status_code} {error.response.reason_phrase}.",
        ) from error
    if isinstance(error, httpx.HTTPError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Microsoft Graph draft request failed before a response was received.",
        ) from error
    raise error


@router.post("/from-ai-draft", response_model=OutlookDraftFromAiDraftResponse)
def create_outlook_draft_from_ai_draft(
    payload: OutlookDraftFromAiDraftRequest,
    db: SessionDep,
) -> OutlookDraftFromAiDraftResponse:
    try:
        return outlook_drafts_service.create_outlook_draft_from_ai_draft(db, payload=payload)
    except (CRMNotFoundError, CRMValidationError, httpx.HTTPError) as error:
        _raise_http_error(error)
