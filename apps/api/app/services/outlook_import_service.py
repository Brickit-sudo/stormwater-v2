from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import EmailImportBatch, EmailMessage
from app.schemas.outlook_import import (
    OutlookImportSelectedRequest,
    OutlookImportSelectedResponse,
    OutlookPreviewMessage,
    OutlookPreviewRequest,
    OutlookPreviewResponse,
    OutlookStatusResponse,
)
from app.services.email_messages_service import require_organization
from app.services.common import CRMValidationError


OUTLOOK_PROVIDER = "outlook"
IMPORT_MODE = "outlook_preview_selected"
MAX_OUTLOOK_LIMIT = 100
_REQUIRED_CONFIG_FIELDS = (
    "MICROSOFT_TENANT_ID",
    "MICROSOFT_CLIENT_ID",
    "MICROSOFT_CLIENT_SECRET",
    "MICROSOFT_REDIRECT_URI",
)


@dataclass(frozen=True)
class OutlookIdentitySets:
    provider_message_ids: set[str]
    internet_message_ids: set[str]


def _setting_by_env_name(settings: Settings, env_name: str) -> str | None:
    field_name = env_name.removeprefix("MICROSOFT_").lower()
    return getattr(settings, f"microsoft_{field_name}", None)


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _cap_limit(limit: int) -> tuple[int, bool]:
    if limit > MAX_OUTLOOK_LIMIT:
        return MAX_OUTLOOK_LIMIT, True
    return max(1, limit), False


def _now() -> datetime:
    return datetime.now(UTC)


def get_outlook_config_status(settings: Settings | None = None) -> OutlookStatusResponse:
    current = settings or get_settings()
    missing = [
        env_name
        for env_name in _REQUIRED_CONFIG_FIELDS
        if not _normalize_optional(_setting_by_env_name(current, env_name))
    ]
    configured = len(missing) == 0
    return OutlookStatusResponse(
        configured=configured,
        configured_fields=[env_name for env_name in _REQUIRED_CONFIG_FIELDS if env_name not in missing],
        missing_fields=missing,
        graph_base_url=current.microsoft_graph_base_url.rstrip("/"),
        message=(
            "Microsoft Graph environment is configured. Use stored Outlook OAuth or a request access token for preview."
            if configured
            else "Microsoft Graph is not configured. Set the missing MICROSOFT_* env vars before previewing Outlook mail."
        ),
    )


def _require_configured(settings: Settings | None = None) -> Settings:
    current = settings or get_settings()
    status = get_outlook_config_status(current)
    if not status.configured:
        missing = ", ".join(status.missing_fields)
        raise CRMValidationError(f"Outlook import is not configured. Missing: {missing}.")
    return current


def build_authorization_url(
    *,
    state: str,
    settings: Settings | None = None,
    scopes: tuple[str, ...] = ("User.Read", "Mail.Read", "offline_access"),
) -> str:
    current = _require_configured(settings)
    tenant_id = current.microsoft_tenant_id or "common"
    query = urlencode(
        {
            "client_id": current.microsoft_client_id,
            "response_type": "code",
            "redirect_uri": current.microsoft_redirect_uri,
            "response_mode": "query",
            "scope": " ".join(scopes),
            "state": state,
        },
    )
    return f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize?{query}"


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    candidate = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        return None


def _email_address_text(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    email_address = value.get("emailAddress")
    if not isinstance(email_address, dict):
        return ""
    address = email_address.get("address")
    name = email_address.get("name")
    if isinstance(address, str) and address.strip():
        return address.strip()
    if isinstance(name, str) and name.strip():
        return name.strip()
    return ""


def _recipients_from_graph(message: dict[str, Any]) -> list[dict[str, str]]:
    recipients: list[dict[str, str]] = []
    for field_name, recipient_type in (("toRecipients", "to"), ("ccRecipients", "cc")):
        values = message.get(field_name)
        if not isinstance(values, list):
            continue
        for item in values:
            if not isinstance(item, dict):
                continue
            email_address = item.get("emailAddress")
            if not isinstance(email_address, dict):
                continue
            name = email_address.get("name")
            address = email_address.get("address")
            normalized = {
                "type": recipient_type,
                "name": name.strip() if isinstance(name, str) else "",
                "email": address.strip() if isinstance(address, str) else "",
            }
            if normalized["name"] or normalized["email"]:
                recipients.append(normalized)
    return recipients


def normalize_graph_message(message: dict[str, Any]) -> OutlookPreviewMessage:
    provider_message_id = _normalize_optional(message.get("id") if isinstance(message.get("id"), str) else None)
    if provider_message_id is None:
        raise CRMValidationError("Outlook message is missing id.")

    sender = _email_address_text(message.get("from")) or "unknown-sender"
    subject = _normalize_optional(message.get("subject") if isinstance(message.get("subject"), str) else None)
    body_preview = _normalize_optional(
        message.get("bodyPreview") if isinstance(message.get("bodyPreview"), str) else None,
    )
    snippet = body_preview

    return OutlookPreviewMessage(
        provider_message_id=provider_message_id,
        provider_conversation_id=_normalize_optional(
            message.get("conversationId") if isinstance(message.get("conversationId"), str) else None,
        ),
        internet_message_id=_normalize_optional(
            message.get("internetMessageId") if isinstance(message.get("internetMessageId"), str) else None,
        ),
        subject=subject or "(no subject)",
        sender=sender,
        recipients=_recipients_from_graph(message),
        received_at=_parse_datetime(message.get("receivedDateTime")),
        snippet=snippet,
        body_preview=body_preview,
        body_text=body_preview or "",
        has_attachments=bool(message.get("hasAttachments")),
        web_link=_normalize_optional(message.get("webLink") if isinstance(message.get("webLink"), str) else None),
    )


def _date_filter(payload: OutlookPreviewRequest) -> str | None:
    filters: list[str] = []
    if payload.date_from is not None:
        filters.append(f"receivedDateTime ge {payload.date_from.astimezone(UTC).isoformat().replace('+00:00', 'Z')}")
    if payload.date_to is not None:
        filters.append(f"receivedDateTime le {payload.date_to.astimezone(UTC).isoformat().replace('+00:00', 'Z')}")
    return " and ".join(filters) if filters else None


def _preview_graph_path(folder_id: str | None) -> str:
    if folder_id:
        safe_folder_id = folder_id.strip().strip("/")
        return f"/me/mailFolders/{safe_folder_id}/messages"
    return "/me/messages"


def _graph_get_messages(
    *,
    settings: Settings,
    access_token: str,
    payload: OutlookPreviewRequest,
    limit: int,
) -> list[dict[str, Any]]:
    base_url = settings.microsoft_graph_base_url.rstrip("/")
    params: dict[str, str | int] = {
        "$top": limit,
        "$select": (
            "id,conversationId,internetMessageId,subject,from,toRecipients,ccRecipients,"
            "receivedDateTime,bodyPreview,hasAttachments,webLink"
        ),
        "$orderby": "receivedDateTime desc",
    }
    search_query = _normalize_optional(payload.search_query)
    if search_query:
        params["$search"] = f'"{search_query.replace(chr(34), "").strip()}"'

    date_filter = _date_filter(payload)
    if date_filter:
        params["$filter"] = date_filter

    with httpx.Client(timeout=15.0) as client:
        response = client.get(
            f"{base_url}{_preview_graph_path(payload.folder_id)}",
            params=params,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "ConsistencyLevel": "eventual",
            },
        )
        response.raise_for_status()
        body = response.json()

    value = body.get("value") if isinstance(body, dict) else None
    if not isinstance(value, list):
        raise CRMValidationError("Microsoft Graph response did not include a message list.")
    return [item for item in value if isinstance(item, dict)]


def _resolve_access_token(
    db: Session | None,
    *,
    organization_id: uuid.UUID,
    request_access_token: str | None,
    settings: Settings | None = None,
) -> str:
    access_token = _normalize_optional(request_access_token)
    if access_token is not None:
        return access_token

    if db is None:
        raise CRMValidationError("Connect Outlook first.")

    from app.services import outlook_auth_service

    return outlook_auth_service.get_valid_access_token(
        db,
        organization_id=organization_id,
        settings=settings,
    )


def preview_outlook_messages(
    payload: OutlookPreviewRequest,
    *,
    db: Session | None = None,
) -> OutlookPreviewResponse:
    settings = _require_configured()
    access_token = _resolve_access_token(
        db,
        organization_id=payload.organization_id,
        request_access_token=payload.access_token,
        settings=settings,
    )

    limit, capped = _cap_limit(payload.limit)
    raw_messages = _graph_get_messages(
        settings=settings,
        access_token=access_token,
        payload=payload,
        limit=limit,
    )
    items = [normalize_graph_message(message) for message in raw_messages[:limit]]
    return OutlookPreviewResponse(items=items, count=len(items), limit=limit, capped=capped)


def dedupe_existing_messages(
    db: Session,
    *,
    organization_id: uuid.UUID,
    messages: list[OutlookPreviewMessage],
) -> OutlookIdentitySets:
    provider_ids = {
        message.provider_message_id.strip()
        for message in messages
        if message.provider_message_id and message.provider_message_id.strip()
    }
    internet_ids = {
        message.internet_message_id.strip()
        for message in messages
        if message.internet_message_id and message.internet_message_id.strip()
    }

    if not provider_ids and not internet_ids:
        return OutlookIdentitySets(provider_message_ids=set(), internet_message_ids=set())

    filters = []
    if provider_ids:
        filters.append(
            and_(
                EmailMessage.provider == OUTLOOK_PROVIDER,
                EmailMessage.provider_message_id.in_(provider_ids),
            ),
        )
    if internet_ids:
        filters.append(EmailMessage.internet_message_id.in_(internet_ids))

    statement = select(EmailMessage).where(
        EmailMessage.organization_id == organization_id,
        or_(*filters),
    )
    existing = list(db.scalars(statement).all())
    return OutlookIdentitySets(
        provider_message_ids={message.provider_message_id for message in existing if message.provider_message_id},
        internet_message_ids={message.internet_message_id for message in existing if message.internet_message_id},
    )


