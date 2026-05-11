from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient


def test_client_create_requires_organization_id(api_client: TestClient) -> None:
    response = api_client.post("/v1/clients", json={"name": "Missing Org"})

    assert response.status_code == 422


def test_create_list_get_patch_archive_client(
    api_client: TestClient,
    organization_id: str,
) -> None:
    create_response = api_client.post(
        "/v1/clients",
        json={
            "organization_id": organization_id,
            "name": "Brightwater HOA",
            "client_code": "BWHOA",
            "email": "ops@example.com",
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["organization_id"] == organization_id
    assert created["status"] == "active"
    assert created["archived_at"] is None

    list_response = api_client.get("/v1/clients", params={"organization_id": organization_id})
    assert list_response.status_code == 200
    listed = list_response.json()
    assert listed["total"] == 1
    assert listed["limit"] == 50
    assert listed["items"][0]["id"] == created["id"]

    get_response = api_client.get(
        f"/v1/clients/{created['id']}",
        params={"organization_id": organization_id},
    )
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Brightwater HOA"

    patch_response = api_client.patch(
        f"/v1/clients/{created['id']}",
        params={"organization_id": organization_id},
        json={"status": "inactive", "notes": "Paused account"},
    )
    assert patch_response.status_code == 200
    patched = patch_response.json()
    assert patched["status"] == "inactive"
    assert patched["notes"] == "Paused account"

    delete_response = api_client.delete(
        f"/v1/clients/{created['id']}",
        params={"organization_id": organization_id},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["archived_at"] is not None

    list_after_archive = api_client.get("/v1/clients", params={"organization_id": organization_id})
    assert list_after_archive.status_code == 200
    assert list_after_archive.json()["total"] == 0

    get_after_archive = api_client.get(
        f"/v1/clients/{created['id']}",
        params={"organization_id": organization_id},
    )
    assert get_after_archive.status_code == 404


def test_clients_list_limit_and_max_validation(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
) -> None:
    create_client_record(name="A Client")
    create_client_record(name="B Client")

    limited_response = api_client.get(
        "/v1/clients",
        params={"organization_id": organization_id, "limit": 1},
    )
    assert limited_response.status_code == 200
    body = limited_response.json()
    assert body["total"] == 2
    assert body["limit"] == 1
    assert len(body["items"]) == 1

    too_large_response = api_client.get(
        "/v1/clients",
        params={"organization_id": organization_id, "limit": 501},
    )
    assert too_large_response.status_code == 422


def test_client_patch_rejects_null_required_fields(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
) -> None:
    client = create_client_record()

    response = api_client.patch(
        f"/v1/clients/{client['id']}",
        params={"organization_id": organization_id},
        json={"name": None},
    )

    assert response.status_code == 400
