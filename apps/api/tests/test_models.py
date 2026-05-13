import app.models
from app.db import Base
from app.models import (
    ActivityLog,
    AiDraft,
    BmpSystem,
    Client,
    ClientAlias,
    Contact,
    EmailImportBatch,
    EmailMessage,
    EmailRecordLink,
    EvidenceFile,
    ExternalRecordId,
    FileCategory,
    ImportBatch,
    ImportRow,
    Job,
    Observation,
    Organization,
    OrganizationMembership,
    OutlookConnection,
    Reminder,
    Report,
    ServiceCatalog,
    Site,
    SiteAlias,
    User,
)


EXPECTED_TABLES = {
    "activity_log",
    "bmp_systems",
    "clients",
    "client_aliases",
    "contacts",
    "ai_drafts",
    "email_import_batches",
    "email_messages",
    "email_record_links",
    "evidence_files",
    "external_record_ids",
    "file_categories",
    "import_batches",
    "import_rows",
    "jobs",
    "observations",
    "organization_memberships",
    "organizations",
    "outlook_connections",
    "reminders",
    "reports",
    "service_catalog",
    "sites",
    "site_aliases",
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
    "ix_external_record_ids_organization_id_entity",
    "ix_client_aliases_organization_id_client_id",
    "ix_client_aliases_organization_id_source_system",
    "ix_site_aliases_organization_id_site_id",
    "ix_site_aliases_organization_id_client_id",
    "ix_site_aliases_organization_id_source_system",
    "ix_service_catalog_organization_id_category",
    "ix_service_catalog_organization_id_is_active",
    "ix_file_categories_organization_id_is_active",
    "ix_import_batches_organization_id_created_at",
    "ix_import_batches_organization_id_import_type",
    "ix_import_batches_organization_id_status",
    "ix_import_rows_organization_id_import_batch_id",
    "ix_import_rows_organization_id_status",
    "ix_import_rows_organization_id_duplicate_key",
    "ix_import_rows_organization_id_matched_entity",
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
    assert "password_hash" in User.__table__.columns
    assert "is_active" in User.__table__.columns
    assert OrganizationMembership.__tablename__ == "organization_memberships"
    assert Client.__tablename__ == "clients"
    assert ClientAlias.__tablename__ == "client_aliases"
    assert Contact.__tablename__ == "contacts"
    assert Site.__tablename__ == "sites"
    assert SiteAlias.__tablename__ == "site_aliases"
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
    assert ExternalRecordId.__tablename__ == "external_record_ids"
    assert ServiceCatalog.__tablename__ == "service_catalog"
    assert FileCategory.__tablename__ == "file_categories"
    assert ImportBatch.__tablename__ == "import_batches"
    assert ImportRow.__tablename__ == "import_rows"
