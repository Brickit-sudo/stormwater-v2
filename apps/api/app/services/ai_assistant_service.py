from __future__ import annotations

import html
import json
import re
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import Client, EmailMessage, Job, Site
from app.schemas.ai_assistant import (
    ActionItemSuggestion,
    AiOperationResponse,
    AiStatusResponse,
    ClientSummaryDraftRequest,
    DraftReplyRequest,
    DraftReplyResponse,
    DraftReplyResult,
    EmailActionItemsRequest,
    EmailActionItemsResponse,
    EmailSummaryRequest,
    EmailSummaryResponse,
    EmailSummaryResult,
    ExtractFileLinksRequest,
    ExtractFileLinksResponse,
    FileLinkCandidate,
    MaintenanceRecommendationDraftRequest,
    RecordLinkSuggestion,
    ReportSectionDraftRequest,
    ReportSectionDraftResponse,
    ReportSectionDraftResult,
    SavedDraftRef,
    SuggestRecordLinksRequest,
    SuggestRecordLinksResponse,
)
from app.services import ai_drafts_service, email_messages_service
from app.services.common import CRMValidationError
from app.services.integrations_service import get_ai_config_status


URL_RE = re.compile(r"https?://[^\s<>\"]+", re.IGNORECASE)
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")
ACTION_KEYWORDS = (
    "please",
    "can you",
    "could you",
    "need",
    "needs",
    "follow up",
    "confirm",
    "send",
    "schedule",
    "revisit",
    "review",
    "provide",
    "recommend",
    "question",
    "summarize",
)
HIGH_PRIORITY_TERMS = ("urgent", "asap", "blocked", "before", "today", "tomorrow")
LOW_PRIORITY_TERMS = ("newsletter", "fyi", "routine", "monthly")


class AiProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class AssistantContext:
    organization_id: uuid.UUID
    email_message: EmailMessage | None
    client_id: uuid.UUID | None
    site_id: uuid.UUID | None
    job_id: uuid.UUID | None
    text: str
    title: str


def _trim(value: str | None) -> str | None:
    if value is None:
        return None
    candidate = value.strip()
    return candidate or None


def _settings_status(settings: Settings | None = None) -> AiStatusResponse:
    current = settings or get_settings()
    status = get_ai_config_status(current)
    enabled = status.configured and current.ai_features_enabled is not False
    return AiStatusResponse(
        configured=status.configured,
        enabled=enabled,
        model=status.model,
        missing_fields=status.missing_fields,
        message=status.message,
    )


def get_ai_status() -> AiStatusResponse:
    return _settings_status()


def _load_context(
    db: Session,
    *,
    organization_id: uuid.UUID,
    email_message_id: uuid.UUID | None,
    client_id: uuid.UUID | None,
    site_id: uuid.UUID | None,
    job_id: uuid.UUID | None,
    user_context: str | None,
    direct_text: str | None = None,
) -> AssistantContext:
    email_messages_service.require_organization(db, organization_id)
    email_message: EmailMessage | None = None
    text_parts: list[str] = []
    title = "Manual AI context"

    if email_message_id is not None:
        email_message = email_messages_service.require_email_message(
            db,
            organization_id=organization_id,
            email_message_id=email_message_id,
        )
        title = email_message.subject
        client_id = client_id or email_message.client_id
        site_id = site_id or email_message.site_id
        job_id = job_id or email_message.job_id
        text_parts.extend(
            [
                f"Subject: {email_message.subject}",
                f"From: {email_message.sender}",
                f"Snippet: {email_message.snippet or ''}",
                email_message.body_text or "",
                html.unescape(email_message.body_html or ""),
                _links_json_text(email_message.links_json),
            ],
        )

    if direct_text:
        text_parts.append(direct_text)
        title = title if email_message else "Provided text"
    if user_context:
        text_parts.append(user_context)

    client_id, site_id, job_id = email_messages_service.normalize_scope(
        db,
        organization_id=organization_id,
        client_id=client_id,
        site_id=site_id,
        job_id=job_id,
    )
    text = "\n".join(part for part in text_parts if part and part.strip()).strip()
    if not text:
        raise CRMValidationError("email_message_id, text, or user_context is required.")

    return AssistantContext(
        organization_id=organization_id,
        email_message=email_message,
        client_id=client_id,
        site_id=site_id,
        job_id=job_id,
        text=text,
        title=title,
    )


