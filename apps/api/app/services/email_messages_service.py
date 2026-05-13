from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Client, EmailImportBatch, EmailMessage, Job, Organization, Site
from app.services.common import CRMNotFoundError, CRMValidationError, Page, paginate


ALLOWED_STATUSES = {"unlinked", "linked", "archived"}
JSON_LIST_FIELDS = {"recipients_json", "attachments_json", "links_json"}


def _now() -> datetime:
    return datetime.now(UTC)


def _normalize_required(value: str | None, field_name: str, default: str | None = None) -> str:
    candidate = default if value is None else value
    trimmed = (candidate or "").strip()
    if not trimmed:
        raise CRMValidationError(f"{field_name} is required.")
    return trimmed


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def validate_status(status: str | None) -> str:
    normalized = (status or "unlinked").strip().lower()
    if normalized not in ALLOWED_STATUSES:
        raise CRMValidationError(
            f"status must be one of: {', '.join(sorted(ALLOWED_STATUSES))}.",
        )
    return normalized


def require_organization(db: Session, organization_id: uuid.UUID) -> Organization:
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise CRMNotFoundError("Organization not found.")
    return organization


def require_client(db: Session, organization_id: uuid.UUID, client_id: uuid.UUID) -> Client:
    statement = select(Client).where(
        Client.organization_id == organization_id,
        Client.id == client_id,
        Client.archived_at.is_(None),
    )
    client = db.scalar(statement)
    if client is None:
        raise CRMNotFoundError("Client not found.")
    return client


def require_site(db: Session, organization_id: uuid.UUID, site_id: uuid.UUID) -> Site:
    statement = select(Site).where(
        Site.organization_id == organization_id,
        Site.id == site_id,
        Site.archived_at.is_(None),
    )
    site = db.scalar(statement)
    if site is None:
        raise CRMNotFoundError("Site not found.")
    return site


def require_job(db: Session, organization_id: uuid.UUID, job_id: uuid.UUID) -> Job:
    statement = select(Job).where(
        Job.organization_id == organization_id,
        Job.id == job_id,
        Job.archived_at.is_(None),
    )
    job = db.scalar(statement)
    if job is None:
        raise CRMNotFoundError("Job not found.")
    return job


def require_import_batch(
    db: Session,
    organization_id: uuid.UUID,
    import_batch_id: uuid.UUID,
) -> EmailImportBatch:
    statement = select(EmailImportBatch).where(
        EmailImportBatch.organization_id == organization_id,
        EmailImportBatch.id == import_batch_id,
        EmailImportBatch.archived_at.is_(None),
    )
    batch = db.scalar(statement)
    if batch is None:
        raise CRMNotFoundError("Email import batch not found.")
    return batch


def get_email_message(
    db: Session,
    *,
    organization_id: uuid.UUID,
    email_message_id: uuid.UUID,
) -> EmailMessage | None:
    statement = select(EmailMessage).where(
        EmailMessage.organization_id == organization_id,
        EmailMessage.id == email_message_id,
        EmailMessage.archived_at.is_(None),
    )
    return db.scalar(statement)


def require_email_message(
    db: Session,
    *,
    organization_id: uuid.UUID,
    email_message_id: uuid.UUID,
) -> EmailMessage:
    message = get_email_message(
        db,
        organization_id=organization_id,
        email_message_id=email_message_id,
    )
    if message is None:
        raise CRMNotFoundError("Email message not found.")
    return message


def normalize_scope(
    db: Session,
    *,
    organization_id: uuid.UUID,
    client_id: uuid.UUID | None,
    site_id: uuid.UUID | None,
    job_id: uuid.UUID | None,
) -> tuple[uuid.UUID | None, uuid.UUID | None, uuid.UUID | None]:
    if job_id is not None:
        job = require_job(db, organization_id, job_id)
        if site_id is not None and site_id != job.site_id:
            raise CRMValidationError("job_id does not belong to the provided site_id.")
        if client_id is not None and client_id != job.client_id:
            raise CRMValidationError("job_id does not belong to the provided client_id.")
        site_id = job.site_id
        client_id = job.client_id

    if site_id is not None:
        site = require_site(db, organization_id, site_id)
        if client_id is not None and client_id != site.client_id:
            raise CRMValidationError("site_id does not belong to the provided client_id.")
        client_id = site.client_id

    if client_id is not None:
        require_client(db, organization_id, client_id)

    return client_id, site_id, job_id


def apply_record_link_to_message(
    db: Session,
    *,
    message: EmailMessage,
    client_id: uuid.UUID | None,
    site_id: uuid.UUID | None,
    job_id: uuid.UUID | None,
) -> None:
    client_id, site_id, job_id = normalize_scope(
        db,
        organization_id=message.organization_id,
        client_id=client_id,
        site_id=site_id,
        job_id=job_id,
    )
    message.client_id = client_id
    message.site_id = site_id
    message.job_id = job_id
    message.status = "linked" if any((client_id, site_id, job_id)) else "unlinked"


