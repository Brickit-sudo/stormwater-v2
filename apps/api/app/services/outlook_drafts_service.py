from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import AiDraft, OutlookConnection
from app.schemas.outlook_draft import (
    OutlookDraftFromAiDraftRequest,
    OutlookDraftFromAiDraftResponse,
)
from app.services import ai_drafts_service, outlook_auth_service
from app.services.common import CRMNotFoundError, CRMValidationError
from app.services.email_messages_service import require_organization


OUTLOOK_PROVIDER = "outlook"
EMAIL_STYLE_DRAFT_TYPES = {"email_reply", "follow_up", "client_email", "client_summary"}
REQUIRED_DRAFT_SCOPE = "Mail.ReadWrite"


def _now() -> datetime:
    return datetime.now(UTC)


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _normalize_required(value: str | None, field_name: str) -> str:
    trimmed = _normalize_optional(value)
    if trimmed is None:
        raise CRMValidationError(f"{field_name} is required.")
    return trimmed


def _normalize_recipients(values: list[str]) -> list[str]:
    recipients = [value.strip() for value in values if value and value.strip()]
    if not recipients:
        raise CRMValidationError("At least one To recipient is required.")
    invalid = [recipient for recipient in recipients if "@" not in recipient or " " in recipient]
    if invalid:
        raise CRMValidationError("To recipients must be email addresses.")
    return recipients


def _require_email_style_draft(draft: AiDraft) -> None:
    draft_type = draft.draft_type.strip()
    if draft_type not in EMAIL_STYLE_DRAFT_TYPES:
        raise CRMValidationError(
            f"AI draft type '{draft_type}' is not email-style. Convert it to client_email before creating an Outlook draft.",
        )


def _require_mail_readwrite_scope(connection: OutlookConnection | None) -> None:
    scopes = {scope.lower() for scope in (connection.scopes_json or [])} if connection else set()
    if REQUIRED_DRAFT_SCOPE.lower() not in scopes:
        raise CRMValidationError(
            "Reconnect Outlook with Microsoft Graph Mail.ReadWrite permission before creating Outlook drafts.",
        )


def _safe_graph_error(error: httpx.HTTPError) -> str:
    if isinstance(error, httpx.HTTPStatusError):
        response = error.response
        return f"Microsoft Graph draft creation failed: {response.status_code} {response.reason_phrase}."
    return "Microsoft Graph draft creation failed before a response was received."


def _graph_create_draft(
    *,
    settings: Settings,
    access_token: str,
    to_recipients: list[str],
    subject: str,
    body_text: str,
) -> dict[str, Any]:
    base_url = settings.microsoft_graph_base_url.rstrip("/")
    payload = {
        "subject": subject,
        "body": {
            "contentType": "Text",
            "content": body_text,
        },
        "toRecipients": [
            {"emailAddress": {"address": recipient}}
            for recipient in to_recipients
        ],
    }

    with httpx.Client(timeout=15.0) as client:
        response = client.post(
            f"{base_url}/me/messages",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        body = response.json()

    if not isinstance(body, dict):
        raise CRMValidationError("Microsoft Graph draft response was not an object.")
    return body


def _mark_provider_error(db: Session, draft: AiDraft, message: str) -> None:
    draft.provider = OUTLOOK_PROVIDER
    draft.provider_status = "error"
    draft.provider_error = message
    db.add(draft)
    db.commit()


def create_outlook_draft_from_ai_draft(
    db: Session,
    *,
    payload: OutlookDraftFromAiDraftRequest,
    settings: Settings | None = None,
) -> OutlookDraftFromAiDraftResponse:
    require_organization(db, payload.organization_id)
    draft = ai_drafts_service.get_ai_draft(
        db,
        organization_id=payload.organization_id,
        draft_id=payload.ai_draft_id,
    )
    if draft is None:
        raise CRMNotFoundError("AI draft not found.")

    _require_email_style_draft(draft)
    subject = _normalize_required(payload.subject, "subject")
    body_text = _normalize_required(
        payload.body_override if payload.body_override is not None else draft.draft_text,
        "draft text",
    )
    to_recipients = _normalize_recipients(payload.to_recipients)

    current = settings or get_settings()
    access_token = outlook_auth_service.get_valid_access_token(
        db,
        organization_id=payload.organization_id,
        settings=current,
    )
    connection = outlook_auth_service.get_latest_connection(db, organization_id=payload.organization_id)
    _require_mail_readwrite_scope(connection)

    try:
        graph_draft = _graph_create_draft(
            settings=current,
            access_token=access_token,
            to_recipients=to_recipients,
            subject=subject,
            body_text=body_text,
        )
    except httpx.HTTPError as error:
        _mark_provider_error(db, draft, _safe_graph_error(error))
        raise

    provider_draft_id = _normalize_required(
        graph_draft.get("id") if isinstance(graph_draft.get("id"), str) else None,
        "Microsoft Graph draft id",
    )
    pushed_at = _now()
    draft.provider = OUTLOOK_PROVIDER
    draft.provider_draft_id = provider_draft_id
    draft.provider_web_link = _normalize_optional(
        graph_draft.get("webLink") if isinstance(graph_draft.get("webLink"), str) else None,
    )
    draft.provider_status = "draft_created"
    draft.pushed_to_provider_at = pushed_at
    draft.provider_error = None
    db.add(draft)
    db.commit()
    db.refresh(draft)

    return OutlookDraftFromAiDraftResponse(
        ai_draft_id=draft.id,
        provider=OUTLOOK_PROVIDER,
        provider_draft_id=provider_draft_id,
        provider_web_link=draft.provider_web_link,
        provider_status=draft.provider_status or "draft_created",
        pushed_to_provider_at=pushed_at,
    )
