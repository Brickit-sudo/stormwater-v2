import app.models
from app.db import Base
from app.models import (
    ActivityLog,
    AiDraft,
    BmpSystem,
    Client,
    Contact,
    EmailImportBatch,
    EmailMessage,
    EmailRecordLink,
    EvidenceFile,
    Job,
    Observation,
    Organization,
    OrganizationMembership,
    OutlookConnection,
    Reminder,
    Report,
    Site,
    User,
)


EXPECTED_TABLES = {
    "activity_log",
    "bmp_systems",
    "clients",
    "contacts",
    "ai_drafts",
    "email_import_batches",
    "email_messages",
    "email_record_links",
    "evidence_files",
    "jobs",
    "observations",
    "organization_memberships",
    "organizations",
    "outlook_connections",
    "reminders",
    "reports",
    "sites",
    "users",
}


EXPECTED_INDEXES = {
    "ix_clients_organization_id_name",
    "ix_clients_organization_id_status",
    "ix_clients_organization_id_legacy_id",
    "ix_sites_organization_id_client_id",
    "ix_sites_organization_id_name",
    "ix_sites_organization_id_city",
    "ix_sites_organization_id_state",
    "ix_sites_organization_id_status",
    "ix_sites_organization_id_legacy_id",
    "ix_jobs_organization_id_client_id",
    "ix_jobs_organization_id_site_id",
    "ix_jobs_organization_id_status",
    "ix_jobs_organization_id_due_date",
    "ix_jobs_organization_id_scheduled_date",
    "ix_jobs_organization_id_legacy_id",
    "ix_bmp_systems_organization_id_site_id",
    "ix_bmp_systems_organization_id_system_type",
    "ix_observations_organization_id_job_id",
    "ix_observations_organization_id_system_id",
    "ix_evidence_files_organization_id_job_id",
    "ix_evidence_files_organization_id_site_id",
    "ix_evidence_files_organization_id_drive_file_id",
    "ix_reports_organization_id_job_id",
    "ix_reports_organization_id_site_id",
    "ix_reports_organization_id_status",
    "ix_reminders_organization_id_due_at",
    "ix_reminders_organization_id_status",
    "ix_reminders_organization_id_priority",
    "ix_reminders_organization_id_job_id",
    "ix_reminders_organization_id_site_id",
    "ix_reminders_organization_id_client_id",
    "ix_email_import_batches_organization_id_created_at",
    "ix_email_messages_organization_id_received_at",
    "ix_email_messages_organization_id_status",
    "ix_email_messages_organization_id_provider_message_id",
    "ix_email_messages_organization_id_client_id",
    "ix_email_messages_organization_id_site_id",
    "ix_email_messages_organization_id_job_id",
    "ix_email_record_links_organization_id_email_message_id",
    "ix_ai_drafts_organization_id_status",
    "ix_ai_drafts_organization_id_draft_type",
    "ix_outlook_connections_organization_id_status",
    "ix_outlook_connections_organization_id_email_address",
}


def test_model_metadata_contains_expected_tables() -> None:
    assert EXPECTED_TABLES <= set(Base.metadata.tables)


def test_model_metadata_contains_expected_indexes() -> None:
    indexes = {
        index.name
        for table in Base.metadata.tables.values()
        for index in table.indexes
    }
    assert EXPECTED_INDEXES <= indexes


def test_core_model_classes_import_cleanly() -> None:
    assert app.models
    assert Organization.__tablename__ == "organizations"
    assert OutlookConnection.__tablename__ == "outlook_connections"
    assert User.__tablename__ == "users"
    assert OrganizationMembership.__tablename__ == "organization_memberships"
    assert Client.__tablename__ == "clients"
    assert Contact.__tablename__ == "contacts"
    assert Site.__tablename__ == "sites"
    assert Job.__tablename__ == "jobs"
    assert BmpSystem.__tablename__ == "bmp_systems"
    assert Observation.__tablename__ == "observations"
    assert EvidenceFile.__tablename__ == "evidence_files"
    assert Reminder.__tablename__ == "reminders"
    assert Report.__tablename__ == "reports"
    assert ActivityLog.__tablename__ == "activity_log"
    assert EmailImportBatch.__tablename__ == "email_import_batches"
    assert EmailMessage.__tablename__ == "email_messages"
    assert EmailRecordLink.__tablename__ == "email_record_links"
    assert AiDraft.__tablename__ == "ai_drafts"
