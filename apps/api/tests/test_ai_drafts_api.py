from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Organization


def _create_email(
    api_client: TestClient,
    organization_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "organization_id": organization_id,
        "provider": "outlook",
        "provider_message_id": "draft-email-default",
        "subject": "Catch basin cleaning follow-up",
        "sender": "mara.whitcomb@pinetree.example",
        "body_text": "Can you send next steps for the blocked catch basins?",
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
        "title": "Blocked catch basin reply",
        "prompt_context": "Manual seed draft based on local email record.",
        "draft_text": "Thanks for the note. We will revisit the blocked structures tomorrow morning.",
        "status": "draft",
    }
    payload.update(overrides)
    response = api_client.post("/v1/ai-drafts", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_list_patch_and_archive_ai_draft(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    job = create_job_record()
    email = _create_email(api_client, organization_id, provider_message_id="draft-email-1")
    draft = _create_draft(
        api_client,
        organization_id,
        job_id=job["id"],
        email_message_id=email["id"],
    )

    assert draft["job_id"] == job["id"]
    assert draft["site_id"] == job["site_id"]
    assert draft["client_id"] == job["client_id"]
    assert draft["email_message_id"] == email["id"]

    list_response = api_client.get("/v1/ai-drafts", params={"organization_id": organization_id})
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert list_response.json()["limit"] == 50

    patch_response = api_client.patch(
        f"/v1/ai-drafts/{draft['id']}",
        params={"organization_id": organization_id},
        json={"status": "reviewed", "title": "Reviewed reply"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "reviewed"
    assert patch_response.json()["title"] == "Reviewed reply"

    used_response = api_client.patch(
        f"/v1/ai-drafts/{draft['id']}",
        params={"organization_id": organization_id},
        json={"status": "used"},
    )
    assert used_response.status_code == 200
    assert used_response.json()["status"] == "used"

    archive_response = api_client.delete(
        f"/v1/ai-drafts/{draft['id']}",
        params={"organization_id": organization_id},
    )
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "archived"
    assert archive_response.json()["archived_at"] is not None


def test_ai_drafts_filter_by_linked_records_and_email(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    job = create_job_record()
    email = _create_email(api_client, organization_id, provider_message_id="draft-email-filter")
    _create_draft(
        api_client,
        organization_id,
        job_id=job["id"],
        email_message_id=email["id"],
        title="Linked draft",
    )
    _create_draft(
        api_client,
        organization_id,
        provider_message_id="ignored",
        title="Client-only draft",
        client_id=job["client_id"],
        email_message_id=None,
    )

    for key, value in {
        "client_id": job["client_id"],
        "site_id": job["site_id"],
        "job_id": job["id"],
        "email_message_id": email["id"],
        "draft_type": "email_reply",
    }.items():
        response = api_client.get(
            "/v1/ai-drafts",
            params={"organization_id": organization_id, key: value},
        )
        assert response.status_code == 200
        assert response.json()["total"] >= 1

    email_response = api_client.get(
        "/v1/ai-drafts",
        params={"organization_id": organization_id, "email_message_id": email["id"]},
    )
    assert email_response.json()["total"] == 1
    assert email_response.json()["items"][0]["title"] == "Linked draft"


def test_ai_drafts_are_organization_scoped(
    api_client: TestClient,
    db_session: Session,
    organization_id: str,
) -> None:
    other_org = Organization(name="Other Org")
    db_session.add(other_org)
    db_session.commit()
    db_session.refresh(other_org)

    draft = _create_draft(api_client, organization_id)

    list_response = api_client.get("/v1/ai-drafts", params={"organization_id": str(other_org.id)})
    get_response = api_client.get(
        f"/v1/ai-drafts/{draft['id']}",
        params={"organization_id": str(other_org.id)},
    )

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 0
    assert get_response.status_code == 404


def test_archived_ai_drafts_excluded_by_default_and_limit_works(
    api_client: TestClient,
    organization_id: str,
) -> None:
    first = _create_draft(api_client, organization_id, title="First")
    _create_draft(api_client, organization_id, title="Second")
    _create_draft(api_client, organization_id, title="Third")
    api_client.delete(f"/v1/ai-drafts/{first['id']}", params={"organization_id": organization_id})

    normal = api_client.get("/v1/ai-drafts", params={"organization_id": organization_id, "limit": 1})
    archived = api_client.get(
        "/v1/ai-drafts",
        params={"organization_id": organization_id, "status": "archived"},
    )

    assert normal.status_code == 200
    assert normal.json()["total"] == 2
    assert normal.json()["limit"] == 1
    assert len(normal.json()["items"]) == 1
    assert archived.status_code == 200
    assert archived.json()["total"] == 1
