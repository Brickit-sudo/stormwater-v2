from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client, Job, Organization, Reminder, Site
from app.services.common import CRMNotFoundError, CRMValidationError, Page, paginate


ALLOWED_STATUSES = {"open", "snoozed", "completed", "archived"}
ALLOWED_PRIORITIES = {"low", "medium", "high"}


def _now() -> datetime:
    return datetime.now(UTC)


def _require_organization(db: Session, organization_id: uuid.UUID) -> Organization:
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise CRMNotFoundError("Organization not found.")
    return organization


def _require_client(db: Session, organization_id: uuid.UUID, client_id: uuid.UUID) -> Client:
    statement = select(Client).where(
        Client.organization_id == organization_id,
        Client.id == client_id,
        Client.archived_at.is_(None),
    )
    client = db.scalar(statement)
    if client is None:
        raise CRMNotFoundError("Client not found.")
    return client


def _require_site(db: Session, organization_id: uuid.UUID, site_id: uuid.UUID) -> Site:
    statement = select(Site).where(
        Site.organization_id == organization_id,
        Site.id == site_id,
        Site.archived_at.is_(None),
    )
    site = db.scalar(statement)
    if site is None:
        raise CRMNotFoundError("Site not found.")
    return site


def _require_job(db: Session, organization_id: uuid.UUID, job_id: uuid.UUID) -> Job:
    statement = select(Job).where(
        Job.organization_id == organization_id,
        Job.id == job_id,
        Job.archived_at.is_(None),
    )
    job = db.scalar(statement)
    if job is None:
        raise CRMNotFoundError("Job not found.")
    return job


def _normalize_title(title: str | None) -> str:
    if title is None:
        raise CRMValidationError("title is required.")
    trimmed = title.strip()
    if not trimmed:
        raise CRMValidationError("title is required.")
    return trimmed


def _validate_status(status: str | None) -> str:
    normalized = (status or "open").strip().lower()
    if normalized not in ALLOWED_STATUSES:
        raise CRMValidationError(
            f"status must be one of: {', '.join(sorted(ALLOWED_STATUSES))}.",
        )
    return normalized


def _validate_priority(priority: str | None) -> str:
    normalized = (priority or "medium").strip().lower()
    if normalized not in ALLOWED_PRIORITIES:
        raise CRMValidationError(
            f"priority must be one of: {', '.join(sorted(ALLOWED_PRIORITIES))}.",
        )
    return normalized


def _validate_exact_one_target(
    client_id: uuid.UUID | None,
    site_id: uuid.UUID | None,
    job_id: uuid.UUID | None,
) -> None:
    target_count = sum(value is not None for value in (client_id, site_id, job_id))
    if target_count != 1:
        raise CRMValidationError("Exactly one of client_id, site_id, or job_id is required.")


def _validate_target_exists(
    db: Session,
    *,
    organization_id: uuid.UUID,
    client_id: uuid.UUID | None,
    site_id: uuid.UUID | None,
    job_id: uuid.UUID | None,
) -> None:
    _validate_exact_one_target(client_id, site_id, job_id)
    if client_id is not None:
        _require_client(db, organization_id, client_id)
    if site_id is not None:
        _require_site(db, organization_id, site_id)
    if job_id is not None:
        _require_job(db, organization_id, job_id)


def _apply_status_transition(reminder: Reminder, previous_status: str | None = None) -> None:
    if reminder.status == "completed" and reminder.completed_at is None:
        reminder.completed_at = _now()
    elif previous_status == "completed" and reminder.status in {"open", "snoozed"}:
        reminder.completed_at = None

    if reminder.status == "archived" and reminder.archived_at is None:
        reminder.archived_at = _now()


def get_reminder(
    db: Session,
    *,
    organization_id: uuid.UUID,
    reminder_id: uuid.UUID,
) -> Reminder | None:
    statement = select(Reminder).where(
        Reminder.organization_id == organization_id,
        Reminder.id == reminder_id,
        Reminder.archived_at.is_(None),
    )
    return db.scalar(statement)


