from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import OutlookConnection
from app.schemas.outlook_auth import (
    OutlookAuthCallbackResponse,
    OutlookAuthStartResponse,
    OutlookAuthStatusResponse,
    OutlookDisconnectResponse,
)
from app.services import outlook_import_service, token_storage_service
from app.services.common import CRMValidationError
from app.services.email_messages_service import require_organization


OUTLOOK_PROVIDER = "outlook"
MINIMAL_SCOPES = ("offline_access", "User.Read", "Mail.ReadWrite")
STATE_TTL_SECONDS = 15 * 60
TOKEN_REFRESH_SKEW_SECONDS = 60
AUTHORITY_BASE_URL = "https://login.microsoftonline.com"
CONNECTED_STATUSES = {"connected", "expired", "error"}


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _require_configured(settings: Settings | None = None) -> Settings:
    current = settings or get_settings()
    status = outlook_import_service.get_outlook_config_status(current)
    if not status.configured:
        missing = ", ".join(status.missing_fields)
        raise CRMValidationError(f"Outlook OAuth is not configured. Missing: {missing}.")
    return current


def _oauth_base(settings: Settings) -> str:
    tenant_id = settings.microsoft_tenant_id or "common"
    return f"{AUTHORITY_BASE_URL}/{tenant_id}/oauth2/v2.0"


def _state_secret(settings: Settings) -> bytes:
    candidate = (
        _normalize_optional(getattr(settings, "token_encryption_key", None))
        or _normalize_optional(settings.microsoft_client_secret)
        or _normalize_optional(settings.microsoft_client_id)
    )
    if candidate is None:
        raise CRMValidationError("Outlook OAuth state signing is not configured.")
    return candidate.encode("utf-8")


