from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.schemas.ai_assistant import AiStatusResponse
from app.services import ai_assistant_service, integrations_service


def _settings(**overrides: object) -> SimpleNamespace:
    defaults: dict[str, object] = {
        "openai_api_key": None,
        "openai_model": "test-model",
        "ai_features_enabled": None,
        "microsoft_tenant_id": None,
        "microsoft_client_id": None,
        "microsoft_client_secret": None,
        "microsoft_redirect_uri": None,
        "microsoft_graph_base_url": "https://graph.microsoft.com/v1.0",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _disable_ai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        ai_assistant_service,
        "get_ai_status",
        lambda: AiStatusResponse(
            configured=False,
            enabled=False,
            model=None,
            missing_fields=["OPENAI_API_KEY"],
            message="Set OPENAI_API_KEY to enable provider-backed draft generation.",
        ),
    )


def _enable_ai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        ai_assistant_service,
        "get_ai_status",
        lambda: AiStatusResponse(
            configured=True,
            enabled=True,
            model="mock-ai",
            missing_fields=[],
            message="AI enabled for tests.",
        ),
    )


def _create_email(
    api_client: TestClient,
    organization_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "organization_id": organization_id,
        "provider": "outlook",
        "provider_message_id": "ai-email-default",
        "subject": "Bayside Retail Plaza follow-up",
        "sender": "mara.whitcomb@pinetree.example",
        "body_text": (
            "Please confirm the Bayside Retail Plaza access window tomorrow. "
            "Recommend saving this file: https://drive.google.com/file/d/test/view"
        ),
    }
    payload.update(overrides)
    response = api_client.post("/v1/email-messages", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_ai_status_no_config_reports_disabled(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ai_assistant_service, "get_settings", lambda: _settings())

    response = api_client.get("/v1/ai/status")

    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is False
    assert body["enabled"] is False
    assert body["missing_fields"] == ["OPENAI_API_KEY"]


def test_integrations_status_reports_provider_readiness_without_secrets(
    api_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(integrations_service, "get_settings", lambda: _settings())

    response = api_client.get("/v1/integrations/status")

    assert response.status_code == 200
    body = response.json()
    assert body["outlook"]["configured"] is False
    assert "MICROSOFT_CLIENT_SECRET" in body["outlook"]["missing_fields"]
    assert body["gmail"]["status"] == "deferred"
    assert body["google_drive"]["status"] == "deferred"
    assert body["onedrive"]["status"] == "deferred"
    assert body["ai"]["missing_fields"] == ["OPENAI_API_KEY"]
    assert "secret" not in str(body).lower().replace("microsoft_client_secret", "")


def test_draft_reply_disabled_without_ai_key_does_not_create_draft(
    api_client: TestClient,
    organization_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _disable_ai(monkeypatch)
    email = _create_email(api_client, organization_id)

    response = api_client.post(
        "/v1/ai/draft-reply",
        json={
            "organization_id": organization_id,
            "email_message_id": email["id"],
            "save_draft": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["error_code"] == "configuration_required"

    drafts = api_client.get("/v1/ai-drafts", params={"organization_id": organization_id})
    assert drafts.status_code == 200
    assert drafts.json()["total"] == 0


def test_mocked_ai_summary_can_save_ai_draft(
    api_client: TestClient,
    organization_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_ai(monkeypatch)
    email = _create_email(api_client, organization_id)

    def fake_provider(*, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        assert "provided local email content" in system_prompt
        assert "Bayside Retail Plaza" in user_prompt
        return {
            "summary": "Client is asking to confirm the access window.",
            "key_points": ["Access timing matters."],
            "questions": [],
            "recommended_next_step": "Confirm crew arrival time.",
        }

    monkeypatch.setattr(ai_assistant_service, "_call_openai_json", fake_provider)

    response = api_client.post(
        "/v1/ai/email-summary",
        json={
            "organization_id": organization_id,
            "email_message_id": email["id"],
            "save_draft": True,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "openai"
    assert body["result"]["summary"] == "Client is asking to confirm the access window."
    assert body["saved_draft"]["draft_type"] == "email_summary"

    drafts = api_client.get("/v1/ai-drafts", params={"organization_id": organization_id})
    assert drafts.json()["total"] == 1
    assert drafts.json()["items"][0]["email_message_id"] == email["id"]


def test_email_summary_loads_selected_email_with_deterministic_fallback(
    api_client: TestClient,
    organization_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _disable_ai(monkeypatch)
    email = _create_email(api_client, organization_id, subject="Action requested")

    response = api_client.post(
        "/v1/ai/email-summary",
        json={"organization_id": organization_id, "email_message_id": email["id"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "deterministic"
    assert "Action requested" in body["result"]["summary"]
    assert body["result"]["recommended_next_step"]


def test_action_items_are_structured_and_do_not_auto_create_reminders(
    api_client: TestClient,
    organization_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _disable_ai(monkeypatch)
    email = _create_email(
        api_client,
        organization_id,
        body_text="Please schedule a revisit tomorrow. Recommend reviewing CB-7 before closeout.",
    )

    response = api_client.post(
        "/v1/ai/email-action-items",
        json={"organization_id": organization_id, "email_message_id": email["id"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "deterministic"
    assert body["items"]
    assert {"title", "priority", "due_hint", "reason", "suggested_owner"} <= set(body["items"][0])

    reminders = api_client.get("/v1/reminders", params={"organization_id": organization_id})
    assert reminders.status_code == 200
    assert reminders.json()["total"] == 0


def test_url_extraction_classifies_drive_onedrive_sharepoint_and_generic(
    api_client: TestClient,
    organization_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _disable_ai(monkeypatch)

    response = api_client.post(
        "/v1/ai/extract-file-links",
        json={
            "organization_id": organization_id,
            "text": (
                "Drive https://drive.google.com/file/d/abc/view "
                "OneDrive https://1drv.ms/f/s!abc "
                "SharePoint https://sterling.sharepoint.com/sites/ops/Shared%20Documents/file.pdf "
                "Web https://example.com/ms4"
            ),
        },
    )

    assert response.status_code == 200
    link_types = {item["link_type"] for item in response.json()["links"]}
    assert {"google_drive", "onedrive", "sharepoint", "generic_url"} <= link_types


def test_record_suggestions_are_review_only_exact_matches(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _disable_ai(monkeypatch)
    job = create_job_record(name="Bayside Spring Inspection", job_code="BAY-2026-INS")

    response = api_client.post(
        "/v1/ai/suggest-record-links",
        json={
            "organization_id": organization_id,
            "text": "Please attach this to BAY-2026-INS for the Bayside Spring Inspection.",
        },
    )

    assert response.status_code == 200
    suggestions = response.json()["suggestions"]
    assert any(item["target_type"] == "job" and item["target_id"] == job["id"] for item in suggestions)


def test_file_link_candidate_still_requires_explicit_parent_to_save(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _disable_ai(monkeypatch)
    response = api_client.post(
        "/v1/ai/extract-file-links",
        json={"organization_id": organization_id, "text": "https://drive.google.com/file/d/abc/view"},
    )
    candidate = response.json()["links"][0]

    orphan = api_client.post(
        "/v1/files",
        json={
            "organization_id": organization_id,
            "file_name": candidate["label"],
            "public_url": candidate["url"],
            "source": "drive_link",
        },
    )
    assert orphan.status_code == 400

    job = create_job_record()
    saved = api_client.post(
        "/v1/files",
        json={
            "organization_id": organization_id,
            "job_id": job["id"],
            "file_name": candidate["label"],
            "public_url": candidate["url"],
            "source": "drive_link",
        },
    )
    assert saved.status_code == 201, saved.text
    assert saved.json()["job_id"] == job["id"]
