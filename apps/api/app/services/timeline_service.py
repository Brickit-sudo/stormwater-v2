from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, load_only

from app.models import (
    AiDraft,
    Client,
    EmailImportBatch,
    EmailMessage,
    EmailRecordLink,
    EvidenceFile,
    Job,
    Reminder,
    Site,
)
from app.schemas.timeline import TimelineEntry, TimelineEntryType, TimelineListResponse
from app.services.common import CRMNotFoundError, CRMValidationError


DEFAULT_LIMIT = 50
MAX_LIMIT = 200
_PREVIEW_LIMIT = 180


@dataclass(frozen=True)
class TimelineTarget:
    kind: str
    client_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    job_id: uuid.UUID | None = None
    record: Client | Site | Job | None = None


def _clamp_limit(limit: int) -> int:
    return max(1, min(limit, MAX_LIMIT))


def _as_datetime(value: datetime | date) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    return datetime.combine(value, time.min, tzinfo=UTC)


def _shorten(value: str | None, max_length: int = _PREVIEW_LIMIT) -> str | None:
    if not value:
        return None
    normalized = " ".join(value.split())
    if len(normalized) <= max_length:
        return normalized
    return f"{normalized[: max_length - 1].rstrip()}..."


def _target_count(
    client_id: uuid.UUID | None,
    site_id: uuid.UUID | None,
    job_id: uuid.UUID | None,
) -> int:
    return sum(value is not None for value in (client_id, site_id, job_id))


def _resolve_target(
    db: Session,
    *,
    organization_id: uuid.UUID,
    client_id: uuid.UUID | None,
    site_id: uuid.UUID | None,
    job_id: uuid.UUID | None,
) -> TimelineTarget:
    if _target_count(client_id, site_id, job_id) != 1:
        raise CRMValidationError("Exactly one of client_id, site_id, or job_id is required.")

    if client_id is not None:
        record = db.scalar(
            select(Client).where(
                Client.organization_id == organization_id,
                Client.id == client_id,
                Client.archived_at.is_(None),
            ),
        )
        if record is None:
            raise CRMNotFoundError("Client not found.")
        return TimelineTarget(kind="client", client_id=client_id, record=record)

    if site_id is not None:
        record = db.scalar(
            select(Site).where(
                Site.organization_id == organization_id,
                Site.id == site_id,
                Site.archived_at.is_(None),
            ),
        )
        if record is None:
            raise CRMNotFoundError("Site not found.")
        return TimelineTarget(
            kind="site",
            client_id=record.client_id,
            site_id=site_id,
            record=record,
        )

    assert job_id is not None
    record = db.scalar(
        select(Job).where(
            Job.organization_id == organization_id,
            Job.id == job_id,
            Job.archived_at.is_(None),
        ),
    )
    if record is None:
        raise CRMNotFoundError("Job not found.")
    return TimelineTarget(
        kind="job",
        client_id=record.client_id,
        site_id=record.site_id,
        job_id=job_id,
        record=record,
    )


def _entry(
    *,
    entry_type: TimelineEntryType,
    source_table: str,
    source_id: uuid.UUID,
    title: str,
    occurred_at: datetime | date,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    related_client_id: uuid.UUID | None = None,
    related_site_id: uuid.UUID | None = None,
    related_job_id: uuid.UUID | None = None,
    href: str | None = None,
    metadata: dict[str, Any] | None = None,
    suffix: str | None = None,
) -> TimelineEntry:
    normalized_at = _as_datetime(occurred_at)
    entry_id = f"{source_table}:{source_id}:{entry_type}"
    if suffix:
        entry_id = f"{entry_id}:{suffix}"
    return TimelineEntry(
        id=entry_id,
        type=entry_type,
        title=title,
        description=description,
        occurred_at=normalized_at,
        source_table=source_table,
        source_id=source_id,
        status=status,
        priority=priority,
        related_client_id=related_client_id,
        related_site_id=related_site_id,
        related_job_id=related_job_id,
        href=href,
        metadata=metadata,
    )


