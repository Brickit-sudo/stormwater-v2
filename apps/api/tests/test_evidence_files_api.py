from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient


def _create_file(
    api_client: TestClient,
    organization_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "organization_id": organization_id,
        "file_name": "Master Service Agreement.pdf",
        "source": "drive_link",
        "public_url": "https://drive.google.com/file/d/abc/view",
    }
    payload.update(overrides)
    response = api_client.post("/v1/files", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_file_linked_to_client(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, Any]],
) -> None:
    client = create_client_record()
    result = _create_file(api_client, organization_id, client_id=client["id"])
    assert result["client_id"] == client["id"]
    assert result["site_id"] is None
    assert result["job_id"] is None
    assert result["source"] == "drive_link"
    assert result["archived_at"] is None


def test_create_file_linked_to_site(
    api_client: TestClient,
    organization_id: str,
    create_site_record: Callable[..., dict[str, Any]],
) -> None:
    site = create_site_record()
    result = _create_file(
        api_client,
        organization_id,
        site_id=site["id"],
        file_name="Site Plan v3.pdf",
        mime_type="application/pdf",
    )
    assert result["site_id"] == site["id"]
    assert result["mime_type"] == "application/pdf"


def test_create_file_linked_to_job(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    job = create_job_record()
    result = _create_file(
        api_client,
        organization_id,
        job_id=job["id"],
        file_name="Field Notes.pdf",
        caption="Pre-inspection scope",
    )
    assert result["job_id"] == job["id"]
    assert result["caption"] == "Pre-inspection scope"


def test_create_google_drive_picker_metadata(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    job = create_job_record()
    result = _create_file(
        api_client,
        organization_id,
        job_id=job["id"],
        file_name="Picked Site Plan.pdf",
        source="google_drive",
        public_url="https://drive.google.com/file/d/drive-picked-123/view",
        drive_file_id="drive-picked-123",
        mime_type="application/pdf",
    )
    assert result["job_id"] == job["id"]
    assert result["source"] == "google_drive"
    assert result["drive_file_id"] == "drive-picked-123"
    assert result["public_url"].startswith("https://drive.google.com/")
    assert result["size_bytes"] is None


def test_list_files_by_organization_id(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, Any]],
) -> None:
    client = create_client_record()
    _create_file(api_client, organization_id, client_id=client["id"], file_name="A.pdf")
    _create_file(api_client, organization_id, client_id=client["id"], file_name="B.pdf")

    response = api_client.get("/v1/files", params={"organization_id": organization_id})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert data["limit"] == 50
    assert data["offset"] == 0


def test_list_files_filter_by_client_id(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, Any]],
) -> None:
    a = create_client_record(name="A", client_code="A")
    b = create_client_record(name="B", client_code="B")
    _create_file(api_client, organization_id, client_id=a["id"], file_name="for-a.pdf")
    _create_file(api_client, organization_id, client_id=b["id"], file_name="for-b.pdf")

    response = api_client.get(
        "/v1/files",
        params={"organization_id": organization_id, "client_id": a["id"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["file_name"] == "for-a.pdf"


def test_list_files_filter_by_site_id(
    api_client: TestClient,
    organization_id: str,
    create_site_record: Callable[..., dict[str, Any]],
) -> None:
    site_a = create_site_record(site_code="SA", name="Site A")
    site_b = create_site_record(site_code="SB", name="Site B")
    _create_file(api_client, organization_id, site_id=site_a["id"], file_name="a.pdf")
    _create_file(api_client, organization_id, site_id=site_b["id"], file_name="b.pdf")

    response = api_client.get(
        "/v1/files",
        params={"organization_id": organization_id, "site_id": site_a["id"]},
    )
    assert response.json()["total"] == 1


def test_list_files_filter_by_job_id(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    job_a = create_job_record(job_code="JA", name="Job A")
    job_b = create_job_record(job_code="JB", name="Job B")
    _create_file(api_client, organization_id, job_id=job_a["id"], file_name="ja.pdf")
    _create_file(api_client, organization_id, job_id=job_b["id"], file_name="jb.pdf")
    _create_file(api_client, organization_id, job_id=job_b["id"], file_name="jb2.pdf")

    response = api_client.get(
        "/v1/files",
        params={"organization_id": organization_id, "job_id": job_b["id"]},
    )
    data = response.json()
    assert data["total"] == 2
    names = {item["file_name"] for item in data["items"]}
    assert names == {"jb.pdf", "jb2.pdf"}


def test_patch_file_metadata(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, Any]],
) -> None:
    client = create_client_record()
    created = _create_file(api_client, organization_id, client_id=client["id"])

    response = api_client.patch(
        f"/v1/files/{created['id']}",
        params={"organization_id": organization_id},
        json={"caption": "Updated", "source": "other"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["caption"] == "Updated"
    assert data["source"] == "other"


def test_archive_file_and_exclude_from_list(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, Any]],
) -> None:
    client = create_client_record()
    created = _create_file(api_client, organization_id, client_id=client["id"])

    response = api_client.delete(
        f"/v1/files/{created['id']}",
        params={"organization_id": organization_id},
    )
    assert response.status_code == 200
    assert response.json()["archived_at"] is not None

    list_response = api_client.get(
        "/v1/files",
        params={"organization_id": organization_id},
    )
    assert list_response.json()["total"] == 0


def test_organization_scoping_isolates_files(
    api_client: TestClient,
    organization_id: str,
    db_session: Any,
    create_client_record: Callable[..., dict[str, Any]],
) -> None:
    from app.models import Organization

    other_org = Organization(name="Other Org")
    db_session.add(other_org)
    db_session.commit()
    db_session.refresh(other_org)

    client = create_client_record()
    _create_file(api_client, organization_id, client_id=client["id"])

    response = api_client.get(
        "/v1/files",
        params={"organization_id": str(other_org.id)},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_create_fails_when_file_name_missing(
    api_client: TestClient,
    organization_id: str,
) -> None:
    response = api_client.post(
        "/v1/files",
        json={"organization_id": organization_id, "source": "drive_link"},
    )
    assert response.status_code == 422


def test_create_fails_when_file_name_blank(
    api_client: TestClient,
    organization_id: str,
) -> None:
    response = api_client.post(
        "/v1/files",
        json={
            "organization_id": organization_id,
            "file_name": "",
            "source": "drive_link",
        },
    )
    assert response.status_code == 422


def test_create_fails_without_parent_scope(
    api_client: TestClient,
    organization_id: str,
) -> None:
    response = api_client.post(
        "/v1/files",
        json={
            "organization_id": organization_id,
            "file_name": "orphan.pdf",
            "source": "drive_link",
        },
    )
    assert response.status_code == 400
    assert "Exactly one" in response.json()["detail"]


def test_create_fails_with_multiple_parent_scopes(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, Any]],
    create_site_record: Callable[..., dict[str, Any]],
) -> None:
    client = create_client_record()
    site = create_site_record(client_id=client["id"])
    response = api_client.post(
        "/v1/files",
        json={
            "organization_id": organization_id,
            "file_name": "too-many-parents.pdf",
            "source": "drive_link",
            "client_id": client["id"],
            "site_id": site["id"],
        },
    )
    assert response.status_code == 400
    assert "Exactly one" in response.json()["detail"]


def test_get_archived_file_returns_404(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, Any]],
) -> None:
    client = create_client_record()
    created = _create_file(api_client, organization_id, client_id=client["id"])
    api_client.delete(
        f"/v1/files/{created['id']}",
        params={"organization_id": organization_id},
    )
    response = api_client.get(
        f"/v1/files/{created['id']}",
        params={"organization_id": organization_id},
    )
    assert response.status_code == 404


def test_list_default_limit_is_50(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, Any]],
) -> None:
    client = create_client_record()
    _create_file(api_client, organization_id, client_id=client["id"])
    response = api_client.get(
        "/v1/files",
        params={"organization_id": organization_id},
    )
    assert response.json()["limit"] == 50
