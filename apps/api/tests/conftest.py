from __future__ import annotations

from collections.abc import Callable, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import Organization


CRM_TABLE_NAMES = [
    "organizations",
    "users",
    "organization_memberships",
    "clients",
    "sites",
    "jobs",
    "reminders",
    "evidence_files",
    "email_import_batches",
    "email_messages",
    "email_record_links",
    "ai_drafts",
    "outlook_connections",
    "product_ideas",
    "product_decisions",
]


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [Base.metadata.tables[name] for name in CRM_TABLE_NAMES]
    Base.metadata.create_all(engine, tables=tables)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)

    with session_factory() as session:
        yield session

    Base.metadata.drop_all(engine, tables=tables)
    engine.dispose()


@pytest.fixture()
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def organization_id(db_session: Session) -> str:
    organization = Organization(name="Demo Organization")
    db_session.add(organization)
    db_session.commit()
    db_session.refresh(organization)
    return str(organization.id)


@pytest.fixture()
def create_client_record(
    api_client: TestClient,
    organization_id: str,
) -> Callable[..., dict[str, object]]:
    def _create_client(**overrides: object) -> dict[str, object]:
        payload: dict[str, object] = {
            "organization_id": organization_id,
            "name": "Acme Property Group",
            "client_code": "ACME",
            "status": "active",
        }
        payload.update(overrides)
        response = api_client.post("/v1/clients", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _create_client


@pytest.fixture()
def create_site_record(
    api_client: TestClient,
    organization_id: str,
    create_client_record: Callable[..., dict[str, object]],
) -> Callable[..., dict[str, object]]:
    def _create_site(**overrides: object) -> dict[str, object]:
        client_id = overrides.pop("client_id", None)
        if client_id is None:
            client = create_client_record()
            client_id = client["id"]
        payload: dict[str, object] = {
            "organization_id": organization_id,
            "client_id": client_id,
            "name": "North Basin Site",
            "site_code": "SITE-1",
            "city": "Raleigh",
            "state": "NC",
            "status": "active",
        }
        payload.update(overrides)
        response = api_client.post("/v1/sites", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _create_site


@pytest.fixture()
def create_job_record(
    api_client: TestClient,
    organization_id: str,
    create_site_record: Callable[..., dict[str, object]],
) -> Callable[..., dict[str, object]]:
    def _create_job(**overrides: object) -> dict[str, object]:
        client_id = overrides.pop("client_id", None)
        site_id = overrides.pop("site_id", None)
        if client_id is None or site_id is None:
            site = create_site_record()
            client_id = site["client_id"]
            site_id = site["id"]
        payload: dict[str, object] = {
            "organization_id": organization_id,
            "client_id": client_id,
            "site_id": site_id,
            "name": "Spring Inspection",
            "job_code": "JOB-1",
            "service_type": "Inspection",
            "status": "scheduled",
            "due_date": "2026-06-01",
        }
        payload.update(overrides)
        response = api_client.post("/v1/jobs", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _create_job
