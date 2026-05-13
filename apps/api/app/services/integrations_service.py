from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.schemas.integration_status import IntegrationProviderStatus, IntegrationsStatusResponse
from app.services import outlook_auth_service, outlook_import_service


def _present(value: str | None) -> bool:
    return bool(value and value.strip())


def get_ai_config_status(settings: Settings | None = None) -> IntegrationProviderStatus:
    current = settings or get_settings()
    configured = _present(current.openai_api_key)
    explicitly_disabled = current.ai_features_enabled is False
    enabled = configured and not explicitly_disabled
    missing = [] if configured else ["OPENAI_API_KEY"]
    if explicitly_disabled:
        status = "missing"
        message = "AI features are explicitly disabled with AI_FEATURES_ENABLED=false."
    elif configured:
        status = "configured"
        message = "AI assistant calls are available for explicit Work Hub actions."
    else:
        status = "missing"
        message = "Set OPENAI_API_KEY to enable provider-backed draft generation."

    return IntegrationProviderStatus(
        provider="openai",
        label="AI Assistant",
        configured=configured,
        status=status,
        missing_fields=missing,
        enabled_capabilities=(
            [
                "email_summary",
                "email_action_items",
                "draft_reply",
                "report_section_draft",
                "maintenance_recommendation_draft",
                "client_summary_draft",
            ]
            if enabled
            else [
                "deterministic_file_link_extraction",
                "deterministic_action_candidates",
                "deterministic_record_suggestions",
            ]
        ),
        deferred_capabilities=["auto_send", "outlook_draft_creation", "final_report_generation"],
        message=message,
        model=current.openai_model if configured else None,
    )


def get_integrations_status(
    settings: Settings | None = None,
    *,
    db: Session | None = None,
    organization_id: uuid.UUID | None = None,
) -> IntegrationsStatusResponse:
    current = settings or get_settings()
    if db is not None and organization_id is not None:
        outlook_auth = outlook_auth_service.get_outlook_connection_status(
            db,
            organization_id=organization_id,
            settings=current,
        )
        outlook_configured = outlook_auth.configured
        outlook_missing = outlook_auth.missing_fields
        outlook_status_value = outlook_auth.connection_status if outlook_configured else "missing"
        outlook_message = outlook_auth.message
        if outlook_auth.connection_status in {"connected", "expired"}:
            outlook_enabled = ["stored_oauth_connection", "bounded_preview", "import_selected_to_local_email_records"]
        elif outlook_configured:
            outlook_enabled = ["oauth_authorization"]
        else:
            outlook_enabled = []
    else:
        outlook = outlook_import_service.get_outlook_config_status(current)
        outlook_configured = outlook.configured
        outlook_missing = outlook.missing_fields
        outlook_status_value = "configured" if outlook.configured else "missing"
        outlook_message = outlook.message
        outlook_enabled = ["oauth_authorization"] if outlook.configured else []
    outlook_status = IntegrationProviderStatus(
        provider="outlook",
        label="Outlook",
        configured=outlook_configured,
        status=outlook_status_value,
        missing_fields=outlook_missing,
        enabled_capabilities=outlook_enabled,
        deferred_capabilities=[
            "delta_query_sync",
            "change_notifications",
            "shared_mailbox_selection",
            "draft_creation",
            "send_mail",
            "attachment_download",
        ],
        message=outlook_message,
    )

    return IntegrationsStatusResponse(
        outlook=outlook_status,
        gmail=IntegrationProviderStatus(
            provider="gmail",
            label="Gmail",
            configured=False,
            status="deferred",
            missing_fields=[],
            enabled_capabilities=[],
            deferred_capabilities=["oauth", "push_notifications", "local_import"],
            message="Gmail integration is deferred. Future sync should use push notifications, not polling.",
        ),
        google_drive=IntegrationProviderStatus(
            provider="google_drive",
            label="Google Drive",
            configured=False,
            status="deferred",
            missing_fields=[],
            enabled_capabilities=["metadata_only_file_links"],
            deferred_capabilities=["picker", "oauth", "folder_scan", "attachment_download"],
            message="Google Drive picker/OAuth are deferred. Current file handling stores reviewed metadata links only.",
        ),
        onedrive=IntegrationProviderStatus(
            provider="onedrive",
            label="OneDrive",
            configured=False,
            status="deferred",
            missing_fields=[],
            enabled_capabilities=["metadata_only_file_links"],
            deferred_capabilities=["picker", "oauth", "folder_scan", "sharepoint_scan"],
            message="OneDrive/SharePoint picker flows are deferred. Current links are reviewed metadata only.",
        ),
        ai=get_ai_config_status(current),
    )
