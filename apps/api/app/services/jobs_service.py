from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Client, Job, Site
from app.services.common import CRMNotFoundError, CRMValidationError, Page, paginate


def _require_client(
    db: Session,
    *,
    organization_id: uuid.UUID,
    client_id: uuid.UUID,
) -> Client:
    statement = select(Client).where(
        Client.organization_id == organization_id,
        Client.id == client_id,
        Client.archived_at.is_(None),
    )
    client = db.scalar(statement)
    if client is None:
        raise CRMNotFoundError("Client not found.")
    return client


def _require_site(
    db: Session,
    *,
    organization_id: uuid.UUID,
    site_id: uuid.UUID,
) -> Site:
    statement = select(Site).where(
        Site.organization_id == organization_id,
        Site.id == site_id,
        Site.archived_at.is_(None),
    )
    site = db.scalar(statement)
    if site is None:
        raise CRMNotFoundError("Site not found.")
    return site


def _validate_job_relationships(
    db: Session,
    *,
    organization_id: uuid.UUID,
    client_id: uuid.UUID,
    site_id: uuid.UUID,
) -> None:
    _require_client(db, organization_id=organization_id, client_id=client_id)
    site = _require_site(db, organization_id=organization_id, site_id=site_id)
    if site.client_id != client_id:
        raise CRMValidationError("site_id must belong to client_id.")


def get_job(
    db: Session,
    *,
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
) -> Job | None:
    statement = select(Job).where(
        Job.organization_id == organization_id,
        Job.id == job_id,
        Job.archived_at.is_(None),
    )
    return db.scalar(statement)


def _require_job(
    db: Session,
    *,
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
) -> Job:
    job = get_job(db, organization_id=organization_id, job_id=job_id)
    if job is None:
        raise CRMNotFoundError("Job not found.")
    return job


def list_jobs(
    db: Session,
    *,
    organization_id: uuid.UUID,
    search: str | None = None,
    status: str | None = None,
    client_id: uuid.UUID | None = None,
    site_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[Job]:
    statement = select(Job).where(
        Job.organization_id == organization_id,
        Job.archived_at.is_(None),
    )
    if client_id:
        statement = statement.where(Job.client_id == client_id)
    if site_id:
        statement = statement.where(Job.site_id == site_id)
    if search:
        search_term = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                Job.name.ilike(search_term),
                Job.job_code.ilike(search_term),
                Job.service_type.ilike(search_term),
            ),
        )
    if status:
        statement = statement.where(Job.status == status)

    return paginate(db, statement.order_by(Job.due_date, Job.name, Job.id), limit=limit, offset=offset)


def create_job(db: Session, *, data: dict[str, Any]) -> Job:
    _validate_job_relationships(
        db,
        organization_id=data["organization_id"],
        client_id=data["client_id"],
        site_id=data["site_id"],
    )
    job = Job(**data)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def update_job(
    db: Session,
    *,
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
    data: dict[str, Any],
) -> Job:
    job = _require_job(db, organization_id=organization_id, job_id=job_id)
    for field in ("name", "status"):
        if field in data and data[field] is None:
            raise CRMValidationError(f"{field} cannot be null.")

    client_id = data.get("client_id", job.client_id)
    site_id = data.get("site_id", job.site_id)
    if client_id is None:
        raise CRMValidationError("client_id cannot be null.")
    if site_id is None:
        raise CRMValidationError("site_id cannot be null.")
    if "client_id" in data or "site_id" in data:
        _validate_job_relationships(
            db,
            organization_id=organization_id,
            client_id=client_id,
            site_id=site_id,
        )

    for field, value in data.items():
        setattr(job, field, value)

    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def archive_job(
    db: Session,
    *,
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
) -> Job:
    job = _require_job(db, organization_id=organization_id, job_id=job_id)
    job.archived_at = datetime.now(UTC)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job
