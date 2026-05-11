from __future__ import annotations

from collections.abc import Callable

from fastapi.testclient import TestClient


def test_job_create_requires_site_id(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
) -> None:
    client = create_client_record()
    response = api_client.post(
        "/v1/jobs",
        json={
            "organization_id": organization_id,
            "client_id": client["id"],
            "name": "Missing Site",
        },
    )

    assert response.status_code == 422


def test_create_list_get_patch_archive_job_and_linked_routes(
    api_client: TestClient,
    organization_id: str,
    create_site_record: Callable[..., dict[str, object]],
) -> None:
    site = create_site_record()
    create_response = api_client.post(
        "/v1/jobs",
        json={
            "organization_id": organization_id,
            "client_id": site["client_id"],
            "site_id": site["id"],
            "name": "Annual Inspection",
            "service_type": "Inspection",
            "status": "scheduled",
            "scheduled_date": "2026-06-15",
        },
    )
    assert create_response.status_code == 201
    job = create_response.json()
    assert job["client_id"] == site["client_id"]
    assert job["site_id"] == site["id"]

    list_response = api_client.get("/v1/jobs", params={"organization_id": organization_id})
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    client_jobs_response = api_client.get(
        f"/v1/clients/{site['client_id']}/jobs",
        params={"organization_id": organization_id},
    )
    assert client_jobs_response.status_code == 200
    assert client_jobs_response.json()["items"][0]["id"] == job["id"]

    site_jobs_response = api_client.get(
        f"/v1/sites/{site['id']}/jobs",
        params={"organization_id": organization_id},
    )
    assert site_jobs_response.status_code == 200
    assert site_jobs_response.json()["items"][0]["id"] == job["id"]

    get_response = api_client.get(f"/v1/jobs/{job['id']}", params={"organization_id": organization_id})
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Annual Inspection"

    patch_response = api_client.patch(
        f"/v1/jobs/{job['id']}",
        params={"organization_id": organization_id},
        json={"status": "completed", "completed_date": "2026-06-16"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["status"] == "completed"

    delete_response = api_client.delete(
        f"/v1/jobs/{job['id']}",
        params={"organization_id": organization_id},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["archived_at"] is not None

    list_after_archive = api_client.get("/v1/jobs", params={"organization_id": organization_id})
    assert list_after_archive.status_code == 200
    assert list_after_archive.json()["total"] == 0


def test_job_rejects_site_that_does_not_belong_to_client(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
    create_site_record: Callable[..., dict[str, object]],
) -> None:
    site = create_site_record()
    other_client = create_client_record(name="Other Same Org Client")

    response = api_client.post(
        "/v1/jobs",
        json={
            "organization_id": organization_id,
            "client_id": other_client["id"],
            "site_id": site["id"],
            "name": "Mismatched Job",
        },
    )

    assert response.status_code == 400


def test_job_patch_rejects_null_required_fields(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, object]],
) -> None:
    job = create_job_record()

    response = api_client.patch(
        f"/v1/jobs/{job['id']}",
        params={"organization_id": organization_id},
        json={"status": None},
    )

    assert response.status_code == 400
