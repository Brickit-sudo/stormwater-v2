from __future__ import annotations

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
    EmailImportBatch,
    EmailMessage,
    EmailRecordLink,
    EvidenceFile,
    Job,
    KnowledgeItem,
    Observation,
    Organization,
    ProductDecision,
    ProductIdea,
    RecordLink,
    RecordNote,
    Reminder,
    Site,
)
from scripts.seed_dev import (
    DEMO_ORGANIZATION_ID,
    LEGACY_SOURCE,
    SEED_BMP_SYSTEMS,
    SEED_CLIENTS,
    SEED_DOCUMENT_EXTRACTED_FIELDS,
    SEED_DOCUMENT_LINK_SUGGESTIONS,
    SEED_DOCUMENT_RECORDS,
    SEED_DOCUMENT_TEXT_CHUNKS,
    SEED_EVIDENCE_FILES,
    SEED_AI_DRAFTS,
    SEED_EMAIL_IMPORT_BATCHES,
    SEED_EMAIL_MESSAGES,
    SEED_EMAIL_RECORD_LINKS,
    SEED_JOBS,
    SEED_KNOWLEDGE_ITEMS,
    SEED_OBSERVATIONS,
    SEED_PRODUCT_DECISIONS,
    SEED_PRODUCT_IDEAS,
    SEED_RECORD_LINKS,
    SEED_RECORD_NOTES,
    SEED_REMINDERS,
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
        "bmp_systems": 4,
        "observations": 4,
        "reminders": 4,
        "evidence_files": 9,
        "record_notes": 3,
        "knowledge_items": 4,
        "document_records": 3,
        "document_text_chunks": 3,
        "document_extracted_fields": 3,
        "document_link_suggestions": 2,
        "email_import_batches": 1,
        "email_messages": 5,
        "email_record_links": 3,
        "ai_drafts": 3,
        "record_links": 5,
        "product_ideas": 21,
        "product_decisions": 8,
    }
    assert {client["status"] for client in SEED_CLIENTS} == {
        "active",
        "inactive",
        "prospect",
    }
    assert {"active", "inactive", "on_hold"}.issubset(
        {site["status"] for site in SEED_SITES},
    )
    assert all(site["latitude"] is not None and site["longitude"] is not None for site in SEED_SITES)
    assert all(-90 <= site["latitude"] <= 90 for site in SEED_SITES)
    assert all(-180 <= site["longitude"] <= 180 for site in SEED_SITES)
    assert {"draft", "scheduled", "in_progress", "in_review", "completed"}.issubset(
        {job["status"] for job in SEED_JOBS},
    )
    assert {record["system_type"] for record in SEED_BMP_SYSTEMS} >= {
        "catch_basin",
        "hydrodynamic_separator",
        "pond_forebay",
    }
    assert {record["severity"] for record in SEED_OBSERVATIONS} >= {"high", "medium", "low"}
    scopes = {record["scope"] for record in SEED_EVIDENCE_FILES}
    assert scopes == {"client", "site", "job"}
    assert {record["status"] for record in SEED_REMINDERS} == {"open", "completed"}
    assert {record["target_type"] for record in SEED_REMINDERS} == {"client", "site", "job"}
    assert {record["status"] for record in SEED_EMAIL_IMPORT_BATCHES} == {"seed"}
    assert len(SEED_EMAIL_MESSAGES) == 5
    assert {"linked", "unlinked"}.issubset({record["status"] for record in SEED_EMAIL_MESSAGES})
    assert len(SEED_EMAIL_RECORD_LINKS) == 3
    assert {record["status"] for record in SEED_AI_DRAFTS} == {"draft", "reviewed"}
    assert {record["parent_type"] for record in SEED_RECORD_NOTES} == {
        "site",
        "job",
        "observation",
    }
    assert {record["knowledge_type"] for record in SEED_KNOWLEDGE_ITEMS} == {
        "site_access",
        "client_preference",
        "permit_note",
        "report_language",
    }
    assert {record["document_type"] for record in SEED_DOCUMENT_RECORDS} == {
        "report",
        "proposal",
        "invoice",
    }
    assert len(SEED_DOCUMENT_TEXT_CHUNKS) == 3
    assert {record["review_status"] for record in SEED_DOCUMENT_EXTRACTED_FIELDS} == {
        "pending",
        "needs_review",
    }
    assert len(SEED_DOCUMENT_LINK_SUGGESTIONS) == 2
    assert {record["target_type"] for record in SEED_RECORD_LINKS} >= {
        "site",
        "job",
        "email_message",
        "bmp_system",
    }
    assert "Auth/login for staging" in {record["title"] for record in SEED_PRODUCT_IDEAS}
    assert "Gmail support later" in {record["title"] for record in SEED_PRODUCT_IDEAS}
    assert "V2 is the future product." in {
        record["decision_title"] for record in SEED_PRODUCT_DECISIONS
    }
    assert {record["status"] for record in SEED_PRODUCT_DECISIONS} == {"decided"}


