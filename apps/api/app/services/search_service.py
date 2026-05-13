from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable, Sequence
from datetime import date, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import AiDraft, Client, EmailMessage, EvidenceFile, Job, Reminder, Site
from app.schemas import SearchGroup, SearchResponse, SearchResult
from app.services.common import CRMValidationError


SearchType = str

DEFAULT_SEARCH_TYPES: tuple[SearchType, ...] = (
    "clients",
    "sites",
    "jobs",
    "files",
    "emails",
    "ai_drafts",
    "reminders",
)
SEARCH_TYPE_LABELS: dict[SearchType, str] = {
    "clients": "Clients",
    "sites": "Sites",
    "jobs": "Jobs",
    "files": "Evidence Files",
    "emails": "Email Messages",
    "ai_drafts": "AI Drafts",
    "reminders": "Reminders",
}
DEFAULT_LIMIT = 10
MAX_LIMIT = 25
BODY_SEARCH_CHAR_LIMIT = 2_000
DESCRIPTION_CHAR_LIMIT = 220


def normalize_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_LIMIT
    return max(1, min(limit, MAX_LIMIT))


def parse_search_types(types: str | None) -> tuple[SearchType, ...]:
    if not types:
        return DEFAULT_SEARCH_TYPES

    requested = [item.strip() for item in types.split(",") if item.strip()]
    if not requested:
        return DEFAULT_SEARCH_TYPES

    invalid = sorted(set(requested).difference(DEFAULT_SEARCH_TYPES))
    if invalid:
        raise CRMValidationError(
            f"types contains unsupported values: {', '.join(invalid)}.",
        )

    requested_set = set(requested)
    return tuple(search_type for search_type in DEFAULT_SEARCH_TYPES if search_type in requested_set)


def search(
    db: Session,
    *,
    organization_id: uuid.UUID,
    q: str,
    types: str | None = None,
    limit: int | None = None,
) -> SearchResponse:
    query = q.strip()
    if len(query) < 2:
        raise CRMValidationError("q must be at least 2 characters.")

    normalized_limit = normalize_limit(limit)
    requested_types = parse_search_types(types)
    search_term = _search_term(query)

    builders: dict[SearchType, Callable[[], list[SearchResult]]] = {
        "clients": lambda: _search_clients(db, organization_id, query, search_term, normalized_limit),
        "sites": lambda: _search_sites(db, organization_id, query, search_term, normalized_limit),
        "jobs": lambda: _search_jobs(db, organization_id, query, search_term, normalized_limit),
        "files": lambda: _search_files(db, organization_id, query, search_term, normalized_limit),
        "emails": lambda: _search_emails(db, organization_id, query, search_term, normalized_limit),
        "ai_drafts": lambda: _search_ai_drafts(db, organization_id, query, search_term, normalized_limit),
        "reminders": lambda: _search_reminders(db, organization_id, query, search_term, normalized_limit),
    }

    groups: list[SearchGroup] = []
    for search_type in requested_types:
        results = builders[search_type]()
        groups.append(
            SearchGroup(
                type=search_type,
                label=SEARCH_TYPE_LABELS[search_type],
                count=len(results),
                results=results,
            ),
        )

    return SearchResponse(
        query=query,
        groups=groups,
        total_count=sum(group.count for group in groups),
    )


def _search_clients(
    db: Session,
    organization_id: uuid.UUID,
    query: str,
    search_term: str,
    limit: int,
) -> list[SearchResult]:
    fields = ("name", "primary_contact_name", "email", "phone", "notes")
    statement = (
        select(Client)
        .where(
            Client.organization_id == organization_id,
            Client.archived_at.is_(None),
            or_(
                _contains(Client.name, search_term),
                _contains(Client.primary_contact_name, search_term),
                _contains(Client.email, search_term),
                _contains(Client.phone, search_term),
                _contains(Client.notes, search_term),
            ),
        )
        .order_by(Client.updated_at.desc(), Client.name, Client.id)
        .limit(limit)
    )
    rows = db.scalars(statement).all()
    return [
        SearchResult(
            id=row.id,
            type="clients",
            title=row.name,
            subtitle=_join_parts(row.primary_contact_name, row.email, row.phone),
            description=_description_from_fields(row, query, ("notes",)),
            status=row.status,
            href="/crm/clients",
            matched_fields=_matched_fields(row, query, fields),
            updated_at=row.updated_at,
            metadata={"client_code": row.client_code},
        )
        for row in rows
    ]


