from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models import AiDraft, Client, EmailMessage, EmailRecordLink, EvidenceFile, Job, Reminder, Site
from app.schemas.report_readiness import ReportReadinessCheck, ReportReadinessResponse
from app.services.common import CRMNotFoundError


READY_STATUSES = {"scheduled", "in_progress", "in_review", "completed"}
WARNING_STATUSES = {"draft"}
BLOCKED_STATUSES = {"cancelled", "archived"}
REPORT_READY_DRAFT_TYPES = {
    "report_section",
    "maintenance_recommendation",
    "client_summary",
    "email_reply",
}
LOCAL_READ_LIMIT = 100


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _has_text(value: str | None) -> bool:
    return bool(value and value.strip())


def _count(db: Session, statement: Select[Any]) -> int:
    return int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)


def _check(
    *,
    key: str,
    label: str,
    group: str,
    status: str,
    severity: str,
    message: str,
    related_count: int | None = None,
    suggested_next_step: str | None = None,
) -> ReportReadinessCheck:
    return ReportReadinessCheck(
        key=key,
        label=label,
        group=group,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        message=message,
        related_count=related_count,
        suggested_next_step=suggested_next_step,
    )


def _get_job(db: Session, *, organization_id: uuid.UUID, job_id: uuid.UUID) -> Job:
    job = db.scalar(
        select(Job).where(
            Job.organization_id == organization_id,
            Job.id == job_id,
            Job.archived_at.is_(None),
        ),
    )
    if job is None:
        raise CRMNotFoundError("Job not found.")
    return job


def _client_exists(db: Session, *, organization_id: uuid.UUID, client_id: uuid.UUID | None) -> bool:
    if client_id is None:
        return False
    return (
        db.scalar(
            select(Client.id).where(
                Client.organization_id == organization_id,
                Client.id == client_id,
                Client.archived_at.is_(None),
            ),
        )
        is not None
    )


def _site_status(
    db: Session,
    *,
    organization_id: uuid.UUID,
    site_id: uuid.UUID | None,
    client_id: uuid.UUID | None,
) -> tuple[bool, bool]:
    if site_id is None:
        return False, False
    site = db.scalar(
        select(Site).where(
            Site.organization_id == organization_id,
            Site.id == site_id,
            Site.archived_at.is_(None),
        ),
    )
    if site is None:
        return False, False
    return True, client_id is None or site.client_id == client_id


def _file_count(db: Session, *, organization_id: uuid.UUID, job_id: uuid.UUID) -> int:
    return _count(
        db,
        select(EvidenceFile.id).where(
            EvidenceFile.organization_id == organization_id,
            EvidenceFile.job_id == job_id,
            EvidenceFile.archived_at.is_(None),
        ),
    )


def _email_context_count(db: Session, *, organization_id: uuid.UUID, job_id: uuid.UUID) -> int:
    direct_count = _count(
        db,
        select(EmailMessage.id).where(
            EmailMessage.organization_id == organization_id,
            EmailMessage.job_id == job_id,
            EmailMessage.archived_at.is_(None),
            EmailMessage.status != "archived",
        ),
    )
    linked_count = _count(
        db,
        select(EmailRecordLink.id)
        .join(EmailMessage, EmailRecordLink.email_message_id == EmailMessage.id)
        .where(
            EmailRecordLink.organization_id == organization_id,
            EmailRecordLink.job_id == job_id,
            EmailMessage.organization_id == organization_id,
            EmailMessage.archived_at.is_(None),
            EmailMessage.status != "archived",
        ),
    )
    return direct_count + linked_count


def _draft_count(db: Session, *, organization_id: uuid.UUID, job_id: uuid.UUID) -> int:
    return _count(
        db,
        select(AiDraft.id).where(
            AiDraft.organization_id == organization_id,
            AiDraft.job_id == job_id,
            AiDraft.archived_at.is_(None),
            AiDraft.status != "archived",
            AiDraft.draft_type.in_(REPORT_READY_DRAFT_TYPES),
        ),
    )


def _load_job_reminders(
    db: Session,
    *,
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
) -> list[Reminder]:
    statement = (
        select(Reminder)
        .where(
            Reminder.organization_id == organization_id,
            Reminder.job_id == job_id,
            Reminder.archived_at.is_(None),
        )
        .order_by(Reminder.due_at.is_(None), Reminder.due_at, Reminder.updated_at.desc(), Reminder.id)
        .limit(LOCAL_READ_LIMIT)
    )
    return list(db.scalars(statement).all())


def _is_high_overdue_open(reminder: Reminder, now: datetime) -> bool:
    if reminder.status != "open" or reminder.priority != "high" or reminder.due_at is None:
        return False
    return _aware(reminder.due_at) < now


def _score(checks: list[ReportReadinessCheck]) -> int:
    if not checks:
        return 0
    points = 0.0
    for check in checks:
        if check.status == "pass":
            points += 1.0
        elif check.status == "warning":
            points += 0.5
    return round((points / len(checks)) * 100)


def _summary(
    *,
    overall_status: str,
    blockers: list[ReportReadinessCheck],
    warnings: list[ReportReadinessCheck],
    ready_items: list[ReportReadinessCheck],
) -> str:
    if overall_status == "blocked":
        return (
            f"Blocked by {len(blockers)} high-priority readiness item"
            f"{'' if len(blockers) == 1 else 's'}."
        )
    if overall_status == "needs_attention":
        return (
            f"{len(warnings)} readiness item{'' if len(warnings) == 1 else 's'} "
            "need attention before this job is fully report-ready."
        )
    return f"Ready with {len(ready_items)} local readiness item{'' if len(ready_items) == 1 else 's'} in place."