def _message_to_email_row(
    *,
    organization_id: uuid.UUID,
    import_batch_id: uuid.UUID,
    message: OutlookPreviewMessage,
) -> EmailMessage:
    attachment_metadata: list[dict[str, Any]] = []
    if message.has_attachments:
        attachment_metadata.append(
            {
                "provider": OUTLOOK_PROVIDER,
                "has_attachments": True,
                "downloaded": False,
            },
        )

    return EmailMessage(
        organization_id=organization_id,
        import_batch_id=import_batch_id,
        provider=OUTLOOK_PROVIDER,
        provider_message_id=message.provider_message_id,
        provider_conversation_id=message.provider_conversation_id,
        internet_message_id=message.internet_message_id,
        subject=message.subject.strip() or "(no subject)",
        sender=message.sender.strip() or "unknown-sender",
        recipients_json=message.recipients,
        received_at=message.received_at,
        snippet=message.snippet or message.body_preview,
        body_text=message.body_text or message.body_preview or "",
        body_html=None,
        attachments_json=attachment_metadata,
        links_json=[],
        web_link=message.web_link,
        status="unlinked",
    )


def _request_summary(payload: OutlookImportSelectedRequest, limit: int, capped: bool) -> dict[str, Any]:
    return {
        "search_query": _normalize_optional(payload.search_query),
        "folder_id": _normalize_optional(payload.folder_id),
        "date_from": payload.date_from.isoformat() if payload.date_from else None,
        "date_to": payload.date_to.isoformat() if payload.date_to else None,
        "requested_limit": payload.limit,
        "effective_limit": limit,
        "capped": capped,
        "selected_count": len(payload.selected_messages),
        "provider": OUTLOOK_PROVIDER,
    }


def import_selected_outlook_messages(
    db: Session,
    *,
    payload: OutlookImportSelectedRequest,
) -> OutlookImportSelectedResponse:
    require_organization(db, payload.organization_id)
    settings = _require_configured()
    _resolve_access_token(
        db,
        organization_id=payload.organization_id,
        request_access_token=payload.access_token,
        settings=settings,
    )

    limit, capped = _cap_limit(payload.limit)
    selected = payload.selected_messages[:limit]
    over_limit_count = max(0, len(payload.selected_messages) - limit)
    existing = dedupe_existing_messages(db, organization_id=payload.organization_id, messages=selected)
    seen_provider_ids: set[str] = set()
    seen_internet_ids: set[str] = set()

    batch = EmailImportBatch(
        organization_id=payload.organization_id,
        provider=OUTLOOK_PROVIDER,
        import_mode=IMPORT_MODE,
        folder_id=_normalize_optional(payload.folder_id),
        search_query=_normalize_optional(payload.search_query),
        date_from=payload.date_from,
        date_to=payload.date_to,
        status="imported",
        preview_count=len(payload.selected_messages),
        imported_count=0,
        skipped_count=0,
        duplicate_count=0,
        error_count=0,
        request_json=_request_summary(payload, limit, capped),
        result_summary_json=None,
        completed_at=_now(),
    )
    db.add(batch)
    db.flush()

    imported_messages: list[EmailMessage] = []
    duplicate_count = 0
    for message in selected:
        provider_id = message.provider_message_id.strip()
        internet_id = message.internet_message_id.strip() if message.internet_message_id else None
        duplicate = provider_id in existing.provider_message_ids or provider_id in seen_provider_ids
        if internet_id:
            duplicate = duplicate or internet_id in existing.internet_message_ids or internet_id in seen_internet_ids

        if duplicate:
            duplicate_count += 1
            continue

        seen_provider_ids.add(provider_id)
        if internet_id:
            seen_internet_ids.add(internet_id)

        email = _message_to_email_row(
            organization_id=payload.organization_id,
            import_batch_id=batch.id,
            message=message,
        )
        db.add(email)
        imported_messages.append(email)

    skipped_count = duplicate_count + over_limit_count
    batch.imported_count = len(imported_messages)
    batch.duplicate_count = duplicate_count
    batch.skipped_count = skipped_count
    batch.error_count = 0
    batch.result_summary_json = {
        "imported_count": batch.imported_count,
        "duplicate_count": duplicate_count,
        "over_limit_count": over_limit_count,
        "skipped_count": skipped_count,
        "attachment_download": False,
    }
    db.add(batch)
    db.commit()
    db.refresh(batch)
    for message in imported_messages:
        db.refresh(message)

    return OutlookImportSelectedResponse(
        batch=batch,
        imported_messages=imported_messages,
        imported_count=batch.imported_count,
        skipped_count=batch.skipped_count,
        duplicate_count=batch.duplicate_count,
        error_count=batch.error_count,
        capped=capped,
    )