def test_seed_is_idempotent(db_session: Session) -> None:
    first_org = seed(db_session)
    second_org = seed(db_session)

    assert first_org.id == second_org.id == DEMO_ORGANIZATION_ID
    assert db_session.scalar(select(Organization).where(Organization.id == DEMO_ORGANIZATION_ID))
    assert db_session.query(Client).filter(Client.legacy_source == LEGACY_SOURCE).count() == 3
    assert db_session.query(Site).filter(Site.legacy_source == LEGACY_SOURCE).count() == 5
    assert db_session.query(Job).filter(Job.legacy_source == LEGACY_SOURCE).count() == 8
    assert db_session.query(BmpSystem).filter(BmpSystem.legacy_source == LEGACY_SOURCE).count() == 4
    assert db_session.query(Observation).count() == 4
    assert db_session.query(Reminder).count() == 4
    assert db_session.query(RecordNote).count() == 3
    assert db_session.query(KnowledgeItem).count() == 4
    assert db_session.query(DocumentRecord).count() == 3
    assert db_session.query(DocumentTextChunk).count() == 3
    assert db_session.query(DocumentExtractedField).count() == 3
    assert db_session.query(DocumentLinkSuggestion).count() == 2
    assert db_session.query(EmailImportBatch).count() == 1
    assert db_session.query(EmailMessage).count() == 5
    assert db_session.query(EmailRecordLink).count() == 3
    assert db_session.query(AiDraft).count() == 3
    assert db_session.query(RecordLink).count() == 5
    assert db_session.query(ProductIdea).count() == 21
    assert db_session.query(ProductDecision).count() == 8
    assert (
        db_session.query(EvidenceFile)
        .filter(EvidenceFile.legacy_source == LEGACY_SOURCE)
        .count()
        == 9
    )


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

    assert deleted == {
        "record_links": 5,
        "ai_drafts": 3,
        "email_record_links": 3,
        "email_messages": 5,
        "email_import_batches": 1,
        "document_link_suggestions": 2,
        "document_extracted_fields": 3,
        "document_text_chunks": 3,
        "document_records": 3,
        "knowledge_items": 4,
        "record_notes": 3,
        "evidence_files": 9,
        "product_decisions": 8,
        "product_ideas": 21,
        "reminders": 4,
        "observations": 4,
        "bmp_systems": 4,
        "jobs": 8,
        "sites": 5,
        "clients": 3,
    }
    assert db_session.scalar(
        select(Client).where(
            Client.organization_id == DEMO_ORGANIZATION_ID,
            Client.legacy_source == "manual",
        ),
    )
    assert db_session.query(Client).filter(Client.legacy_source == LEGACY_SOURCE).count() == 0
    assert db_session.query(Site).filter(Site.legacy_source == LEGACY_SOURCE).count() == 0
    assert db_session.query(Job).filter(Job.legacy_source == LEGACY_SOURCE).count() == 0
    assert db_session.query(BmpSystem).filter(BmpSystem.legacy_source == LEGACY_SOURCE).count() == 0
    assert db_session.query(Observation).count() == 0
    assert db_session.query(Reminder).count() == 0
    assert db_session.query(RecordNote).count() == 0
    assert db_session.query(KnowledgeItem).count() == 0
    assert db_session.query(DocumentRecord).count() == 0
    assert db_session.query(DocumentTextChunk).count() == 0
    assert db_session.query(DocumentExtractedField).count() == 0
    assert db_session.query(DocumentLinkSuggestion).count() == 0
    assert db_session.query(EmailImportBatch).count() == 0
    assert db_session.query(EmailMessage).count() == 0
    assert db_session.query(EmailRecordLink).count() == 0
    assert db_session.query(AiDraft).count() == 0
    assert db_session.query(RecordLink).count() == 0
    assert db_session.query(ProductIdea).count() == 0
    assert db_session.query(ProductDecision).count() == 0
    assert (
        db_session.query(EvidenceFile)
        .filter(EvidenceFile.legacy_source == LEGACY_SOURCE)
        .count()
        == 0
    )