def get_report_readiness(
    db: Session,
    *,
    organization_id: uuid.UUID,
    job_id: uuid.UUID,
) -> ReportReadinessResponse:
    job = _get_job(db, organization_id=organization_id, job_id=job_id)
    now = _now()

    client_ok = _client_exists(db, organization_id=organization_id, client_id=job.client_id)
    site_ok, site_matches_client = _site_status(
        db,
        organization_id=organization_id,
        site_id=job.site_id,
        client_id=job.client_id,
    )
    files_count = _file_count(db, organization_id=organization_id, job_id=job.id)
    email_count = _email_context_count(db, organization_id=organization_id, job_id=job.id)
    draft_count = _draft_count(db, organization_id=organization_id, job_id=job.id)
    reminders = _load_job_reminders(db, organization_id=organization_id, job_id=job.id)
    active_reminders = [
        reminder
        for reminder in reminders
        if reminder.status in {"open", "snoozed"} and reminder.archived_at is None
    ]
    blocking_reminders = [
        reminder for reminder in active_reminders if _is_high_overdue_open(reminder, now)
    ]
    other_open_reminders = [
        reminder for reminder in active_reminders if reminder.id not in {item.id for item in blocking_reminders}
    ]
    timeline_activity_count = files_count + email_count + draft_count + len(active_reminders)

    checks: list[ReportReadinessCheck] = []

    checks.append(
        _check(
            key="client_linked",
            label="Client linked",
            group="Required",
            status="pass" if client_ok else "fail",
            severity="high",
            message="Job has a linked client." if client_ok else "Job is missing a usable client link.",
            related_count=1 if client_ok else 0,
            suggested_next_step=None if client_ok else "Link a client before report work starts.",
        ),
    )

    site_status = "pass" if site_ok and site_matches_client else "fail"
    site_message = "Job has a linked site."
    site_next_step = None
    if not site_ok:
        site_message = "Job is missing a usable site link."
        site_next_step = "Link a site before report work starts."
    elif not site_matches_client:
        site_message = "The linked site does not belong to the linked client."
        site_next_step = "Fix the job client/site relationship before report work starts."
    checks.append(
        _check(
            key="site_linked",
            label="Site linked",
            group="Required",
            status=site_status,
            severity="high",
            message=site_message,
            related_count=1 if site_ok and site_matches_client else 0,
            suggested_next_step=site_next_step,
        ),
    )

    service_type_present = _has_text(job.service_type)
    checks.append(
        _check(
            key="service_type",
            label="Service type present",
            group="Required",
            status="pass" if service_type_present else "warning",
            severity="medium",
            message=(
                "Service type is present."
                if service_type_present
                else "Service type is missing, so report scope may be unclear."
            ),
            related_count=1 if service_type_present else 0,
            suggested_next_step=None if service_type_present else "Add a service type to clarify the report path.",
        ),
    )

    normalized_status = (job.status or "").strip().lower()
    if normalized_status in READY_STATUSES:
        status_check = _check(
            key="job_status",
            label="Usable job status",
            group="Required",
            status="pass",
            severity="medium",
            message=f"Job status is {normalized_status.replace('_', ' ')}.",
            related_count=1,
        )
    elif normalized_status in WARNING_STATUSES:
        status_check = _check(
            key="job_status",
            label="Usable job status",
            group="Required",
            status="warning",
            severity="medium",
            message="Job is still in draft status.",
            related_count=1,
            suggested_next_step="Move the job out of draft when report work is ready to begin.",
        )
    elif normalized_status in BLOCKED_STATUSES:
        status_check = _check(
            key="job_status",
            label="Usable job status",
            group="Required",
            status="fail",
            severity="high",
            message=f"Job status is {normalized_status.replace('_', ' ')}, so report work is blocked.",
            related_count=1,
            suggested_next_step="Use an active job status before report work starts.",
        )
    else:
        status_check = _check(
            key="job_status",
            label="Usable job status",
            group="Required",
            status="warning",
            severity="medium",
            message="Job status is not recognized by the readiness checklist.",
            related_count=1 if normalized_status else 0,
            suggested_next_step="Confirm the job status before report work starts.",
        )
    checks.append(status_check)

    date_count = sum(value is not None for value in (job.scheduled_date, job.due_date))
    checks.append(
        _check(
            key="date_readiness",
            label="Date readiness",
            group="Required",
            status="pass" if date_count > 0 else "warning",
            severity="medium",
            message=(
                "Job has a scheduled date or due date."
                if date_count > 0
                else "Job has no scheduled date or due date."
            ),
            related_count=date_count,
            suggested_next_step=None if date_count > 0 else "Add a scheduled date or due date.",
        ),
    )

    scope_ready = _has_text(job.scope) or _has_text(job.notes)
    checks.append(
        _check(
            key="scope_notes",
            label="Scope or notes present",
            group="Supporting Evidence",
            status="pass" if scope_ready else "warning",
            severity="medium",
            message=(
                "Job has scope or notes for report context."
                if scope_ready
                else "Job is missing scope and notes."
            ),
            related_count=1 if scope_ready else 0,
            suggested_next_step=None if scope_ready else "Add scope or notes before drafting report language.",
        ),
    )

    checks.append(
        _check(
            key="evidence_files",
            label="Evidence or files linked",
            group="Supporting Evidence",
            status="pass" if files_count > 0 else "warning",
            severity="medium",
            message=(
                f"{files_count} job file record{'' if files_count == 1 else 's'} linked."
                if files_count > 0
                else "No job evidence files are linked yet."
            ),
            related_count=files_count,
            suggested_next_step=None if files_count > 0 else "Link local file metadata or evidence before report work.",
        ),
    )

    has_drive_folder = _has_text(job.drive_folder_url)
    drive_status = "pass" if has_drive_folder else "warning"
    drive_severity = "low" if files_count > 0 else "medium"
    drive_message = "Job has a stored Drive folder URL."
    drive_next_step = None
    if not has_drive_folder and files_count > 0:
        drive_message = "Job has linked file records but no stored Drive folder URL."
        drive_next_step = "Add the Drive folder URL when it is available."
    elif not has_drive_folder:
        drive_message = "Job has no stored Drive folder URL or linked job file records."
        drive_next_step = "Add a Drive folder URL or linked file records when available."
    checks.append(
        _check(
            key="drive_context",
            label="Drive or file context",
            group="Supporting Evidence",
            status=drive_status,
            severity=drive_severity,
            message=drive_message,
            related_count=1 if has_drive_folder else files_count,
            suggested_next_step=drive_next_step,
        ),
    )

    if blocking_reminders:
        reminders_check = _check(
            key="open_reminders",
            label="Open blockers or reminders",
            group="Open Issues",
            status="fail",
            severity="high",
            message=(
                f"{len(blocking_reminders)} high-priority overdue open reminder"
                f"{'' if len(blocking_reminders) == 1 else 's'} linked to this job."
            ),
            related_count=len(blocking_reminders),
            suggested_next_step="Resolve or complete high-priority overdue job reminders.",
        )
    elif other_open_reminders:
        reminders_check = _check(
            key="open_reminders",
            label="Open blockers or reminders",
            group="Open Issues",
            status="warning",
            severity="medium",
            message=(
                f"{len(other_open_reminders)} open reminder"
                f"{'' if len(other_open_reminders) == 1 else 's'} linked to this job."
            ),
            related_count=len(other_open_reminders),
            suggested_next_step="Review open job reminders before final report work.",
        )
    else:
        reminders_check = _check(
            key="open_reminders",
            label="Open blockers or reminders",
            group="Open Issues",
            status="pass",
            severity="medium",
            message="No open job reminders are blocking report work.",
            related_count=0,
        )
    checks.append(reminders_check)

    checks.append(
        _check(
            key="ai_drafts",
            label="AI draft context",
            group="Draft / Communication Context",
            status="pass" if draft_count > 0 else "warning",
            severity="low",
            message=(
                f"{draft_count} relevant AI draft{'' if draft_count == 1 else 's'} linked."
                if draft_count > 0
                else "No report, maintenance, client summary, or useful email draft is linked yet."
            ),
            related_count=draft_count,
            suggested_next_step=None if draft_count > 0 else "Add draft context later if it helps; this is not a blocker.",
        ),
    )

    checks.append(
        _check(
            key="email_context",
            label="Email context",
            group="Draft / Communication Context",
            status="pass" if email_count > 0 else "warning",
            severity="low",
            message=(
                f"{email_count} local email context item{'' if email_count == 1 else 's'} linked."
                if email_count > 0
                else "No local email context is linked to this job."
            ),
            related_count=email_count,
            suggested_next_step=None if email_count > 0 else "Link email context later if it affects report language.",
        ),
    )

    if timeline_activity_count >= 2:
        timeline_status = "pass"
        timeline_severity = "low"
        timeline_message = "Local timeline has enough activity to support report work."
        timeline_next_step = None
    elif timeline_activity_count == 1:
        timeline_status = "warning"
        timeline_severity = "low"
        timeline_message = "Local timeline has only one supporting activity item."
        timeline_next_step = "Review linked job activity before relying on the timeline."
    else:
        timeline_status = "warning"
        timeline_severity = "medium"
        timeline_message = "Local timeline is sparse for this job."
        timeline_next_step = "Link evidence, reminders, emails, or drafts as they become available."
    checks.append(
        _check(
            key="timeline_activity",
            label="Timeline activity",
            group="Draft / Communication Context",
            status=timeline_status,
            severity=timeline_severity,
            message=timeline_message,
            related_count=timeline_activity_count,
            suggested_next_step=timeline_next_step,
        ),
    )

    blockers = [check for check in checks if check.status == "fail" and check.severity == "high"]
    warnings = [check for check in checks if check.status == "warning" or check.status == "fail"]
    ready_items = [check for check in checks if check.status == "pass"]

    if blockers:
        overall_status = "blocked"
    elif warnings:
        overall_status = "needs_attention"
    else:
        overall_status = "ready"

    return ReportReadinessResponse(
        job_id=job.id,
        overall_status=overall_status,  # type: ignore[arg-type]
        score=_score(checks),
        summary=_summary(
            overall_status=overall_status,
            blockers=blockers,
            warnings=warnings,
            ready_items=ready_items,
        ),
        checks=checks,
        blockers=blockers,
        warnings=warnings,
        ready_items=ready_items,
    )
