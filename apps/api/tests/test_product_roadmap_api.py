from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Organization


def _create_idea(
    api_client: TestClient,
    organization_id: str,
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "organization_id": organization_id,
        "title": "Capture boss feedback",
        "description": "Keep product ideas in one place during demos.",
        "category": "UX",
        "lane": "V2",
        "status": "new",
        "priority": "medium",
        "source": "test",
        "boss_demo_relevant": True,
    }
    payload.update(overrides)
    response = api_client.post("/v1/product-ideas", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _create_decision(
    api_client: TestClient,
    organization_id: str,
    **overrides: object,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "organization_id": organization_id,
        "decision_title": "Keep AI review-first",
        "decision_summary": "AI drafts stay editable and never auto-send.",
        "decision_reason": "Provider actions need explicit review.",
        "status": "decided",
    }
    payload.update(overrides)
    response = api_client.post("/v1/product-decisions", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_product_idea_create_list_filter_and_archive(
    api_client: TestClient,
    organization_id: str,
) -> None:
    first = _create_idea(
        api_client,
        organization_id,
        title="Outlook Draft Push",
        category="Outlook",
        lane="Microsoft 365",
        priority="high",
        status="planned",
        boss_demo_relevant=True,
    )
    _create_idea(
        api_client,
        organization_id,
        title="Gmail support later",
        category="Gmail",
        lane="Future",
        priority="low",
        status="deferred",
        boss_demo_relevant=False,
    )

    filtered = api_client.get(
        "/v1/product-ideas",
        params={
            "organization_id": organization_id,
            "category": "Outlook",
            "lane": "Microsoft 365",
            "priority": "high",
            "status": "planned",
            "boss_demo_relevant": "true",
        },
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["id"] == first["id"]

    archived = api_client.delete(
        f"/v1/product-ideas/{first['id']}",
        params={"organization_id": organization_id},
    )
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None

    normal = api_client.get("/v1/product-ideas", params={"organization_id": organization_id})
    assert normal.status_code == 200
    assert normal.json()["total"] == 1


def test_product_idea_patch_and_get(
    api_client: TestClient,
    organization_id: str,
) -> None:
    idea = _create_idea(api_client, organization_id)

    updated = api_client.patch(
        f"/v1/product-ideas/{idea['id']}",
        params={"organization_id": organization_id},
        json={"status": "needs_review", "priority": "critical", "target_version": "V2.1"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "needs_review"
    assert updated.json()["priority"] == "critical"
    assert updated.json()["target_version"] == "V2.1"

    fetched = api_client.get(
        f"/v1/product-ideas/{idea['id']}",
        params={"organization_id": organization_id},
    )
    assert fetched.status_code == 200
    assert fetched.json()["id"] == idea["id"]


def test_product_decision_create_list_and_archive(
    api_client: TestClient,
    organization_id: str,
) -> None:
    idea = _create_idea(api_client, organization_id, title="Roadmap tracker")
    decision = _create_decision(api_client, organization_id, related_idea_id=idea["id"])

    listed = api_client.get(
        "/v1/product-decisions",
        params={
            "organization_id": organization_id,
            "status": "decided",
            "related_idea_id": idea["id"],
        },
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["id"] == decision["id"]

    archived = api_client.delete(
        f"/v1/product-decisions/{decision['id']}",
        params={"organization_id": organization_id},
    )
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None

    normal = api_client.get("/v1/product-decisions", params={"organization_id": organization_id})
    assert normal.status_code == 200
    assert normal.json()["total"] == 0


def test_product_roadmap_organization_scoping(
    api_client: TestClient,
    db_session: Session,
    organization_id: str,
) -> None:
    other_org = Organization(name="Other Organization")
    db_session.add(other_org)
    db_session.commit()
    db_session.refresh(other_org)

    idea = _create_idea(api_client, organization_id)
    decision = _create_decision(api_client, organization_id, related_idea_id=idea["id"])

    list_ideas = api_client.get(
        "/v1/product-ideas",
        params={"organization_id": str(other_org.id)},
    )
    get_idea = api_client.get(
        f"/v1/product-ideas/{idea['id']}",
        params={"organization_id": str(other_org.id)},
    )
    list_decisions = api_client.get(
        "/v1/product-decisions",
        params={"organization_id": str(other_org.id)},
    )
    archive_decision = api_client.delete(
        f"/v1/product-decisions/{decision['id']}",
        params={"organization_id": str(other_org.id)},
    )

    assert list_ideas.status_code == 200
    assert list_ideas.json()["total"] == 0
    assert get_idea.status_code == 404
    assert list_decisions.status_code == 200
    assert list_decisions.json()["total"] == 0
    assert archive_decision.status_code == 404


def test_rejects_invalid_roadmap_choices(
    api_client: TestClient,
    organization_id: str,
) -> None:
    idea = api_client.post(
        "/v1/product-ideas",
        json={
            "organization_id": organization_id,
            "title": "Bad category",
            "category": "Not A Category",
        },
    )
    decision = api_client.post(
        "/v1/product-decisions",
        json={
            "organization_id": organization_id,
            "decision_title": "Bad status",
            "status": "maybe",
        },
    )

    assert idea.status_code == 400
    assert decision.status_code == 400
