from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Organization, ProductDecision, ProductIdea
from app.services.common import CRMNotFoundError, CRMValidationError, Page, paginate


IDEA_STATUSES = {
    "new",
    "needs_review",
    "planned",
    "in_progress",
    "done",
    "deferred",
    "rejected",
}
DECISION_STATUSES = {"proposed", "decided", "superseded", "deferred"}
IDEA_PRIORITIES = {"low", "medium", "high", "critical"}
IDEA_CATEGORIES = {
    "CRM",
    "Files",
    "Reports",
    "Email",
    "Outlook",
    "Gmail",
    "Drive",
    "Map",
    "Scheduling",
    "Billing",
    "AI",
    "Import",
    "Migration",
    "UX",
    "Security",
    "Performance",
    "Microsoft 365",
    "Knowledgebase",
}
IDEA_LANES = {"V2", "Original Streamlit", "Migration", "Microsoft 365", "Docs", "Future"}


def _now() -> datetime:
    return datetime.now(UTC)


def _require_organization(db: Session, organization_id: uuid.UUID) -> Organization:
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise CRMNotFoundError("Organization not found.")
    return organization


def _clean_required_text(value: str | None, field_name: str) -> str:
    if value is None:
        raise CRMValidationError(f"{field_name} is required.")
    trimmed = value.strip()
    if not trimmed:
        raise CRMValidationError(f"{field_name} is required.")
    return trimmed


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _validate_lower_choice(
    value: str | None,
    *,
    choices: set[str],
    default: str,
    field_name: str,
) -> str:
    normalized = (value or default).strip().lower()
    if normalized not in choices:
        raise CRMValidationError(f"{field_name} must be one of: {', '.join(sorted(choices))}.")
    return normalized


def _validate_canonical_choice(
    value: str | None,
    *,
    choices: set[str],
    default: str,
    field_name: str,
) -> str:
    raw = (value or default).strip()
    by_lower = {choice.lower(): choice for choice in choices}
    normalized = by_lower.get(raw.lower())
    if normalized is None:
        raise CRMValidationError(f"{field_name} must be one of: {', '.join(sorted(choices))}.")
    return normalized


def _normalize_idea_data(data: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
    normalized = dict(data)
    if "title" in normalized or not partial:
        normalized["title"] = _clean_required_text(normalized.get("title"), "title")
    if "description" in normalized:
        normalized["description"] = _clean_optional_text(normalized["description"])
    if "category" in normalized or not partial:
        normalized["category"] = _validate_canonical_choice(
            normalized.get("category"),
            choices=IDEA_CATEGORIES,
            default="UX",
            field_name="category",
        )
    if "lane" in normalized or not partial:
        normalized["lane"] = _validate_canonical_choice(
            normalized.get("lane"),
            choices=IDEA_LANES,
            default="V2",
            field_name="lane",
        )
    if "status" in normalized or not partial:
        normalized["status"] = _validate_lower_choice(
            normalized.get("status"),
            choices=IDEA_STATUSES,
            default="new",
            field_name="status",
        )
    if "priority" in normalized or not partial:
        normalized["priority"] = _validate_lower_choice(
            normalized.get("priority"),
            choices=IDEA_PRIORITIES,
            default="medium",
            field_name="priority",
        )
    for field in ("source", "owner", "target_version", "effort", "risk"):
        if field in normalized:
            normalized[field] = _clean_optional_text(normalized[field])
    return normalized


def _normalize_decision_data(data: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
    normalized = dict(data)
    if "decision_title" in normalized or not partial:
        normalized["decision_title"] = _clean_required_text(
            normalized.get("decision_title"),
            "decision_title",
        )
    for field in ("decision_summary", "decision_reason", "alternatives_considered"):
        if field in normalized:
            normalized[field] = _clean_optional_text(normalized[field])
    if "status" in normalized or not partial:
        normalized["status"] = _validate_lower_choice(
            normalized.get("status"),
            choices=DECISION_STATUSES,
            default="proposed",
            field_name="status",
        )
    return normalized


def get_product_idea(
    db: Session,
    *,
    organization_id: uuid.UUID,
    idea_id: uuid.UUID,
) -> ProductIdea | None:
    statement = select(ProductIdea).where(
        ProductIdea.organization_id == organization_id,
        ProductIdea.id == idea_id,
        ProductIdea.archived_at.is_(None),
    )
    return db.scalar(statement)


def _require_product_idea(
    db: Session,
    *,
    organization_id: uuid.UUID,
    idea_id: uuid.UUID,
) -> ProductIdea:
    idea = get_product_idea(db, organization_id=organization_id, idea_id=idea_id)
    if idea is None:
        raise CRMNotFoundError("Product idea not found.")
    return idea


def _require_related_idea(
    db: Session,
    *,
    organization_id: uuid.UUID,
    related_idea_id: uuid.UUID | None,
) -> None:
    if related_idea_id is None:
        return
    _require_product_idea(db, organization_id=organization_id, idea_id=related_idea_id)


def list_product_ideas(
    db: Session,
    *,
    organization_id: uuid.UUID,
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    lane: str | None = None,
    boss_demo_relevant: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[ProductIdea]:
    statement = select(ProductIdea).where(
        ProductIdea.organization_id == organization_id,
        ProductIdea.archived_at.is_(None),
    )
    if status:
        statement = statement.where(
            ProductIdea.status
            == _validate_lower_choice(
                status,
                choices=IDEA_STATUSES,
                default="new",
                field_name="status",
            ),
        )
    if priority:
        statement = statement.where(
            ProductIdea.priority
            == _validate_lower_choice(
                priority,
                choices=IDEA_PRIORITIES,
                default="medium",
                field_name="priority",
            ),
        )
    if category:
        statement = statement.where(
            ProductIdea.category
            == _validate_canonical_choice(
                category,
                choices=IDEA_CATEGORIES,
                default="UX",
                field_name="category",
            ),
        )
    if lane:
        statement = statement.where(
            ProductIdea.lane
            == _validate_canonical_choice(
                lane,
                choices=IDEA_LANES,
                default="V2",
                field_name="lane",
            ),
        )
    if boss_demo_relevant is not None:
        statement = statement.where(ProductIdea.boss_demo_relevant == boss_demo_relevant)

    statement = statement.order_by(
        ProductIdea.boss_demo_relevant.desc(),
        ProductIdea.updated_at.desc(),
        ProductIdea.title,
        ProductIdea.id,
    )
    return paginate(db, statement, limit=limit, offset=offset)


def create_product_idea(db: Session, *, data: dict[str, Any]) -> ProductIdea:
    organization_id = data.get("organization_id")
    if organization_id is None:
        raise CRMValidationError("organization_id is required.")
    _require_organization(db, organization_id)

    normalized = _normalize_idea_data(data)
    idea = ProductIdea(**normalized)
    db.add(idea)
    db.commit()
    db.refresh(idea)
    return idea


def update_product_idea(
    db: Session,
    *,
    organization_id: uuid.UUID,
    idea_id: uuid.UUID,
    data: dict[str, Any],
) -> ProductIdea:
    if "organization_id" in data:
        raise CRMValidationError("organization_id cannot be changed.")

    idea = _require_product_idea(db, organization_id=organization_id, idea_id=idea_id)
    normalized = _normalize_idea_data(data, partial=True)
    for field, value in normalized.items():
        setattr(idea, field, value)
    db.add(idea)
    db.commit()
    db.refresh(idea)
    return idea


def archive_product_idea(
    db: Session,
    *,
    organization_id: uuid.UUID,
    idea_id: uuid.UUID,
) -> ProductIdea:
    idea = _require_product_idea(db, organization_id=organization_id, idea_id=idea_id)
    idea.archived_at = _now()
    db.add(idea)
    db.commit()
    db.refresh(idea)
    return idea


def list_product_decisions(
    db: Session,
    *,
    organization_id: uuid.UUID,
    status: str | None = None,
    related_idea_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[ProductDecision]:
    statement = select(ProductDecision).where(
        ProductDecision.organization_id == organization_id,
        ProductDecision.archived_at.is_(None),
    )
    if status:
        statement = statement.where(
            ProductDecision.status
            == _validate_lower_choice(
                status,
                choices=DECISION_STATUSES,
                default="proposed",
                field_name="status",
            ),
        )
    if related_idea_id is not None:
        statement = statement.where(ProductDecision.related_idea_id == related_idea_id)

    statement = statement.order_by(
        ProductDecision.decided_at.is_(None),
        ProductDecision.decided_at.desc(),
        ProductDecision.updated_at.desc(),
        ProductDecision.decision_title,
        ProductDecision.id,
    )
    return paginate(db, statement, limit=limit, offset=offset)


def create_product_decision(db: Session, *, data: dict[str, Any]) -> ProductDecision:
    organization_id = data.get("organization_id")
    if organization_id is None:
        raise CRMValidationError("organization_id is required.")
    _require_organization(db, organization_id)
    _require_related_idea(
        db,
        organization_id=organization_id,
        related_idea_id=data.get("related_idea_id"),
    )

    normalized = _normalize_decision_data(data)
    decision = ProductDecision(**normalized)
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision


def update_product_decision(
    db: Session,
    *,
    organization_id: uuid.UUID,
    decision_id: uuid.UUID,
    data: dict[str, Any],
) -> ProductDecision:
    if "organization_id" in data:
        raise CRMValidationError("organization_id cannot be changed.")

    decision = _require_product_decision(
        db,
        organization_id=organization_id,
        decision_id=decision_id,
    )
    if "related_idea_id" in data:
        _require_related_idea(
            db,
            organization_id=organization_id,
            related_idea_id=data.get("related_idea_id"),
        )

    normalized = _normalize_decision_data(data, partial=True)
    for field, value in normalized.items():
        setattr(decision, field, value)
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision


def _require_product_decision(
    db: Session,
    *,
    organization_id: uuid.UUID,
    decision_id: uuid.UUID,
) -> ProductDecision:
    statement = select(ProductDecision).where(
        ProductDecision.organization_id == organization_id,
        ProductDecision.id == decision_id,
        ProductDecision.archived_at.is_(None),
    )
    decision = db.scalar(statement)
    if decision is None:
        raise CRMNotFoundError("Product decision not found.")
    return decision


def archive_product_decision(
    db: Session,
    *,
    organization_id: uuid.UUID,
    decision_id: uuid.UUID,
) -> ProductDecision:
    decision = _require_product_decision(
        db,
        organization_id=organization_id,
        decision_id=decision_id,
    )
    decision.archived_at = _now()
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision
