from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import AiDraft, Organization


def _create_reminder(
    api_client: TestClient,
    organization_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "organization_id": organization_id,
        "title": "Follow up on inspection report",
        "description": "Confirm the maintenance plan.",
        "status": "open",
        "priority": "high",
        "due_at": "2026-05-20T14:00:00Z",
    }
    payload.update(overrides)
    response = api_client.post("/v1/reminders", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _create_file(
    api_client: TestClient,
    organization_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "organization_id": organization_id,
        "file_name": "Site Plan PDF",
        "source": "drive_link",
        "public_url": "https://drive.google.com/file/d/timeline/view",
        "caption": "Approved site plan",
    }
    payload.update(overrides)
    response = api_client.post("/v1/files", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _create_import_batch(
    api_client: TestClient,
    organization_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "organization_id": organization_id,
        "provider": "outlook",
        "import_mode": "manual_seed",
        "status": "seed",
        "preview_count": 1,
        "imported_count": 1,
    }
    payload.update(overrides)
    response = api_client.post("/v1/email-import-batches", json=payload)
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
        "provider_message_id": "timeline-email",
        "subject": "Approval for maintenance",
        "sender": "tom@example.com",
        "received_at": "2026-05-12T13:00:00Z",
        "snippet": "Approved to proceed with maintenance.",
        "body_text": "Approved to proceed with maintenance.",
    }
    payload.update(overrides)
    response = api_client.post("/v1/email-messages", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _create_email_link(
    api_client: TestClient,
    organization_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "organization_id": organization_id,
        "link_reason": "manual",
        "confidence": 1.0,
    }
    payload.update(overrides)
    response = api_client.post("/v1/email-record-links", json=payload)
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
        "title": "Draft reply",
        "prompt_context": "Local timeline test context.",
        "draft_text": "Thanks for the update. We will proceed.",
        "status": "draft",
    }
    payload.update(overrides)
    response = api_client.post("/v1/ai-drafts", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _timeline(
    api_client: TestClient,
    organization_id: str,
    **params: Any,
) -> dict[str, Any]:
    response = api_client.get(
        "/v1/timeline",
        params={"organization_id": organization_id, **params},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _types(data: dict[str, Any]) -> set[str]:
    return {item["type"] for item in data["items"]}


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_client_timeline_returns_related_local_activity(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, Any]],
    create_site_record: Callable[..., dict[str, Any]],
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    client = create_client_record(name="Timeline Client")
    site = create_site_record(client_id=client["id"], name="Timeline Site")
    job = create_job_record(client_id=client["id"], site_id=site["id"], name="Spring Inspection")
    _create_reminder(api_client, organization_id, client_id=client["id"])
    _create_file(api_client, organization_id, client_id=client["id"])
    batch = _create_import_batch(api_client, organization_id)
    direct_email = _create_email(
        api_client,
        organization_id,
        provider_message_id="timeline-client-direct",
        import_batch_id=batch["id"],
        client_id=client["id"],
    )
    linked_email = _create_email(
        api_client,
        organization_id,
        provider_message_id="timeline-client-link",
        subject="Link-only message",
    )
    _create_email_link(
        api_client,
        organization_id,
        email_message_id=linked_email["id"],
        client_id=client["id"],
    )
    _create_draft(
        api_client,
        organization_id,
        title="Client reply draft",
        client_id=client["id"],
        email_message_id=direct_email["id"],
    )

    data = _timeline(api_client, organization_id, client_id=client["id"])

    assert {
        "record",
        "job",
        "reminder",
        "file",
        "email",
        "email_link",
        "ai_draft",
        "import_batch",
    }.issubset(_types(data))
    assert any(item["source_id"] == job["id"] for item in data["items"])


def test_site_timeline_returns_related_local_activity(
    api_client: TestClient,
    organization_id: str,
    create_site_record: Callable[..., dict[str, Any]],
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    site = create_site_record(name="Timeline Site")
    job = create_job_record(client_id=site["client_id"], site_id=site["id"], name="Site Inspection")
    _create_reminder(api_client, organization_id, site_id=site["id"])
    _create_file(api_client, organization_id, site_id=site["id"])
    email = _create_email(
        api_client,
        organization_id,
        provider_message_id="timeline-site-email",
        site_id=site["id"],
    )
    _create_draft(
        api_client,
        organization_id,
        title="Site draft",
        site_id=site["id"],
        email_message_id=email["id"],
    )

    data = _timeline(api_client, organization_id, site_id=site["id"])

    assert {"record", "job", "reminder", "file", "email", "ai_draft"}.issubset(_types(data))
    assert any(item["source_id"] == job["id"] for item in data["items"])


def test_job_timeline_returns_related_local_activity_and_outlook_metadata(
    api_client: TestClient,
    db_session: Session,
    organization_id: str,
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    job = create_job_record(name="Job Timeline")
    _create_reminder(api_client, organization_id, job_id=job["id"])
    _create_file(api_client, organization_id, job_id=job["id"])
    email = _create_email(
        api_client,
        organization_id,
        provider_message_id="timeline-job-email",
        job_id=job["id"],
    )
    draft = _create_draft(
        api_client,
        organization_id,
        title="Job draft",
        job_id=job["id"],
        email_message_id=email["id"],
    )

    draft_record = db_session.get(AiDraft, UUID(draft["id"]))
    assert draft_record is not None
    draft_record.provider = "outlook"
    draft_record.provider_draft_id = "graph-draft-timeline"
    draft_record.provider_web_link = "https://outlook.office.com/mail/draft"
    draft_record.provider_status = "created"
    draft_record.pushed_to_provider_at = datetime(2026, 5, 13, 15, 0, tzinfo=UTC)
    db_session.add(draft_record)
    db_session.commit()

    data = _timeline(api_client, organization_id, job_id=job["id"])

    assert {"record", "reminder", "file", "email", "ai_draft", "outlook_draft"}.issubset(_types(data))
    outlook_entry = next(item for item in data["items"] if item["type"] == "outlook_draft")
    assert outlook_entry["metadata"]["provider_draft_id"] == "graph-draft-timeline"


def test_timeline_organization_scoping_is_enforced(
    api_client: TestClient,
    db_session: Session,
    organization_id: str,
    create_client_record: Callable[..., dict[str, Any]],
) -> None:
    other_org = Organization(name="Other Org")
    db_session.add(other_org)
    db_session.commit()
    db_session.refresh(other_org)
    client = create_client_record()
    _create_reminder(api_client, organization_id, client_id=client["id"])

    response = api_client.get(
        "/v1/timeline",
        params={"organization_id": str(other_org.id), "client_id": client["id"]},
    )

    assert response.status_code == 404
    assert "Client not found" in response.json()["detail"]


def test_timeline_limit_is_enforced(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, Any]],
) -> None:
    client = create_client_record()
    for index in range(5):
        _create_reminder(
            api_client,
            organization_id,
            client_id=client["id"],
            title=f"Reminder {index}",
            due_at=f"2026-05-2{index}T12:00:00Z",
        )

    data = _timeline(api_client, organization_id, client_id=client["id"], limit=3)

    assert data["limit"] == 3
    assert len(data["items"]) == 3
    assert data["total"] >= 5


def test_timeline_requires_exactly_one_target(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, Any]],
    create_site_record: Callable[..., dict[str, Any]],
) -> None:
    client = create_client_record()
    site = create_site_record(client_id=client["id"])

    no_target = api_client.get("/v1/timeline", params={"organization_id": organization_id})
    multiple_targets = api_client.get(
        "/v1/timeline",
        params={
            "organization_id": organization_id,
            "client_id": client["id"],
            "site_id": site["id"],
        },
    )

    assert no_target.status_code == 400
    assert multiple_targets.status_code == 400
    assert "Exactly one" in no_target.json()["detail"]
    assert "Exactly one" in multiple_targets.json()["detail"]


