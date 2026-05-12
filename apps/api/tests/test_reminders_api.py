from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Organization


def _create_reminder(
    api_client: TestClient,
    organization_id: str,
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "organization_id": organization_id,
        "title": "Review follow-up",
        "priority": "medium",
        "status": "open",
        "due_at": "2026-05-12T14:00:00Z",
    }
    payload.update(overrides)
    response = api_client.post("/v1/reminders", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_client_linked_reminder(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
) -> None:
    client = create_client_record()

    reminder = _create_reminder(api_client, organization_id, client_id=client["id"])

    assert reminder["client_id"] == client["id"]
    assert reminder["site_id"] is None
    assert reminder["job_id"] is None
    assert reminder["status"] == "open"
    assert reminder["priority"] == "medium"


def test_create_site_linked_reminder(
    api_client: TestClient,
    organization_id: str,
    create_site_record: Callable[..., dict[str, object]],
) -> None:
    site = create_site_record()

    reminder = _create_reminder(api_client, organization_id, site_id=site["id"])

    assert reminder["site_id"] == site["id"]


def test_create_job_linked_reminder(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, object]],
) -> None:
    job = create_job_record()

    reminder = _create_reminder(api_client, organization_id, job_id=job["id"])

    assert reminder["job_id"] == job["id"]