def _load_context_from_payload(
    db: Session,
    payload: Any,
    *,
    direct_text: str | None = None,
) -> AssistantContext:
    return _load_context(
        db,
        organization_id=payload.organization_id,
        email_message_id=payload.email_message_id,
        client_id=payload.client_id,
        site_id=payload.site_id,
        job_id=payload.job_id,
        user_context=payload.user_context,
        direct_text=direct_text,
    )


def _links_json_text(items: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in items or []:
        for key in ("url", "href", "webUrl", "web_url"):
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                label = item.get("label") if isinstance(item.get("label"), str) else "stored link"
                parts.append(f"{label}: {value.strip()}")
    return "\n".join(parts)


def extract_urls_from_text(text: str) -> list[str]:
    decoded = html.unescape(text or "")
    seen: set[str] = set()
    urls: list[str] = []
    for match in URL_RE.finditer(decoded):
        url = match.group(0).rstrip(").,;]'")
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def _label_from_url(url: str, link_type: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if link_type == "google_drive":
        return "Google Drive link"
    if link_type == "onedrive":
        return "OneDrive link"
    if link_type == "sharepoint":
        return "SharePoint link"
    if path:
        leaf = path.split("/")[-1] or parsed.netloc
        return leaf.replace("-", " ").replace("_", " ")[:80]
    return parsed.netloc or url[:80]


def classify_file_links(urls: list[str]) -> list[FileLinkCandidate]:
    candidates: list[FileLinkCandidate] = []
    for url in urls:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if "drive.google.com" in host or "docs.google.com" in host:
            link_type = "google_drive"
            confidence = 0.95
        elif "1drv.ms" in host or "onedrive.live.com" in host:
            link_type = "onedrive"
            confidence = 0.95
        elif "sharepoint.com" in host:
            link_type = "sharepoint"
            confidence = 0.95
        else:
            link_type = "generic_url"
            confidence = 0.6
        candidates.append(
            FileLinkCandidate(
                url=url,
                link_type=link_type,
                label=_label_from_url(url, link_type),
                confidence=confidence,
            ),
        )
    return candidates


def _sentences(text: str) -> list[str]:
    return [
        part.strip(" \t\r\n-")
        for part in SENTENCE_RE.split(text)
        if part.strip(" \t\r\n-")
    ]


def _priority_for_sentence(sentence: str) -> str:
    lowered = sentence.lower()
    if any(term in lowered for term in HIGH_PRIORITY_TERMS):
        return "high"
    if any(term in lowered for term in LOW_PRIORITY_TERMS):
        return "low"
    return "medium"


def _due_hint(sentence: str) -> str | None:
    lowered = sentence.lower()
    for phrase in ("today", "tomorrow", "next week", "this week"):
        if phrase in lowered:
            return phrase
    before = re.search(r"\bbefore\s+([0-9]{1,2}(?::[0-9]{2})?\s*(?:am|pm)?)", lowered)
    if before:
        return f"before {before.group(1)}"
    by_match = re.search(r"\bby\s+([A-Za-z]+(?:\s+[0-9]{1,2})?)", sentence)
    if by_match:
        return f"by {by_match.group(1)}"
    return None


def _action_title(sentence: str) -> str:
    title = re.sub(r"^(please|can you|could you)\s+", "", sentence.strip(), flags=re.IGNORECASE)
    if len(title) > 100:
        title = f"{title[:97].rstrip()}..."
    return title[:1].upper() + title[1:]


def extract_action_items(text: str) -> list[ActionItemSuggestion]:
    items: list[ActionItemSuggestion] = []
    seen: set[str] = set()
    for sentence in _sentences(text):
        lowered = sentence.lower()
        if not any(keyword in lowered for keyword in ACTION_KEYWORDS):
            continue
        title = _action_title(sentence)
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)
        items.append(
            ActionItemSuggestion(
                title=title,
                priority=_priority_for_sentence(sentence),
                due_hint=_due_hint(sentence),
                reason="Keyword-based local suggestion from the selected email text.",
                suggested_owner=None,
            ),
        )
        if len(items) >= 6:
            break
    return items


def _deterministic_summary(text: str) -> EmailSummaryResult:
    sentences = _sentences(text)
    first = sentences[0] if sentences else text[:180]
    questions = [sentence for sentence in sentences if "?" in sentence][:3]
    key_points = [sentence for sentence in sentences[:5] if sentence != first][:4]
    actions = extract_action_items(text)
    next_step = (
        f"Review and decide whether to create a reminder: {actions[0].title}"
        if actions
        else "Review the message and link it to the correct Client, Site, or Job before taking action."
    )
    return EmailSummaryResult(
        summary=first[:500],
        key_points=key_points,
        questions=questions,
        recommended_next_step=next_step,
    )


def _match_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def _append_suggestion(
    suggestions: list[RecordLinkSuggestion],
    seen: set[tuple[str, uuid.UUID]],
    *,
    target_type: str,
    target_id: uuid.UUID,
    target_name: str,
    confidence: float,
    reason: str,
) -> None:
    key = (target_type, target_id)
    if key in seen:
        return
    seen.add(key)
    suggestions.append(
        RecordLinkSuggestion(
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            confidence=confidence,
            reason=reason,
        ),
    )


def suggest_record_links(db: Session, *, organization_id: uuid.UUID, text: str) -> list[RecordLinkSuggestion]:
    haystack = _match_text(text)
    suggestions: list[RecordLinkSuggestion] = []
    seen: set[tuple[str, uuid.UUID]] = set()

    clients = db.scalars(
        select(Client)
        .where(Client.organization_id == organization_id, Client.archived_at.is_(None))
        .order_by(Client.name)
        .limit(200),
    ).all()
    for client in clients:
        for field, value, confidence in (
            ("name", client.name, 0.82),
            ("client code", client.client_code, 0.9),
            ("primary contact", client.primary_contact_name, 0.72),
            ("email", client.email, 0.78),
        ):
            needle = _match_text(value)
            if needle and needle in haystack:
                _append_suggestion(
                    suggestions,
                    seen,
                    target_type="client",
                    target_id=client.id,
                    target_name=client.name,
                    confidence=confidence,
                    reason=f"Matched client {field}: {value}.",
                )
                break

    sites = db.scalars(
        select(Site)
        .where(Site.organization_id == organization_id, Site.archived_at.is_(None))
        .order_by(Site.name)
        .limit(300),
    ).all()
    for site in sites:
        for field, value, confidence in (
            ("name", site.name, 0.84),
            ("site code", site.site_code, 0.9),
            ("address", site.address, 0.76),
        ):
            needle = _match_text(value)
            if needle and needle in haystack:
                _append_suggestion(
                    suggestions,
                    seen,
                    target_type="site",
                    target_id=site.id,
                    target_name=site.name,
                    confidence=confidence,
                    reason=f"Matched site {field}: {value}.",
                )
                break

    jobs = db.scalars(
        select(Job)
        .where(Job.organization_id == organization_id, Job.archived_at.is_(None))
        .order_by(Job.name)
        .limit(300),
    ).all()
    for job in jobs:
        for field, value, confidence in (
            ("name", job.name, 0.86),
            ("job code", job.job_code, 0.94),
            ("service type", job.service_type, 0.68),
        ):
            needle = _match_text(value)
            if needle and needle in haystack:
                _append_suggestion(
                    suggestions,
                    seen,
                    target_type="job",
                    target_id=job.id,
                    target_name=job.name,
                    confidence=confidence,
                    reason=f"Matched job {field}: {value}.",
                )
                break

    return sorted(suggestions, key=lambda item: item.confidence, reverse=True)[:8]


def _extract_output_text(body: dict[str, Any]) -> str:
    output_text = body.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    chunks: list[str] = []
    output = body.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for content_item in content:
                if not isinstance(content_item, dict):
                    continue
                text = content_item.get("text")
                if isinstance(text, str):
                    chunks.append(text)
    return "\n".join(chunks).strip()


def _parse_json_text(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise AiProviderError("AI provider did not return JSON.") from None
        parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise AiProviderError("AI provider returned a non-object JSON value.")
    return parsed


def _call_openai_json(*, system_prompt: str, user_prompt: str) -> dict[str, Any]:
    settings = get_settings()
    status = _settings_status(settings)
    if not status.enabled:
        raise AiProviderError("AI provider is not configured.")

    payload = {
        "model": settings.openai_model,
        "input": f"{system_prompt}\n\n{user_prompt}",
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            body = response.json()
    except httpx.HTTPStatusError as error:
        raise AiProviderError(
            f"OpenAI request failed: {error.response.status_code} {error.response.reason_phrase}.",
        ) from error
    except httpx.HTTPError as error:
        raise AiProviderError("OpenAI request failed before a response was received.") from error

    if not isinstance(body, dict):
        raise AiProviderError("OpenAI response body was not an object.")
    return _parse_json_text(_extract_output_text(body))


def _save_output(
    db: Session,
    *,
    context: AssistantContext,
    draft_type: str,
    title: str,
    prompt_context: str,
    draft_text: str,
) -> SavedDraftRef:
    draft = ai_drafts_service.create_ai_draft(
        db,
        data={
            "organization_id": context.organization_id,
            "client_id": context.client_id,
            "site_id": context.site_id,
            "job_id": context.job_id,
            "email_message_id": context.email_message.id if context.email_message else None,
            "draft_type": draft_type,
            "title": title[:255],
            "prompt_context": prompt_context,
            "draft_text": draft_text,
            "status": "draft",
        },
    )
    return SavedDraftRef(id=draft.id, draft_type=draft.draft_type, title=draft.title, status=draft.status)


def _json_draft_text(value: Any) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(
        value,
        indent=2,
        sort_keys=True,
        default=lambda item: item.model_dump(mode="json") if hasattr(item, "model_dump") else str(item),
    )


def _disabled_response(message: str) -> dict[str, Any]:
    return {
        "available": False,
        "source": "disabled",
        "model": None,
        "error_code": "configuration_required",
        "message": message,
    }


def _model_name() -> str | None:
    status = get_ai_status()
    return status.model if status.enabled else None


def summarize_email(db: Session, payload: EmailSummaryRequest) -> EmailSummaryResponse:
    context = _load_context_from_payload(db, payload)
    status = get_ai_status()
    if status.enabled:
        data = _call_openai_json(
            system_prompt=(
                "You summarize only the provided local email content for human review. "
                "Do not claim compliance status or infer facts not present. "
                "Return JSON with summary, key_points, questions, recommended_next_step."
            ),
            user_prompt=f"Email/content:\n{context.text}",
        )
        result = EmailSummaryResult.model_validate(data)
        source = "openai"
        message = "AI summary generated for review."
    else:
        result = _deterministic_summary(context.text)
        source = "deterministic"
        message = "Local deterministic summary generated. Configure AI for provider-backed summaries."

    saved = (
        _save_output(
            db,
            context=context,
            draft_type="email_summary",
            title=f"Summary: {context.title}",
            prompt_context=context.text[:4000],
            draft_text=_json_draft_text(result),
        )
        if payload.save_draft
        else None
    )
    return EmailSummaryResponse(
        available=True,
        source=source,
        model=_model_name(),
        message=message,
        result=result,
        saved_draft=saved,
    )


def extract_email_action_items(db: Session, payload: EmailActionItemsRequest) -> EmailActionItemsResponse:
    context = _load_context_from_payload(db, payload)
    status = get_ai_status()
    if status.enabled:
        data = _call_openai_json(
            system_prompt=(
                "Extract possible action items from only the provided email/content. "
                "Return JSON with an items array. Each item has title, priority, due_hint, reason, suggested_owner. "
                "Use low, medium, or high priority. These are suggestions only."
            ),
            user_prompt=f"Email/content:\n{context.text}",
        )
        raw_items = data.get("items", [])
        if not isinstance(raw_items, list):
            raise AiProviderError("AI provider action item response did not include an items list.")
        items = [ActionItemSuggestion.model_validate(item) for item in raw_items]
        source = "openai"
        message = "AI action item suggestions generated for review."
    else:
        items = extract_action_items(context.text)
        source = "deterministic"
        message = "Local keyword action suggestions generated. Configure AI for deeper extraction."

    saved = (
        _save_output(
            db,
            context=context,
            draft_type="email_action_items",
            title=f"Action items: {context.title}",
            prompt_context=context.text[:4000],
            draft_text=_json_draft_text({"items": items}),
        )
        if payload.save_draft
        else None
    )
    return EmailActionItemsResponse(
        available=True,
        source=source,
        model=_model_name(),
        message=message,
        items=items,
        saved_draft=saved,
    )


def extract_file_links(db: Session, payload: ExtractFileLinksRequest) -> ExtractFileLinksResponse:
    context = _load_context_from_payload(db, payload, direct_text=payload.text)
    links = classify_file_links(extract_urls_from_text(context.text))
    saved = (
        _save_output(
            db,
            context=context,
            draft_type="file_link_candidates",
            title=f"Detected links: {context.title}",
            prompt_context=context.text[:4000],
            draft_text=_json_draft_text({"links": links}),
        )
        if payload.save_draft
        else None
    )
    return ExtractFileLinksResponse(
        available=True,
        source="deterministic",
        model=None,
        message="Local URL extraction completed. No file download or Drive scan was performed.",
        links=links,
        saved_draft=saved,
    )


def suggest_email_record_links(db: Session, payload: SuggestRecordLinksRequest) -> SuggestRecordLinksResponse:
    context = _load_context_from_payload(db, payload, direct_text=payload.text)
    suggestions = suggest_record_links(db, organization_id=payload.organization_id, text=context.text)
    saved = (
        _save_output(
            db,
            context=context,
            draft_type="record_link_suggestions",
            title=f"Record suggestions: {context.title}",
            prompt_context=context.text[:4000],
            draft_text=_json_draft_text({"suggestions": suggestions}),
        )
        if payload.save_draft
        else None
    )
    return SuggestRecordLinksResponse(
        available=True,
        source="deterministic",
        model=None,
        message="Local record suggestions generated from exact name/code matches only.",
        suggestions=suggestions,
        saved_draft=saved,
    )


def draft_reply(db: Session, payload: DraftReplyRequest) -> DraftReplyResponse:
    context = _load_context_from_payload(db, payload)
    status = get_ai_status()
    if not status.enabled:
        return DraftReplyResponse(
            **_disabled_response("Configure OPENAI_API_KEY before generating reply drafts."),
            result=None,
        )

    data = _call_openai_json(
        system_prompt=(
            "Draft a human-reviewed email reply using only the provided local email/content. "
            "Do not send email, create provider drafts, promise final compliance results, or invent facts. "
            "Return JSON with subject, body, tone, review_note."
        ),
        user_prompt=f"Requested tone: {payload.tone}\nEmail/content:\n{context.text}",
    )
    result = DraftReplyResult.model_validate(data)
    saved = (
        _save_output(
            db,
            context=context,
            draft_type="email_reply",
            title=f"Reply: {context.title}",
            prompt_context=context.text[:4000],
            draft_text=result.body,
        )
        if payload.save_draft
        else None
    )
    return DraftReplyResponse(
        available=True,
        source="openai",
        model=status.model,
        message="Reply draft generated and kept local for human review.",
        result=result,
        saved_draft=saved,
    )


def report_section_draft(db: Session, payload: ReportSectionDraftRequest) -> ReportSectionDraftResponse:
    context = _load_context_from_payload(db, payload)
    status = get_ai_status()
    if not status.enabled:
        return ReportSectionDraftResponse(
            **_disabled_response("Configure OPENAI_API_KEY before generating report section drafts."),
            result=None,
        )

    data = _call_openai_json(
        system_prompt=(
            "Draft a stormwater report section from provided notes only. "
            "This is not a final report and must be reviewed by a human. "
            "Avoid compliance conclusions unless directly stated. "
            "Return JSON with heading, draft_text, cautions."
        ),
        user_prompt=f"Requested heading: {payload.section_heading}\nContext:\n{context.text}",
    )
    result = ReportSectionDraftResult.model_validate(data)
    saved = (
        _save_output(
            db,
            context=context,
            draft_type="report_section",
            title=result.heading,
            prompt_context=context.text[:4000],
            draft_text=result.draft_text,
        )
        if payload.save_draft
        else None
    )
    return ReportSectionDraftResponse(
        available=True,
        source="openai",
        model=status.model,
        message="Report section draft generated locally for review; no report file was created.",
        result=result,
        saved_draft=saved,
    )


def maintenance_recommendation_draft(
    db: Session,
    payload: MaintenanceRecommendationDraftRequest,
) -> ReportSectionDraftResponse:
    context = _load_context_from_payload(db, payload)
    status = get_ai_status()
    if not status.enabled:
        return ReportSectionDraftResponse(
            **_disabled_response("Configure OPENAI_API_KEY before generating maintenance recommendations."),
            result=None,
        )

    data = _call_openai_json(
        system_prompt=(
            "Draft stormwater maintenance recommendations from provided notes only. "
            "Use client-facing language, avoid unsupported compliance claims, and require human review. "
            "Return JSON with heading, draft_text, cautions."
        ),
        user_prompt=f"System/BMP type: {payload.system_type or 'Not specified'}\nContext:\n{context.text}",
    )
    result = ReportSectionDraftResult.model_validate(data)
    saved = (
        _save_output(
            db,
            context=context,
            draft_type="maintenance_recommendation",
            title=result.heading,
            prompt_context=context.text[:4000],
            draft_text=result.draft_text,
        )
        if payload.save_draft
        else None
    )
    return ReportSectionDraftResponse(
        available=True,
        source="openai",
        model=status.model,
        message="Maintenance recommendation draft generated locally for review.",
        result=result,
        saved_draft=saved,
    )


def client_summary_draft(db: Session, payload: ClientSummaryDraftRequest) -> ReportSectionDraftResponse:
    context = _load_context_from_payload(db, payload)
    status = get_ai_status()
    if not status.enabled:
        return ReportSectionDraftResponse(
            **_disabled_response("Configure OPENAI_API_KEY before generating client-facing summary drafts."),
            result=None,
        )

    data = _call_openai_json(
        system_prompt=(
            "Draft a concise client-facing stormwater summary or email body from provided notes only. "
            "No sending, no final report generation, and no unsupported compliance claims. "
            "Return JSON with heading, draft_text, cautions."
        ),
        user_prompt=f"Audience: {payload.audience}\nContext:\n{context.text}",
    )
    result = ReportSectionDraftResult.model_validate(data)
    saved = (
        _save_output(
            db,
            context=context,
            draft_type="client_summary",
            title=result.heading,
            prompt_context=context.text[:4000],
            draft_text=result.draft_text,
        )
        if payload.save_draft
        else None
    )
    return ReportSectionDraftResponse(
        available=True,
        source="openai",
        model=status.model,
        message="Client-facing draft generated locally for review.",
        result=result,
        saved_draft=saved,
    )
