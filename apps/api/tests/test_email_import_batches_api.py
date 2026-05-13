from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Organization


def _create_batch(
    api_client: TestClient,
    organization_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "organization_id": organization_id,
        "provider": "outlook",
        "import_mode": "manual_seed",
        "folder_id": "inbox",
        "search_query": "stormwater OR catch basin",
        "date_from": "2026-05-01T00:00:00Z",
        "date_to": "2026-05-12T23:59:59Z",
        "status": "seed",
        "preview_count": 5,
        "imported_count": 5,
        "skipped_count": 0,
        "duplicate_count": 0,
        "error_count": 0,
        "request_json": {"source": "seed"},
        "result_summary_json": {"note": "Seeded local email examples"},
    }
    payload.update(overrides)
    response = api_client.post("/v1/email-import-batches", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_list_and_get_email_import_batch(
    api_client: TestClient,
    organization_id: str,
) -> None:
    batch = _create_batch(api_client, organization_id)

    list_response = api_client.get(
        "/v1/email-import-batches",
        params={"organization_id": organization_id},
    )
    get_response = api_client.get(
        f"/v1/email-import-batches/{batch['id']}",
        params={"organization_id": organization_id},
    )

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1
    assert list_response.json()["limit"] == 50
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "seed"
    assert get_response.json()["imported_count"] == 5


def test_email_import_batches_filter_by_status_provider_and_limit(
    api_client: TestClient,
    organization_id: str,
) -> None:
    _create_batch(api_client, organization_id, status="seed")
    _create_batch(
        api_client,
        organization_id,
        status="previewed",
        provider="local",
        folder_id="archive",
    )

    status_response = api_client.get(
        "/v1/email-import-batches",
        params={"organization_id": organization_id, "status": "previewed"},
    )
    provider_response = api_client.get(
        "/v1/email-import-batches",
        params={"organization_id": organization_id, "provider": "local", "limit": 1},
    )

    assert status_response.status_code == 200
    assert status_response.json()["total"] == 1
    assert provider_response.status_code == 200
    assert provider_response.json()["total"] == 1
    assert provider_response.json()["limit"] == 1


def test_email_import_batches_are_organization_scoped(
    api_client: TestClient,
    db_session: Session,
    organization_id: str,
) -> None:
    other_org = Organization(name="Other Org")
    db_session.add(other_org)
    db_session.commit()
    db_session.refresh(other_org)

    batch = _create_batch(api_client, organization_id)

    list_response = api_client.get(
        "/v1/email-import-batches",
        params={"organization_id": str(other_org.id)},
    )
    get_response = api_client.get(
        f"/v1/email-import-batches/{batch['id']}",
        params={"organization_id": str(other_org.id)},
    )

    assert list_response.status_code == 200
    assert list_response.json()["total"] == 0
    assert get_response.status_code == 404


def test_archived_import_batches_excluded_by_default(
    api_client: TestClient,
    organization_id: str,
) -> None:
    _create_batch(api_client, organization_id, status="seed")
    _create_batch(api_client, organization_id, status="archived", folder_id="archived")

    normal = api_client.get("/v1/email-import-batches", params={"organization_id": organization_id})
    archived = api_client.get(
        "/v1/email-import-batches",
        params={"organization_id": organization_id, "status": "archived"},
    )

    assert normal.status_code == 200
    assert normal.json()["total"] == 1
    assert archived.status_code == 200
    assert archived.json()["total"] == 1