def _b64_json(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64_decode(value: str) -> bytes:
    padded = value + ("=" * (-len(value) % 4))
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def build_oauth_state(organization_id: uuid.UUID, settings: Settings | None = None) -> str:
    current = _require_configured(settings)
    payload = {
        "organization_id": str(organization_id),
        "nonce": secrets.token_urlsafe(18),
        "iat": int(time.time()),
        "exp": int(time.time()) + STATE_TTL_SECONDS,
    }
    encoded = _b64_json(payload)
    signature = hmac.new(_state_secret(current), encoded.encode("ascii"), hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return f"{encoded}.{encoded_signature}"


def validate_oauth_state(state: str, settings: Settings | None = None) -> uuid.UUID:
    current = _require_configured(settings)
    try:
        encoded, encoded_signature = state.split(".", 1)
    except ValueError as exc:
        raise CRMValidationError("Outlook OAuth state is invalid.") from exc

    expected = hmac.new(_state_secret(current), encoded.encode("ascii"), hashlib.sha256).digest()
    actual = _b64_decode(encoded_signature)
    if not hmac.compare_digest(expected, actual):
        raise CRMValidationError("Outlook OAuth state could not be verified.")

    try:
        payload = json.loads(_b64_decode(encoded))
        expires_at = int(payload["exp"])
        organization_id = uuid.UUID(str(payload["organization_id"]))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise CRMValidationError("Outlook OAuth state payload is invalid.") from exc

    if expires_at < int(time.time()):
        raise CRMValidationError("Outlook OAuth state has expired. Start the connection again.")
    return organization_id


def build_authorization_url(
    *,
    organization_id: uuid.UUID,
    state: str | None = None,
    settings: Settings | None = None,
) -> tuple[str, str]:
    current = _require_configured(settings)
    oauth_state = state or build_oauth_state(organization_id, current)
    query = urlencode(
        {
            "client_id": current.microsoft_client_id,
            "response_type": "code",
            "redirect_uri": current.microsoft_redirect_uri,
            "response_mode": "query",
            "scope": " ".join(MINIMAL_SCOPES),
            "state": oauth_state,
        },
    )
    return f"{_oauth_base(current)}/authorize?{query}", oauth_state


def start_authorization(
    db: Session,
    *,
    organization_id: uuid.UUID,
    settings: Settings | None = None,
) -> OutlookAuthStartResponse:
    require_organization(db, organization_id)
    current = _require_configured(settings)
    auth_url, state = build_authorization_url(organization_id=organization_id, settings=current)
    return OutlookAuthStartResponse(
        configured=True,
        auth_url=auth_url,
        state=state,
        message="Open the Microsoft authorization URL to connect Outlook.",
    )


def _token_endpoint(settings: Settings) -> str:
    return f"{_oauth_base(settings)}/token"


def _post_token_request(settings: Settings, data: dict[str, str]) -> dict[str, Any]:
    with httpx.Client(timeout=15.0) as client:
        response = client.post(
            _token_endpoint(settings),
            data=data,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        body = response.json()
    if not isinstance(body, dict):
        raise CRMValidationError("Microsoft token response was not an object.")
    return body


def _fetch_user_profile(settings: Settings, access_token: str) -> dict[str, Any]:
    base_url = settings.microsoft_graph_base_url.rstrip("/")
    with httpx.Client(timeout=15.0) as client:
        response = client.get(
            f"{base_url}/me",
            params={"$select": "displayName,mail,userPrincipalName,id"},
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )
        response.raise_for_status()
        body = response.json()
    return body if isinstance(body, dict) else {}


def _expires_at(token_body: dict[str, Any]) -> datetime | None:
    raw = token_body.get("expires_in")
    try:
        seconds = int(raw)
    except (TypeError, ValueError):
        return None
    return _now() + timedelta(seconds=max(1, seconds))


def _scopes_from_token(token_body: dict[str, Any]) -> list[str]:
    raw = token_body.get("scope")
    if isinstance(raw, str) and raw.strip():
        return [scope for scope in raw.split() if scope]
    return list(MINIMAL_SCOPES)


def _email_from_profile(profile: dict[str, Any]) -> str | None:
    for key in ("mail", "userPrincipalName"):
        value = profile.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _display_name_from_profile(profile: dict[str, Any]) -> str | None:
    value = profile.get("displayName")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _latest_connection(db: Session, organization_id: uuid.UUID) -> OutlookConnection | None:
    statement = (
        select(OutlookConnection)
        .where(
            OutlookConnection.organization_id == organization_id,
            OutlookConnection.provider == OUTLOOK_PROVIDER,
            OutlookConnection.archived_at.is_(None),
            OutlookConnection.status.in_(CONNECTED_STATUSES),
        )
        .order_by(OutlookConnection.connected_at.desc(), OutlookConnection.created_at.desc())
    )
    return db.scalar(statement)


def get_latest_connection(
    db: Session,
    *,
    organization_id: uuid.UUID,
) -> OutlookConnection | None:
    return _latest_connection(db, organization_id)


def _mark_superseded_connections(
    db: Session,
    organization_id: uuid.UUID,
    settings: Settings | None = None,
) -> None:
    statement = select(OutlookConnection).where(
        OutlookConnection.organization_id == organization_id,
        OutlookConnection.provider == OUTLOOK_PROVIDER,
        OutlookConnection.archived_at.is_(None),
    )
    current_time = _now()
    for connection in db.scalars(statement).all():
        connection.status = "disconnected"
        connection.archived_at = current_time
        connection.access_token_encrypted = token_storage_service.protect_token("", settings)
        connection.refresh_token_encrypted = None
        db.add(connection)


def store_connection(
    db: Session,
    *,
    organization_id: uuid.UUID,
    token_body: dict[str, Any],
    profile: dict[str, Any],
    settings: Settings | None = None,
) -> OutlookConnection:
    current = settings or get_settings()
    access_token = token_body.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        raise CRMValidationError("Microsoft token response did not include an access token.")

    refresh_token = token_body.get("refresh_token")
    normalized_refresh_token = refresh_token.strip() if isinstance(refresh_token, str) and refresh_token.strip() else None
    current_time = _now()
    _mark_superseded_connections(db, organization_id, current)
    connection = OutlookConnection(
        organization_id=organization_id,
        provider=OUTLOOK_PROVIDER,
        email_address=_email_from_profile(profile),
        display_name=_display_name_from_profile(profile),
        tenant_id=_normalize_optional(current.microsoft_tenant_id),
        scopes_json=_scopes_from_token(token_body),
        access_token_encrypted=token_storage_service.protect_token(access_token.strip(), current),
        refresh_token_encrypted=(
            token_storage_service.protect_token(normalized_refresh_token, current)
            if normalized_refresh_token
            else None
        ),
        expires_at=_expires_at(token_body),
        status="connected",
        connected_at=current_time,
        last_used_at=None,
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)
    return connection


def exchange_code_for_tokens(
    db: Session,
    *,
    code: str,
    state: str,
    settings: Settings | None = None,
) -> OutlookAuthCallbackResponse:
    current = _require_configured(settings)
    organization_id = validate_oauth_state(state, current)
    require_organization(db, organization_id)
    token_body = _post_token_request(
        current,
        {
            "client_id": current.microsoft_client_id or "",
            "client_secret": current.microsoft_client_secret or "",
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": current.microsoft_redirect_uri or "",
            "scope": " ".join(MINIMAL_SCOPES),
        },
    )
    access_token = token_body.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        raise CRMValidationError("Microsoft token response did not include an access token.")
    profile = _fetch_user_profile(current, access_token.strip())
    connection = store_connection(
        db,
        organization_id=organization_id,
        token_body=token_body,
        profile=profile,
        settings=current,
    )
    return OutlookAuthCallbackResponse(
        connected=True,
        connection_status=connection.status,
        email_address=connection.email_address,
        display_name=connection.display_name,
        message="Outlook is connected. Return to Work Hub to preview messages.",
    )


def _connection_is_expired(connection: OutlookConnection) -> bool:
    expires_at = _aware(connection.expires_at)
    return expires_at is not None and expires_at <= _now() + timedelta(seconds=TOKEN_REFRESH_SKEW_SECONDS)


def _status_message(configured: bool, connection: OutlookConnection | None, connection_status: str) -> str:
    if not configured:
        return "Microsoft Graph is not configured. Set the missing MICROSOFT_* env vars before connecting Outlook."
    if connection is None:
        return "Microsoft Graph is configured. Connect Outlook before previewing mail without a request token."
    if connection_status == "expired":
        return "Outlook is connected but the access token is expired. Preview will refresh it if possible."
    if connection_status == "error":
        return "Outlook connection needs attention. Disconnect and reconnect if preview fails."
    return "Outlook is connected. Preview/import actions still require explicit clicks."


def get_outlook_connection_status(
    db: Session,
    *,
    organization_id: uuid.UUID,
    settings: Settings | None = None,
) -> OutlookAuthStatusResponse:
    require_organization(db, organization_id)
    current = settings or get_settings()
    config_status = outlook_import_service.get_outlook_config_status(current)
    connection = _latest_connection(db, organization_id)
    connection_status = "disconnected"
    if connection is not None:
        connection_status = connection.status
        if connection.status == "connected" and _connection_is_expired(connection):
            connection_status = "expired"
            connection.status = "expired"
            db.add(connection)
            db.commit()
            db.refresh(connection)

    return OutlookAuthStatusResponse(
        configured=config_status.configured,
        configured_fields=config_status.configured_fields,
        missing_fields=config_status.missing_fields,
        graph_base_url=config_status.graph_base_url,
        connection_status=connection_status,
        connected=connection_status == "connected",
        email_address=connection.email_address if connection else None,
        display_name=connection.display_name if connection else None,
        scopes=connection.scopes_json or [] if connection else [],
        expires_at=connection.expires_at if connection else None,
        connected_at=connection.connected_at if connection else None,
        last_used_at=connection.last_used_at if connection else None,
        token_storage_mode=token_storage_service.token_storage_mode(current),
        message=_status_message(config_status.configured, connection, connection_status),
    )


def refresh_access_token(
    db: Session,
    *,
    connection: OutlookConnection,
    settings: Settings | None = None,
) -> str:
    current = _require_configured(settings)
    if not connection.refresh_token_encrypted:
        connection.status = "expired"
        db.add(connection)
        db.commit()
        raise CRMValidationError("Outlook connection expired. Reconnect Outlook.")

    refresh_token = token_storage_service.unprotect_token(connection.refresh_token_encrypted, current)
    token_body = _post_token_request(
        current,
        {
            "client_id": current.microsoft_client_id or "",
            "client_secret": current.microsoft_client_secret or "",
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "redirect_uri": current.microsoft_redirect_uri or "",
            "scope": " ".join(MINIMAL_SCOPES),
        },
    )
    access_token = token_body.get("access_token")
    if not isinstance(access_token, str) or not access_token.strip():
        connection.status = "error"
        db.add(connection)
        db.commit()
        raise CRMValidationError("Microsoft refresh response did not include an access token.")

    new_refresh_token = token_body.get("refresh_token")
    connection.access_token_encrypted = token_storage_service.protect_token(access_token.strip(), current)
    if isinstance(new_refresh_token, str) and new_refresh_token.strip():
        connection.refresh_token_encrypted = token_storage_service.protect_token(new_refresh_token.strip(), current)
    connection.expires_at = _expires_at(token_body)
    connection.scopes_json = _scopes_from_token(token_body)
    connection.status = "connected"
    connection.last_used_at = _now()
    db.add(connection)
    db.commit()
    db.refresh(connection)
    return access_token.strip()


def get_valid_access_token(
    db: Session,
    *,
    organization_id: uuid.UUID,
    settings: Settings | None = None,
) -> str:
    require_organization(db, organization_id)
    current = _require_configured(settings)
    connection = _latest_connection(db, organization_id)
    if connection is None:
        raise CRMValidationError("Connect Outlook first.")
    if connection.status == "disconnected":
        raise CRMValidationError("Connect Outlook first.")
    if connection.status == "error":
        raise CRMValidationError("Outlook connection is in an error state. Disconnect and reconnect Outlook.")

    if connection.status == "expired" or _connection_is_expired(connection):
        return refresh_access_token(db, connection=connection, settings=current)

    connection.last_used_at = _now()
    db.add(connection)
    db.commit()
    return token_storage_service.unprotect_token(connection.access_token_encrypted, current)


def disconnect_connection(
    db: Session,
    *,
    organization_id: uuid.UUID,
    settings: Settings | None = None,
) -> OutlookDisconnectResponse:
    require_organization(db, organization_id)
    connection = _latest_connection(db, organization_id)
    if connection is None:
        return OutlookDisconnectResponse(
            disconnected=True,
            connection_status="disconnected",
            message="Outlook is already disconnected.",
        )

    current = settings or get_settings()
    connection.status = "disconnected"
    connection.archived_at = _now()
    connection.access_token_encrypted = token_storage_service.protect_token("", current)
    connection.refresh_token_encrypted = None
    db.add(connection)
    db.commit()
    return OutlookDisconnectResponse(
        disconnected=True,
        connection_status="disconnected",
        message="Outlook disconnected. Stored token values were cleared from the active connection.",
    )