def _normalize_payload(
    db: Session,
    *,
    organization_id: uuid.UUID,
    data: dict[str, Any],
    current: EmailMessage | None = None,
) -> dict[str, Any]:
    normalized = dict(data)

    if "provider" in normalized or current is None:
        normalized["provider"] = _normalize_required(
            normalized.get("provider"),
            "provider",
            current.provider if current else "outlook",
        ).lower()
    if "subject" in normalized or current is None:
        normalized["subject"] = _normalize_required(
            normalized.get("subject"),
            "subject",
            current.subject if current else None,
        )
    if "sender" in normalized or current is None:
        normalized["sender"] = _normalize_required(
            normalized.get("sender"),
            "sender",
            current.sender if current else None,
        )

    for field in JSON_LIST_FIELDS:
        if field in normalized or current is None:
            normalized[field] = normalized.get(field) or []

    for field in (
        "provider_message_id",
        "provider_conversation_id",
        "internet_message_id",
        "snippet",
        "body_html",
        "web_link",
    ):
        if field in normalized:
            normalized[field] = _normalize_optional(normalized[field])

    if "body_text" in normalized:
        normalized["body_text"] = normalized.get("body_text") or ""
    elif current is None:
        normalized["body_text"] = ""

    if normalized.get("import_batch_id") is not None:
        require_import_batch(db, organization_id, normalized["import_batch_id"])

    client_id = normalized.get("client_id", current.client_id if current else None)
    site_id = normalized.get("site_id", current.site_id if current else None)
    job_id = normalized.get("job_id", current.job_id if current else None)
    client_id, site_id, job_id = normalize_scope(
        db,
        organization_id=organization_id,
        client_id=client_id,
        site_id=site_id,
        job_id=job_id,
    )
    normalized["client_id"] = client_id
    normalized["site_id"] = site_id
    normalized["job_id"] = job_id

    if "status" in normalized or current is None:
        normalized["status"] = validate_status(normalized.get("status"))
    if normalized.get("status") == "unlinked" and any((client_id, site_id, job_id)):
        normalized["status"] = "linked"
    if normalized.get("status") == "linked" and not any((client_id, site_id, job_id)):
        raise CRMValidationError("linked email messages require client_id, site_id, or job_id.")
    if normalized.get("status") == "archived":
        normalized["archived_at"] = _now()

    return normalized


def list_email_messages(
    db: Session,
    *,
    organization_id: uuid.UUID,
    search: str | None = None,
    status: str | None = None,
    client_id: uuid.UUID | None = None,
    site_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    provider: str | None = None,
    received_before: datetime | None = None,
    received_after: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[EmailMessage]:
    statement = select(EmailMessage).where(EmailMessage.organization_id == organization_id)

    normalized_status = validate_status(status) if status else None
    if normalized_status == "archived":
        statement = statement.where(EmailMessage.status == "archived")
    else:
        statement = statement.where(EmailMessage.archived_at.is_(None))
        if normalized_status:
            statement = statement.where(EmailMessage.status == normalized_status)

    if search:
        search_term = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                EmailMessage.subject.ilike(search_term),
                EmailMessage.sender.ilike(search_term),
                EmailMessage.snippet.ilike(search_term),
                EmailMessage.body_text.ilike(search_term),
            ),
        )
    if client_id is not None:
        statement = statement.where(EmailMessage.client_id == client_id)
    if site_id is not None:
        statement = statement.where(EmailMessage.site_id == site_id)
    if job_id is not None:
        statement = statement.where(EmailMessage.job_id == job_id)
    if provider:
        statement = statement.where(EmailMessage.provider == provider.strip().lower())
    if received_before is not None:
        statement = statement.where(EmailMessage.received_at <= received_before)
    if received_after is not None:
        statement = statement.where(EmailMessage.received_at >= received_after)

    statement = statement.order_by(EmailMessage.received_at.desc(), EmailMessage.created_at.desc(), EmailMessage.id)
    return paginate(db, statement, limit=limit, offset=offset)


def _find_dedupe_target(
    db: Session,
    *,
    organization_id: uuid.UUID,
    provider: str,
    provider_message_id: str | None,
) -> EmailMessage | None:
    if not provider_message_id:
        return None
    statement = select(EmailMessage).where(
        EmailMessage.organization_id == organization_id,
        EmailMessage.provider == provider,
        EmailMessage.provider_message_id == provider_message_id,
    )
    return db.scalar(statement)


def create_email_message(db: Session, *, data: dict[str, Any]) -> EmailMessage:
    organization_id = data.get("organization_id")
    if organization_id is None:
        raise CRMValidationError("organization_id is required.")
    require_organization(db, organization_id)

    normalized = _normalize_payload(db, organization_id=organization_id, data=data)
    existing = _find_dedupe_target(
        db,
        organization_id=organization_id,
        provider=normalized["provider"],
        provider_message_id=normalized.get("provider_message_id"),
    )
    if existing is not None:
        for field, value in normalized.items():
            if field != "organization_id":
                setattr(existing, field, value)
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    message = EmailMessage(**normalized)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def update_email_message(
    db: Session,
    *,
    organization_id: uuid.UUID,
    email_message_id: uuid.UUID,
    data: dict[str, Any],
) -> EmailMessage:
    if "organization_id" in data:
        raise CRMValidationError("organization_id cannot be changed.")
    message = require_email_message(
        db,
        organization_id=organization_id,
        email_message_id=email_message_id,
    )
    normalized = _normalize_payload(
        db,
        organization_id=organization_id,
        data=data,
        current=message,
    )

    for field, value in normalized.items():
        setattr(message, field, value)

    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def archive_email_message(
    db: Session,
    *,
    organization_id: uuid.UUID,
    email_message_id: uuid.UUID,
) -> EmailMessage:
    message = require_email_message(
        db,
        organization_id=organization_id,
        email_message_id=email_message_id,
    )
    message.status = "archived"
    message.archived_at = _now()
    db.add(message)
    db.commit()
    db.refresh(message)
    return message
