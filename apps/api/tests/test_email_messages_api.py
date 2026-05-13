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
        "provider_message_id": "msg-default",
        "subject": "Access window for Bayside inspection",
        "sender": "mara.whitcomb@pinetree.example",
        "recipients_json": [{"name": "Sterling Ops", "email": "ops@sterling.example"}],
        "received_at": "2026-05-12T13:30:00Z",
        "snippet": "Can the crew arrive before retail traffic?",
        "body_text": "Please confirm an early access window for the Bayside inspection.",
        "attachments_json": [{"name": "site-access.pdf", "size": 12400}],
        "links_json": [{"label": "Site folder", "url": "https://drive.google.com/seed"}],
        "web_link": "https://outlook.office.com/mail/seed",
    }
    payload.update(overrides)
    response = api_client.post("/v1/email-messages", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_list_get_patch_and_archive_email_message(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    job = create_job_record()
    email = _create_email(api_client, organization_id, job_id=job["id"])

    assert email["job_id"] == job["id"]
    assert email["site_id"] == job["site_id"]
    assert email["client_id"] == job["client_id"]
    assert email["status"] == "linked"

    list_response = api_client.get("/v1/email-messages", params={"organization_id": organization_id})
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert list_response.json()["limit"] == 50

    get_response = api_client.get(
        f"/v1/email-messages/{email['id']}",
        params={"organization_id": organization_id},
    )
    assert get_response.status_code == 200
    assert get_response.json()["subject"] == email["subject"]

    patch_response = api_client.patch(
        f"/v1/email-messages/{email['id']}",
        params={"organization_id": organization_id},
        json={
            "subject": "Updated access window",
            "client_id": None,
            "site_id": None,
            "job_id": None,
            "status": "unlinked",
        },
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["subject"] == "Updated access window"
    assert patch_response.json()["status"] == "unlinked"

    archive_response = api_client.delete(
        f"/v1/email-messages/{email['id']}",
        params={"organization_id": organization_id},
    )
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == "archived"
    assert archive_response.json()["archived_at"] is not None


def test_search_email_messages_by_subject_snippet_and_body(
    api_client: TestClient,
    organization_id: str,
) -> None:
    _create_email(
        api_client,
        organization_id,
        provider_message_id="msg-search-1",
        subject="Catch basin cleanout quote",
        snippet="Two inlets are holding sediment.",
        body_text="Forebay sediment depth is close to maintenance trigger.",
    )
    _create_email(
        api_client,
        organization_id,
        provider_message_id="msg-search-2",
        subject="Insurance certificate",
        snippet="Routine admin item.",
        body_text="No field operations in this note.",
    )

    subject = api_client.get(
        "/v1/email-messages",
        params={"organization_id": organization_id, "search": "catch basin"},
    )
    body = api_client.get(
        "/v1/email-messages",
        params={"organization_id": organization_id, "search": "forebay"},
    )

    assert subject.status_code == 200
    assert subject.json()["total"] == 1
    assert body.status_code == 200
    assert body.json()["total"] == 1
    assert body.json()["items"][0]["provider_message_id"] == "msg-search-1"


def test_filter_email_messages_by_scope_status_and_provider(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    job = create_job_record()
    _create_email(
        api_client,
        organization_id,
        provider_message_id="msg-filter-linked",
        provider="outlook",
        job_id=job["id"],
    )
    _create_email(
        api_client,
        organization_id,
        provider_message_id="msg-filter-unlinked",
        provider="local",
        subject="Unlinked field note",
    )

    for key, value in {
        "client_id": job["client_id"],
        "site_id": job["site_id"],
        "job_id": job["id"],
        "status": "linked",
        "provider": "outlook",
    }.items():
        response = api_client.get(
            "/v1/email-messages",
            params={"organization_id": organization_id, key: value},
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["provider_message_id"] == "msg-filter-linked"


def test_provider_message_id_dedupes_within_organization(
    api_client: TestClient,
    organization_id: str,
) -> None:
    first = _create_email(api_client, organization_id, provider_message_id="dupe-1")
    second = _create_email(
        api_client,
        organization_id,
        provider_message_id="dupe-1",
        subject="Updated duplicate copy",
    )

    response = api_client.get("/v1/email-messages", params={"organization_id": organization_id})

    assert second["id"] == first["id"]
    assert second["subject"] == "Updated duplicate copy"
    assert response.json()["total"] == 1


def test_email_record_link_create_and_delete_updates_message_scope(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    job = create_job_record()
    email = _create_email(
        api_client,
        organization_id,
        provider_message_id="msg-link",
        subject="Please link this to the cleaning job",
    )

    create_response = api_client.post(
        "/v1/email-record-links",
        json={
            "organization_id": organization_id,
            "email_message_id": email["id"],
            "job_id": job["id"],
            "link_reason": "manual",
            "confidence": 1.0,
        },
    )
    assert create_response.status_code == 201, create_response.text
    link = create_response.json()

    linked_email = api_client.get(
        f"/v1/email-messages/{email['id']}",
        params={"organization_id": organization_id},
    ).json()
    assert linked_email["status"] == "linked"
    assert linked_email["job_id"] == job["id"]

    list_response = api_client.get(
        "/v1/email-record-links",
        params={"organization_id": organization_id, "email_message_id": email["id"]},
    )
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    delete_response = api_client.delete(
        f"/v1/email-record-links/{link['id']}",
        params={"organization_id": organization_id},
    )
    assert delete_response.status_code == 200

    unlinked_email = api_client.get(
        f"/v1/email-messages/{email['id']}",
        params={"organization_id": organization_id},
    ).json()
    assert unlinked_email["status"] == "unlinked"
    assert unlinked_email["job_id"] is None


def test_email_messages_are_organization_scoped(
    api_client: TestClient,
    db_session: Session,
    organization_id: str,
) -> None:
    other_org = Organization(name="Other Org")
    db_session.add(other_org)
    db_session.commit()
    db_session.refresh(other_org)

    email = _create_email(api_client, organization_id, provider_message_id="msg-scope")

    list_response = api_client.get(
        "/v1/email-messages",
        params={"organization_id": str(other_org.id)},
    )
    get_response = api_client.get(
        f"/v1/email-messages/{email['id']}",
        params={"organization_id": str(other_org.id)},
    )

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 0
    assert get_response.status_code == 404


def test_archived_email_messages_excluded_by_default_and_limit_works(
    api_client: TestClient,
    organization_id: str,
) -> None:
    first = _create_email(api_client, organization_id, provider_message_id="msg-limit-1")
    _create_email(api_client, organization_id, provider_message_id="msg-limit-2")
    _create_email(api_client, organization_id, provider_message_id="msg-limit-3")
    api_client.delete(f"/v1/email-messages/{first['id']}", params={"organization_id": organization_id})

    normal = api_client.get("/v1/email-messages", params={"organization_id": organization_id, "limit": 1})
    archived = api_client.get(
        "/v1/email-messages",
        params={"organization_id": organization_id, "status": "archived"},
    )

    assert normal.status_code == 200
    assert normal.json()["total"] == 2
    assert normal.json()["limit"] == 1
    assert len(normal.json()["items"]) == 1
    assert archived.status_code == 200
    assert archived.json()["total"] == 1
