from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Client, Job, Organization, Site
from scripts.seed_dev import (
    DEMO_ORGANIZATION_ID,
    LEGACY_SOURCE,
    SEED_CLIENTS,
    SEED_JOBS,
    SEED_SITES,
    reset_seed,
    seed,
    seed_counts,
)


def test_seed_constants_have_expected_structure() -> None:
    assert seed_counts() == {
        "organizations": 1,
        "clients": 3,
        "sites": 5,
        "jobs": 8,
    }
    assert {client["status"] for client in SEED_CLIENTS} == {
        "active",
        "inactive",
        "prospect",
    }
    assert {"active", "inactive", "on_hold"}.issubset(
        {site["status"] for site in SEED_SITES},
    )
    assert {"draft", "scheduled", "in_progress", "in_review", "completed"}.issubset(
        {job["status"] for job in SEED_JOBS},
    )


def test_seed_is_idempotent(db_session: Session) -> None:
    first_org = seed(db_session)
    second_org = seed(db_session)

    assert first_org.id == second_org.id == DEMO_ORGANIZATION_ID
    assert db_session.scalar(select(Organization).where(Organization.id == DEMO_ORGANIZATION_ID))
    assert db_session.query(Client).filter(Client.legacy_source == LEGACY_SOURCE).count() == 3
    assert db_session.query(Site).filter(Site.legacy_source == LEGACY_SOURCE).count() == 5
    assert db_session.query(Job).filter(Job.legacy_source == LEGACY_SOURCE).count() == 8


def test_reset_seed_deletes_only_seed_source_rows(db_session: Session) -> None:
    seed(db_session)
    manual_client = Client(
        organization_id=DEMO_ORGANIZATION_ID,
        name="Manual Client",
        status="active",
        legacy_source="manual",
        legacy_id="client:manual",
    )
    db_session.add(manual_client)
    db_session.commit()

    deleted = reset_seed(db_session)
    db_session.commit()

    assert deleted == {"jobs": 8, "sites": 5, "clients": 3}
    assert db_session.scalar(
        select(Client).where(
            Client.organization_id == DEMO_ORGANIZATION_ID,
            Client.legacy_source == "manual",
        ),
    )
    assert db_session.query(Client).filter(Client.legacy_source == LEGACY_SOURCE).count() == 0
    assert db_session.query(Site).filter(Site.legacy_source == LEGACY_SOURCE).count() == 0
    assert db_session.query(Job).filter(Job.legacy_source == LEGACY_SOURCE).count() == 0
