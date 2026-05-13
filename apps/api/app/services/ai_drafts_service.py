from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AiDraft
from app.services import email_messages_service
from app.services.common import CRMNotFoundError, CRMValidationError, Page, paginate


ALLOWED_STATUSES = {"draft", "reviewed", "used", "archived"}


def _now() -> datetime:
    return datetime.now(UTC)


def _validate_status(status: str | None) -> str:
    normalized = (status or "draft").strip().lower()
    if normalized not in ALLOWED_STATUSES:
        raise CRMValidationError(
            f"status must be one of: {', '.join(sorted(ALLOWED_STATUSES))}.",
        )
    return normalized


def _normalize_required(value: str | None, field_name: str, default: str | None = None) -> str:
    candidate = default if value is None else value
    trimmed = (candidate or "").strip()
    if not trimmed:
        raise CRMValidationError(f"{field_name} is required.")
    return trimmed


def get_ai_draft(
    db: Session,
    *,
    organization_id: uuid.UUID,
    draft_id: uuid.UUID,
) -> AiDraft | None:
    statement = select(AiDraft).where(
        AiDraft.organization_id == organization_id,
        AiDraft.id == draft_id,
        AiDraft.archived_at.is_(None),
    )
    return db.scalar(statement)


def _require_ai_draft(
    db: Session,
    *,
    organization_id: uuid.UUID,
    draft_id: uuid.UUID,
) -> AiDraft:
    draft = get_ai_draft(db, organization_id=organization_id, draft_id=draft_id)
    if draft is None:
        raise CRMNotFoundError("AI draft not found.")
    return draft


def _normalize_payload(
    db: Session,
    *,
    organization_id: uuid.UUID,
    data: dict[str, Any],
    current: AiDraft | None = None,
) -> dict[str, Any]:
    normalized = dict(data)
    if "draft_type" in normalized or current is None:
        normalized["draft_type"] = _normalize_required(
            normalized.get("draft_type"),
            "draft_type",
            current.draft_type if current else "email_reply",
        )
    if "title" in normalized or current is None:
        normalized["title"] = _normalize_required(
            normalized.get("title"),
            "title",
            current.title if current else None,
        )
    if "draft_text" in normalized or current is None:
        normalized["draft_text"] = _normalize_required(
            normalized.get("draft_text"),
            "draft_text",
            current.draft_text if current else None,
        )
    if "status" in normalized or current is None:
        normalized["status"] = _validate_status(normalized.get("status"))

    email_message_id = normalized.get(
        "email_message_id",
        current.email_message_id if current else None,
    )
    if email_message_id is not None:
        email_messages_service.require_email_message(
            db,
            organization_id=organization_id,
            email_message_id=email_message_id,
        )

    client_id = normalized.get("client_id", current.client_id if current else None)
    site_id = normalized.get("site_id", current.site_id if current else None)
    job_id = normalized.get("job_id", current.job_id if current else None)
    client_id, site_id, job_id = email_messages_service.normalize_scope(
        db,
        organization_id=organization_id,
        client_id=client_id,
        site_id=site_id,
        job_id=job_id,
    )
    normalized["client_id"] = client_id
    normalized["site_id"] = site_id
    normalized["job_id"] = job_id
    if normalized.get("status") == "archived":
        normalized["archived_at"] = _now()
    return normalized


def list_ai_drafts(
    db: Session,
    *,
    organization_id: uuid.UUID,
    status: str | None = None,
    draft_type: str | None = None,
    client_id: uuid.UUID | None = None,
    site_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    email_message_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[AiDraft]:
    statement = select(AiDraft).where(AiDraft.organization_id == organization_id)

    normalized_status = _validate_status(status) if status else None
    if normalized_status == "archived":
        statement = statement.where(AiDraft.status == "archived")
    else:
        statement = statement.where(AiDraft.archived_at.is_(None))
        if normalized_status:
            statement = statement.where(AiDraft.status == normalized_status)

    if draft_type:
        statement = statement.where(AiDraft.draft_type == draft_type.strip())
    if client_id is not None:
        statement = statement.where(AiDraft.client_id == client_id)
    if site_id is not None:
        statement = statement.where(AiDraft.site_id == site_id)
    if job_id is not None:
        statement = statement.where(AiDraft.job_id == job_id)
    if email_message_id is not None:
        statement = statement.where(AiDraft.email_message_id == email_message_id)

    statement = statement.order_by(AiDraft.updated_at.desc(), AiDraft.created_at.desc(), AiDraft.id)
    return paginate(db, statement, limit=limit, offset=offset)


def create_ai_draft(db: Session, *, data: dict[str, Any]) -> AiDraft:
    organization_id = data.get("organization_id")
    if organization_id is None:
        raise CRMValidationError("organization_id is required.")
    email_messages_service.require_organization(db, organization_id)
    normalized = _normalize_payload(db, organization_id=organization_id, data=data)
    draft = AiDraft(**normalized)
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


def update_ai_draft(
    db: Session,
    *,
    organization_id: uuid.UUID,
    draft_id: uuid.UUID,
    data: dict[str, Any],
) -> AiDraft:
    if "organization_id" in data:
        raise CRMValidationError("organization_id cannot be changed.")
    draft = _require_ai_draft(db, organization_id=organization_id, draft_id=draft_id)
    normalized = _normalize_payload(
        db,
        organization_id=organization_id,
        data=data,
        current=draft,
    )
    for field, value in normalized.items():
        setattr(draft, field, value)
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


def archive_ai_draft(
    db: Session,
    *,
    organization_id: uuid.UUID,
    draft_id: uuid.UUID,
) -> AiDraft:
    draft = _require_ai_draft(db, organization_id=organization_id, draft_id=draft_id)
    draft.status = "archived"
    draft.archived_at = _now()
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft
