from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EmailImportBatch, Organization
from app.services.common import CRMNotFoundError, CRMValidationError, Page, paginate


ALLOWED_STATUSES = {"previewed", "imported", "failed", "archived", "seed"}


def _now() -> datetime:
    return datetime.now(UTC)


def _require_organization(db: Session, organization_id: uuid.UUID) -> Organization:
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise CRMNotFoundError("Organization not found.")
    return organization


def _validate_status(status: str | None) -> str:
    normalized = (status or "previewed").strip().lower()
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


def get_import_batch(
    db: Session,
    *,
    organization_id: uuid.UUID,
    batch_id: uuid.UUID,
) -> EmailImportBatch | None:
    statement = select(EmailImportBatch).where(
        EmailImportBatch.organization_id == organization_id,
        EmailImportBatch.id == batch_id,
        EmailImportBatch.archived_at.is_(None),
    )
    return db.scalar(statement)


def list_import_batches(
    db: Session,
    *,
    organization_id: uuid.UUID,
    status: str | None = None,
    provider: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[EmailImportBatch]:
    statement = select(EmailImportBatch).where(EmailImportBatch.organization_id == organization_id)

    normalized_status = _validate_status(status) if status else None
    if normalized_status == "archived":
        statement = statement.where(EmailImportBatch.status == "archived")
    else:
        statement = statement.where(EmailImportBatch.archived_at.is_(None))
        if normalized_status:
            statement = statement.where(EmailImportBatch.status == normalized_status)

    if provider:
        statement = statement.where(EmailImportBatch.provider == provider.strip().lower())

    statement = statement.order_by(EmailImportBatch.created_at.desc(), EmailImportBatch.id)
    return paginate(db, statement, limit=limit, offset=offset)


def create_import_batch(db: Session, *, data: dict[str, Any]) -> EmailImportBatch:
    organization_id = data.get("organization_id")
    if organization_id is None:
        raise CRMValidationError("organization_id is required.")
    _require_organization(db, organization_id)

    normalized = dict(data)
    normalized["provider"] = _normalize_required(normalized.get("provider"), "provider", "outlook").lower()
    normalized["import_mode"] = _normalize_required(
        normalized.get("import_mode"),
        "import_mode",
        "manual_seed",
    )
    normalized["status"] = _validate_status(normalized.get("status"))
    for field in ("preview_count", "imported_count", "skipped_count", "duplicate_count", "error_count"):
        normalized[field] = max(0, int(normalized.get(field) or 0))
    if normalized["status"] == "archived":
        normalized["archived_at"] = _now()

    batch = EmailImportBatch(**normalized)
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch
