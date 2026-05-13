from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AiDraft
from app.services import outlook_auth_service, outlook_drafts_service


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
    monkeypatch.setattr(outlook_drafts_service, "get_settings", lambda: settings)
    return settings


def _store_connection(
    db_session: Session,
    organization_id: str,
    settings: SimpleNamespace,
    *,
    scopes: str = "offline_access User.Read Mail.ReadWrite",
    access_token: str = "stored-draft-token",
) -> None:
    outlook_auth_service.store_connection(
        db_session,
        organization_id=uuid.UUID(organization_id),
        token_body={
            "access_token": access_token,
            "refresh_token": "stored-refresh-token",
            "expires_in": 3600,
            "scope": scopes,
        },
        profile={
            "mail": "mara.whitcomb@pinetree.example",
            "displayName": "Mara Whitcomb",
        },
        settings=settings,  # type: ignore[arg-type]
    )


def _create_draft(
    api_client: TestClient,
    organization_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "organization_id": organization_id,
        "draft_type": "email_reply",
        "title": "Catch basin follow-up",
        "prompt_context": "Reviewed local reply.",
        "draft_text": "Thanks for the note. We will revisit the blocked structures tomorrow morning.",
        "status": "reviewed",
    }
    payload.update(overrides)
    response = api_client.post("/v1/ai-drafts", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _draft_payload(organization_id: str, draft_id: str, **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "organization_id": organization_id,
        "ai_draft_id": draft_id,
        "to_recipients": ["client@example.com"],
        "subject": "Catch basin follow-up",
    }
    payload.update(overrides)
    return payload


def test_create_outlook_draft_requires_connection(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    _configure_outlook(monkeypatch)
    draft = _create_draft(api_client, organization_id)

    response = api_client.post(
        "/v1/outlook/drafts/from-ai-draft",
        json=_draft_payload(organization_id, draft["id"]),
    )

    assert response.status_code == 400
    assert "Connect Outlook first" in response.json()["detail"]


def test_create_outlook_draft_invalid_ai_draft_id_returns_404(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    _configure_outlook(monkeypatch)

    response = api_client.post(
        "/v1/outlook/drafts/from-ai-draft",
        json=_draft_payload(organization_id, str(uuid.uuid4())),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "AI draft not found."


def test_create_outlook_draft_rejects_non_email_draft_type(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    _configure_outlook(monkeypatch)
    draft = _create_draft(api_client, organization_id, draft_type="report_section")

    response = api_client.post(
        "/v1/outlook/drafts/from-ai-draft",
        json=_draft_payload(organization_id, draft["id"]),
    )

    assert response.status_code == 400
    assert "not email-style" in response.json()["detail"]


def test_create_outlook_draft_rejects_missing_recipients(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    _configure_outlook(monkeypatch)
    draft = _create_draft(api_client, organization_id)

    response = api_client.post(
        "/v1/outlook/drafts/from-ai-draft",
        json=_draft_payload(organization_id, draft["id"], to_recipients=[]),
    )

    assert response.status_code == 400
    assert "To recipient" in response.json()["detail"]


def test_create_outlook_draft_rejects_missing_subject(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    _configure_outlook(monkeypatch)
    draft = _create_draft(api_client, organization_id)

    response = api_client.post(
        "/v1/outlook/drafts/from-ai-draft",
        json=_draft_payload(organization_id, draft["id"], subject=" "),
    )

    assert response.status_code == 400
    assert "subject is required" in response.json()["detail"]


def test_create_outlook_draft_rejects_missing_body(
    api_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    _configure_outlook(monkeypatch)
    draft = AiDraft(
        organization_id=uuid.UUID(organization_id),
        draft_type="email_reply",
        title="Blank local draft",
        draft_text=" ",
        status="reviewed",
    )
    db_session.add(draft)
    db_session.commit()
    db_session.refresh(draft)

    response = api_client.post(
        "/v1/outlook/drafts/from-ai-draft",
        json=_draft_payload(organization_id, str(draft.id)),
    )

    assert response.status_code == 400
    assert "draft text is required" in response.json()["detail"]


def test_create_outlook_draft_requires_mail_readwrite_scope(
    api_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    settings = _configure_outlook(monkeypatch)
    _store_connection(db_session, organization_id, settings, scopes="offline_access User.Read Mail.Read")
    draft = _create_draft(api_client, organization_id)

    response = api_client.post(
        "/v1/outlook/drafts/from-ai-draft",
        json=_draft_payload(organization_id, draft["id"]),
    )

    assert response.status_code == 400
    assert "Mail.ReadWrite" in response.json()["detail"]


def test_create_outlook_draft_calls_graph_create_message_and_saves_metadata(
    api_client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    organization_id: str,
) -> None:
    settings = _configure_outlook(monkeypatch)
    _store_connection(db_session, organization_id, settings, access_token="stored-draft-token")
    draft = _create_draft(api_client, organization_id)
    seen: dict[str, Any] = {}

    class FakeResponse:
        status_code = 201
        reason_phrase = "Created"

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {
                "id": "graph-draft-123",
                "webLink": "https://outlook.office.com/mail/id/graph-draft-123",
            }

    class FakeClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            seen["timeout"] = kwargs.get("timeout")

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def post(self, url: str, **kwargs: Any) -> FakeResponse:
            seen["url"] = url
            seen["json"] = kwargs["json"]
            seen["headers"] = kwargs["headers"]
            assert "sendMail" not in url
            assert not url.rstrip("/").endswith("/send")
            return FakeResponse()

    monkeypatch.setattr(outlook_drafts_service.httpx, "Client", FakeClient)

    response = api_client.post(
        "/v1/outlook/drafts/from-ai-draft",
        json=_draft_payload(
            organization_id,
            draft["id"],
            to_recipients=["client@example.com", "pm@example.com"],
            subject="Reviewed follow-up",
            body_override="Reviewed body text.",
        ),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ai_draft_id"] == draft["id"]
    assert body["provider"] == "outlook"
    assert body["provider_draft_id"] == "graph-draft-123"
    assert body["provider_status"] == "draft_created"
    assert body["provider_web_link"] == "https://outlook.office.com/mail/id/graph-draft-123"
    assert datetime.fromisoformat(body["pushed_to_provider_at"]).tzinfo is not None
    assert "stored-draft-token" not in response.text
    assert seen["url"] == "https://graph.microsoft.com/v1.0/me/messages"
    assert seen["headers"]["Authorization"] == "Bearer stored-draft-token"
    assert seen["json"]["subject"] == "Reviewed follow-up"
    assert seen["json"]["body"] == {"contentType": "Text", "content": "Reviewed body text."}
    assert seen["json"]["toRecipients"] == [
        {"emailAddress": {"address": "client@example.com"}},
        {"emailAddress": {"address": "pm@example.com"}},
    ]

    saved = db_session.scalar(select(AiDraft).where(AiDraft.id == uuid.UUID(draft["id"])))
    assert saved is not None
    assert saved.provider == "outlook"
    assert saved.provider_draft_id == "graph-draft-123"
    assert saved.provider_status == "draft_created"
    assert saved.provider_error is None
    assert saved.pushed_to_provider_at is not None
