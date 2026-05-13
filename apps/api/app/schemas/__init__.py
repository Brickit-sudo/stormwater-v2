"""Pydantic schemas for API request and response bodies."""

from app.schemas.ai_draft import AiDraftCreate, AiDraftListResponse, AiDraftRead, AiDraftUpdate
from app.schemas.client import ClientBase, ClientCreate, ClientListResponse, ClientRead, ClientUpdate
from app.schemas.email_import_batch import (
    EmailImportBatchBase,
    EmailImportBatchCreate,
    EmailImportBatchListResponse,
    EmailImportBatchRead,
)
from app.schemas.email_message import (
    EmailMessageBase,
    EmailMessageCreate,
    EmailMessageListResponse,
    EmailMessageRead,
    EmailMessageUpdate,
)
from app.schemas.email_record_link import (
    EmailRecordLinkBase,
    EmailRecordLinkCreate,
    EmailRecordLinkListResponse,
    EmailRecordLinkRead,
)
from app.schemas.evidence_file import (
    EvidenceFileBase,
    EvidenceFileCreate,
    EvidenceFileListResponse,
    EvidenceFileRead,
    EvidenceFileUpdate,
)
from app.schemas.job import JobBase, JobCreate, JobListResponse, JobRead, JobUpdate
from app.schemas.outlook_import import (
    OutlookImportSelectedRequest,
    OutlookImportSelectedResponse,
    OutlookPreviewMessage,
    OutlookPreviewRequest,
    OutlookPreviewResponse,
    OutlookStatusResponse,
)
from app.schemas.reminder import (
    ReminderBase,
    ReminderCreate,
    ReminderListResponse,
    ReminderRead,
    ReminderUpdate,
)
from app.schemas.site import (
    SiteBase,
    SiteCreate,
    SiteListResponse,
    SiteMapListResponse,
    SiteMapRead,
    SiteRead,
    SiteUpdate,
)

__all__ = [
    "AiDraftCreate",
    "AiDraftListResponse",
    "AiDraftRead",
    "AiDraftUpdate",
    "ClientBase",
    "ClientCreate",
    "ClientListResponse",
    "ClientRead",
    "ClientUpdate",
    "EmailImportBatchBase",
    "EmailImportBatchCreate",
    "EmailImportBatchListResponse",
    "EmailImportBatchRead",
    "EmailMessageBase",
    "EmailMessageCreate",
    "EmailMessageListResponse",
    "EmailMessageRead",
    "EmailMessageUpdate",
    "EmailRecordLinkBase",
    "EmailRecordLinkCreate",
    "EmailRecordLinkListResponse",
    "EmailRecordLinkRead",
    "EvidenceFileBase",
    "EvidenceFileCreate",
    "EvidenceFileListResponse",
    "EvidenceFileRead",
    "EvidenceFileUpdate",
    "JobBase",
    "JobCreate",
    "JobListResponse",
    "JobRead",
    "JobUpdate",
    "OutlookImportSelectedRequest",
    "OutlookImportSelectedResponse",
    "OutlookPreviewMessage",
    "OutlookPreviewRequest",
    "OutlookPreviewResponse",
    "OutlookStatusResponse",
    "ReminderBase",
    "ReminderCreate",
    "ReminderListResponse",
    "ReminderRead",
    "ReminderUpdate",
    "SiteBase",
    "SiteCreate",
    "SiteListResponse",
    "SiteMapListResponse",
    "SiteMapRead",
    "SiteRead",
    "SiteUpdate",
]
