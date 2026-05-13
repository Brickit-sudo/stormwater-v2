from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import date
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Job, Organization


def _create_file(
    api_client: TestClient,
    organization_id: str,
    *,
    job_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "organization_id": organization_id,
        "job_id": job_id,
        "file_name": "Inspection evidence.pdf",
        "source": "drive_link",
        "public_url": "https://drive.google.com/file/d/readiness/view",
        "caption": "Inspection evidence.",
    }
    payload.update(overrides)
    response = api_client.post("/v1/files", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _create_email(
    api_client: TestClient,
    organization_id: str,
    *,
    job_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "organization_id": organization_id,
        "job_id": job_id,
        "provider": "outlook",
        "provider_message_id": f"readiness-{uuid.uuid4()}",
        "subject": "Report context",
        "sender": "client@example.com",
        "body_text": "Local report context for the job.",
    }
    payload.update(overrides)
    response = api_client.post("/v1/email-messages", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _create_draft(
    api_client: TestClient,
    organization_id: str,
    *,
    job_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "organization_id": organization_id,
        "job_id": job_id,
        "draft_type": "report_section",
        "title": "Report section draft",
        "prompt_context": "Local readiness test context.",
        "draft_text": "The site was inspected and supporting evidence is linked.",
        "status": "draft",
    }
    payload.update(overrides)
    response = api_client.post("/v1/ai-drafts", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _create_reminder(
    api_client: TestClient,
    organization_id: str,
    *,
    job_id: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "organization_id": organization_id,
        "job_id": job_id,
        "title": "Review field issue",
        "description": "Local readiness reminder.",
        "status": "open",
        "priority": "medium",
        "due_at": "2026-05-20T12:00:00Z",
    }
    payload.update(overrides)
    response = api_client.post("/v1/reminders", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _readiness(
    api_client: TestClient,
    organization_id: str,
    job_id: str,
) -> dict[str, Any]:
    response = api_client.get(
        f"/v1/jobs/{job_id}/report-readiness",
        params={"organization_id": organization_id},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _check(data: dict[str, Any], key: str) -> dict[str, Any]:
    return next(item for item in data["checks"] if item["key"] == key)


def _report_ready_job(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, Any]],
    **overrides: Any,
) -> dict[str, Any]:
    job_defaults: dict[str, Any] = {
        "status": "scheduled",
        "service_type": "Annual inspection",
        "due_date": "2026-06-01",
        "scope": "Inspect BMPs and document report evidence.",
        "drive_folder_url": "https://drive.google.com/drive/folders/readiness-job",
    }
    job_defaults.update(overrides)
    job = create_job_record(**job_defaults)
    file = _create_file(api_client, organization_id, job_id=job["id"])
    email = _create_email(api_client, organization_id, job_id=job["id"])
    _create_draft(
        api_client,
        organization_id,
        job_id=job["id"],
        email_message_id=email["id"],
        draft_type="email_reply",
        title="Useful job reply",
    )
    assert file["job_id"] == job["id"]
    return job


def test_report_readiness_response_shape_and_ready_status(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    job = _report_ready_job(api_client, organization_id, create_job_record)

    data = _readiness(api_client, organization_id, job["id"])

    assert set(data) == {
        "job_id",
        "overall_status",
        "score",
        "summary",
        "checks",
        "blockers",
        "warnings",
        "ready_items",
    }
    assert data["job_id"] == job["id"]
    assert data["overall_status"] == "ready"
    assert data["blockers"] == []
    assert data["warnings"] == []
    assert isinstance(data["score"], int)
    assert {
        "client_linked",
        "site_linked",
        "service_type",
        "job_status",
        "date_readiness",
        "scope_notes",
        "evidence_files",
        "drive_context",
        "open_reminders",
        "ai_drafts",
        "email_context",
        "timeline_activity",
    } == {item["key"] for item in data["checks"]}
    for item in data["checks"]:
        assert set(item) == {
            "key",
            "label",
            "group",
            "status",
            "severity",
            "message",
            "related_count",
            "suggested_next_step",
        }


def test_report_readiness_organization_scoping_is_enforced(
    api_client: TestClient,
    db_session: Session,
    organization_id: str,
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    other_org = Organization(name="Other Org")
    db_session.add(other_org)
    db_session.commit()
    db_session.refresh(other_org)
    job = create_job_record()

    response = api_client.get(
        f"/v1/jobs/{job['id']}/report-readiness",
        params={"organization_id": str(other_org.id)},
    )

    assert response.status_code == 404
    assert "Job not found" in response.json()["detail"]


def test_missing_client_creates_high_failure_and_block(
    api_client: TestClient,
    db_session: Session,
    organization_id: str,
) -> None:
    job = Job(
        organization_id=uuid.UUID(organization_id),
        client_id=uuid.uuid4(),
        site_id=uuid.uuid4(),
        name="Orphaned Client Job",
        service_type="Inspection",
        status="scheduled",
        due_date=date(2026, 6, 1),
        scope="Inspect site.",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    data = _readiness(api_client, organization_id, str(job.id))

    assert data["overall_status"] == "blocked"
    client_check = _check(data, "client_linked")
    assert client_check["status"] == "fail"
    assert client_check["severity"] == "high"
    assert any(item["key"] == "client_linked" for item in data["blockers"])


def test_missing_site_creates_high_failure_and_block(
    api_client: TestClient,
    db_session: Session,
    organization_id: str,
    create_client_record: Callable[..., dict[str, Any]],
) -> None:
    client = create_client_record()
    job = Job(
        organization_id=uuid.UUID(organization_id),
        client_id=uuid.UUID(client["id"]),
        site_id=uuid.uuid4(),
        name="Orphaned Site Job",
        service_type="Inspection",
        status="scheduled",
        due_date=date(2026, 6, 1),
        scope="Inspect site.",
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    data = _readiness(api_client, organization_id, str(job.id))

    assert data["overall_status"] == "blocked"
    site_check = _check(data, "site_linked")
    assert site_check["status"] == "fail"
    assert site_check["severity"] == "high"
    assert any(item["key"] == "site_linked" for item in data["blockers"])


def test_missing_service_type_warns_without_blocking(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    job = create_job_record(service_type=None, scope="Inspection scope.", drive_folder_url="https://drive.example/job")
    _create_file(api_client, organization_id, job_id=job["id"])
    _create_email(api_client, organization_id, job_id=job["id"])
    _create_draft(api_client, organization_id, job_id=job["id"])

    data = _readiness(api_client, organization_id, job["id"])

    service_check = _check(data, "service_type")
    assert service_check["status"] == "warning"
    assert service_check["severity"] == "medium"
    assert data["overall_status"] == "needs_attention"
    assert data["blockers"] == []


def test_no_files_is_medium_warning(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    job = create_job_record(
        scope="Inspection scope.",
        drive_folder_url="https://drive.google.com/drive/folders/no-files",
    )
    _create_email(api_client, organization_id, job_id=job["id"])
    _create_draft(api_client, organization_id, job_id=job["id"])

    data = _readiness(api_client, organization_id, job["id"])

    files_check = _check(data, "evidence_files")
    assert files_check["status"] == "warning"
    assert files_check["severity"] == "medium"
    assert data["overall_status"] == "needs_attention"
    assert data["blockers"] == []


def test_high_priority_overdue_open_reminder_creates_blocker(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    job = _report_ready_job(api_client, organization_id, create_job_record)
    _create_reminder(
        api_client,
        organization_id,
        job_id=job["id"],
        priority="high",
        status="open",
        due_at="2020-01-01T12:00:00Z",
    )

    data = _readiness(api_client, organization_id, job["id"])

    assert data["overall_status"] == "blocked"
    reminder_check = _check(data, "open_reminders")
    assert reminder_check["status"] == "fail"
    assert reminder_check["severity"] == "high"
    assert any(item["key"] == "open_reminders" for item in data["blockers"])


def test_completed_and_archived_reminders_do_not_block(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    job = _report_ready_job(api_client, organization_id, create_job_record)
    _create_reminder(
        api_client,
        organization_id,
        job_id=job["id"],
        priority="high",
        status="completed",
        due_at="2020-01-01T12:00:00Z",
    )
    archived = _create_reminder(
        api_client,
        organization_id,
        job_id=job["id"],
        priority="high",
        status="open",
        due_at="2020-01-01T12:00:00Z",
    )
    archive_response = api_client.delete(
        f"/v1/reminders/{archived['id']}",
        params={"organization_id": organization_id},
    )
    assert archive_response.status_code == 200

    data = _readiness(api_client, organization_id, job["id"])

    assert data["overall_status"] == "ready"
    assert _check(data, "open_reminders")["status"] == "pass"
    assert data["blockers"] == []


def test_ai_draft_presence_improves_readiness(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    job = create_job_record(
        scope="Inspection scope.",
        drive_folder_url="https://drive.google.com/drive/folders/ai-improves",
    )
    _create_file(api_client, organization_id, job_id=job["id"])
    _create_email(api_client, organization_id, job_id=job["id"])

    before = _readiness(api_client, organization_id, job["id"])
    _create_draft(
        api_client,
        organization_id,
        job_id=job["id"],
        draft_type="maintenance_recommendation",
    )
    after = _readiness(api_client, organization_id, job["id"])

    assert _check(before, "ai_drafts")["status"] == "warning"
    assert _check(after, "ai_drafts")["status"] == "pass"
    assert after["score"] > before["score"]


def test_missing_ai_and_email_context_warn_only(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    job = create_job_record(
        scope="Inspection scope.",
        drive_folder_url="https://drive.google.com/drive/folders/optional-context",
    )
    _create_file(api_client, organization_id, job_id=job["id"])

    data = _readiness(api_client, organization_id, job["id"])

    assert data["overall_status"] == "needs_attention"
    assert data["blockers"] == []
    ai_check = _check(data, "ai_drafts")
    email_check = _check(data, "email_context")
    assert ai_check["status"] == "warning"
    assert ai_check["severity"] == "low"
    assert email_check["status"] == "warning"
    assert email_check["severity"] == "low"


def test_archived_job_is_unavailable_and_cancelled_job_is_blocked(
    api_client: TestClient,
    organization_id: str,
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    archived_job = create_job_record(name="Archive readiness")
    archive_response = api_client.delete(
        f"/v1/jobs/{archived_job['id']}",
        params={"organization_id": organization_id},
    )
    assert archive_response.status_code == 200

    unavailable = api_client.get(
        f"/v1/jobs/{archived_job['id']}/report-readiness",
        params={"organization_id": organization_id},
    )
    assert unavailable.status_code == 404

    cancelled_job = _report_ready_job(
        api_client,
        organization_id,
        create_job_record,
        name="Cancelled readiness",
        status="cancelled",
    )
    blocked = _readiness(api_client, organization_id, cancelled_job["id"])
    assert blocked["overall_status"] == "blocked"
    assert _check(blocked, "job_status")["status"] == "fail"


def test_report_readiness_does_not_call_provider_services(
    api_client: TestClient,
    monkeypatch: Any,
    organization_id: str,
    create_job_record: Callable[..., dict[str, Any]],
) -> None:
    from app.services import ai_assistant_service, outlook_drafts_service, outlook_import_service

    def fail_provider_call(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("Report readiness should not call provider services.")

    monkeypatch.setattr(outlook_import_service, "preview_outlook_messages", fail_provider_call)
    monkeypatch.setattr(outlook_import_service, "import_selected_outlook_messages", fail_provider_call)
    monkeypatch.setattr(outlook_drafts_service, "create_outlook_draft_from_ai_draft", fail_provider_call)
    monkeypatch.setattr(ai_assistant_service, "_call_openai_json", fail_provider_call)

    job = _report_ready_job(api_client, organization_id, create_job_record)
    data = _readiness(api_client, organization_id, job["id"])

    assert data["overall_status"] == "ready"
