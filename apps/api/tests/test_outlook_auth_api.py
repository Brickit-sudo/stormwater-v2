from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from urllib.parse import parse_qs, urlparse
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import OutlookConnection
from app.services import outlook_auth_service, outlook_import_service, token_storage_service


def _settings(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "microsoft_tenant_id": "tenant-id",
        "microsoft_client_id": "client-id",
        "microsoft_client_secret": "client-secret",
        "microsoft_redirect_uri": "http://localhost:8000/v1/outlook/auth/callback",
        "microsoft_graph_base_url": "https://graph.microsoft.com/v1.0",
        "token_encryption_key": None,
        "openai_api_key": None,
        "openai_model": "test-model",
        "ai_features_enabled": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _configure_outlook(monkeypatch: pytest.MonkeyPatch, **overrides: object) -> SimpleNamespace:
    settings = _settings(**overrides)
    monkeypatch.setattr(outlook_auth_service, "get_settings", lambda: settings)
    monkeypatch.setattr(outlook_import_service, "get_settings", lambda: settings)
    return settings


def _graph_message(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "graph-msg-1",
        "conversationId": "conversation-1",
        "internetMessageId": "<graph-msg-1@example.com>",
        "subject": "Access window for Bayside",
        "from": {"emailAddress": {"name": "Mara Whitcomb", "address": "mara.whitcomb@pinetree.example"}},
        "toRecipients": [],
        "ccRecipients": [],
        "receivedDateTime": "2026-05-12T13:30:00Z",
        "bodyPreview": "Can the crew arrive before retail traffic?",
        "hasAttachments": False,
        "webLink": "https://outlook.office.com/mail/id/graph-msg-1",
    }
    payload.update(overrides)
    return payload


def _store_connection(
    db_session: Session,
    organization_id: str,
    settings: SimpleNamespace,
    *,
    access_token: str = "stored-access-token",
    refresh_token: str = "stored-refresh-token",
    expires_in: int = 3600,
) -> OutlookConnection:
    return outlook_auth_service.store_connection(
        db_session,
        organization_id=uuid.UUID(organization_id),
        token_body={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": expires_in,
            "scope": "offline_access User.Read Mail.ReadWrite",
        },
        profile={
            "mail": "mara.whitcomb@pinetree.example",
            "displayName": "Mara Whitcomb",
        },
        settings=settings,  # type: ignore[arg-type]
    )


def test_outlook_auth_status_disconnected_with_no_connection(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    _configure_outlook(monkeypatch)

    response = api_client.get("/v1/outlook/auth/status", params={"organization_id": organization_id})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["configured"] is True
    assert body["connection_status"] == "disconnected"
    assert body["connected"] is False
    assert body["email_address"] is None
    assert "client-secret" not in response.text


def test_outlook_auth_start_returns_auth_url_when_configured(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    _configure_outlook(monkeypatch)

    response = api_client.get("/v1/outlook/auth/start", params={"organization_id": organization_id})

    assert response.status_code == 200, response.text
    body = response.json()
    parsed = urlparse(body["auth_url"])
    query = parse_qs(parsed.query)
    scopes = query["scope"][0].split()
    assert parsed.netloc == "login.microsoftonline.com"
    assert "tenant-id" in parsed.path
    assert query["client_id"] == ["client-id"]
    assert query["redirect_uri"] == ["http://localhost:8000/v1/outlook/auth/callback"]
    assert {"offline_access", "User.Read", "Mail.ReadWrite"} <= set(scopes)
    assert "Mail.Send" not in scopes
    assert body["state"]
    assert "client-secret" not in response.text


def test_outlook_auth_start_reports_missing_config_clearly(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    _configure_outlook(monkeypatch, microsoft_client_secret=None)

    response = api_client.get("/v1/outlook/auth/start", params={"organization_id": organization_id})

    assert response.status_code == 400
    assert "Outlook OAuth is not configured" in response.json()["detail"]
    assert "MICROSOFT_CLIENT_SECRET" in response.json()["detail"]
    assert "client-secret" not in response.text


def test_outlook_auth_callback_exchanges_mocked_token_and_stores_connection(
    api_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    settings = _configure_outlook(monkeypatch)
    start = api_client.get("/v1/outlook/auth/start", params={"organization_id": organization_id})
    state = start.json()["state"]

    def fake_post_token(settings_arg: object, data: dict[str, str]) -> dict[str, Any]:
        assert settings_arg is settings
        assert data["grant_type"] == "authorization_code"
        assert data["code"] == "oauth-code"
        assert "Mail.Send" not in data["scope"].split()
        return {
            "access_token": "callback-access-token",
            "refresh_token": "callback-refresh-token",
            "expires_in": 3600,
            "scope": "offline_access User.Read Mail.ReadWrite",
        }

    monkeypatch.setattr(outlook_auth_service, "_post_token_request", fake_post_token)
    monkeypatch.setattr(
        outlook_auth_service,
        "_fetch_user_profile",
        lambda _settings, _token: {
            "mail": "mara.whitcomb@pinetree.example",
            "displayName": "Mara Whitcomb",
        },
    )

    response = api_client.get(
        "/v1/outlook/auth/callback",
        params={"code": "oauth-code", "state": state},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["connected"] is True
    assert body["email_address"] == "mara.whitcomb@pinetree.example"
    assert "callback-access-token" not in response.text
    assert "callback-refresh-token" not in response.text

    connection = db_session.scalar(select(OutlookConnection))
    assert connection is not None
    assert connection.status == "connected"
    assert connection.email_address == "mara.whitcomb@pinetree.example"
    assert connection.access_token_encrypted != "callback-access-token"
    assert token_storage_service.unprotect_token(connection.access_token_encrypted, settings) == "callback-access-token"
    assert connection.refresh_token_encrypted is not None
    assert token_storage_service.unprotect_token(connection.refresh_token_encrypted, settings) == "callback-refresh-token"


def test_outlook_auth_status_connected_hides_tokens(
    api_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    settings = _configure_outlook(monkeypatch)
    _store_connection(db_session, organization_id, settings)

    response = api_client.get("/v1/outlook/auth/status", params={"organization_id": organization_id})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["connection_status"] == "connected"
    assert body["connected"] is True
    assert body["email_address"] == "mara.whitcomb@pinetree.example"
    assert "stored-access-token" not in response.text
    assert "stored-refresh-token" not in response.text


def test_outlook_auth_disconnect_archives_connection_and_clears_tokens(
    api_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    settings = _configure_outlook(monkeypatch)
    connection = _store_connection(db_session, organization_id, settings)

    response = api_client.post("/v1/outlook/auth/disconnect", json={"organization_id": organization_id})

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["disconnected"] is True
    db_session.refresh(connection)
    assert connection.status == "disconnected"
    assert connection.archived_at is not None
    assert token_storage_service.unprotect_token(connection.access_token_encrypted, settings) == ""
    assert connection.refresh_token_encrypted is None


def test_outlook_preview_uses_stored_token_when_request_token_missing(
    api_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    settings = _configure_outlook(monkeypatch)
    _store_connection(db_session, organization_id, settings, access_token="stored-preview-token")
    seen: dict[str, str] = {}

    def fake_graph_messages(**kwargs: object) -> list[dict[str, object]]:
        seen["access_token"] = str(kwargs["access_token"])
        return [_graph_message()]

    monkeypatch.setattr(outlook_import_service, "_graph_get_messages", fake_graph_messages)

    response = api_client.post(
        "/v1/outlook/preview",
        json={"organization_id": organization_id, "limit": 25},
    )

    assert response.status_code == 200, response.text
    assert seen["access_token"] == "stored-preview-token"
    assert response.json()["count"] == 1


def test_outlook_preview_refreshes_expired_stored_token(
    api_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    settings = _configure_outlook(monkeypatch)
    connection = _store_connection(
        db_session,
        organization_id,
        settings,
        access_token="old-access-token",
        refresh_token="refresh-me",
    )
    connection.status = "expired"
    connection.expires_at = datetime.now(UTC) - timedelta(minutes=5)
    db_session.add(connection)
    db_session.commit()
    seen: dict[str, str] = {}

    def fake_post_token(_settings: object, data: dict[str, str]) -> dict[str, Any]:
        assert data["grant_type"] == "refresh_token"
        assert data["refresh_token"] == "refresh-me"
        assert "Mail.Send" not in data["scope"].split()
        return {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 3600,
            "scope": "offline_access User.Read Mail.ReadWrite",
        }

    def fake_graph_messages(**kwargs: object) -> list[dict[str, object]]:
        seen["access_token"] = str(kwargs["access_token"])
        return [_graph_message()]

    monkeypatch.setattr(outlook_auth_service, "_post_token_request", fake_post_token)
    monkeypatch.setattr(outlook_import_service, "_graph_get_messages", fake_graph_messages)

    response = api_client.post(
        "/v1/outlook/preview",
        json={"organization_id": organization_id, "limit": 25},
    )

    assert response.status_code == 200, response.text
    assert seen["access_token"] == "new-access-token"
    db_session.refresh(connection)
    assert connection.status == "connected"
    assert token_storage_service.unprotect_token(connection.access_token_encrypted, settings) == "new-access-token"
    assert connection.last_used_at is not None
