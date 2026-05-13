from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Organization
from app.services import ai_assistant_service, outlook_drafts_service, outlook_import_service


def _get_group(body: dict[str, Any], group_type: str) -> dict[str, Any]:
    return next(group for group in body["groups"] if group["type"] == group_type)


def _create_file(
    api_client: TestClient,
    organization_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "organization_id": organization_id,
        "file_name": "Forebay Photo Log.pdf",
        "source": "drive_link",
        "caption": "Forebay inlet sediment photo log.",
        "job_id": overrides.pop("job_id"),
    }
    payload.update(overrides)
    response = api_client.post("/v1/files", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _create_email(
    api_client: TestClient,
    organization_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "organization_id": organization_id,
        "provider": "outlook",
        "provider_message_id": "global-search-email",
        "subject": "Forebay inspection access",
        "sender": "sam.client@example.com",
        "snippet": "Please confirm the forebay gate code.",
        "body_text": "The inspection crew needs safe access to the forebay and outlet.",
    }
    payload.update(overrides)
    response = api_client.post("/v1/email-messages", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _create_draft(
    api_client: TestClient,
    organization_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "organization_id": organization_id,
        "draft_type": "email_reply",
        "title": "Forebay access reply",
        "draft_text": "We can inspect the forebay after the gate code is confirmed.",
        "status": "draft",
    }
    payload.update(overrides)
    response = api_client.post("/v1/ai-drafts", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _create_reminder(
    api_client: TestClient,
    organization_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "organization_id": organization_id,
        "title": "Confirm forebay gate code",
        "description": "Call the site contact before the inspection window.",
        "priority": "high",
        "status": "open",
        "job_id": overrides.pop("job_id"),
    }
    payload.update(overrides)
    response = api_client.post("/v1/reminders", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_search_requires_q(
    api_client: TestClient,
    organization_id: str,
) -> None:
    response = api_client.get("/v1/search", params={"organization_id": organization_id})

    assert response.status_code == 422


def test_search_q_min_length(
    api_client: TestClient,
    organization_id: str,
) -> None:
    response = api_client.get(
        "/v1/search",
        params={"organization_id": organization_id, "q": "a"},
    )

    assert response.status_code == 422


def test_search_is_organization_scoped(
    api_client: TestClient,
    db_session: Session,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
) -> None:
    other_org = Organization(name="Other Search Org")
    db_session.add(other_org)
    db_session.commit()
    db_session.refresh(other_org)

    create_client_record(name="Scoped Basin Client", notes="visible basin note")
    response = api_client.post(
        "/v1/clients",
        json={
            "organization_id": str(other_org.id),
            "name": "Hidden Basin Client",
            "notes": "hidden basin note",
        },
    )
    assert response.status_code == 201, response.text

    search_response = api_client.get(
        "/v1/search",
        params={"organization_id": organization_id, "q": "basin", "types": "clients"},
    )

    assert search_response.status_code == 200
    clients = _get_group(search_response.json(), "clients")
    assert clients["count"] == 1
    assert clients["results"][0]["title"] == "Scoped Basin Client"


def test_clients_search(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
) -> None:
    create_client_record(
        name="Basin Ridge HOA",
        primary_contact_name="Mara Basin",
        email="mara@example.com",
        notes="Prefers forebay inspection notes.",
    )

    response = api_client.get(
        "/v1/search",
        params={"organization_id": organization_id, "q": "mara", "types": "clients"},
    )

    assert response.status_code == 200
    result = _get_group(response.json(), "clients")["results"][0]
    assert result["title"] == "Basin Ridge HOA"
    assert "primary_contact_name" in result["matched_fields"]
    assert result["href"] == "/crm/clients"


def test_sites_search(
    api_client: TestClient,
    organization_id: str,
    create_site_record: Callable[..., dict[str, object]],
) -> None:
    site = create_site_record(
        name="Forebay Retail Site",
        address="100 Outlet Lane",
        city="Cary",
        notes="Gate code needed for forebay access.",
    )

    response = api_client.get(
        "/v1/search",
        params={"organization_id": organization_id, "q": "outlet", "types": "sites"},
    )

    assert response.status_code == 200
    result = _get_group(response.json(), "sites")["results"][0]
    assert result["title"] == "Forebay Retail Site"
    assert "address" in result["matched_fields"]
    assert result["href"] == f"/crm/sites?site_id={site['id']}"


def test_jobs_search(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, object]],
) -> None:
    create_job_record(
        name="Outlet Control Inspection",
        service_type="Inspection",
        scope="Inspect outlet control structure and forebay.",
    )

    response = api_client.get(
        "/v1/search",
        params={"organization_id": organization_id, "q": "control", "types": "jobs"},
    )

    assert response.status_code == 200
    result = _get_group(response.json(), "jobs")["results"][0]
    assert result["title"] == "Outlet Control Inspection"
    assert "name" in result["matched_fields"] or "scope" in result["matched_fields"]
    assert result["href"] == "/crm/jobs"


def test_files_search(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, object]],
) -> None:
    job = create_job_record()
    _create_file(api_client, organization_id, job_id=job["id"])

    response = api_client.get(
        "/v1/search",
        params={"organization_id": organization_id, "q": "sediment", "types": "files"},
    )

    assert response.status_code == 200
    result = _get_group(response.json(), "files")["results"][0]
    assert result["title"] == "Forebay Photo Log.pdf"
    assert "caption" in result["matched_fields"]
    assert result["href"] == "/work"


