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


def get_site(
    db: Session,
    *,
    organization_id: uuid.UUID,
    site_id: uuid.UUID,
) -> Site | None:
    statement = select(Site).where(
        Site.organization_id == organization_id,
        Site.id == site_id,
        Site.archived_at.is_(None),
    )
    return db.scalar(statement)


def _require_site(
    db: Session,
    *,
    organization_id: uuid.UUID,
    site_id: uuid.UUID,
) -> Site:
    site = get_site(db, organization_id=organization_id, site_id=site_id)
    if site is None:
        raise CRMNotFoundError("Site not found.")
    return site


def list_sites(
    db: Session,
    *,
    organization_id: uuid.UUID,
    search: str | None = None,
    status: str | None = None,
    client_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[Site]:
    statement = select(Site).where(
        Site.organization_id == organization_id,
        Site.archived_at.is_(None),
    )
    if client_id:
        statement = statement.where(Site.client_id == client_id)
    if search:
        search_term = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                Site.name.ilike(search_term),
                Site.site_code.ilike(search_term),
                Site.address.ilike(search_term),
                Site.city.ilike(search_term),
                Site.state.ilike(search_term),
            ),
        )
    if status:
        statement = statement.where(Site.status == status)

    return paginate(db, statement.order_by(Site.name, Site.id), limit=limit, offset=offset)


def create_site(db: Session, *, data: dict[str, Any]) -> Site:
    _require_client(
        db,
        organization_id=data["organization_id"],
        client_id=data["client_id"],
    )
    site = Site(**data)
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def update_site(
    db: Session,
    *,
    organization_id: uuid.UUID,
    site_id: uuid.UUID,
    data: dict[str, Any],
) -> Site:
    site = _require_site(db, organization_id=organization_id, site_id=site_id)
    for field in ("name", "status"):
        if field in data and data[field] is None:
            raise CRMValidationError(f"{field} cannot be null.")

    if "client_id" in data:
        if data["client_id"] is None:
            raise CRMValidationError("client_id cannot be null.")
        _require_client(db, organization_id=organization_id, client_id=data["client_id"])

    for field, value in data.items():
        setattr(site, field, value)

    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def archive_site(
    db: Session,
    *,
    organization_id: uuid.UUID,
    site_id: uuid.UUID,
) -> Site:
    site = _require_site(db, organization_id=organization_id, site_id=site_id)
    site.archived_at = datetime.now(UTC)
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def list_site_jobs(
    db: Session,
    *,
    organization_id: uuid.UUID,
    site_id: uuid.UUID,
    search: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[Job]:
    _require_site(db, organization_id=organization_id, site_id=site_id)
    statement = select(Job).where(
        Job.organization_id == organization_id,
        Job.site_id == site_id,
        Job.archived_at.is_(None),
    )
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