def _record_entries(target: TimelineTarget) -> list[TimelineEntry]:
    record = target.record
    if record is None:
        return []

    label = getattr(record, "name", "Record")
    status = getattr(record, "status", None)
    source_table = f"{target.kind}s"
    created_title = f"{target.kind.title()} created"
    entries = [
        _entry(
            entry_type="record",
            source_table=source_table,
            source_id=record.id,
            title=created_title,
            description=label,
            occurred_at=record.created_at,
            status=status,
            related_client_id=target.client_id,
            related_site_id=target.site_id,
            related_job_id=target.job_id,
            suffix="created",
        ),
    ]

    if record.updated_at and _as_datetime(record.updated_at) > _as_datetime(record.created_at):
        entries.append(
            _entry(
                entry_type="record",
                source_table=source_table,
                source_id=record.id,
                title=f"{target.kind.title()} updated",
                description=label,
                occurred_at=record.updated_at,
                status=status,
                related_client_id=target.client_id,
                related_site_id=target.site_id,
                related_job_id=target.job_id,
                suffix="updated",
            ),
        )

    return entries


def _scope_condition(
    model: type[Reminder] | type[EvidenceFile] | type[EmailMessage] | type[AiDraft],
    *,
    client_ids: set[uuid.UUID],
    site_ids: set[uuid.UUID],
    job_ids: set[uuid.UUID],
) -> Any:
    clauses = []
    if client_ids:
        clauses.append(model.client_id.in_(client_ids))
    if site_ids:
        clauses.append(model.site_id.in_(site_ids))
    if job_ids:
        clauses.append(model.job_id.in_(job_ids))
    return or_(*clauses)


def _link_scope_condition(
    *,
    client_ids: set[uuid.UUID],
    site_ids: set[uuid.UUID],
    job_ids: set[uuid.UUID],
) -> Any:
    clauses = []
    if client_ids:
        clauses.append(EmailRecordLink.client_id.in_(client_ids))
    if site_ids:
        clauses.append(EmailRecordLink.site_id.in_(site_ids))
    if job_ids:
        clauses.append(EmailRecordLink.job_id.in_(job_ids))
    return or_(*clauses)


def _job_event_at(job: Job) -> datetime | date:
    return job.completed_date or job.scheduled_date or job.due_date or job.updated_at or job.created_at


def _job_title(job: Job) -> str:
    if job.completed_date:
        return f"{job.name} completed"
    if job.scheduled_date:
        return f"{job.name} scheduled"
    return job.name


def _collect_related_site_ids(
    db: Session,
    *,
    organization_id: uuid.UUID,
    client_id: uuid.UUID,
    limit: int,
) -> set[uuid.UUID]:
    statement = (
        select(Site.id)
        .where(
            Site.organization_id == organization_id,
            Site.client_id == client_id,
            Site.archived_at.is_(None),
        )
        .order_by(Site.updated_at.desc(), Site.created_at.desc(), Site.id)
        .limit(limit)
    )
    return set(db.scalars(statement).all())


def _collect_jobs(
    db: Session,
    *,
    organization_id: uuid.UUID,
    client_id: uuid.UUID | None,
    site_id: uuid.UUID | None,
    limit: int,
) -> list[Job]:
    statement = select(Job).where(
        Job.organization_id == organization_id,
        Job.archived_at.is_(None),
    )
    if site_id is not None:
        statement = statement.where(Job.site_id == site_id)
    elif client_id is not None:
        statement = statement.where(Job.client_id == client_id)
    else:
        return []
    statement = statement.order_by(Job.updated_at.desc(), Job.created_at.desc(), Job.id).limit(limit)
    return list(db.scalars(statement).all())


def _job_entries(jobs: list[Job]) -> list[TimelineEntry]:
    return [
        _entry(
            entry_type="job",
            source_table="jobs",
            source_id=job.id,
            title=_job_title(job),
            description=_shorten(job.service_type or job.scope),
            occurred_at=_job_event_at(job),
            status=job.status,
            related_client_id=job.client_id,
            related_site_id=job.site_id,
            related_job_id=job.id,
        )
        for job in jobs
    ]


