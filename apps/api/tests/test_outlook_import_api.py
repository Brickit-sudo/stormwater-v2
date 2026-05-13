from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.services import outlook_import_service


def _settings(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "microsoft_tenant_id": "tenant-id",
        "microsoft_client_id": "client-id",
        "microsoft_client_secret": "client-secret",
        "microsoft_redirect_uri": "http://localhost:8000/auth/callback",
        "microsoft_graph_base_url": "https://graph.microsoft.com/v1.0",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _configure_outlook(monkeypatch: pytest.MonkeyPatch, **overrides: object) -> None:
    settings = _settings(**overrides)
    monkeypatch.setattr(outlook_import_service, "get_settings", lambda: settings)


def _preview_message(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "provider_message_id": "graph-msg-1",
        "provider_conversation_id": "conversation-1",
        "internet_message_id": "<graph-msg-1@example.com>",
        "subject": "Access window for Bayside",
        "sender": "mara.whitcomb@pinetree.example",
        "recipients": [{"type": "to", "email": "ops@sterling.example", "name": "Ops"}],
        "received_at": "2026-05-12T13:30:00Z",
        "snippet": "Can the crew arrive early?",
        "body_preview": "Can the crew arrive early?",
        "body_text": "Can the crew arrive early?",
        "has_attachments": False,
        "web_link": "https://outlook.office.com/mail/id/graph-msg-1",
    }
    payload.update(overrides)
    return payload


def _graph_message(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "graph-msg-1",
        "conversationId": "conversation-1",
        "internetMessageId": "<graph-msg-1@example.com>",
        "subject": "Access window for Bayside",
        "from": {"emailAddress": {"name": "Mara Whitcomb", "address": "mara.whitcomb@pinetree.example"}},
        "toRecipients": [{"emailAddress": {"name": "Ops", "address": "ops@sterling.example"}}],
        "ccRecipients": [],
        "receivedDateTime": "2026-05-12T13:30:00Z",
        "bodyPreview": "Can the crew arrive before retail traffic?",
        "hasAttachments": False,
        "webLink": "https://outlook.office.com/mail/id/graph-msg-1",
    }
    payload.update(overrides)
    return payload


def _create_email(
    api_client: TestClient,
    organization_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "organization_id": organization_id,
        "provider": "outlook",
        "provider_message_id": "existing-provider-id",
        "internet_message_id": "<existing@example.com>",
        "subject": "Existing local email",
        "sender": "existing@example.com",
        "recipients_json": [],
        "received_at": "2026-05-10T13:30:00Z",
        "snippet": "Already imported.",
        "body_text": "Already imported.",
    }
    payload.update(overrides)
    response = api_client.post("/v1/email-messages", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_outlook_status_reports_missing_config_without_secrets(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_outlook(
        monkeypatch,
        microsoft_tenant_id=None,
        microsoft_client_id=None,
        microsoft_client_secret=None,
        microsoft_redirect_uri=None,
    )

    response = api_client.get("/v1/outlook/status")

    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is False
    assert body["missing_fields"] == [
        "MICROSOFT_TENANT_ID",
        "MICROSOFT_CLIENT_ID",
        "MICROSOFT_CLIENT_SECRET",
        "MICROSOFT_REDIRECT_URI",
    ]
    assert "client-secret" not in response.text


def test_outlook_preview_requires_org_and_request_token(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    _configure_outlook(monkeypatch)

    missing_org = api_client.post("/v1/outlook/preview", json={"access_token": "token"})
    missing_token = api_client.post(
        "/v1/outlook/preview",
        json={"organization_id": organization_id, "limit": 25},
    )

    assert missing_org.status_code == 422
    assert missing_token.status_code == 400
    assert "access_token" in missing_token.json()["detail"]


def test_outlook_preview_caps_limit_and_uses_mocked_graph(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    _configure_outlook(monkeypatch)
    seen: dict[str, int] = {}

    def fake_graph_messages(**kwargs: object) -> list[dict[str, object]]:
        seen["limit"] = int(kwargs["limit"])
        return [_graph_message(id=f"graph-msg-{index}") for index in range(seen["limit"])]

    monkeypatch.setattr(outlook_import_service, "_graph_get_messages", fake_graph_messages)

    response = api_client.post(
        "/v1/outlook/preview",
        json={
            "organization_id": organization_id,
            "access_token": "dev-token",
            "search_query": "catch basin",
            "limit": 250,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert seen["limit"] == 100
    assert body["limit"] == 100
    assert body["capped"] is True
    assert body["count"] == 100


def test_normalize_graph_message() -> None:
    normalized = outlook_import_service.normalize_graph_message(
        _graph_message(hasAttachments=True),
    )

    assert normalized.provider_message_id == "graph-msg-1"
    assert normalized.provider_conversation_id == "conversation-1"
    assert normalized.internet_message_id == "<graph-msg-1@example.com>"
    assert normalized.subject == "Access window for Bayside"
    assert normalized.sender == "mara.whitcomb@pinetree.example"
    assert normalized.recipients == [
        {"type": "to", "name": "Ops", "email": "ops@sterling.example"},
    ]
    assert isinstance(normalized.received_at, datetime)
    assert normalized.has_attachments is True


def test_import_selected_creates_batch_and_email_messages(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    _configure_outlook(monkeypatch)

    response = api_client.post(
        "/v1/outlook/import-selected",
        json={
            "organization_id": organization_id,
            "search_query": "Bayside",
            "limit": 25,
            "selected_messages": [_preview_message()],
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["batch"]["provider"] == "outlook"
    assert body["batch"]["import_mode"] == "outlook_preview_selected"
    assert body["batch"]["status"] == "imported"
    assert body["imported_count"] == 1
    assert body["imported_messages"][0]["provider_message_id"] == "graph-msg-1"

    messages = api_client.get(
        "/v1/email-messages",
        params={"organization_id": organization_id, "provider": "outlook"},
    )
    batches = api_client.get(
        "/v1/email-import-batches",
        params={"organization_id": organization_id, "provider": "outlook"},
    )
    assert messages.json()["total"] == 1
    assert batches.json()["total"] == 1


def test_import_selected_skips_duplicate_provider_message_id(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    _configure_outlook(monkeypatch)
    _create_email(api_client, organization_id, provider_message_id="graph-msg-1")

    response = api_client.post(
        "/v1/outlook/import-selected",
        json={
            "organization_id": organization_id,
            "selected_messages": [_preview_message(internet_message_id="<new@example.com>")],
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["imported_count"] == 0
    assert body["duplicate_count"] == 1
    assert body["skipped_count"] == 1


def test_import_selected_skips_duplicate_internet_message_id(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    _configure_outlook(monkeypatch)
    _create_email(
        api_client,
        organization_id,
        provider="local",
        provider_message_id="already-local",
        internet_message_id="<graph-msg-1@example.com>",
    )

    response = api_client.post(
        "/v1/outlook/import-selected",
        json={
            "organization_id": organization_id,
            "selected_messages": [_preview_message(provider_message_id="new-provider-id")],
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["imported_count"] == 0
    assert body["duplicate_count"] == 1
    assert body["skipped_count"] == 1


def test_import_selected_handles_empty_list(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    _configure_outlook(monkeypatch)

    response = api_client.post(
        "/v1/outlook/import-selected",
        json={"organization_id": organization_id, "selected_messages": []},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["batch"]["preview_count"] == 0
    assert body["imported_count"] == 0
    assert body["skipped_count"] == 0


def test_import_selected_never_imports_more_than_requested_limit(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    _configure_outlook(monkeypatch)

    response = api_client.post(
        "/v1/outlook/import-selected",
        json={
            "organization_id": organization_id,
            "limit": 2,
            "selected_messages": [
                _preview_message(provider_message_id="limit-1", internet_message_id="<limit-1@example.com>"),
                _preview_message(provider_message_id="limit-2", internet_message_id="<limit-2@example.com>"),
                _preview_message(provider_message_id="limit-3", internet_message_id="<limit-3@example.com>"),
            ],
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["imported_count"] == 2
    assert body["skipped_count"] == 1
    assert body["batch"]["result_summary_json"]["over_limit_count"] == 1


def test_import_selected_does_not_download_attachments_or_call_graph(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    _configure_outlook(monkeypatch)

    def fail_graph_call(**_kwargs: object) -> list[dict[str, object]]:
        raise AssertionError("import-selected must not call Microsoft Graph")

    monkeypatch.setattr(outlook_import_service, "_graph_get_messages", fail_graph_call)

    response = api_client.post(
        "/v1/outlook/import-selected",
        json={
            "organization_id": organization_id,
            "selected_messages": [_preview_message(has_attachments=True)],
        },
    )

    assert response.status_code == 200, response.text
    imported = response.json()["imported_messages"][0]
    assert imported["attachments_json"] == [
        {"provider": "outlook", "has_attachments": True, "downloaded": False},
    ]


def test_outlook_preview_missing_config_returns_clear_error(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    _configure_outlook(monkeypatch, microsoft_tenant_id=None)

    response = api_client.post(
        "/v1/outlook/preview",
        json={"organization_id": organization_id, "access_token": "dev-token"},
    )

    assert response.status_code == 400
    assert "Outlook import is not configured" in response.json()["detail"]
    assert "MICROSOFT_TENANT_ID" in response.json()["detail"]


def test_outlook_missing_config_returns_clear_error(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    _configure_outlook(monkeypatch, microsoft_client_secret=None)

    response = api_client.post(
        "/v1/outlook/import-selected",
        json={"organization_id": organization_id, "selected_messages": []},
    )

    assert response.status_code == 400
    assert "Outlook import is not configured" in response.json()["detail"]
    assert "MICROSOFT_CLIENT_SECRET" in response.json()["detail"]