def test_emails_search(
    api_client: TestClient,
    organization_id: str,
) -> None:
    _create_email(api_client, organization_id)

    response = api_client.get(
        "/v1/search",
        params={"organization_id": organization_id, "q": "gate code", "types": "emails"},
    )

    assert response.status_code == 200
    result = _get_group(response.json(), "emails")["results"][0]
    assert result["title"] == "Forebay inspection access"
    assert "snippet" in result["matched_fields"]
    assert result["href"] == "/work"


def test_ai_drafts_search(
    api_client: TestClient,
    organization_id: str,
) -> None:
    _create_draft(api_client, organization_id)

    response = api_client.get(
        "/v1/search",
        params={"organization_id": organization_id, "q": "inspect", "types": "ai_drafts"},
    )

    assert response.status_code == 200
    result = _get_group(response.json(), "ai_drafts")["results"][0]
    assert result["title"] == "Forebay access reply"
    assert "draft_text" in result["matched_fields"]
    assert result["href"] == "/work"


def test_reminders_search(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, object]],
) -> None:
    job = create_job_record()
    _create_reminder(api_client, organization_id, job_id=job["id"])

    response = api_client.get(
        "/v1/search",
        params={"organization_id": organization_id, "q": "gate", "types": "reminders"},
    )

    assert response.status_code == 200
    result = _get_group(response.json(), "reminders")["results"][0]
    assert result["title"] == "Confirm forebay gate code"
    assert "title" in result["matched_fields"]
    assert result["href"] == "/schedule"


def test_type_filter_returns_only_requested_groups(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
    create_job_record: Callable[..., dict[str, object]],
) -> None:
    create_client_record(name="Basin Client")
    create_job_record(name="Basin Job")

    response = api_client.get(
        "/v1/search",
        params={"organization_id": organization_id, "q": "basin", "types": "jobs"},
    )

    assert response.status_code == 200
    body = response.json()
    assert [group["type"] for group in body["groups"]] == ["jobs"]
    assert body["total_count"] == 1


def test_limit_cap_enforced(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
) -> None:
    for index in range(30):
        create_client_record(name=f"Cap Basin Client {index:02d}")

    response = api_client.get(
        "/v1/search",
        params={
            "organization_id": organization_id,
            "q": "basin",
            "types": "clients",
            "limit": 100,
        },
    )

    assert response.status_code == 200
    clients = _get_group(response.json(), "clients")
    assert clients["count"] == 25
    assert len(clients["results"]) == 25


def test_archived_records_are_excluded(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
) -> None:
    archived = create_client_record(name="Archived Basin Client")
    active = create_client_record(name="Active Basin Client")
    delete_response = api_client.delete(
        f"/v1/clients/{archived['id']}",
        params={"organization_id": organization_id},
    )
    assert delete_response.status_code == 200

    response = api_client.get(
        "/v1/search",
        params={"organization_id": organization_id, "q": "basin", "types": "clients"},
    )

    assert response.status_code == 200
    clients = _get_group(response.json(), "clients")
    assert clients["count"] == 1
    assert clients["results"][0]["id"] == active["id"]


def test_response_shape_stable(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
) -> None:
    create_client_record(name="Shape Basin Client")

    response = api_client.get(
        "/v1/search",
        params={"organization_id": organization_id, "q": "basin"},
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"query", "groups", "total_count"}
    assert [group["type"] for group in body["groups"]] == [
        "clients",
        "sites",
        "jobs",
        "files",
        "emails",
        "ai_drafts",
        "reminders",
    ]
    result = _get_group(body, "clients")["results"][0]
    assert {
        "id",
        "type",
        "title",
        "subtitle",
        "description",
        "status",
        "href",
        "matched_fields",
        "occurred_at",
        "updated_at",
        "metadata",
    } == set(result)


def test_search_does_not_call_provider_services(
    api_client: TestClient,
    monkeypatch: Any,
    organization_id: str,
) -> None:
    _create_email(api_client, organization_id)

    def fail_provider_call(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("global search must not call provider-backed services")

    monkeypatch.setattr(outlook_import_service, "preview_outlook_messages", fail_provider_call)
    monkeypatch.setattr(outlook_import_service, "import_selected_outlook_messages", fail_provider_call)
    monkeypatch.setattr(outlook_drafts_service, "create_outlook_draft_from_ai_draft", fail_provider_call)
    monkeypatch.setattr(ai_assistant_service, "draft_reply", fail_provider_call)
    monkeypatch.setattr(ai_assistant_service, "report_section_draft", fail_provider_call)
    monkeypatch.setattr(ai_assistant_service, "maintenance_recommendation_draft", fail_provider_call)
    monkeypatch.setattr(ai_assistant_service, "client_summary_draft", fail_provider_call)

    response = api_client.get(
        "/v1/search",
        params={"organization_id": organization_id, "q": "forebay"},
    )

    assert response.status_code == 200
    assert response.json()["total_count"] >= 1
