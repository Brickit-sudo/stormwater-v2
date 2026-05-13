from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import auth
from app.db import get_db
from app.schemas.ai_assistant import (
    AiStatusResponse,
    ClientSummaryDraftRequest,
    DraftReplyRequest,
    DraftReplyResponse,
    EmailActionItemsRequest,
    EmailActionItemsResponse,
    EmailSummaryRequest,
    EmailSummaryResponse,
    ExtractFileLinksRequest,
    ExtractFileLinksResponse,
    MaintenanceRecommendationDraftRequest,
    ReportSectionDraftRequest,
    ReportSectionDraftResponse,
    SuggestRecordLinksRequest,
    SuggestRecordLinksResponse,
)
from app.services import ai_assistant_service
from app.services.common import CRMNotFoundError, CRMValidationError


router = APIRouter(prefix="/v1/ai", tags=["ai-assistant"])
SessionDep = Annotated[Session, Depends(get_db)]


def _raise_http_error(error: Exception) -> None:
    if isinstance(error, CRMNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if isinstance(error, CRMValidationError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    if isinstance(error, ai_assistant_service.AiProviderError):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    raise error


@router.get("/status", response_model=AiStatusResponse)
def get_ai_status(current_user: auth.CurrentUserDep) -> AiStatusResponse:
    return ai_assistant_service.get_ai_status()


@router.post("/email-summary", response_model=EmailSummaryResponse)
def summarize_email(
    payload: EmailSummaryRequest,
    db: SessionDep,
    current_user: auth.CurrentUserDep,
) -> EmailSummaryResponse:
    auth.require_organization_access(db, current_user, payload.organization_id)
    try:
        return ai_assistant_service.summarize_email(db, payload)
    except (CRMNotFoundError, CRMValidationError, ai_assistant_service.AiProviderError) as error:
        _raise_http_error(error)


@router.post("/email-action-items", response_model=EmailActionItemsResponse)
def extract_email_action_items(
    payload: EmailActionItemsRequest,
    db: SessionDep,
    current_user: auth.CurrentUserDep,
) -> EmailActionItemsResponse:
    auth.require_organization_access(db, current_user, payload.organization_id)
    try:
        return ai_assistant_service.extract_email_action_items(db, payload)
    except (CRMNotFoundError, CRMValidationError, ai_assistant_service.AiProviderError) as error:
        _raise_http_error(error)


@router.post("/extract-file-links", response_model=ExtractFileLinksResponse)
def extract_file_links(
    payload: ExtractFileLinksRequest,
    db: SessionDep,
    current_user: auth.CurrentUserDep,
) -> ExtractFileLinksResponse:
    auth.require_organization_access(db, current_user, payload.organization_id)
    try:
        return ai_assistant_service.extract_file_links(db, payload)
    except (CRMNotFoundError, CRMValidationError, ai_assistant_service.AiProviderError) as error:
        _raise_http_error(error)


@router.post("/suggest-record-links", response_model=SuggestRecordLinksResponse)
def suggest_record_links(
    payload: SuggestRecordLinksRequest,
    db: SessionDep,
    current_user: auth.CurrentUserDep,
) -> SuggestRecordLinksResponse:
    auth.require_organization_access(db, current_user, payload.organization_id)
    try:
        return ai_assistant_service.suggest_email_record_links(db, payload)
    except (CRMNotFoundError, CRMValidationError, ai_assistant_service.AiProviderError) as error:
        _raise_http_error(error)


@router.post("/draft-reply", response_model=DraftReplyResponse)
def draft_reply(
    payload: DraftReplyRequest,
    db: SessionDep,
    current_user: auth.CurrentUserDep,
) -> DraftReplyResponse:
    auth.require_organization_access(db, current_user, payload.organization_id)
    try:
        return ai_assistant_service.draft_reply(db, payload)
    except (CRMNotFoundError, CRMValidationError, ai_assistant_service.AiProviderError) as error:
        _raise_http_error(error)


@router.post("/report-section-draft", response_model=ReportSectionDraftResponse)
def report_section_draft(
    payload: ReportSectionDraftRequest,
    db: SessionDep,
    current_user: auth.CurrentUserDep,
) -> ReportSectionDraftResponse:
    auth.require_organization_access(db, current_user, payload.organization_id)
    try:
        return ai_assistant_service.report_section_draft(db, payload)
    except (CRMNotFoundError, CRMValidationError, ai_assistant_service.AiProviderError) as error:
        _raise_http_error(error)


@router.post("/maintenance-recommendation-draft", response_model=ReportSectionDraftResponse)
def maintenance_recommendation_draft(
    payload: MaintenanceRecommendationDraftRequest,
    db: SessionDep,
    current_user: auth.CurrentUserDep,
) -> ReportSectionDraftResponse:
    auth.require_organization_access(db, current_user, payload.organization_id)
    try:
        return ai_assistant_service.maintenance_recommendation_draft(db, payload)
    except (CRMNotFoundError, CRMValidationError, ai_assistant_service.AiProviderError) as error:
        _raise_http_error(error)


@router.post("/client-summary-draft", response_model=ReportSectionDraftResponse)
def client_summary_draft(
    payload: ClientSummaryDraftRequest,
    db: SessionDep,
    current_user: auth.CurrentUserDep,
) -> ReportSectionDraftResponse:
    auth.require_organization_access(db, current_user, payload.organization_id)
    try:
        return ai_assistant_service.client_summary_draft(db, payload)
    except (CRMNotFoundError, CRMValidationError, ai_assistant_service.AiProviderError) as error:
        _raise_http_error(error)