def test_list_by_organization(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
) -> None:
    client = create_client_record()
    _create_reminder(api_client, organization_id, client_id=client["id"])

    response = api_client.get("/v1/reminders", params={"organization_id": organization_id})

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_filter_by_status(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
) -> None:
    client = create_client_record()
    _create_reminder(api_client, organization_id, client_id=client["id"], status="open")
    _create_reminder(api_client, organization_id, client_id=client["id"], status="snoozed")

    response = api_client.get(
        "/v1/reminders",
        params={"organization_id": organization_id, "status": "snoozed"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["status"] == "snoozed"


def test_filter_by_priority(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
) -> None:
    client = create_client_record()
    _create_reminder(api_client, organization_id, client_id=client["id"], priority="low")
    _create_reminder(api_client, organization_id, client_id=client["id"], priority="high")

    response = api_client.get(
        "/v1/reminders",
        params={"organization_id": organization_id, "priority": "high"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["priority"] == "high"


def test_filter_by_job_id(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, object]],
) -> None:
    first = create_job_record(name="First Job")
    second = create_job_record(name="Second Job")
    _create_reminder(api_client, organization_id, job_id=first["id"])
    _create_reminder(api_client, organization_id, job_id=second["id"])

    response = api_client.get(
        "/v1/reminders",
        params={"organization_id": organization_id, "job_id": first["id"]},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["job_id"] == first["id"]


def test_patch_title_priority_and_due_date(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
) -> None:
    client = create_client_record()
    reminder = _create_reminder(api_client, organization_id, client_id=client["id"])

    response = api_client.patch(
        f"/v1/reminders/{reminder['id']}",
        params={"organization_id": organization_id},
        json={
            "title": "Updated follow-up",
            "priority": "high",
            "due_at": "2026-05-13T16:30:00Z",
        },
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["title"] == "Updated follow-up"
    assert updated["priority"] == "high"
    assert updated["due_at"].startswith("2026-05-13T16:30:00")


def test_patch_title_without_resending_target_still_passes(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
) -> None:
    client = create_client_record()
    reminder = _create_reminder(api_client, organization_id, client_id=client["id"])

    response = api_client.patch(
        f"/v1/reminders/{reminder['id']}",
        params={"organization_id": organization_id},
        json={"title": "Still linked"},
    )

    assert response.status_code == 200
    assert response.json()["client_id"] == client["id"]


def test_exact_one_target_rejects_zero_targets(
    api_client: TestClient,
    organization_id: str,
) -> None:
    response = api_client.post(
        "/v1/reminders",
        json={"organization_id": organization_id, "title": "No target"},
    )

    assert response.status_code == 400


def test_exact_one_target_rejects_multiple_targets(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
    create_site_record: Callable[..., dict[str, object]],
    create_job_record: Callable[..., dict[str, object]],
) -> None:
    client = create_client_record()
    site = create_site_record(client_id=client["id"])
    job = create_job_record(client_id=client["id"], site_id=site["id"])

    create_response = api_client.post(
        "/v1/reminders",
        json={
            "organization_id": organization_id,
            "title": "Too many targets",
            "client_id": client["id"],
            "job_id": job["id"],
        },
    )
    assert create_response.status_code == 400

    reminder = _create_reminder(api_client, organization_id, client_id=client["id"])
    patch_response = api_client.patch(
        f"/v1/reminders/{reminder['id']}",
        params={"organization_id": organization_id},
        json={"job_id": job["id"]},
    )
    assert patch_response.status_code == 400


def test_mark_complete_sets_completed_at(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, object]],
) -> None:
    job = create_job_record()
    reminder = _create_reminder(api_client, organization_id, job_id=job["id"])

    response = api_client.patch(
        f"/v1/reminders/{reminder['id']}",
        params={"organization_id": organization_id},
        json={"status": "completed"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["completed_at"] is not None


def test_reopening_clears_completed_at(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, object]],
) -> None:
    job = create_job_record()
    reminder = _create_reminder(api_client, organization_id, job_id=job["id"], status="completed")

    response = api_client.patch(
        f"/v1/reminders/{reminder['id']}",
        params={"organization_id": organization_id},
        json={"status": "open"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "open"
    assert response.json()["completed_at"] is None


def test_archive_reminder(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
) -> None:
    client = create_client_record()
    reminder = _create_reminder(api_client, organization_id, client_id=client["id"])

    response = api_client.delete(
        f"/v1/reminders/{reminder['id']}",
        params={"organization_id": organization_id},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "archived"
    assert response.json()["archived_at"] is not None


def test_archived_excluded_from_normal_list(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
) -> None:
    client = create_client_record()
    reminder = _create_reminder(api_client, organization_id, client_id=client["id"])
    api_client.delete(f"/v1/reminders/{reminder['id']}", params={"organization_id": organization_id})

    normal = api_client.get("/v1/reminders", params={"organization_id": organization_id})
    archived = api_client.get(
        "/v1/reminders",
        params={"organization_id": organization_id, "status": "archived"},
    )

    assert normal.status_code == 200
    assert normal.json()["total"] == 0
    assert archived.status_code == 200
    assert archived.json()["total"] == 1


def test_completed_visible_when_status_completed(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
) -> None:
    client = create_client_record()
    _create_reminder(api_client, organization_id, client_id=client["id"], status="completed")

    response = api_client.get(
        "/v1/reminders",
        params={"organization_id": organization_id, "status": "completed"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["status"] == "completed"


def test_organization_scoping_enforced(
    api_client: TestClient,
    db_session: Session,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
) -> None:
    other_org = Organization(name="Other Organization")
    db_session.add(other_org)
    db_session.commit()
    db_session.refresh(other_org)

    client = create_client_record()
    reminder = _create_reminder(api_client, organization_id, client_id=client["id"])

    list_response = api_client.get(
        "/v1/reminders",
        params={"organization_id": str(other_org.id)},
    )
    get_response = api_client.get(
        f"/v1/reminders/{reminder['id']}",
        params={"organization_id": str(other_org.id)},
    )

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 0
    assert get_response.status_code == 404


def test_limit_default_behavior(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
) -> None:
    client = create_client_record()
    for index in range(3):
        _create_reminder(api_client, organization_id, client_id=client["id"], title=f"Reminder {index}")

    default_response = api_client.get("/v1/reminders", params={"organization_id": organization_id})
    limited_response = api_client.get(
        "/v1/reminders",
        params={"organization_id": organization_id, "limit": 1},
    )

    assert default_response.status_code == 200
    assert default_response.json()["limit"] == 50
    assert default_response.json()["total"] == 3
    assert limited_response.status_code == 200
    assert limited_response.json()["limit"] == 1
    assert len(limited_response.json()["items"]) == 1


def test_missing_or_blank_title_rejected(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
) -> None:
    client = create_client_record()

    missing = api_client.post(
        "/v1/reminders",
        json={"organization_id": organization_id, "client_id": client["id"]},
    )
    blank = api_client.post(
        "/v1/reminders",
        json={"organization_id": organization_id, "client_id": client["id"], "title": "   "},
    )

    assert missing.status_code == 422
    assert blank.status_code == 400
