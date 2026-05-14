from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AiDraft,
    BmpSystem,
    Client,
    DocumentExtractedField,
    DocumentLinkSuggestion,
    DocumentRecord,
    DocumentTextChunk,
    EmailMessage,
    EvidenceFile,
    Job,
    KnowledgeItem,
    Observation,
    Organization,
    RecordLink,
    RecordNote,
    Site,
)
from app.services.common import CRMNotFoundError, CRMValidationError, Page, paginate


ALLOWED_RECORD_TYPES = {
    "client",
    "site",
    "job",
    "bmp_system",
    "observation",
    "evidence_file",
    "document",
    "email_message",
    "ai_draft",
}
ALLOWED_KNOWLEDGE_TYPES = {
    "site_access",
    "client_preference",
    "permit_note",
    "report_language",
    "historical_context",
}
ALLOWED_DOCUMENT_TYPES = {
    "report",
    "proposal",
    "quote",
    "invoice",
    "plan",
    "photosheet",
    "email_attachment",
    "permit",
    "unknown",
}
ALLOWED_REVIEW_STATUSES = {"pending", "approved", "rejected", "needs_review"}
ALLOWED_DOCUMENT_STATUSES = {"queued", "reviewing", "reviewed", "archived"}
ALLOWED_EXTRACTION_STATUSES = {"not_started", "pending", "complete", "failed", "skipped"}


def _now() -> datetime:
    return datetime.now(UTC)


def _require_organization(db: Session, organization_id: uuid.UUID) -> Organization:
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise CRMNotFoundError("Organization not found.")
    return organization


def _normalize_text(value: str | None, field_name: str) -> str:
    if value is None:
        raise CRMValidationError(f"{field_name} is required.")
    trimmed = value.strip()
    if not trimmed:
        raise CRMValidationError(f"{field_name} is required.")
    return trimmed


def _validate_allowed(value: str | None, allowed: set[str], field_name: str, default: str | None = None) -> str:
    normalized = (value or default or "").strip().lower()
    if normalized not in allowed:
        raise CRMValidationError(f"{field_name} must be one of: {', '.join(sorted(allowed))}.")
    return normalized


def _validate_confidence(confidence: float | None) -> float | None:
    if confidence is None:
        return None
    if confidence < 0 or confidence > 1:
        raise CRMValidationError("confidence must be between 0 and 1.")
    return confidence


def _record_model(record_type: str) -> Any:
    return {
        "client": Client,
        "site": Site,
        "job": Job,
        "bmp_system": BmpSystem,
        "observation": Observation,
        "evidence_file": EvidenceFile,
        "document": DocumentRecord,
        "email_message": EmailMessage,
        "ai_draft": AiDraft,
    }[record_type]


def _require_record(
    db: Session,
    *,
    organization_id: uuid.UUID,
    record_type: str,
    record_id: uuid.UUID,
) -> Any:
    normalized_type = _validate_allowed(record_type, ALLOWED_RECORD_TYPES, "record_type")
    model = _record_model(normalized_type)
    statement = select(model).where(
        model.organization_id == organization_id,
        model.id == record_id,
    )
    if hasattr(model, "archived_at"):
        statement = statement.where(model.archived_at.is_(None))
    record = db.scalar(statement)
    if record is None:
        raise CRMNotFoundError(f"{normalized_type} not found.")
    return record


def _validate_optional_scope(
    db: Session,
    *,
    organization_id: uuid.UUID,
    client_id: uuid.UUID | None = None,
    site_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
) -> None:
    site = None
    job = None
    if client_id is not None:
        _require_record(db, organization_id=organization_id, record_type="client", record_id=client_id)
    if site_id is not None:
        site = _require_record(db, organization_id=organization_id, record_type="site", record_id=site_id)
    if job_id is not None:
        job = _require_record(db, organization_id=organization_id, record_type="job", record_id=job_id)

    if site is not None and client_id is not None and site.client_id != client_id:
        raise CRMValidationError("site_id must belong to client_id.")
    if job is not None and site_id is not None and job.site_id != site_id:
        raise CRMValidationError("job_id must belong to site_id.")
    if job is not None and client_id is not None and job.client_id != client_id:
        raise CRMValidationError("job_id must belong to client_id.")


def list_bmp_systems(
    db: Session,
    *,
    organization_id: uuid.UUID,
    site_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[BmpSystem]:
    statement = select(BmpSystem).where(
        BmpSystem.organization_id == organization_id,
        BmpSystem.archived_at.is_(None),
    )
    if site_id is not None:
        statement = statement.where(BmpSystem.site_id == site_id)
    statement = statement.order_by(BmpSystem.system_type, BmpSystem.name, BmpSystem.system_code, BmpSystem.id)
    return paginate(db, statement, limit=limit, offset=offset)


def get_bmp_system(db: Session, *, organization_id: uuid.UUID, system_id: uuid.UUID) -> BmpSystem | None:
    statement = select(BmpSystem).where(
        BmpSystem.organization_id == organization_id,
        BmpSystem.id == system_id,
        BmpSystem.archived_at.is_(None),
    )
    return db.scalar(statement)


def list_observations(
    db: Session,
    *,
    organization_id: uuid.UUID,
    job_id: uuid.UUID | None = None,
    site_id: uuid.UUID | None = None,
    system_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[Observation]:
    statement = select(Observation).where(
        Observation.organization_id == organization_id,
        Observation.archived_at.is_(None),
    )
    if job_id is not None:
        statement = statement.where(Observation.job_id == job_id)
    if system_id is not None:
        statement = statement.where(Observation.system_id == system_id)
    if site_id is not None:
        statement = statement.join(Job, Observation.job_id == Job.id).where(
            Job.organization_id == organization_id,
            Job.site_id == site_id,
            Job.archived_at.is_(None),
        )
    statement = statement.order_by(Observation.created_at.desc(), Observation.id)
    return paginate(db, statement, limit=limit, offset=offset)


def get_observation(db: Session, *, organization_id: uuid.UUID, observation_id: uuid.UUID) -> Observation | None:
    statement = select(Observation).where(
        Observation.organization_id == organization_id,
        Observation.id == observation_id,
        Observation.archived_at.is_(None),
    )
    return db.scalar(statement)


def list_record_links(
    db: Session,
    *,
    organization_id: uuid.UUID,
    source_type: str | None = None,
    source_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
    relationship_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[RecordLink]:
    statement = select(RecordLink).where(
        RecordLink.organization_id == organization_id,
        RecordLink.archived_at.is_(None),
    )
    if source_type:
        statement = statement.where(RecordLink.source_type == _validate_allowed(source_type, ALLOWED_RECORD_TYPES, "source_type"))
    if source_id is not None:
        statement = statement.where(RecordLink.source_id == source_id)
    if target_type:
        statement = statement.where(RecordLink.target_type == _validate_allowed(target_type, ALLOWED_RECORD_TYPES, "target_type"))
    if target_id is not None:
        statement = statement.where(RecordLink.target_id == target_id)
    if relationship_type:
        statement = statement.where(RecordLink.relationship_type == relationship_type.strip().lower())
    statement = statement.order_by(RecordLink.created_at.desc(), RecordLink.id)
    return paginate(db, statement, limit=limit, offset=offset)


def create_record_link(db: Session, *, data: dict[str, Any], created_by: uuid.UUID | None = None) -> RecordLink:
    organization_id = data.get("organization_id")
    if organization_id is None:
        raise CRMValidationError("organization_id is required.")
    _require_organization(db, organization_id)
    source_type = _validate_allowed(data.get("source_type"), ALLOWED_RECORD_TYPES, "source_type")
    target_type = _validate_allowed(data.get("target_type"), ALLOWED_RECORD_TYPES, "target_type")
    source_id = data.get("source_id")
    target_id = data.get("target_id")
    if source_id is None or target_id is None:
        raise CRMValidationError("source_id and target_id are required.")
    _require_record(db, organization_id=organization_id, record_type=source_type, record_id=source_id)
    _require_record(db, organization_id=organization_id, record_type=target_type, record_id=target_id)

    record = RecordLink(
        organization_id=organization_id,
        source_type=source_type,
        source_id=source_id,
        target_type=target_type,
        target_id=target_id,
        relationship_type=_normalize_text(data.get("relationship_type") or "related", "relationship_type").lower(),
        confidence=_validate_confidence(data.get("confidence")),
        link_reason=data.get("link_reason"),
        created_by=created_by,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_record_link(db: Session, *, organization_id: uuid.UUID, link_id: uuid.UUID) -> RecordLink | None:
    statement = select(RecordLink).where(
        RecordLink.organization_id == organization_id,
        RecordLink.id == link_id,
        RecordLink.archived_at.is_(None),
    )
    return db.scalar(statement)


def update_record_link(db: Session, *, organization_id: uuid.UUID, link_id: uuid.UUID, data: dict[str, Any]) -> RecordLink:
    record = get_record_link(db, organization_id=organization_id, link_id=link_id)
    if record is None:
        raise CRMNotFoundError("Record link not found.")
    if "relationship_type" in data and data["relationship_type"] is not None:
        record.relationship_type = _normalize_text(data["relationship_type"], "relationship_type").lower()
    if "confidence" in data:
        record.confidence = _validate_confidence(data["confidence"])
    if "link_reason" in data:
        record.link_reason = data["link_reason"]
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def archive_record_link(db: Session, *, organization_id: uuid.UUID, link_id: uuid.UUID) -> RecordLink:
    record = get_record_link(db, organization_id=organization_id, link_id=link_id)
    if record is None:
        raise CRMNotFoundError("Record link not found.")
    record.archived_at = _now()
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_record_notes(
    db: Session,
    *,
    organization_id: uuid.UUID,
    parent_type: str | None = None,
    parent_id: uuid.UUID | None = None,
    note_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[RecordNote]:
    statement = select(RecordNote).where(
        RecordNote.organization_id == organization_id,
        RecordNote.archived_at.is_(None),
    )
    if parent_type:
        statement = statement.where(RecordNote.parent_type == _validate_allowed(parent_type, ALLOWED_RECORD_TYPES, "parent_type"))
    if parent_id is not None:
        statement = statement.where(RecordNote.parent_id == parent_id)
    if note_type:
        statement = statement.where(RecordNote.note_type == note_type.strip().lower())
    statement = statement.order_by(RecordNote.created_at.desc(), RecordNote.id)
    return paginate(db, statement, limit=limit, offset=offset)


def create_record_note(db: Session, *, data: dict[str, Any], created_by: uuid.UUID | None = None) -> RecordNote:
    organization_id = data.get("organization_id")
    if organization_id is None:
        raise CRMValidationError("organization_id is required.")
    _require_organization(db, organization_id)
    parent_type = _validate_allowed(data.get("parent_type"), ALLOWED_RECORD_TYPES, "parent_type")
    parent_id = data.get("parent_id")
    if parent_id is None:
        raise CRMValidationError("parent_id is required.")
    _require_record(db, organization_id=organization_id, record_type=parent_type, record_id=parent_id)
    note = RecordNote(
        organization_id=organization_id,
        parent_type=parent_type,
        parent_id=parent_id,
        title=_normalize_text(data.get("title"), "title"),
        body=_normalize_text(data.get("body"), "body"),
        note_type=_normalize_text(data.get("note_type") or "general", "note_type").lower(),
        visibility=_normalize_text(data.get("visibility") or "internal", "visibility").lower(),
        created_by=created_by,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def get_record_note(db: Session, *, organization_id: uuid.UUID, note_id: uuid.UUID) -> RecordNote | None:
    statement = select(RecordNote).where(
        RecordNote.organization_id == organization_id,
        RecordNote.id == note_id,
        RecordNote.archived_at.is_(None),
    )
    return db.scalar(statement)


def update_record_note(db: Session, *, organization_id: uuid.UUID, note_id: uuid.UUID, data: dict[str, Any]) -> RecordNote:
    note = get_record_note(db, organization_id=organization_id, note_id=note_id)
    if note is None:
        raise CRMNotFoundError("Record note not found.")
    for field in ("title", "body", "note_type", "visibility"):
        if field in data and data[field] is not None:
            value = _normalize_text(data[field], field)
            setattr(note, field, value.lower() if field in {"note_type", "visibility"} else value)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def archive_record_note(db: Session, *, organization_id: uuid.UUID, note_id: uuid.UUID) -> RecordNote:
    note = get_record_note(db, organization_id=organization_id, note_id=note_id)
    if note is None:
        raise CRMNotFoundError("Record note not found.")
    note.archived_at = _now()
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def list_knowledge_items(
    db: Session,
    *,
    organization_id: uuid.UUID,
    client_id: uuid.UUID | None = None,
    site_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    knowledge_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[KnowledgeItem]:
    statement = select(KnowledgeItem).where(
        KnowledgeItem.organization_id == organization_id,
        KnowledgeItem.archived_at.is_(None),
    )
    if client_id is not None:
        statement = statement.where(KnowledgeItem.client_id == client_id)
    if site_id is not None:
        statement = statement.where(KnowledgeItem.site_id == site_id)
    if job_id is not None:
        statement = statement.where(KnowledgeItem.job_id == job_id)
    if knowledge_type:
        statement = statement.where(
            KnowledgeItem.knowledge_type == _validate_allowed(knowledge_type, ALLOWED_KNOWLEDGE_TYPES, "knowledge_type"),
        )
    statement = statement.order_by(KnowledgeItem.knowledge_type, KnowledgeItem.title, KnowledgeItem.id)
    return paginate(db, statement, limit=limit, offset=offset)


def _knowledge_values(db: Session, data: dict[str, Any], organization_id: uuid.UUID) -> dict[str, Any]:
    _validate_optional_scope(
        db,
        organization_id=organization_id,
        client_id=data.get("client_id"),
        site_id=data.get("site_id"),
        job_id=data.get("job_id"),
    )
    source_type = data.get("source_type")
    source_id = data.get("source_id")
    if (source_type is None) != (source_id is None):
        raise CRMValidationError("source_type and source_id must be provided together.")
    if source_type is not None:
        source_type = _validate_allowed(source_type, ALLOWED_RECORD_TYPES, "source_type")
        _require_record(db, organization_id=organization_id, record_type=source_type, record_id=source_id)
    return {
        "client_id": data.get("client_id"),
        "site_id": data.get("site_id"),
        "job_id": data.get("job_id"),
        "title": _normalize_text(data.get("title"), "title"),
        "content": _normalize_text(data.get("content"), "content"),
        "knowledge_type": _validate_allowed(data.get("knowledge_type"), ALLOWED_KNOWLEDGE_TYPES, "knowledge_type"),
        "tags_json": data.get("tags_json"),
        "source_type": source_type,
        "source_id": source_id,
    }


def create_knowledge_item(db: Session, *, data: dict[str, Any]) -> KnowledgeItem:
    organization_id = data.get("organization_id")
    if organization_id is None:
        raise CRMValidationError("organization_id is required.")
    _require_organization(db, organization_id)
    item = KnowledgeItem(organization_id=organization_id, **_knowledge_values(db, data, organization_id))
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_knowledge_item(db: Session, *, organization_id: uuid.UUID, item_id: uuid.UUID) -> KnowledgeItem | None:
    statement = select(KnowledgeItem).where(
        KnowledgeItem.organization_id == organization_id,
        KnowledgeItem.id == item_id,
        KnowledgeItem.archived_at.is_(None),
    )
    return db.scalar(statement)


def update_knowledge_item(db: Session, *, organization_id: uuid.UUID, item_id: uuid.UUID, data: dict[str, Any]) -> KnowledgeItem:
    item = get_knowledge_item(db, organization_id=organization_id, item_id=item_id)
    if item is None:
        raise CRMNotFoundError("Knowledge item not found.")
    merged = {
        "client_id": item.client_id,
        "site_id": item.site_id,
        "job_id": item.job_id,
        "title": item.title,
        "content": item.content,
        "knowledge_type": item.knowledge_type,
        "tags_json": item.tags_json,
        "source_type": item.source_type,
        "source_id": item.source_id,
    }
    merged.update(data)
    for field, value in _knowledge_values(db, merged, organization_id).items():
        setattr(item, field, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def archive_knowledge_item(db: Session, *, organization_id: uuid.UUID, item_id: uuid.UUID) -> KnowledgeItem:
    item = get_knowledge_item(db, organization_id=organization_id, item_id=item_id)
    if item is None:
        raise CRMNotFoundError("Knowledge item not found.")
    item.archived_at = _now()
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_documents(
    db: Session,
    *,
    organization_id: uuid.UUID,
    client_id: uuid.UUID | None = None,
    site_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    status: str | None = None,
    document_type: str | None = None,
    extraction_status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[DocumentRecord]:
    statement = select(DocumentRecord).where(
        DocumentRecord.organization_id == organization_id,
        DocumentRecord.archived_at.is_(None),
    )
    if client_id is not None:
        statement = statement.where(DocumentRecord.client_id == client_id)
    if site_id is not None:
        statement = statement.where(DocumentRecord.site_id == site_id)
    if job_id is not None:
        statement = statement.where(DocumentRecord.job_id == job_id)
    if status:
        statement = statement.where(DocumentRecord.status == _validate_allowed(status, ALLOWED_DOCUMENT_STATUSES, "status"))
    if document_type:
        statement = statement.where(DocumentRecord.document_type == _validate_allowed(document_type, ALLOWED_DOCUMENT_TYPES, "document_type"))
    if extraction_status:
        statement = statement.where(
            DocumentRecord.extraction_status == _validate_allowed(extraction_status, ALLOWED_EXTRACTION_STATUSES, "extraction_status"),
        )
    statement = statement.order_by(DocumentRecord.created_at.desc(), DocumentRecord.file_name, DocumentRecord.id)
    return paginate(db, statement, limit=limit, offset=offset)


def _document_values(db: Session, data: dict[str, Any], organization_id: uuid.UUID) -> dict[str, Any]:
    _validate_optional_scope(
        db,
        organization_id=organization_id,
        client_id=data.get("client_id"),
        site_id=data.get("site_id"),
        job_id=data.get("job_id"),
    )
    evidence_file_id = data.get("evidence_file_id")
    if evidence_file_id is not None:
        _require_record(db, organization_id=organization_id, record_type="evidence_file", record_id=evidence_file_id)
    return {
        "evidence_file_id": evidence_file_id,
        "source": _normalize_text(data.get("source") or "manual", "source").lower(),
        "file_name": _normalize_text(data.get("file_name"), "file_name"),
        "file_url": data.get("file_url"),
        "storage_path": data.get("storage_path"),
        "mime_type": data.get("mime_type"),
        "document_type": _validate_allowed(data.get("document_type") or "unknown", ALLOWED_DOCUMENT_TYPES, "document_type"),
        "client_id": data.get("client_id"),
        "site_id": data.get("site_id"),
        "job_id": data.get("job_id"),
        "status": _validate_allowed(data.get("status") or "queued", ALLOWED_DOCUMENT_STATUSES, "status"),
        "extraction_status": _validate_allowed(
            data.get("extraction_status") or "not_started",
            ALLOWED_EXTRACTION_STATUSES,
            "extraction_status",
        ),
    }


def create_document(db: Session, *, data: dict[str, Any]) -> DocumentRecord:
    organization_id = data.get("organization_id")
    if organization_id is None:
        raise CRMValidationError("organization_id is required.")
    _require_organization(db, organization_id)
    document = DocumentRecord(organization_id=organization_id, **_document_values(db, data, organization_id))
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def get_document(db: Session, *, organization_id: uuid.UUID, document_id: uuid.UUID) -> DocumentRecord | None:
    statement = select(DocumentRecord).where(
        DocumentRecord.organization_id == organization_id,
        DocumentRecord.id == document_id,
        DocumentRecord.archived_at.is_(None),
    )
    return db.scalar(statement)


def _require_document(db: Session, *, organization_id: uuid.UUID, document_id: uuid.UUID) -> DocumentRecord:
    document = get_document(db, organization_id=organization_id, document_id=document_id)
    if document is None:
        raise CRMNotFoundError("Document not found.")
    return document


def update_document(db: Session, *, organization_id: uuid.UUID, document_id: uuid.UUID, data: dict[str, Any]) -> DocumentRecord:
    document = _require_document(db, organization_id=organization_id, document_id=document_id)
    merged = {
        "evidence_file_id": document.evidence_file_id,
        "source": document.source,
        "file_name": document.file_name,
        "file_url": document.file_url,
        "storage_path": document.storage_path,
        "mime_type": document.mime_type,
        "document_type": document.document_type,
        "client_id": document.client_id,
        "site_id": document.site_id,
        "job_id": document.job_id,
        "status": document.status,
        "extraction_status": document.extraction_status,
    }
    merged.update(data)
    for field, value in _document_values(db, merged, organization_id).items():
        setattr(document, field, value)
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def archive_document(db: Session, *, organization_id: uuid.UUID, document_id: uuid.UUID) -> DocumentRecord:
    document = _require_document(db, organization_id=organization_id, document_id=document_id)
    document.archived_at = _now()
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def list_document_chunks(
    db: Session,
    *,
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    limit: int = 50,
    offset: int = 0,
) -> Page[DocumentTextChunk]:
    _require_document(db, organization_id=organization_id, document_id=document_id)
    statement = select(DocumentTextChunk).where(
        DocumentTextChunk.organization_id == organization_id,
        DocumentTextChunk.document_id == document_id,
    ).order_by(DocumentTextChunk.chunk_index, DocumentTextChunk.id)
    return paginate(db, statement, limit=limit, offset=offset)


def create_document_chunk(db: Session, *, organization_id: uuid.UUID, document_id: uuid.UUID, data: dict[str, Any]) -> DocumentTextChunk:
    _require_document(db, organization_id=organization_id, document_id=document_id)
    chunk = DocumentTextChunk(
        organization_id=organization_id,
        document_id=document_id,
        chunk_index=data.get("chunk_index") or 0,
        page_number=data.get("page_number"),
        heading=data.get("heading"),
        text=_normalize_text(data.get("text"), "text"),
        token_count=data.get("token_count"),
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)
    return chunk


def list_document_extracted_fields(
    db: Session,
    *,
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    review_status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[DocumentExtractedField]:
    _require_document(db, organization_id=organization_id, document_id=document_id)
    statement = select(DocumentExtractedField).where(
        DocumentExtractedField.organization_id == organization_id,
        DocumentExtractedField.document_id == document_id,
        DocumentExtractedField.archived_at.is_(None),
    )
    if review_status:
        statement = statement.where(
            DocumentExtractedField.review_status == _validate_allowed(review_status, ALLOWED_REVIEW_STATUSES, "review_status"),
        )
    statement = statement.order_by(DocumentExtractedField.field_name, DocumentExtractedField.id)
    return paginate(db, statement, limit=limit, offset=offset)


def create_document_extracted_field(
    db: Session,
    *,
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    data: dict[str, Any],
) -> DocumentExtractedField:
    _require_document(db, organization_id=organization_id, document_id=document_id)
    field = DocumentExtractedField(
        organization_id=organization_id,
        document_id=document_id,
        field_name=_normalize_text(data.get("field_name"), "field_name").lower(),
        field_value=_normalize_text(data.get("field_value"), "field_value"),
        confidence=_validate_confidence(data.get("confidence")),
        source_page=data.get("source_page"),
        review_status=_validate_allowed(data.get("review_status") or "pending", ALLOWED_REVIEW_STATUSES, "review_status"),
    )
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


def _require_extracted_field(
    db: Session,
    *,
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    field_id: uuid.UUID,
) -> DocumentExtractedField:
    statement = select(DocumentExtractedField).where(
        DocumentExtractedField.organization_id == organization_id,
        DocumentExtractedField.document_id == document_id,
        DocumentExtractedField.id == field_id,
        DocumentExtractedField.archived_at.is_(None),
    )
    field = db.scalar(statement)
    if field is None:
        raise CRMNotFoundError("Extracted field not found.")
    return field


def update_document_extracted_field(
    db: Session,
    *,
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    field_id: uuid.UUID,
    data: dict[str, Any],
) -> DocumentExtractedField:
    field = _require_extracted_field(db, organization_id=organization_id, document_id=document_id, field_id=field_id)
    if "field_name" in data and data["field_name"] is not None:
        field.field_name = _normalize_text(data["field_name"], "field_name").lower()
    if "field_value" in data and data["field_value"] is not None:
        field.field_value = _normalize_text(data["field_value"], "field_value")
    if "confidence" in data:
        field.confidence = _validate_confidence(data["confidence"])
    if "source_page" in data:
        field.source_page = data["source_page"]
    if "review_status" in data and data["review_status"] is not None:
        field.review_status = _validate_allowed(data["review_status"], ALLOWED_REVIEW_STATUSES, "review_status")
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


def archive_document_extracted_field(
    db: Session,
    *,
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    field_id: uuid.UUID,
) -> DocumentExtractedField:
    field = _require_extracted_field(db, organization_id=organization_id, document_id=document_id, field_id=field_id)
    field.archived_at = _now()
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


def list_document_link_suggestions(
    db: Session,
    *,
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    review_status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Page[DocumentLinkSuggestion]:
    _require_document(db, organization_id=organization_id, document_id=document_id)
    statement = select(DocumentLinkSuggestion).where(
        DocumentLinkSuggestion.organization_id == organization_id,
        DocumentLinkSuggestion.document_id == document_id,
        DocumentLinkSuggestion.archived_at.is_(None),
    )
    if review_status:
        statement = statement.where(
            DocumentLinkSuggestion.review_status == _validate_allowed(review_status, ALLOWED_REVIEW_STATUSES, "review_status"),
        )
    statement = statement.order_by(DocumentLinkSuggestion.review_status, DocumentLinkSuggestion.target_label, DocumentLinkSuggestion.id)
    return paginate(db, statement, limit=limit, offset=offset)


def create_document_link_suggestion(
    db: Session,
    *,
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    data: dict[str, Any],
) -> DocumentLinkSuggestion:
    _require_document(db, organization_id=organization_id, document_id=document_id)
    target_type = _validate_allowed(data.get("target_type"), ALLOWED_RECORD_TYPES, "target_type")
    target_id = data.get("target_id")
    if target_id is not None:
        _require_record(db, organization_id=organization_id, record_type=target_type, record_id=target_id)
    suggestion = DocumentLinkSuggestion(
        organization_id=organization_id,
        document_id=document_id,
        target_type=target_type,
        target_id=target_id,
        target_label=data.get("target_label"),
        confidence=_validate_confidence(data.get("confidence")),
        reason=data.get("reason"),
        review_status=_validate_allowed(data.get("review_status") or "pending", ALLOWED_REVIEW_STATUSES, "review_status"),
    )
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)
    return suggestion


def _require_link_suggestion(
    db: Session,
    *,
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    suggestion_id: uuid.UUID,
) -> DocumentLinkSuggestion:
    statement = select(DocumentLinkSuggestion).where(
        DocumentLinkSuggestion.organization_id == organization_id,
        DocumentLinkSuggestion.document_id == document_id,
        DocumentLinkSuggestion.id == suggestion_id,
        DocumentLinkSuggestion.archived_at.is_(None),
    )
    suggestion = db.scalar(statement)
    if suggestion is None:
        raise CRMNotFoundError("Document link suggestion not found.")
    return suggestion


def update_document_link_suggestion(
    db: Session,
    *,
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    suggestion_id: uuid.UUID,
    data: dict[str, Any],
) -> DocumentLinkSuggestion:
    suggestion = _require_link_suggestion(
        db,
        organization_id=organization_id,
        document_id=document_id,
        suggestion_id=suggestion_id,
    )
    target_type = data.get("target_type", suggestion.target_type)
    if target_type is not None:
        target_type = _validate_allowed(target_type, ALLOWED_RECORD_TYPES, "target_type")
    target_id = data.get("target_id", suggestion.target_id)
    if target_id is not None:
        _require_record(db, organization_id=organization_id, record_type=target_type, record_id=target_id)
    if "target_type" in data and data["target_type"] is not None:
        suggestion.target_type = target_type
    if "target_id" in data:
        suggestion.target_id = data["target_id"]
    if "target_label" in data:
        suggestion.target_label = data["target_label"]
    if "confidence" in data:
        suggestion.confidence = _validate_confidence(data["confidence"])
    if "reason" in data:
        suggestion.reason = data["reason"]
    if "review_status" in data and data["review_status"] is not None:
        suggestion.review_status = _validate_allowed(data["review_status"], ALLOWED_REVIEW_STATUSES, "review_status")
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)
    return suggestion


def archive_document_link_suggestion(
    db: Session,
    *,
    organization_id: uuid.UUID,
    document_id: uuid.UUID,
    suggestion_id: uuid.UUID,
) -> DocumentLinkSuggestion:
    suggestion = _require_link_suggestion(
        db,
        organization_id=organization_id,
        document_id=document_id,
        suggestion_id=suggestion_id,
    )
    suggestion.archived_at = _now()
    db.add(suggestion)
    db.commit()
    db.refresh(suggestion)
    return suggestion