def test_timeline_is_sorted_newest_first(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, Any]],
) -> None:
    client = create_client_record()
    for title, due_at in (
        ("Old", "2026-05-10T12:00:00Z"),
        ("New", "2026-05-12T12:00:00Z"),
        ("Middle", "2026-05-11T12:00:00Z"),
    ):
        _create_reminder(api_client, organization_id, client_id=client["id"], title=title, due_at=due_at)

    data = _timeline(api_client, organization_id, client_id=client["id"])
    occurred = [_parse_iso(item["occurred_at"]) for item in data["items"]]

    assert occurred == sorted(occurred, reverse=True)


def test_timeline_excludes_archived_records_where_appropriate(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, Any]],
    create_site_record: Callable[..., dict[str, Any]],
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    client = create_client_record()
    site = create_site_record(client_id=client["id"])
    job = create_job_record(client_id=client["id"], site_id=site["id"], name="Archive Me")
    reminder = _create_reminder(api_client, organization_id, client_id=client["id"])
    file = _create_file(api_client, organization_id, client_id=client["id"])
    email = _create_email(
        api_client,
        organization_id,
        provider_message_id="timeline-archived-email",
        client_id=client["id"],
    )
    draft = _create_draft(api_client, organization_id, client_id=client["id"])

    api_client.delete(f"/v1/jobs/{job['id']}", params={"organization_id": organization_id})
    api_client.delete(f"/v1/reminders/{reminder['id']}", params={"organization_id": organization_id})
    api_client.delete(f"/v1/files/{file['id']}", params={"organization_id": organization_id})
    api_client.delete(f"/v1/email-messages/{email['id']}", params={"organization_id": organization_id})
    api_client.delete(f"/v1/ai-drafts/{draft['id']}", params={"organization_id": organization_id})

    data = _timeline(api_client, organization_id, client_id=client["id"])
    source_ids = {item["source_id"] for item in data["items"]}

    assert job["id"] not in source_ids
    assert reminder["id"] not in source_ids
    assert file["id"] not in source_ids
    assert email["id"] not in source_ids
    assert draft["id"] not in source_ids


def test_timeline_does_not_call_provider_services(
    api_client: TestClient,
    monkeypatch: Any,
    organization_id: str,
    create_client_record: Callable[..., dict[str, Any]],
) -> None:
    from app.services import outlook_drafts_service, outlook_import_service

    def fail_provider_call(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("Timeline should not call provider services.")

    monkeypatch.setattr(outlook_import_service, "preview_outlook_messages", fail_provider_call)
    monkeypatch.setattr(outlook_import_service, "import_selected_outlook_messages", fail_provider_call)
    monkeypatch.setattr(outlook_drafts_service, "create_outlook_draft_from_ai_draft", fail_provider_call)

    client = create_client_record()
    _create_reminder(api_client, organization_id, client_id=client["id"])

    data = _timeline(api_client, organization_id, client_id=client["id"])

    assert data["total"] >= 1


def test_empty_timeline_returns_clean_empty_list(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, Any]],
) -> None:
    client = create_client_record(name="Quiet Client")

    data = _timeline(api_client, organization_id, client_id=client["id"])

    assert data == {"items": [], "total": 0, "limit": 50, "offset": 0}