def _require_reminder(
    db: Session,
    *,
    organization_id: uuid.UUID,
    reminder_id: uuid.UUID,
) -> Reminder:
    reminder = get_reminder(db, organization_id=organization_id, reminder_id=reminder_id)
    if reminder is None:
        raise CRMNotFoundError("Reminder not found.")
    return reminder


def list_reminders(
    db: Session,
    *,
    organization_id: uuid.UUID,
    status: str | None = None,
    priority: str | None = None,
    client_id: uuid.UUID | None = None,
    site_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    due_before: datetime | None = None,
    due_after: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[Reminder]:
    statement = select(Reminder).where(Reminder.organization_id == organization_id)

    normalized_status = _validate_status(status) if status else None
    if normalized_status == "archived":
        statement = statement.where(Reminder.status == "archived")
    else:
        statement = statement.where(Reminder.archived_at.is_(None))
        if normalized_status:
            statement = statement.where(Reminder.status == normalized_status)

    if priority:
        statement = statement.where(Reminder.priority == _validate_priority(priority))
    if client_id is not None:
        statement = statement.where(Reminder.client_id == client_id)
    if site_id is not None:
        statement = statement.where(Reminder.site_id == site_id)
    if job_id is not None:
        statement = statement.where(Reminder.job_id == job_id)
    if due_before is not None:
        statement = statement.where(Reminder.due_at <= due_before)
    if due_after is not None:
        statement = statement.where(Reminder.due_at >= due_after)

    statement = statement.order_by(
        Reminder.due_at.is_(None),
        Reminder.due_at,
        Reminder.priority,
        Reminder.title,
        Reminder.id,
    )
    return paginate(db, statement, limit=limit, offset=offset)


def create_reminder(db: Session, *, data: dict[str, Any]) -> Reminder:
    organization_id = data.get("organization_id")
    if organization_id is None:
        raise CRMValidationError("organization_id is required.")
    _require_organization(db, organization_id)

    client_id = data.get("client_id")
    site_id = data.get("site_id")
    job_id = data.get("job_id")
    _validate_target_exists(
        db,
        organization_id=organization_id,
        client_id=client_id,
        site_id=site_id,
        job_id=job_id,
    )

    normalized: dict[str, Any] = dict(data)
    normalized["title"] = _normalize_title(normalized.get("title"))
    normalized["status"] = _validate_status(normalized.get("status"))
    normalized["priority"] = _validate_priority(normalized.get("priority"))

    reminder = Reminder(**normalized)
    _apply_status_transition(reminder)
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


def update_reminder(
    db: Session,
    *,
    organization_id: uuid.UUID,
    reminder_id: uuid.UUID,
    data: dict[str, Any],
) -> Reminder:
    if "organization_id" in data:
        raise CRMValidationError("organization_id cannot be changed.")

    reminder = _require_reminder(db, organization_id=organization_id, reminder_id=reminder_id)
    previous_status = reminder.status

    client_id = data.get("client_id", reminder.client_id)
    site_id = data.get("site_id", reminder.site_id)
    job_id = data.get("job_id", reminder.job_id)
    _validate_target_exists(
        db,
        organization_id=organization_id,
        client_id=client_id,
        site_id=site_id,
        job_id=job_id,
    )

    if "title" in data:
        reminder.title = _normalize_title(data["title"])
    if "status" in data:
        reminder.status = _validate_status(data["status"])
    if "priority" in data:
        reminder.priority = _validate_priority(data["priority"])

    for field in (
        "client_id",
        "site_id",
        "job_id",
        "assigned_to",
        "source_type",
        "source_id",
        "description",
        "due_at",
        "reminder_at",
        "completed_at",
    ):
        if field in data:
            setattr(reminder, field, data[field])

    _apply_status_transition(reminder, previous_status=previous_status)
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


def archive_reminder(
    db: Session,
    *,
    organization_id: uuid.UUID,
    reminder_id: uuid.UUID,
) -> Reminder:
    reminder = _require_reminder(db, organization_id=organization_id, reminder_id=reminder_id)
    reminder.status = "archived"
    reminder.archived_at = _now()
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder
