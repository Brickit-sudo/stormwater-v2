from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session


DEFAULT_LIMIT = 50
MAX_LIMIT = 500

T = TypeVar("T")


class CRMNotFoundError(Exception):
    """Raised when a CRM resource is not found within the organization scope."""


class CRMValidationError(Exception):
    """Raised when CRM relationships or mutations are invalid."""


@dataclass(frozen=True)
class Page(Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


def normalize_limit(limit: int) -> int:
    return max(1, min(limit, MAX_LIMIT))


def normalize_offset(offset: int) -> int:
    return max(0, offset)


def paginate(db: Session, statement: Any, *, limit: int, offset: int) -> Page[Any]:
    normalized_limit = normalize_limit(limit)
    normalized_offset = normalize_offset(offset)
    count_statement = select(func.count()).select_from(statement.order_by(None).subquery())
    total = db.scalar(count_statement) or 0
    items = list(db.scalars(statement.limit(normalized_limit).offset(normalized_offset)).all())
    return Page(
        items=items,
        total=total,
        limit=normalized_limit,
        offset=normalized_offset,
    )
