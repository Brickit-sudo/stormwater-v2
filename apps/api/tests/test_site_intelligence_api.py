from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import BmpSystem, Observation, Organization


def _create_bmp(
    db_session: Session,
    organization_id: str,
    site_id: str,
    *,
    system_code: str = "CB-1",
) -> BmpSystem:
    system = BmpSystem(
        organization_id=uuid.UUID(organization_id),
        site_id=uuid.UUID(site_id),
        system_code=system_code,
        system_type="catch_basin",
        name=f"Catch Basin {system_code}",
        location_description="North lot",
    )
    db_session.add(system)
    db_session.commit()
    db_session.refresh(system)
    return system


def _create_observation(
    db_session: Session,
    organization_id: str,
    job_id: str,
    system_id: str,
) -> Observation:
    observation = Observation(
        organization_id=uuid.UUID(organization_id),
        job_id=uuid.UUID(job_id),
        system_id=uuid.UUID(system_id),
        observation_type="inspection_finding",
        finding="Sediment is visible in the sump.",
        recommendation="Schedule cleanout before closeout.",
        severity="medium",
        maintenance_needed=True,
    )
    db_session.add(observation)
    db_session.commit()
    db_session.refresh(observation)
    return observation


def test_list_bmp_systems_and_observations_by_site(
    api_client: TestClient,
    organization_id: str,
    db_session: Session,
    create_site_record: Callable[..., dict[str, Any]],
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    site = create_site_record()
    job = create_job_record(client_id=site["client_id"], site_id=site["id"])
    system = _create_bmp(db_session, organization_id, site["id"])
    _create_observation(db_session, organization_id, job["id"], str(system.id))

    bmp_response = api_client.get(
        "/v1/bmp-systems",
        params={"organization_id": organization_id, "site_id": site["id"]},
    )
    assert bmp_response.status_code == 200
    assert bmp_response.json()["total"] == 1
    assert bmp_response.json()["items"][0]["system_code"] == "CB-1"

    observation_response = api_client.get(
        "/v1/observations",
        params={"organization_id": organization_id, "site_id": site["id"]},
    )
    assert observation_response.status_code == 200
    assert observation_response.json()["total"] == 1
    assert observation_response.json()["items"][0]["system_id"] == str(system.id)


def test_record_notes_crud_archive_and_allowed_type_validation(
    api_client: TestClient,
    organization_id: str,
    create_site_record: Callable[..., dict[str, Any]],
) -> None:
    site = create_site_record()
    create_response = api_client.post(
        "/v1/record-notes",
        json={
            "organization_id": organization_id,
            "parent_type": "site",
            "parent_id": site["id"],
            "title": "Gate code",
            "body": "Use rear gate before 7 AM.",
            "note_type": "site_access",
        },
    )
    assert create_response.status_code == 201, create_response.text
    note = create_response.json()

    list_response = api_client.get(
        "/v1/record-notes",
        params={
            "organization_id": organization_id,
            "parent_type": "site",
            "parent_id": site["id"],
        },
    )
    assert list_response.json()["total"] == 1

    patch_response = api_client.patch(
        f"/v1/record-notes/{note['id']}",
        params={"organization_id": organization_id},
        json={"title": "Updated gate code"},
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["title"] == "Updated gate code"

    invalid_response = api_client.post(
        "/v1/record-notes",
        json={
            "organization_id": organization_id,
            "parent_type": "spreadsheet",
            "parent_id": site["id"],
            "title": "Bad",
            "body": "Bad",
        },
    )
    assert invalid_response.status_code == 400

    delete_response = api_client.delete(
        f"/v1/record-notes/{note['id']}",
        params={"organization_id": organization_id},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["archived_at"] is not None


def test_knowledge_items_are_scoped_and_type_validated(
    api_client: TestClient,
    organization_id: str,
    create_site_record: Callable[..., dict[str, Any]],
) -> None:
    site = create_site_record()
    response = api_client.post(
        "/v1/knowledge-items",
        json={
            "organization_id": organization_id,
            "site_id": site["id"],
            "title": "Access note",
            "content": "Unlock rear gate first.",
            "knowledge_type": "site_access",
            "tags_json": ["access"],
        },
    )
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["knowledge_type"] == "site_access"

    list_response = api_client.get(
        "/v1/knowledge-items",
        params={"organization_id": organization_id, "site_id": site["id"]},
    )
    assert list_response.json()["total"] == 1

    invalid_response = api_client.post(
        "/v1/knowledge-items",
        json={
            "organization_id": organization_id,
            "site_id": site["id"],
            "title": "Loose note",
            "content": "No bucket.",
            "knowledge_type": "misc",
        },
    )
    assert invalid_response.status_code == 400


def test_knowledge_and_documents_allow_related_scope_combinations(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, Any]],
    create_site_record: Callable[..., dict[str, Any]],
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    client = create_client_record()
    site = create_site_record(client_id=client["id"])
    job = create_job_record(client_id=client["id"], site_id=site["id"])

    site_job_knowledge = api_client.post(
        "/v1/knowledge-items",
        json={
            "organization_id": organization_id,
            "site_id": site["id"],
            "job_id": job["id"],
            "title": "Job access",
            "content": "Use the same staging area for this job.",
            "knowledge_type": "site_access",
        },
    )
    assert site_job_knowledge.status_code == 201, site_job_knowledge.text

    full_scope_knowledge = api_client.post(
        "/v1/knowledge-items",
        json={
            "organization_id": organization_id,
            "client_id": client["id"],
            "site_id": site["id"],
            "job_id": job["id"],
            "title": "Client site job context",
            "content": "Client prefers the report note to mention the basin ID.",
            "knowledge_type": "client_preference",
        },
    )
    assert full_scope_knowledge.status_code == 201, full_scope_knowledge.text

    site_job_document = api_client.post(
        "/v1/documents",
        json={
            "organization_id": organization_id,
            "site_id": site["id"],
            "job_id": job["id"],
            "source": "demo_test",
            "file_name": "Job Photosheet.pdf",
            "document_type": "photosheet",
        },
    )
    assert site_job_document.status_code == 201, site_job_document.text

    unscoped_knowledge = api_client.post(
        "/v1/knowledge-items",
        json={
            "organization_id": organization_id,
            "title": "Reusable report phrase",
            "content": "Use this only as general report language.",
            "knowledge_type": "report_language",
        },
    )
    assert unscoped_knowledge.status_code == 201, unscoped_knowledge.text

    unscoped_document = api_client.post(
        "/v1/documents",
        json={
            "organization_id": organization_id,
            "source": "manual",
            "file_name": "General Reference.pdf",
            "document_type": "unknown",
        },
    )
    assert unscoped_document.status_code == 201, unscoped_document.text


def test_knowledge_item_source_type_and_source_id_must_be_paired(
    api_client: TestClient,
    organization_id: str,
    create_site_record: Callable[..., dict[str, Any]],
) -> None:
    site = create_site_record()
    base_payload = {
        "organization_id": organization_id,
        "site_id": site["id"],
        "title": "Source pairing",
        "content": "Source metadata should be complete when present.",
        "knowledge_type": "site_access",
    }

    source_id_only = api_client.post(
        "/v1/knowledge-items",
        json={**base_payload, "source_id": site["id"]},
    )
    assert source_id_only.status_code == 400

    source_type_only = api_client.post(
        "/v1/knowledge-items",
        json={**base_payload, "source_type": "site"},
    )
    assert source_type_only.status_code == 400

    both_source_fields = api_client.post(
        "/v1/knowledge-items",
        json={**base_payload, "source_type": "site", "source_id": site["id"]},
    )
    assert both_source_fields.status_code == 201, both_source_fields.text

    neither_source_field = api_client.post(
        "/v1/knowledge-items",
        json={**base_payload, "title": "No source metadata"},
    )
    assert neither_source_field.status_code == 201, neither_source_field.text


def test_document_intake_records_chunks_fields_and_link_suggestions(
    api_client: TestClient,
    organization_id: str,
    create_site_record: Callable[..., dict[str, Any]],
) -> None:
    site = create_site_record()
    create_document = api_client.post(
        "/v1/documents",
        json={
            "organization_id": organization_id,
            "site_id": site["id"],
            "source": "demo_test",
            "file_name": "Inspection Report.pdf",
            "document_type": "report",
            "status": "queued",
            "extraction_status": "complete",
        },
    )
    assert create_document.status_code == 201, create_document.text
    document = create_document.json()

    chunk_response = api_client.post(
        f"/v1/documents/{document['id']}/chunks",
        json={
            "organization_id": organization_id,
            "chunk_index": 0,
            "heading": "Summary",
            "text": "Synthetic inspection summary.",
            "token_count": 3,
        },
    )
    assert chunk_response.status_code == 201, chunk_response.text

    field_response = api_client.post(
        f"/v1/documents/{document['id']}/extracted-fields",
        json={
            "organization_id": organization_id,
            "field_name": "inspection_date",
            "field_value": "2026-05-14",
            "confidence": 0.9,
        },
    )
    assert field_response.status_code == 201, field_response.text
    field = field_response.json()

    suggestion_response = api_client.post(
        f"/v1/documents/{document['id']}/link-suggestions",
        json={
            "organization_id": organization_id,
            "target_type": "site",
            "target_id": site["id"],
            "target_label": site["name"],
            "confidence": 0.95,
        },
    )
    assert suggestion_response.status_code == 201, suggestion_response.text
    suggestion = suggestion_response.json()

    assert api_client.get(
        f"/v1/documents/{document['id']}/chunks",
        params={"organization_id": organization_id},
    ).json()["total"] == 1

    field_patch = api_client.patch(
        f"/v1/documents/{document['id']}/extracted-fields/{field['id']}",
        params={"organization_id": organization_id},
        json={"review_status": "approved"},
    )
    assert field_patch.status_code == 200
    assert field_patch.json()["review_status"] == "approved"

    suggestion_patch = api_client.patch(
        f"/v1/documents/{document['id']}/link-suggestions/{suggestion['id']}",
        params={"organization_id": organization_id},
        json={"review_status": "rejected"},
    )
    assert suggestion_patch.status_code == 200
    assert suggestion_patch.json()["review_status"] == "rejected"


def test_record_links_create_list_archive_and_organization_scoping(
    api_client: TestClient,
    organization_id: str,
    db_session: Session,
    create_site_record: Callable[..., dict[str, Any]],
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    site = create_site_record()
    job = create_job_record(client_id=site["client_id"], site_id=site["id"])

    created_response = api_client.post(
        "/v1/record-links",
        json={
            "organization_id": organization_id,
            "source_type": "job",
            "source_id": job["id"],
            "target_type": "site",
            "target_id": site["id"],
            "relationship_type": "scheduled_at",
            "confidence": 1.0,
        },
    )
    assert created_response.status_code == 201, created_response.text
    link = created_response.json()

    list_response = api_client.get(
        "/v1/record-links",
        params={
            "organization_id": organization_id,
            "target_type": "site",
            "target_id": site["id"],
        },
    )
    assert list_response.json()["total"] == 1

    other_org = Organization(name="Other Org")
    db_session.add(other_org)
    db_session.commit()
    db_session.refresh(other_org)
    scoped_response = api_client.get(
        "/v1/record-links",
        params={"organization_id": str(other_org.id), "target_type": "site", "target_id": site["id"]},
    )
    assert scoped_response.status_code == 200
    assert scoped_response.json()["total"] == 0

    delete_response = api_client.delete(
        f"/v1/record-links/{link['id']}",
        params={"organization_id": organization_id},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["archived_at"] is not None
