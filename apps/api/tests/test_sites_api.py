from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Organization


def test_site_create_requires_client_id(api_client: TestClient, organization_id: str) -> None:
    response = api_client.post(
        "/v1/sites",
        json={"organization_id": organization_id, "name": "Missing Client"},
    )

    assert response.status_code == 422


def test_create_list_get_patch_archive_site_and_client_link(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
) -> None:
    client = create_client_record()
    create_response = api_client.post(
        "/v1/sites",
        json={
            "organization_id": organization_id,
            "client_id": client["id"],
            "name": "West Pond",
            "city": "Durham",
            "status": "active",
        },
    )
    assert create_response.status_code == 201
    site = create_response.json()
    assert site["client_id"] == client["id"]

    list_response = api_client.get("/v1/sites", params={"organization_id": organization_id})
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    linked_response = api_client.get(
        f"/v1/clients/{client['id']}/sites",
        params={"organization_id": organization_id},
    )
    assert linked_response.status_code == 200
    assert linked_response.json()["items"][0]["id"] == site["id"]

    get_response = api_client.get(f"/v1/sites/{site['id']}", params={"organization_id": organization_id})
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "West Pond"

    patch_response = api_client.patch(
        f"/v1/sites/{site['id']}",
        params={"organization_id": organization_id},
        json={"status": "inactive", "notes": "Access gate locked"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "inactive"

    delete_response = api_client.delete(
        f"/v1/sites/{site['id']}",
        params={"organization_id": organization_id},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["archived_at"] is not None

    list_after_archive = api_client.get("/v1/sites", params={"organization_id": organization_id})
    assert list_after_archive.status_code == 200
    assert list_after_archive.json()["total"] == 0


def test_site_rejects_client_from_other_organization(
    api_client: TestClient,
    db_session: Session,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
) -> None:
    other_org = Organization(name="Other Organization")
    db_session.add(other_org)
    db_session.commit()
    db_session.refresh(other_org)
    other_client = create_client_record(organization_id=str(other_org.id), name="Other Client")

    response = api_client.post(
        "/v1/sites",
        json={
            "organization_id": organization_id,
            "client_id": other_client["id"],
            "name": "Wrong Org Site",
        },
    )

    assert response.status_code == 404


def test_site_patch_rejects_null_required_relationship(
    api_client: TestClient,
    organization_id: str,
    create_site_record: Callable[..., dict[str, object]],
) -> None:
    site = create_site_record()

    response = api_client.patch(
        f"/v1/sites/{site['id']}",
        params={"organization_id": organization_id},
        json={"client_id": None},
    )

    assert response.status_code == 400
