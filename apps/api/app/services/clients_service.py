from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Client, Job, Organization, Site
from app.services.common import CRMNotFoundError, CRMValidationError, Page, paginate


def _require_organization(db: Session, organization_id: uuid.UUID) -> Organization:
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise CRMNotFoundError("Organization not found.")
    return organization


def get_client(
    db: Session,
    *,
    organization_id: uuid.UUID,
    client_id: uuid.UUID,
) -> Client | None:
    statement = select(Client).where(
        Client.organization_id == organization_id,
        Client.id == client_id,
        Client.archived_at.is_(None),
    )
    return db.scalar(statement)


def _require_client(
    db: Session,
    *,
    organization_id: uuid.UUID,
    client_id: uuid.UUID,
) -> Client:
    client = get_client(db, organization_id=organization_id, client_id=client_id)
    if client is None:
        raise CRMNotFoundError("Client not found.")
    return client


def list_clients(
    db: Session,
    *,
    organization_id: uuid.UUID,
    search: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[Client]:
    statement = select(Client).where(
        Client.organization_id == organization_id,
        Client.archived_at.is_(None),
    )
    if search:
        search_term = f"%{search.strip()}%"
        statement = statement.where(
            or_(
                Client.name.ilike(search_term),
                Client.client_code.ilike(search_term),
                Client.primary_contact_name.ilike(search_term),
                Client.email.ilike(search_term),
            ),
        )
    if status:
        statement = statement.where(Client.status == status)

    return paginate(db, statement.order_by(Client.name, Client.id), limit=limit, offset=offset)


def create_client(db: Session, *, data: dict[str, Any]) -> Client:
    _require_organization(db, data["organization_id"])
    client = Client(**data)
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def update_client(
    db: Session,
    *,
    organization_id: uuid.UUID,
    client_id: uuid.UUID,
    data: dict[str, Any],
) -> Client:
    client = _require_client(db, organization_id=organization_id, client_id=client_id)
    for field in ("name", "status"):
        if field in data and data[field] is None:
            raise CRMValidationError(f"{field} cannot be null.")

    for field, value in data.items():
        setattr(client, field, value)

    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def archive_client(
    db: Session,
    *,
    organization_id: uuid.UUID,
    client_id: uuid.UUID,
) -> Client:
    client = _require_client(db, organization_id=organization_id, client_id=client_id)
    client.archived_at = datetime.now(UTC)
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def list_client_sites(
    db: Session,
    *,
    organization_id: uuid.UUID,
    client_id: uuid.UUID,
    search: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[Site]:
    _require_client(db, organization_id=organization_id, client_id=client_id)
    statement = select(Site).where(
        Site.organization_id == organization_id,
        Site.client_id == client_id,
        Site.archived_at.is_(None),
    )
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


def list_client_jobs(
    db: Session,
    *,
    organization_id: uuid.UUID,
    client_id: uuid.UUID,
    search: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[Job]:
    _require_client(db, organization_id=organization_id, client_id=client_id)
    statement = select(Job).where(
        Job.organization_id == organization_id,
        Job.client_id == client_id,
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
