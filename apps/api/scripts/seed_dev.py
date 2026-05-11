from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session_factory
from app.models import Client, Job, Organization, Site


def seed(session: Session) -> Organization:
    organization = session.scalar(
        select(Organization).where(Organization.name == "Demo Organization"),
    )
    if organization is None:
        organization = Organization(name="Demo Organization")
        session.add(organization)
        session.flush()

    client = session.scalar(
        select(Client).where(
            Client.organization_id == organization.id,
            Client.name == "Brightwater HOA",
            Client.archived_at.is_(None),
        ),
    )
    if client is None:
        client = Client(
            organization_id=organization.id,
            name="Brightwater HOA",
            client_code="BWHOA",
            status="active",
            primary_contact_name="Jordan Lee",
            email="ops@brightwater.example",
            phone="555-0104",
            billing_address="1200 Watershed Drive",
            notes="Dev seed client for CRM smoke testing.",
        )
        session.add(client)
        session.flush()

    site = session.scalar(
        select(Site).where(
            Site.organization_id == organization.id,
            Site.client_id == client.id,
            Site.name == "North Basin",
            Site.archived_at.is_(None),
        ),
    )
    if site is None:
        site = Site(
            organization_id=organization.id,
            client_id=client.id,
            name="North Basin",
            status="active",
            address="1200 Watershed Drive",
            city="Raleigh",
            state="NC",
            zip="27601",
            notes="Primary stormwater maintenance site.",
        )
        session.add(site)
        session.flush()

    job = session.scalar(
        select(Job).where(
            Job.organization_id == organization.id,
            Job.client_id == client.id,
            Job.site_id == site.id,
            Job.name == "Spring Inspection",
            Job.archived_at.is_(None),
        ),
    )
    if job is None:
        session.add(
            Job(
                organization_id=organization.id,
                client_id=client.id,
                site_id=site.id,
                name="Spring Inspection",
                service_type="Inspection",
                status="scheduled",
                scheduled_date=date(2026, 6, 15),
                due_date=date(2026, 6, 30),
                scope="Inspect stormwater controls and document maintenance needs.",
                notes="Dev seed job for the first CRM frontend.",
            ),
        )

    session.commit()
    session.refresh(organization)
    return organization


def main() -> None:
    session_factory = get_session_factory()
    with session_factory() as session:
        organization = seed(session)
        print("Seeded demo CRM data.")
        print(f"NEXT_PUBLIC_DEMO_ORG_ID={organization.id}")


if __name__ == "__main__":
    main()
