from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EmailRecordLink
from app.services import email_messages_service
from app.services.common import CRMNotFoundError, CRMValidationError, Page, paginate


def _validate_exact_one_target(
    client_id: uuid.UUID | None,
    site_id: uuid.UUID | None,
    job_id: uuid.UUID | None,
) -> None:
    target_count = sum(value is not None for value in (client_id, site_id, job_id))
    if target_count != 1:
        raise CRMValidationError("Exactly one of client_id, site_id, or job_id is required.")


def _require_link(
    db: Session,
    *,
    organization_id: uuid.UUID,
    link_id: uuid.UUID,
) -> EmailRecordLink:
    statement = select(EmailRecordLink).where(
        EmailRecordLink.organization_id == organization_id,
        EmailRecordLink.id == link_id,
    )
    link = db.scalar(statement)
    if link is None:
        raise CRMNotFoundError("Email record link not found.")
    return link


def list_email_record_links(
    db: Session,
    *,
    organization_id: uuid.UUID,
    email_message_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> Page[EmailRecordLink]:
    email_messages_service.require_email_message(
        db,
        organization_id=organization_id,
        email_message_id=email_message_id,
    )
    statement = (
        select(EmailRecordLink)
        .where(
            EmailRecordLink.organization_id == organization_id,
            EmailRecordLink.email_message_id == email_message_id,
        )
        .order_by(EmailRecordLink.created_at.desc(), EmailRecordLink.id)
    )
    return paginate(db, statement, limit=limit, offset=offset)


def create_email_record_link(db: Session, *, data: dict[str, Any]) -> EmailRecordLink:
    organization_id = data.get("organization_id")
    email_message_id = data.get("email_message_id")
    if organization_id is None:
        raise CRMValidationError("organization_id is required.")
    if email_message_id is None:
        raise CRMValidationError("email_message_id is required.")

    message = email_messages_service.require_email_message(
        db,
        organization_id=organization_id,
        email_message_id=email_message_id,
    )
    client_id = data.get("client_id")
    site_id = data.get("site_id")
    job_id = data.get("job_id")
    _validate_exact_one_target(client_id, site_id, job_id)

    email_messages_service.normalize_scope(
        db,
        organization_id=organization_id,
        client_id=client_id,
        site_id=site_id,
        job_id=job_id,
    )

    existing = db.scalar(
        select(EmailRecordLink).where(
            EmailRecordLink.organization_id == organization_id,
            EmailRecordLink.email_message_id == email_message_id,
            EmailRecordLink.client_id == client_id,
            EmailRecordLink.site_id == site_id,
            EmailRecordLink.job_id == job_id,
        ),
    )
    if existing is not None:
        return existing

    normalized = dict(data)
    normalized["link_reason"] = (normalized.get("link_reason") or "manual").strip()
    normalized["confidence"] = float(normalized.get("confidence") if normalized.get("confidence") is not None else 1.0)
    link = EmailRecordLink(**normalized)
    db.add(link)
    email_messages_service.apply_record_link_to_message(
        db,
        message=message,
        client_id=client_id,
        site_id=site_id,
        job_id=job_id,
    )
    db.add(message)
    db.commit()
    db.refresh(link)
    return link


def delete_email_record_link(
    db: Session,
    *,
    organization_id: uuid.UUID,
    link_id: uuid.UUID,
) -> EmailRecordLink:
    link = _require_link(db, organization_id=organization_id, link_id=link_id)
    message = email_messages_service.require_email_message(
        db,
        organization_id=organization_id,
        email_message_id=link.email_message_id,
    )
    deleted_copy = EmailRecordLink(
        id=link.id,
        organization_id=link.organization_id,
        email_message_id=link.email_message_id,
        client_id=link.client_id,
        site_id=link.site_id,
        job_id=link.job_id,
        link_reason=link.link_reason,
        confidence=link.confidence,
        created_at=link.created_at,
    )
    db.delete(link)
    db.flush()

    remaining = list(
        db.scalars(
            select(EmailRecordLink)
            .where(
                EmailRecordLink.organization_id == organization_id,
                EmailRecordLink.email_message_id == message.id,
            )
            .order_by(EmailRecordLink.created_at, EmailRecordLink.id),
        ).all(),
    )
    message.client_id = None
    message.site_id = None
    message.job_id = None
    message.status = "unlinked"
    for remaining_link in remaining:
        email_messages_service.apply_record_link_to_message(
            db,
            message=message,
            client_id=remaining_link.client_id,
            site_id=remaining_link.site_id,
            job_id=remaining_link.job_id,
        )

    db.add(message)
    db.commit()
    return deleted_copy