def _collect_reminders(
    db: Session,
    *,
    organization_id: uuid.UUID,
    client_ids: set[uuid.UUID],
    site_ids: set[uuid.UUID],
    job_ids: set[uuid.UUID],
    limit: int,
) -> list[Reminder]:
    statement = (
        select(Reminder)
        .where(
            Reminder.organization_id == organization_id,
            Reminder.archived_at.is_(None),
            _scope_condition(Reminder, client_ids=client_ids, site_ids=site_ids, job_ids=job_ids),
        )
        .order_by(Reminder.updated_at.desc(), Reminder.created_at.desc(), Reminder.id)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def _reminder_entries(reminders: list[Reminder]) -> list[TimelineEntry]:
    entries = []
    for reminder in reminders:
        occurred_at = reminder.completed_at or reminder.due_at or reminder.reminder_at or reminder.created_at
        entries.append(
            _entry(
                entry_type="reminder",
                source_table="reminders",
                source_id=reminder.id,
                title=reminder.title,
                description=_shorten(reminder.description),
                occurred_at=occurred_at,
                status=reminder.status,
                priority=reminder.priority,
                related_client_id=reminder.client_id,
                related_site_id=reminder.site_id,
                related_job_id=reminder.job_id,
            ),
        )
    return entries


def _collect_files(
    db: Session,
    *,
    organization_id: uuid.UUID,
    client_ids: set[uuid.UUID],
    site_ids: set[uuid.UUID],
    job_ids: set[uuid.UUID],
    limit: int,
) -> list[EvidenceFile]:
    statement = (
        select(EvidenceFile)
        .where(
            EvidenceFile.organization_id == organization_id,
            EvidenceFile.archived_at.is_(None),
            _scope_condition(EvidenceFile, client_ids=client_ids, site_ids=site_ids, job_ids=job_ids),
        )
        .order_by(EvidenceFile.updated_at.desc(), EvidenceFile.created_at.desc(), EvidenceFile.id)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def _file_entries(files: list[EvidenceFile]) -> list[TimelineEntry]:
    entries = []
    for file in files:
        entries.append(
            _entry(
                entry_type="file",
                source_table="evidence_files",
                source_id=file.id,
                title=f"{file.file_name} linked",
                description=_shorten(file.caption or file.mime_type or file.source),
                occurred_at=file.created_at,
                status=file.source,
                related_client_id=file.client_id,
                related_site_id=file.site_id,
                related_job_id=file.job_id,
                href=file.public_url,
                metadata={
                    "mime_type": file.mime_type,
                    "size_bytes": file.size_bytes,
                    "drive_file_id": file.drive_file_id,
                },
            ),
        )
    return entries


def _collect_email_messages(
    db: Session,
    *,
    organization_id: uuid.UUID,
    client_ids: set[uuid.UUID],
    site_ids: set[uuid.UUID],
    job_ids: set[uuid.UUID],
    limit: int,
) -> list[EmailMessage]:
    statement = (
        select(EmailMessage)
        .options(
            load_only(
                EmailMessage.id,
                EmailMessage.import_batch_id,
                EmailMessage.client_id,
                EmailMessage.site_id,
                EmailMessage.job_id,
                EmailMessage.provider,
                EmailMessage.subject,
                EmailMessage.sender,
                EmailMessage.received_at,
                EmailMessage.snippet,
                EmailMessage.web_link,
                EmailMessage.status,
                EmailMessage.created_at,
            ),
        )
        .where(
            EmailMessage.organization_id == organization_id,
            EmailMessage.archived_at.is_(None),
            EmailMessage.status != "archived",
            _scope_condition(EmailMessage, client_ids=client_ids, site_ids=site_ids, job_ids=job_ids),
        )
        .order_by(EmailMessage.received_at.desc(), EmailMessage.created_at.desc(), EmailMessage.id)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def _email_entries(messages: list[EmailMessage]) -> list[TimelineEntry]:
    entries = []
    for message in messages:
        entries.append(
            _entry(
                entry_type="email",
                source_table="email_messages",
                source_id=message.id,
                title=f"Email from {message.sender}: {message.subject}",
                description=_shorten(message.snippet),
                occurred_at=message.received_at or message.created_at,
                status=message.status,
                related_client_id=message.client_id,
                related_site_id=message.site_id,
                related_job_id=message.job_id,
                href=message.web_link,
                metadata={
                    "provider": message.provider,
                    "import_batch_id": str(message.import_batch_id) if message.import_batch_id else None,
                },
            ),
        )
    return entries


def _collect_email_links(
    db: Session,
    *,
    organization_id: uuid.UUID,
    client_ids: set[uuid.UUID],
    site_ids: set[uuid.UUID],
    job_ids: set[uuid.UUID],
    limit: int,
) -> list[tuple[EmailRecordLink, EmailMessage]]:
    statement = (
        select(EmailRecordLink, EmailMessage)
        .join(EmailMessage, EmailRecordLink.email_message_id == EmailMessage.id)
        .options(
            load_only(
                EmailRecordLink.id,
                EmailRecordLink.email_message_id,
                EmailRecordLink.client_id,
                EmailRecordLink.site_id,
                EmailRecordLink.job_id,
                EmailRecordLink.link_reason,
                EmailRecordLink.confidence,
                EmailRecordLink.created_at,
            ),
            load_only(
                EmailMessage.id,
                EmailMessage.subject,
                EmailMessage.sender,
                EmailMessage.import_batch_id,
                EmailMessage.archived_at,
                EmailMessage.status,
            ),
        )
        .where(
            EmailRecordLink.organization_id == organization_id,
            EmailMessage.organization_id == organization_id,
            EmailMessage.archived_at.is_(None),
            EmailMessage.status != "archived",
            _link_scope_condition(client_ids=client_ids, site_ids=site_ids, job_ids=job_ids),
        )
        .order_by(EmailRecordLink.created_at.desc(), EmailRecordLink.id)
        .limit(limit)
    )
    return [(link, message) for link, message in db.execute(statement).all()]


def _email_link_entries(rows: list[tuple[EmailRecordLink, EmailMessage]]) -> list[TimelineEntry]:
    entries = []
    for link, message in rows:
        entries.append(
            _entry(
                entry_type="email_link",
                source_table="email_record_links",
                source_id=link.id,
                title=f"Email linked: {message.subject}",
                description=f"{link.link_reason} link from {message.sender}",
                occurred_at=link.created_at,
                status=link.link_reason,
                related_client_id=link.client_id,
                related_site_id=link.site_id,
                related_job_id=link.job_id,
                metadata={
                    "email_message_id": str(link.email_message_id),
                    "confidence": link.confidence,
                },
            ),
        )
    return entries


def _collect_ai_drafts(
    db: Session,
    *,
    organization_id: uuid.UUID,
    client_ids: set[uuid.UUID],
    site_ids: set[uuid.UUID],
    job_ids: set[uuid.UUID],
    email_message_ids: set[uuid.UUID],
    limit: int,
) -> list[AiDraft]:
    clauses = [
        _scope_condition(AiDraft, client_ids=client_ids, site_ids=site_ids, job_ids=job_ids),
    ]
    if email_message_ids:
        clauses.append(AiDraft.email_message_id.in_(email_message_ids))
    statement = (
        select(AiDraft)
        .where(
            AiDraft.organization_id == organization_id,
            AiDraft.archived_at.is_(None),
            AiDraft.status != "archived",
            or_(*clauses),
        )
        .order_by(AiDraft.updated_at.desc(), AiDraft.created_at.desc(), AiDraft.id)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def _ai_draft_entries(drafts: list[AiDraft]) -> list[TimelineEntry]:
    entries = []
    for draft in drafts:
        entries.append(
            _entry(
                entry_type="ai_draft",
                source_table="ai_drafts",
                source_id=draft.id,
                title=f"{draft.title} created",
                description=_shorten(draft.prompt_context),
                occurred_at=draft.created_at,
                status=draft.status,
                related_client_id=draft.client_id,
                related_site_id=draft.site_id,
                related_job_id=draft.job_id,
                metadata={
                    "draft_type": draft.draft_type,
                    "email_message_id": str(draft.email_message_id) if draft.email_message_id else None,
                },
            ),
        )
        if draft.provider_draft_id or draft.pushed_to_provider_at:
            entries.append(
                _entry(
                    entry_type="outlook_draft",
                    source_table="ai_drafts",
                    source_id=draft.id,
                    title="Outlook draft created",
                    description=_shorten(draft.title),
                    occurred_at=draft.pushed_to_provider_at or draft.updated_at,
                    status=draft.provider_status,
                    related_client_id=draft.client_id,
                    related_site_id=draft.site_id,
                    related_job_id=draft.job_id,
                    href=draft.provider_web_link,
                    metadata={
                        "provider": draft.provider,
                        "provider_draft_id": draft.provider_draft_id,
                        "ai_draft_id": str(draft.id),
                    },
                ),
            )
    return entries


def _collect_import_batches(
    db: Session,
    *,
    organization_id: uuid.UUID,
    import_batch_ids: set[uuid.UUID],
    limit: int,
) -> list[EmailImportBatch]:
    if not import_batch_ids:
        return []
    statement = (
        select(EmailImportBatch)
        .where(
            EmailImportBatch.organization_id == organization_id,
            EmailImportBatch.archived_at.is_(None),
            EmailImportBatch.id.in_(import_batch_ids),
        )
        .order_by(EmailImportBatch.created_at.desc(), EmailImportBatch.id)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


def _import_batch_entries(
    batches: list[EmailImportBatch],
    target: TimelineTarget,
) -> list[TimelineEntry]:
    entries = []
    for batch in batches:
        provider = batch.provider.title()
        description = (
            f"{batch.imported_count} imported, {batch.skipped_count} skipped, "
            f"{batch.duplicate_count} duplicates"
        )
        entries.append(
            _entry(
                entry_type="import_batch",
                source_table="email_import_batches",
                source_id=batch.id,
                title=f"{provider} email import batch",
                description=description,
                occurred_at=batch.completed_at or batch.created_at,
                status=batch.status,
                related_client_id=target.client_id,
                related_site_id=target.site_id,
                related_job_id=target.job_id,
                metadata={
                    "provider": batch.provider,
                    "import_mode": batch.import_mode,
                    "preview_count": batch.preview_count,
                    "imported_count": batch.imported_count,
                    "error_count": batch.error_count,
                },
            ),
        )
    return entries


def list_timeline(
    db: Session,
    *,
    organization_id: uuid.UUID,
    client_id: uuid.UUID | None = None,
    site_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    limit: int = DEFAULT_LIMIT,
) -> TimelineListResponse:
    normalized_limit = _clamp_limit(limit)
    source_limit = max(normalized_limit, DEFAULT_LIMIT)
    target = _resolve_target(
        db,
        organization_id=organization_id,
        client_id=client_id,
        site_id=site_id,
        job_id=job_id,
    )

    related_site_ids: set[uuid.UUID] = set()
    if target.kind == "client" and target.client_id is not None:
        related_site_ids = _collect_related_site_ids(
            db,
            organization_id=organization_id,
            client_id=target.client_id,
            limit=source_limit,
        )

    jobs = []
    if target.kind in {"client", "site"}:
        jobs = _collect_jobs(
            db,
            organization_id=organization_id,
            client_id=target.client_id,
            site_id=target.site_id,
            limit=source_limit,
        )

    client_ids = {target.client_id} if target.client_id is not None else set()
    site_ids = {target.site_id} if target.site_id is not None else set()
    site_ids.update(related_site_ids)
    job_ids = {target.job_id} if target.job_id is not None else set()
    job_ids.update(job.id for job in jobs)

    entries: list[TimelineEntry] = []
    entries.extend(_job_entries(jobs))

    reminders = _collect_reminders(
        db,
        organization_id=organization_id,
        client_ids=client_ids,
        site_ids=site_ids,
        job_ids=job_ids,
        limit=source_limit,
    )
    entries.extend(_reminder_entries(reminders))

    files = _collect_files(
        db,
        organization_id=organization_id,
        client_ids=client_ids,
        site_ids=site_ids,
        job_ids=job_ids,
        limit=source_limit,
    )
    entries.extend(_file_entries(files))

    emails = _collect_email_messages(
        db,
        organization_id=organization_id,
        client_ids=client_ids,
        site_ids=site_ids,
        job_ids=job_ids,
        limit=source_limit,
    )
    entries.extend(_email_entries(emails))

    email_link_rows = _collect_email_links(
        db,
        organization_id=organization_id,
        client_ids=client_ids,
        site_ids=site_ids,
        job_ids=job_ids,
        limit=source_limit,
    )
    entries.extend(_email_link_entries(email_link_rows))

    email_message_ids = {message.id for message in emails}
    email_message_ids.update(message.id for _, message in email_link_rows)

    drafts = _collect_ai_drafts(
        db,
        organization_id=organization_id,
        client_ids=client_ids,
        site_ids=site_ids,
        job_ids=job_ids,
        email_message_ids=email_message_ids,
        limit=source_limit,
    )
    entries.extend(_ai_draft_entries(drafts))

    import_batch_ids = {message.import_batch_id for message in emails if message.import_batch_id}
    import_batch_ids.update(
        message.import_batch_id for _, message in email_link_rows if message.import_batch_id
    )
    batches = _collect_import_batches(
        db,
        organization_id=organization_id,
        import_batch_ids=import_batch_ids,
        limit=source_limit,
    )
    entries.extend(_import_batch_entries(batches, target))

    if entries:
        entries.extend(_record_entries(target))

    sorted_entries = sorted(
        entries,
        key=lambda item: (_as_datetime(item.occurred_at), item.id),
        reverse=True,
    )
    return TimelineListResponse(
        items=sorted_entries[:normalized_limit],
        total=len(sorted_entries),
        limit=normalized_limit,
        offset=0,
    )