def _search_sites(
    db: Session,
    organization_id: uuid.UUID,
    query: str,
    search_term: str,
    limit: int,
) -> list[SearchResult]:
    fields = ("name", "address", "city", "state", "notes", "drive_folder_url")
    statement = (
        select(Site)
        .where(
            Site.organization_id == organization_id,
            Site.archived_at.is_(None),
            or_(
                _contains(Site.name, search_term),
                _contains(Site.address, search_term),
                _contains(Site.city, search_term),
                _contains(Site.state, search_term),
                _contains(Site.notes, search_term),
                _contains(Site.drive_folder_url, search_term),
            ),
        )
        .order_by(Site.updated_at.desc(), Site.name, Site.id)
        .limit(limit)
    )
    rows = db.scalars(statement).all()
    return [
        SearchResult(
            id=row.id,
            type="sites",
            title=row.name,
            subtitle=_join_parts(row.address, row.city, row.state),
            description=_description_from_fields(row, query, ("notes", "drive_folder_url")),
            status=row.status,
            href=f"/crm/sites?site_id={row.id}",
            matched_fields=_matched_fields(row, query, fields),
            updated_at=row.updated_at,
            metadata={
                "client_id": str(row.client_id),
                "site_code": row.site_code,
                "city": row.city,
                "state": row.state,
            },
        )
        for row in rows
    ]


def _search_jobs(
    db: Session,
    organization_id: uuid.UUID,
    query: str,
    search_term: str,
    limit: int,
) -> list[SearchResult]:
    fields = ("name", "service_type", "status", "scope", "notes")
    statement = (
        select(Job)
        .where(
            Job.organization_id == organization_id,
            Job.archived_at.is_(None),
            or_(
                _contains(Job.name, search_term),
                _contains(Job.service_type, search_term),
                _contains(Job.status, search_term),
                _contains(Job.scope, search_term),
                _contains(Job.notes, search_term),
            ),
        )
        .order_by(Job.updated_at.desc(), Job.due_date, Job.name, Job.id)
        .limit(limit)
    )
    rows = db.scalars(statement).all()
    return [
        SearchResult(
            id=row.id,
            type="jobs",
            title=row.name,
            subtitle=_join_parts(row.service_type, _date_label("due", row.due_date)),
            description=_description_from_fields(row, query, ("scope", "notes")),
            status=row.status,
            href="/crm/jobs",
            matched_fields=_matched_fields(row, query, fields),
            updated_at=row.updated_at,
            metadata={
                "client_id": str(row.client_id),
                "site_id": str(row.site_id),
                "job_code": row.job_code,
                "scheduled_date": _iso(row.scheduled_date),
                "due_date": _iso(row.due_date),
            },
        )
        for row in rows
    ]


def _search_files(
    db: Session,
    organization_id: uuid.UUID,
    query: str,
    search_term: str,
    limit: int,
) -> list[SearchResult]:
    fields = ("file_name", "caption", "public_url", "source")
    statement = (
        select(EvidenceFile)
        .where(
            EvidenceFile.organization_id == organization_id,
            EvidenceFile.archived_at.is_(None),
            or_(
                _contains(EvidenceFile.file_name, search_term),
                _contains(EvidenceFile.caption, search_term),
                _contains(EvidenceFile.public_url, search_term),
                _contains(EvidenceFile.source, search_term),
            ),
        )
        .order_by(EvidenceFile.updated_at.desc(), EvidenceFile.file_name, EvidenceFile.id)
        .limit(limit)
    )
    rows = db.scalars(statement).all()
    return [
        SearchResult(
            id=row.id,
            type="files",
            title=row.file_name,
            subtitle=_join_parts(row.source, row.mime_type),
            description=_description_from_fields(row, query, ("caption", "public_url")),
            status=row.source,
            href="/work",
            matched_fields=_matched_fields(row, query, fields),
            updated_at=row.updated_at,
            metadata={
                "client_id": _string_or_none(row.client_id),
                "site_id": _string_or_none(row.site_id),
                "job_id": _string_or_none(row.job_id),
                "drive_file_id": row.drive_file_id,
                "size_bytes": row.size_bytes,
            },
        )
        for row in rows
    ]


def _search_emails(
    db: Session,
    organization_id: uuid.UUID,
    query: str,
    search_term: str,
    limit: int,
) -> list[SearchResult]:
    fields = ("subject", "sender", "snippet", "body_text")
    body_prefix = func.substr(EmailMessage.body_text, 1, BODY_SEARCH_CHAR_LIMIT)
    statement = (
        select(EmailMessage)
        .where(
            EmailMessage.organization_id == organization_id,
            EmailMessage.archived_at.is_(None),
            or_(
                _contains(EmailMessage.subject, search_term),
                _contains(EmailMessage.sender, search_term),
                _contains(EmailMessage.snippet, search_term),
                _contains(body_prefix, search_term),
            ),
        )
        .order_by(EmailMessage.received_at.desc(), EmailMessage.created_at.desc(), EmailMessage.id)
        .limit(limit)
    )
    rows = db.scalars(statement).all()
    return [
        SearchResult(
            id=row.id,
            type="emails",
            title=row.subject,
            subtitle=_join_parts(row.sender, _date_label("received", row.received_at)),
            description=_description_from_fields(
                row,
                query,
                ("snippet", "body_text"),
                capped_fields={"body_text": BODY_SEARCH_CHAR_LIMIT},
            ),
            status=row.status,
            href="/work",
            matched_fields=_matched_fields(
                row,
                query,
                fields,
                capped_fields={"body_text": BODY_SEARCH_CHAR_LIMIT},
            ),
            occurred_at=row.received_at,
            updated_at=row.updated_at,
            metadata={
                "client_id": _string_or_none(row.client_id),
                "site_id": _string_or_none(row.site_id),
                "job_id": _string_or_none(row.job_id),
                "provider": row.provider,
                "provider_message_id": row.provider_message_id,
            },
        )
        for row in rows
    ]


