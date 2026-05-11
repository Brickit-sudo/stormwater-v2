from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client, EvidenceFile, Job, Organization, Site
from app.services.common import CRMNotFoundError, CRMValidationError, Page, paginate


_ALLOWED_SOURCES = {
    "drive_link",
    "upload_placeholder",
    "report_export",
    "photo",
    "other",
}


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


def _validate_source(source: str | None) -> str:
    if source is None or source == "":
        return "drive_link"
    if source not in _ALLOWED_SOURCES:
        raise CRMValidationError(
            f"source must be one of: {', '.join(sorted(_ALLOWED_SOURCES))}.",
        )
    return source


def _normalize_file_name(file_name: str | None) -> str:
    if file_name is None:
        raise CRMValidationError("file_name is required.")
    trimmed = file_name.strip()
    if not trimmed:
        raise CRMValidationError("file_name is required.")
    return trimmed


def _validate_scope(
    client_id: uuid.UUID | None,
    site_id: uuid.UUID | None,
    job_id: uuid.UUID | None,
) -> None:
    scope_count = sum(value is not None for value in (client_id, site_id, job_id))
    if scope_count != 1:
        raise CRMValidationError("Exactly one of client_id, site_id, or job_id is required.")


def get_evidence_file(
    db: Session,
    *,
    organization_id: uuid.UUID,
    file_id: uuid.UUID,
) -> EvidenceFile | None:
    statement = select(EvidenceFile).where(
        EvidenceFile.organization_id == organization_id,
        EvidenceFile.id == file_id,
        EvidenceFile.archived_at.is_(None),
    )
    return db.scalar(statement)


def _require_evidence_file(
    db: Session,
    *,
    organization_id: uuid.UUID,
    file_id: uuid.UUID,
) -> EvidenceFile:
    record = get_evidence_file(db, organization_id=organization_id, file_id=file_id)
    if record is None:
        raise CRMNotFoundError("File not found.")
    return record


def list_evidence_files(
    db: Session,
    *,
    organization_id: uuid.UUID,
    client_id: uuid.UUID | None = None,
    site_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[EvidenceFile]:
    statement = select(EvidenceFile).where(
        EvidenceFile.organization_id == organization_id,
        EvidenceFile.archived_at.is_(None),
    )
    if client_id is not None:
        statement = statement.where(EvidenceFile.client_id == client_id)
    if site_id is not None:
        statement = statement.where(EvidenceFile.site_id == site_id)
    if job_id is not None:
        statement = statement.where(EvidenceFile.job_id == job_id)

    statement = statement.order_by(
        EvidenceFile.sort_order,
        EvidenceFile.created_at.desc(),
        EvidenceFile.id,
    )
    return paginate(db, statement, limit=limit, offset=offset)


def create_evidence_file(db: Session, *, data: dict[str, Any]) -> EvidenceFile:
    organization_id = data.get("organization_id")
    if organization_id is None:
        raise CRMValidationError("organization_id is required.")
    _require_organization(db, organization_id)

    client_id = data.get("client_id")
    site_id = data.get("site_id")
    job_id = data.get("job_id")
    _validate_scope(client_id, site_id, job_id)

    if client_id is not None:
        _require_client(db, organization_id, client_id)
    if site_id is not None:
        _require_site(db, organization_id, site_id)
    if job_id is not None:
        _require_job(db, organization_id, job_id)

    normalized: dict[str, Any] = dict(data)
    normalized["file_name"] = _normalize_file_name(normalized.get("file_name"))
    normalized["source"] = _validate_source(normalized.get("source"))
    if normalized.get("sort_order") is None:
        normalized["sort_order"] = 0

    record = EvidenceFile(**normalized)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_evidence_file(
    db: Session,
    *,
    organization_id: uuid.UUID,
    file_id: uuid.UUID,
    data: dict[str, Any],
) -> EvidenceFile:
    record = _require_evidence_file(db, organization_id=organization_id, file_id=file_id)

    if "file_name" in data:
        record.file_name = _normalize_file_name(data["file_name"])
    if "source" in data:
        record.source = _validate_source(data["source"])
    for field in (
        "public_url",
        "drive_file_id",
        "mime_type",
        "size_bytes",
        "caption",
    ):
        if field in data:
            setattr(record, field, data[field])
    if "sort_order" in data and data["sort_order"] is not None:
        record.sort_order = data["sort_order"]

    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def archive_evidence_file(
    db: Session,
    *,
    organization_id: uuid.UUID,
    file_id: uuid.UUID,
) -> EvidenceFile:
    record = _require_evidence_file(db, organization_id=organization_id, file_id=file_id)
    record.archived_at = datetime.now(UTC)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