def _search_ai_drafts(
    db: Session,
    organization_id: uuid.UUID,
    query: str,
    search_term: str,
    limit: int,
) -> list[SearchResult]:
    fields = ("title", "draft_type", "draft_text")
    draft_prefix = func.substr(AiDraft.draft_text, 1, BODY_SEARCH_CHAR_LIMIT)
    statement = (
        select(AiDraft)
        .where(
            AiDraft.organization_id == organization_id,
            AiDraft.archived_at.is_(None),
            or_(
                _contains(AiDraft.title, search_term),
                _contains(AiDraft.draft_type, search_term),
                _contains(draft_prefix, search_term),
            ),
        )
        .order_by(AiDraft.updated_at.desc(), AiDraft.title, AiDraft.id)
        .limit(limit)
    )
    rows = db.scalars(statement).all()
    return [
        SearchResult(
            id=row.id,
            type="ai_drafts",
            title=row.title,
            subtitle=_join_parts(row.draft_type, row.status),
            description=_description_from_fields(
                row,
                query,
                ("draft_text",),
                capped_fields={"draft_text": BODY_SEARCH_CHAR_LIMIT},
            ),
            status=row.status,
            href="/work",
            matched_fields=_matched_fields(
                row,
                query,
                fields,
                capped_fields={"draft_text": BODY_SEARCH_CHAR_LIMIT},
            ),
            updated_at=row.updated_at,
            metadata={
                "client_id": _string_or_none(row.client_id),
                "site_id": _string_or_none(row.site_id),
                "job_id": _string_or_none(row.job_id),
                "email_message_id": _string_or_none(row.email_message_id),
            },
        )
        for row in rows
    ]


def _search_reminders(
    db: Session,
    organization_id: uuid.UUID,
    query: str,
    search_term: str,
    limit: int,
) -> list[SearchResult]:
    fields = ("title", "description", "status", "priority")
    statement = (
        select(Reminder)
        .where(
            Reminder.organization_id == organization_id,
            Reminder.archived_at.is_(None),
            or_(
                _contains(Reminder.title, search_term),
                _contains(Reminder.description, search_term),
                _contains(Reminder.status, search_term),
                _contains(Reminder.priority, search_term),
            ),
        )
        .order_by(
            Reminder.due_at.is_(None),
            Reminder.due_at,
            Reminder.updated_at.desc(),
            Reminder.title,
            Reminder.id,
        )
        .limit(limit)
    )
    rows = db.scalars(statement).all()
    return [
        SearchResult(
            id=row.id,
            type="reminders",
            title=row.title,
            subtitle=_join_parts(row.priority, _date_label("due", row.due_at)),
            description=_description_from_fields(row, query, ("description",)),
            status=row.status,
            href="/schedule",
            matched_fields=_matched_fields(row, query, fields),
            occurred_at=row.due_at,
            updated_at=row.updated_at,
            metadata={
                "client_id": _string_or_none(row.client_id),
                "site_id": _string_or_none(row.site_id),
                "job_id": _string_or_none(row.job_id),
                "reminder_at": _iso(row.reminder_at),
            },
        )
        for row in rows
    ]


def _matched_fields(
    row: Any,
    query: str,
    fields: Iterable[str],
    *,
    capped_fields: dict[str, int] | None = None,
) -> list[str]:
    query_lower = query.casefold()
    matches: list[str] = []
    for field in fields:
        value = getattr(row, field, None)
        if value is None:
            continue
        text = str(value)
        cap = (capped_fields or {}).get(field)
        if cap is not None:
            text = text[:cap]
        if query_lower in text.casefold():
            matches.append(field)
    return matches


def _search_term(query: str) -> str:
    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _contains(column: Any, search_term: str) -> Any:
    return column.ilike(search_term, escape="\\")


def _description_from_fields(
    row: Any,
    query: str,
    fields: Sequence[str],
    *,
    capped_fields: dict[str, int] | None = None,
) -> str | None:
    matched = _matched_fields(row, query, fields, capped_fields=capped_fields)
    selected_fields = matched or list(fields)
    for field in selected_fields:
        value = getattr(row, field, None)
        if not value:
            continue
        text = str(value)
        cap = (capped_fields or {}).get(field)
        if cap is not None:
            text = text[:cap]
        return _truncate(text)
    return None


def _truncate(value: str, limit: int = DESCRIPTION_CHAR_LIMIT) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 1].rstrip()}..."


def _join_parts(*parts: object) -> str | None:
    text = " - ".join(str(part) for part in parts if part not in (None, ""))
    return text or None


def _date_label(label: str, value: date | datetime | None) -> str | None:
    if value is None:
        return None
    return f"{label}: {_iso(value)}"


def _iso(value: date | datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _string_or_none(value: uuid.UUID | None) -> str | None:
    return str(value) if value is not None else None
