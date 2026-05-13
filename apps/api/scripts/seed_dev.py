from __future__ import annotations

import argparse
import sys
import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.db import get_session_factory  # noqa: E402
from app.models import (  # noqa: E402
    AiDraft,
    Client,
    EmailImportBatch,
    EmailMessage,
    EmailRecordLink,
    EvidenceFile,
    Job,
    Organization,
    Reminder,
    Site,
)


LEGACY_SOURCE = "seed_dev"
_UUID_NAMESPACE = uuid.UUID("a2e00679-2448-4c18-9a56-072e385be96b")
DEMO_ORGANIZATION_ID = uuid.uuid5(_UUID_NAMESPACE, f"{LEGACY_SOURCE}:organization:sterling-demo")
DEMO_ORGANIZATION_NAME = "Sterling Stormwater Demo"


def _seed_uuid(legacy_id: str) -> uuid.UUID:
    return uuid.uuid5(_UUID_NAMESPACE, f"{LEGACY_SOURCE}:{legacy_id}")


SEED_CLIENTS: list[dict[str, Any]] = [
    {
        "legacy_id": "client:pine-tree-property-management",
        "id": _seed_uuid("client:pine-tree-property-management"),
        "client_code": "PTPM",
        "name": "Pine Tree Property Management",
        "status": "active",
        "primary_contact_name": "Mara Whitcomb",
        "email": "mara.whitcomb@pinetree.example",
        "phone": "207-555-0142",
        "billing_address": "482 Congress Street\nPortland, ME 04101",
        "notes": "Regional property manager with recurring inspection and maintenance work.",
        "drive_folder_id": "seed-client-ptpm",
        "drive_folder_url": "https://drive.google.com/drive/folders/seed-client-ptpm",
    },
    {
        "legacy_id": "client:northeast-retail-portfolio",
        "id": _seed_uuid("client:northeast-retail-portfolio"),
        "client_code": "NERP",
        "name": "Northeast Retail Portfolio",
        "status": "prospect",
        "primary_contact_name": "Evan Calder",
        "email": "facilities@northeastretail.example",
        "phone": "603-555-0188",
        "billing_address": "15 Market Square\nPortsmouth, NH 03801",
        "notes": "Multi-state retail portfolio evaluating consolidated stormwater service.",
        "drive_folder_id": None,
        "drive_folder_url": None,
    },
    {
        "legacy_id": "client:kennebec-millworks",
        "id": _seed_uuid("client:kennebec-millworks"),
        "client_code": "KMW",
        "name": "Kennebec Millworks",
        "status": "inactive",
        "primary_contact_name": "Lena Caron",
        "email": "lcaron@kennebecmill.example",
        "phone": "207-555-0119",
        "billing_address": "78 Canal Street\nLewiston, ME 04240",
        "notes": "Inactive industrial account retained for historical CRM workflow testing.",
        "drive_folder_id": "seed-client-kmw",
        "drive_folder_url": "https://drive.google.com/drive/folders/seed-client-kmw",
    },
]

SEED_SITES: list[dict[str, Any]] = [
    {
        "legacy_id": "site:bayside-retail-plaza",
        "id": _seed_uuid("site:bayside-retail-plaza"),
        "client_legacy_id": "client:pine-tree-property-management",
        "site_code": "PTPM-BAY",
        "name": "Bayside Retail Plaza",
        "address": "112 Marginal Way",
        "city": "Portland",
        "state": "ME",
        "zip": "04101",
        "latitude": Decimal("43.663320"),
        "longitude": Decimal("-70.256760"),
        "status": "active",
        "notes": "Urban retail plaza with catch basins, proprietary treatment units, and tight access windows.",
        "drive_folder_id": "seed-site-bayside-retail-plaza",
        "drive_folder_url": "https://drive.google.com/drive/folders/seed-site-bayside-retail-plaza",
    },
    {
        "legacy_id": "site:augusta-logistics-yard",
        "id": _seed_uuid("site:augusta-logistics-yard"),
        "client_legacy_id": "client:pine-tree-property-management",
        "site_code": "PTPM-AUG",
        "name": "Augusta Logistics Yard",
        "address": "42 Industrial Drive",
        "city": "Augusta",
        "state": "ME",
        "zip": "04330",
        "latitude": Decimal("44.310620"),
        "longitude": Decimal("-69.779490"),
        "status": "active",
        "notes": "Truck yard with sediment loading at inlet structures after winter operations.",
        "drive_folder_id": None,
        "drive_folder_url": None,
    },
    {
        "legacy_id": "site:portsmouth-crossing",
        "id": _seed_uuid("site:portsmouth-crossing"),
        "client_legacy_id": "client:northeast-retail-portfolio",
        "site_code": "NERP-PSC",
        "name": "Portsmouth Crossing",
        "address": "8 Woodbury Avenue",
        "city": "Portsmouth",
        "state": "NH",
        "zip": "03801",
        "latitude": Decimal("43.081900"),
        "longitude": Decimal("-70.775180"),
        "status": "on_hold",
        "notes": "Prospect site pending portfolio onboarding and access agreement.",
        "drive_folder_id": "seed-site-portsmouth-crossing",
        "drive_folder_url": "https://drive.google.com/drive/folders/seed-site-portsmouth-crossing",
    },
    {
        "legacy_id": "site:bangor-cold-storage",
        "id": _seed_uuid("site:bangor-cold-storage"),
        "client_legacy_id": "client:northeast-retail-portfolio",
        "site_code": "NERP-BCS",
        "name": "Bangor Cold Storage",
        "address": "240 Bomarc Road",
        "city": "Bangor",
        "state": "ME",
        "zip": "04401",
        "latitude": Decimal("44.819820"),
        "longitude": Decimal("-68.802070"),
        "status": "active",
        "notes": "Cold storage facility with roof runoff pretreatment and forebay maintenance needs.",
        "drive_folder_id": None,
        "drive_folder_url": None,
    },
    {
        "legacy_id": "site:androscoggin-mill-complex",
        "id": _seed_uuid("site:androscoggin-mill-complex"),
        "client_legacy_id": "client:kennebec-millworks",
        "site_code": "KMW-AMC",
        "name": "Androscoggin Mill Complex",
        "address": "78 Canal Street",
        "city": "Lewiston",
        "state": "ME",
        "zip": "04240",
        "latitude": Decimal("44.098560"),
        "longitude": Decimal("-70.221960"),
        "status": "inactive",
        "notes": "Legacy industrial site retained to verify inactive status filters and archive flows.",
        "drive_folder_id": "seed-site-androscoggin-mill-complex",
        "drive_folder_url": "https://drive.google.com/drive/folders/seed-site-androscoggin-mill-complex",
    },
]

SEED_JOBS: list[dict[str, Any]] = [
    {
        "legacy_id": "job:bayside-2026-spring-inspection",
        "id": _seed_uuid("job:bayside-2026-spring-inspection"),
        "client_legacy_id": "client:pine-tree-property-management",
        "site_legacy_id": "site:bayside-retail-plaza",
        "job_code": "BAY-2026-INS",
        "name": "2026 Spring BMP Inspection",
        "service_type": "Annual stormwater BMP inspection",
        "status": "scheduled",
        "scheduled_date": date(2026, 5, 18),
        "due_date": date(2026, 5, 22),
        "completed_date": None,
        "scope": "Inspect catch basins, hydrodynamic separators, outlet controls, and pavement drainage patterns.",
        "notes": "Coordinate with property manager for early morning access before retail traffic.",
        "drive_folder_id": "seed-job-bayside-2026-spring-inspection",
        "drive_folder_url": "https://drive.google.com/drive/folders/seed-job-bayside-2026-spring-inspection",
    },
    {
        "legacy_id": "job:bayside-catch-basin-cleaning",
        "id": _seed_uuid("job:bayside-catch-basin-cleaning"),
        "client_legacy_id": "client:pine-tree-property-management",
        "site_legacy_id": "site:bayside-retail-plaza",
        "job_code": "BAY-2026-CB",
        "name": "Catch Basin Cleaning and Sediment Disposal",
        "service_type": "Vac truck maintenance",
        "status": "in_progress",
        "scheduled_date": date(2026, 5, 11),
        "due_date": date(2026, 5, 15),
        "completed_date": None,
        "scope": "Clean priority structures, document sediment depths, and stage disposal manifests.",
        "notes": "Crew reported two structures under parked vehicles; revisit needed.",
        "drive_folder_id": None,
        "drive_folder_url": None,
    },
    {
        "legacy_id": "job:bayside-post-storm-outfall-review",
        "id": _seed_uuid("job:bayside-post-storm-outfall-review"),
        "client_legacy_id": "client:pine-tree-property-management",
        "site_legacy_id": "site:bayside-retail-plaza",
        "job_code": "BAY-2026-OUT",
        "name": "Post-Storm Outfall Walkthrough",
        "service_type": "Outfall inspection",
        "status": "in_review",
        "scheduled_date": date(2026, 4, 29),
        "due_date": date(2026, 5, 6),
        "completed_date": date(2026, 4, 29),
        "scope": "Review discharge points after major rainfall and capture photo evidence for the client file.",
        "notes": "Draft findings need PM review before client delivery.",
        "drive_folder_id": "seed-job-bayside-post-storm-outfall-review",
        "drive_folder_url": "https://drive.google.com/drive/folders/seed-job-bayside-post-storm-outfall-review",
    },
    {
        "legacy_id": "job:augusta-winter-sediment-cleanout",
        "id": _seed_uuid("job:augusta-winter-sediment-cleanout"),
        "client_legacy_id": "client:pine-tree-property-management",
        "site_legacy_id": "site:augusta-logistics-yard",
        "job_code": "AUG-2026-SED",
        "name": "Winter Sediment Cleanout",
        "service_type": "Sediment removal",
        "status": "completed",
        "scheduled_date": date(2026, 4, 20),
        "due_date": date(2026, 4, 24),
        "completed_date": date(2026, 4, 22),
        "scope": "Remove winter sand accumulation from inlet sumps and inspect outlet stabilization.",
        "notes": "Completed with disposal ticket attached in the job folder.",
        "drive_folder_id": "seed-job-augusta-winter-sediment-cleanout",
        "drive_folder_url": "https://drive.google.com/drive/folders/seed-job-augusta-winter-sediment-cleanout",
    },
    {
        "legacy_id": "job:augusta-yard-swppp-review",
        "id": _seed_uuid("job:augusta-yard-swppp-review"),
        "client_legacy_id": "client:pine-tree-property-management",
        "site_legacy_id": "site:augusta-logistics-yard",
        "job_code": "AUG-2026-SWPPP",
        "name": "Industrial Yard SWPPP Support",
        "service_type": "SWPPP support",
        "status": "draft",
        "scheduled_date": None,
        "due_date": date(2026, 6, 12),
        "completed_date": None,
        "scope": "Prepare a scoped visit for drainage housekeeping, spill-kit locations, and exposed material storage.",
        "notes": "Draft job used to verify create/edit workflows before scheduling.",
        "drive_folder_id": None,
        "drive_folder_url": None,
    },
    {
        "legacy_id": "job:portsmouth-portfolio-onboarding",
        "id": _seed_uuid("job:portsmouth-portfolio-onboarding"),
        "client_legacy_id": "client:northeast-retail-portfolio",
        "site_legacy_id": "site:portsmouth-crossing",
        "job_code": "PSC-2026-ONB",
        "name": "Portfolio Onboarding Site Walk",
        "service_type": "Baseline assessment",
        "status": "scheduled",
        "scheduled_date": date(2026, 6, 3),
        "due_date": date(2026, 6, 7),
        "completed_date": None,
        "scope": "Create baseline asset list, note access constraints, and identify report-ready BMP inventory gaps.",
        "notes": "Prospect workflow seed with an on-hold site.",
        "drive_folder_id": None,
        "drive_folder_url": None,
    },
    {
        "legacy_id": "job:bangor-forebay-dredge-scoping",
        "id": _seed_uuid("job:bangor-forebay-dredge-scoping"),
        "client_legacy_id": "client:northeast-retail-portfolio",
        "site_legacy_id": "site:bangor-cold-storage",
        "job_code": "BCS-2026-FBY",
        "name": "Stormwater Pond Forebay Dredge Scoping",
        "service_type": "Pond maintenance scoping",
        "status": "in_review",
        "scheduled_date": date(2026, 5, 4),
        "due_date": date(2026, 5, 14),
        "completed_date": date(2026, 5, 4),
        "scope": "Estimate forebay sediment volume, access path constraints, and recommended maintenance sequencing.",
        "notes": "Needs internal review before quote generation is built.",
        "drive_folder_id": "seed-job-bangor-forebay-dredge-scoping",
        "drive_folder_url": "https://drive.google.com/drive/folders/seed-job-bangor-forebay-dredge-scoping",
    },
    {
        "legacy_id": "job:androscoggin-closeout-inspection",
        "id": _seed_uuid("job:androscoggin-closeout-inspection"),
        "client_legacy_id": "client:kennebec-millworks",
        "site_legacy_id": "site:androscoggin-mill-complex",
        "job_code": "AMC-2025-CLOSE",
        "name": "2025 Closeout Inspection",
        "service_type": "Compliance inspection",
        "status": "completed",
        "scheduled_date": date(2025, 10, 16),
        "due_date": date(2025, 10, 31),
        "completed_date": date(2025, 10, 17),
        "scope": "Document final site condition before account inactivity and archive historical maintenance notes.",
        "notes": "Completed legacy-style job for inactive client/site filtering checks.",
        "drive_folder_id": "seed-job-androscoggin-closeout-inspection",
        "drive_folder_url": "https://drive.google.com/drive/folders/seed-job-androscoggin-closeout-inspection",
    },
]


SEED_REMINDERS: list[dict[str, Any]] = [
    {
        "id": _seed_uuid("reminder:bayside-catch-basin-revisit"),
        "target_type": "job",
        "target_legacy_id": "job:bayside-catch-basin-cleaning",
        "title": "Revisit blocked catch basins",
        "description": "Two structures were blocked by parked vehicles during the first cleaning visit.",
        "status": "open",
        "priority": "high",
        "due_at": datetime(2026, 5, 10, 13, 0, tzinfo=UTC),
        "reminder_at": datetime(2026, 5, 10, 8, 0, tzinfo=UTC),
        "completed_at": None,
        "source_type": "seed_dev",
        "source_id": "operation:blocked-catch-basin-revisit",
    },
    {
        "id": _seed_uuid("reminder:bayside-site-access-confirmation"),
        "target_type": "site",
        "target_legacy_id": "site:bayside-retail-plaza",
        "title": "Confirm Bayside early access window",
        "description": "Coordinate site access before retail traffic for the scheduled inspection window.",
        "status": "open",
        "priority": "medium",
        "due_at": datetime(2026, 5, 12, 14, 0, tzinfo=UTC),
        "reminder_at": datetime(2026, 5, 12, 9, 0, tzinfo=UTC),
        "completed_at": None,
        "source_type": "seed_dev",
        "source_id": "operation:site-access-confirmation",
    },
    {
        "id": _seed_uuid("reminder:northeast-retail-onboarding-checkin"),
        "target_type": "client",
        "target_legacy_id": "client:northeast-retail-portfolio",
        "title": "Portfolio onboarding follow-up",
        "description": "Check whether Northeast Retail wants the consolidated stormwater service package.",
        "status": "open",
        "priority": "low",
        "due_at": datetime(2026, 5, 25, 15, 0, tzinfo=UTC),
        "reminder_at": datetime(2026, 5, 22, 13, 0, tzinfo=UTC),
        "completed_at": None,
        "source_type": "seed_dev",
        "source_id": "operation:portfolio-onboarding",
    },
    {
        "id": _seed_uuid("reminder:augusta-completed-ticket-closeout"),
        "target_type": "job",
        "target_legacy_id": "job:augusta-winter-sediment-cleanout",
        "title": "Confirm cleanout closeout was logged",
        "description": "Completed seed reminder used to verify completed reminder filtering.",
        "status": "completed",
        "priority": "medium",
        "due_at": datetime(2026, 4, 23, 16, 0, tzinfo=UTC),
        "reminder_at": datetime(2026, 4, 23, 12, 0, tzinfo=UTC),
        "completed_at": datetime(2026, 4, 23, 18, 0, tzinfo=UTC),
        "source_type": "seed_dev",
        "source_id": "operation:job-closeout",
    },
]


SEED_EVIDENCE_FILES: list[dict[str, Any]] = [
    {
        "legacy_id": "evidence_file:ptpm-master-service-agreement",
        "id": _seed_uuid("evidence_file:ptpm-master-service-agreement"),
        "scope": "client",
        "client_legacy_id": "client:pine-tree-property-management",
        "site_legacy_id": None,
        "job_legacy_id": None,
        "source": "drive_link",
        "file_name": "Master Service Agreement (2026).pdf",
        "mime_type": "application/pdf",
        "public_url": "https://drive.google.com/file/d/seed-msa-ptpm-2026/view",
        "caption": "Signed master service agreement for 2026.",
        "sort_order": 0,
    },
    {
        "legacy_id": "evidence_file:kmw-certificate-of-insurance",
        "id": _seed_uuid("evidence_file:kmw-certificate-of-insurance"),
        "scope": "client",
        "client_legacy_id": "client:kennebec-millworks",
        "site_legacy_id": None,
        "job_legacy_id": None,
        "source": "drive_link",
        "file_name": "Certificate of Insurance.pdf",
        "mime_type": "application/pdf",
        "public_url": "https://drive.google.com/file/d/seed-coi-kmw/view",
        "caption": None,
        "sort_order": 0,
    },
    {
        "legacy_id": "evidence_file:bayside-site-plan-v3",
        "id": _seed_uuid("evidence_file:bayside-site-plan-v3"),
        "scope": "site",
        "client_legacy_id": None,
        "site_legacy_id": "site:bayside-retail-plaza",
        "job_legacy_id": None,
        "source": "drive_link",
        "file_name": "Site Plan v3.pdf",
        "mime_type": "application/pdf",
        "public_url": "https://drive.google.com/file/d/seed-bayside-site-plan-v3/view",
        "caption": "Latest stamped civil site plan for the retail plaza.",
        "sort_order": 0,
    },
    {
        "legacy_id": "evidence_file:augusta-ms4-permit-notice",
        "id": _seed_uuid("evidence_file:augusta-ms4-permit-notice"),
        "scope": "site",
        "client_legacy_id": None,
        "site_legacy_id": "site:augusta-logistics-yard",
        "job_legacy_id": None,
        "source": "other",
        "file_name": "MS4 Permit Notice.pdf",
        "mime_type": "application/pdf",
        "public_url": "https://drive.google.com/file/d/seed-augusta-ms4-permit/view",
        "caption": None,
        "sort_order": 0,
    },
    {
        "legacy_id": "evidence_file:bayside-spring-inspection-photo-set",
        "id": _seed_uuid("evidence_file:bayside-spring-inspection-photo-set"),
        "scope": "job",
        "client_legacy_id": None,
        "site_legacy_id": None,
        "job_legacy_id": "job:bayside-2026-spring-inspection",
        "source": "drive_link",
        "file_name": "Inspection Photo Set Placeholder",
        "mime_type": None,
        "public_url": "https://drive.google.com/drive/folders/seed-bayside-2026-photos",
        "caption": "Photo collection placeholder until the photo flow lands.",
        "sort_order": 0,
    },
    {
        "legacy_id": "evidence_file:augusta-winter-sediment-cleanout-verification",
        "id": _seed_uuid("evidence_file:augusta-winter-sediment-cleanout-verification"),
        "scope": "job",
        "client_legacy_id": None,
        "site_legacy_id": None,
        "job_legacy_id": "job:augusta-winter-sediment-cleanout",
        "source": "drive_link",
        "file_name": "Maintenance Verification Notes.pdf",
        "mime_type": "application/pdf",
        "public_url": "https://drive.google.com/file/d/seed-augusta-maintenance-verification/view",
        "caption": "Crew verification of inlet sumps after winter sediment removal.",
        "sort_order": 0,
    },
    {
        "legacy_id": "evidence_file:augusta-swppp-pending-field-notes",
        "id": _seed_uuid("evidence_file:augusta-swppp-pending-field-notes"),
        "scope": "job",
        "client_legacy_id": None,
        "site_legacy_id": None,
        "job_legacy_id": "job:augusta-yard-swppp-review",
        "source": "other",
        "file_name": "Pending Field Notes",
        "mime_type": None,
        "public_url": None,
        "caption": "Draft placeholder; no URL yet - exercises the missing-URL render path.",
        "sort_order": 0,
    },
]


SEED_EMAIL_IMPORT_BATCHES: list[dict[str, Any]] = [
    {
        "id": _seed_uuid("email_import_batch:work-hub-seed"),
        "provider": "outlook",
        "import_mode": "manual_seed",
        "folder_id": "seed-inbox",
        "search_query": "stormwater OR catch basin OR BMP",
        "date_from": datetime(2026, 5, 1, 0, 0, tzinfo=UTC),
        "date_to": datetime(2026, 5, 12, 23, 59, tzinfo=UTC),
        "status": "seed",
        "preview_count": 5,
        "imported_count": 5,
        "skipped_count": 0,
        "duplicate_count": 0,
        "error_count": 0,
        "request_json": {
            "source": "seed_dev",
            "note": "Local Work Hub seed only; Outlook is not connected yet.",
        },
        "result_summary_json": {
            "summary": "Seeded five local stormwater email records for Work Hub testing.",
        },
        "completed_at": datetime(2026, 5, 12, 16, 0, tzinfo=UTC),
    },
]


SEED_EMAIL_MESSAGES: list[dict[str, Any]] = [
    {
        "legacy_id": "email:bayside-access-window",
        "id": _seed_uuid("email:bayside-access-window"),
        "import_batch_id": _seed_uuid("email_import_batch:work-hub-seed"),
        "target_type": "job",
        "target_legacy_id": "job:bayside-2026-spring-inspection",
        "provider": "outlook",
        "provider_message_id": "seed-outlook-bayside-access-window",
        "provider_conversation_id": "seed-conv-bayside-access",
        "internet_message_id": "<seed-bayside-access@example>",
        "subject": "Bayside inspection access window",
        "sender": "Mara Whitcomb <mara.whitcomb@pinetree.example>",
        "recipients_json": [
            {"name": "Sterling Operations", "email": "ops@sterling.example"},
        ],
        "received_at": datetime(2026, 5, 12, 13, 20, tzinfo=UTC),
        "snippet": "Can your crew arrive before the stores open for the BMP inspection?",
        "body_text": (
            "Can your crew arrive before the stores open for the BMP inspection? "
            "The property manager can unlock the rear gate at 6:30 AM. "
            "The current site folder is https://drive.google.com/drive/folders/seed-site-bayside-retail-plaza"
        ),
        "body_html": None,
        "attachments_json": [
            {"name": "Bayside access map.pdf", "size_bytes": 186400, "content_type": "application/pdf"},
        ],
        "links_json": [
            {"label": "Bayside site folder", "url": "https://drive.google.com/drive/folders/seed-site-bayside-retail-plaza"},
        ],
        "web_link": "https://outlook.office.com/mail/seed-bayside-access-window",
        "status": "linked",
    },
    {
        "legacy_id": "email:catch-basin-blocked-structures",
        "id": _seed_uuid("email:catch-basin-blocked-structures"),
        "import_batch_id": _seed_uuid("email_import_batch:work-hub-seed"),
        "target_type": "job",
        "target_legacy_id": "job:bayside-catch-basin-cleaning",
        "provider": "outlook",
        "provider_message_id": "seed-outlook-catch-basin-blocked",
        "provider_conversation_id": "seed-conv-catch-basin-blocked",
        "internet_message_id": "<seed-catch-basin-blocked@example>",
        "subject": "Two blocked catch basins need a revisit",
        "sender": "Field Crew <crew@sterling.example>",
        "recipients_json": [
            {"name": "Sterling PM", "email": "pm@sterling.example"},
        ],
        "received_at": datetime(2026, 5, 11, 20, 45, tzinfo=UTC),
        "snippet": "CB-4 and CB-7 were blocked by vehicles during the cleanout visit.",
        "body_text": (
            "CB-4 and CB-7 were blocked by vehicles during the cleanout visit. "
            "Recommend a short return visit after the tenant notice goes out. "
            "Photos are staged at https://1drv.ms/f/s!seedBlockedStructures"
        ),
        "body_html": None,
        "attachments_json": [
            {"name": "blocked-structures.jpg", "size_bytes": 944200, "content_type": "image/jpeg"},
        ],
        "links_json": [
            {"label": "Photo placeholder", "url": "https://drive.google.com/drive/folders/seed-bayside-2026-photos"},
        ],
        "web_link": "https://outlook.office.com/mail/seed-catch-basin-blocked",
        "status": "linked",
    },
    {
        "legacy_id": "email:augusta-disposal-ticket",
        "id": _seed_uuid("email:augusta-disposal-ticket"),
        "import_batch_id": _seed_uuid("email_import_batch:work-hub-seed"),
        "target_type": "job",
        "target_legacy_id": "job:augusta-winter-sediment-cleanout",
        "provider": "outlook",
        "provider_message_id": "seed-outlook-augusta-disposal-ticket",
        "provider_conversation_id": "seed-conv-augusta-disposal",
        "internet_message_id": "<seed-augusta-disposal@example>",
        "subject": "Augusta cleanout disposal ticket",
        "sender": "Disposal Desk <tickets@disposal.example>",
        "recipients_json": [
            {"name": "Sterling Admin", "email": "admin@sterling.example"},
        ],
        "received_at": datetime(2026, 4, 23, 14, 10, tzinfo=UTC),
        "snippet": "Attached is the disposal ticket for the Augusta winter sediment cleanout.",
        "body_text": "Attached is the disposal ticket for the Augusta winter sediment cleanout.",
        "body_html": None,
        "attachments_json": [
            {"name": "AUG-2026-SED-disposal-ticket.pdf", "size_bytes": 224300, "content_type": "application/pdf"},
        ],
        "links_json": [
            {"label": "Maintenance verification", "url": "https://drive.google.com/file/d/seed-augusta-maintenance-verification/view"},
        ],
        "web_link": "https://outlook.office.com/mail/seed-augusta-disposal",
        "status": "linked",
    },
    {
        "legacy_id": "email:northeast-portfolio-request",
        "id": _seed_uuid("email:northeast-portfolio-request"),
        "import_batch_id": _seed_uuid("email_import_batch:work-hub-seed"),
        "target_type": "client",
        "target_legacy_id": "client:northeast-retail-portfolio",
        "provider": "outlook",
        "provider_message_id": "seed-outlook-northeast-portfolio-request",
        "provider_conversation_id": "seed-conv-northeast-portfolio",
        "internet_message_id": "<seed-northeast-portfolio@example>",
        "subject": "Stormwater portfolio service question",
        "sender": "Evan Calder <facilities@northeastretail.example>",
        "recipients_json": [
            {"name": "Sterling Sales", "email": "sales@sterling.example"},
        ],
        "received_at": datetime(2026, 5, 9, 18, 25, tzinfo=UTC),
        "snippet": "Can you summarize what the baseline onboarding visit includes?",
        "body_text": (
            "Can you summarize what the baseline onboarding visit includes? "
            "We are comparing a few vendors for the retail portfolio. "
            "Our SharePoint checklist is https://sterlingstormwater.sharepoint.com/sites/ops/Shared%20Documents/portfolio-checklist.pdf"
        ),
        "body_html": None,
        "attachments_json": [],
        "links_json": [
            {
                "label": "Portfolio checklist",
                "url": "https://sterlingstormwater.sharepoint.com/sites/ops/Shared%20Documents/portfolio-checklist.pdf",
            },
        ],
        "web_link": "https://outlook.office.com/mail/seed-northeast-portfolio",
        "status": "linked",
    },
    {
        "legacy_id": "email:unlinked-ms4-newsletter",
        "id": _seed_uuid("email:unlinked-ms4-newsletter"),
        "import_batch_id": _seed_uuid("email_import_batch:work-hub-seed"),
        "target_type": None,
        "target_legacy_id": None,
        "provider": "outlook",
        "provider_message_id": "seed-outlook-ms4-newsletter",
        "provider_conversation_id": "seed-conv-ms4-newsletter",
        "internet_message_id": "<seed-ms4-newsletter@example>",
        "subject": "MS4 permit newsletter",
        "sender": "Stormwater Bulletin <bulletin@example>",
        "recipients_json": [
            {"name": "Sterling Admin", "email": "admin@sterling.example"},
        ],
        "received_at": datetime(2026, 5, 8, 12, 0, tzinfo=UTC),
        "snippet": "Monthly regulatory newsletter with regional MS4 reminders.",
        "body_text": "Monthly regulatory newsletter with regional MS4 reminders.",
        "body_html": None,
        "attachments_json": [],
        "links_json": [
            {"label": "Regional MS4 notice", "url": "https://example.com/ms4-newsletter"},
        ],
        "web_link": "https://outlook.office.com/mail/seed-ms4-newsletter",
        "status": "unlinked",
    },
]


SEED_EMAIL_RECORD_LINKS: list[dict[str, Any]] = [
    {
        "id": _seed_uuid("email_record_link:bayside-access-window"),
        "email_legacy_id": "email:bayside-access-window",
        "target_type": "job",
        "target_legacy_id": "job:bayside-2026-spring-inspection",
        "link_reason": "Seeded manual Work Hub link",
        "confidence": 1.0,
    },
    {
        "id": _seed_uuid("email_record_link:catch-basin-blocked-structures"),
        "email_legacy_id": "email:catch-basin-blocked-structures",
        "target_type": "job",
        "target_legacy_id": "job:bayside-catch-basin-cleaning",
        "link_reason": "Seeded manual Work Hub link",
        "confidence": 1.0,
    },
    {
        "id": _seed_uuid("email_record_link:northeast-portfolio-request"),
        "email_legacy_id": "email:northeast-portfolio-request",
        "target_type": "client",
        "target_legacy_id": "client:northeast-retail-portfolio",
        "link_reason": "Seeded manual Work Hub link",
        "confidence": 1.0,
    },
]


SEED_AI_DRAFTS: list[dict[str, Any]] = [
    {
        "id": _seed_uuid("ai_draft:bayside-access-reply"),
        "target_type": "job",
        "target_legacy_id": "job:bayside-2026-spring-inspection",
        "email_legacy_id": "email:bayside-access-window",
        "draft_type": "email_reply",
        "title": "Bayside access confirmation reply",
        "prompt_context": "Manual draft tied to the seeded Bayside access email.",
        "draft_text": (
            "Hi Mara,\n\nYes, Sterling can arrive at 6:30 AM for the Bayside BMP inspection. "
            "We will keep the crew focused on the rear gate access route and avoid the retail traffic window.\n\nThanks,\nSterling Stormwater"
        ),
        "status": "draft",
    },
    {
        "id": _seed_uuid("ai_draft:blocked-catch-basin-revisit"),
        "target_type": "job",
        "target_legacy_id": "job:bayside-catch-basin-cleaning",
        "email_legacy_id": "email:catch-basin-blocked-structures",
        "draft_type": "maintenance_recommendation",
        "title": "Blocked catch basin revisit note",
        "prompt_context": "Manual draft for crew/PM follow-up.",
        "draft_text": (
            "We documented CB-4 and CB-7 as blocked by vehicles. "
            "A short return visit after tenant notice should close out the remaining structures."
        ),
        "status": "reviewed",
    },
    {
        "id": _seed_uuid("ai_draft:portfolio-onboarding-summary"),
        "target_type": "client",
        "target_legacy_id": "client:northeast-retail-portfolio",
        "email_legacy_id": "email:northeast-portfolio-request",
        "draft_type": "report_section",
        "title": "Portfolio onboarding visit report section",
        "prompt_context": "Manual local draft; AI generation is intentionally deferred.",
        "draft_text": (
            "The baseline onboarding visit documents BMP inventory, access constraints, drainage concerns, "
            "and report-readiness gaps for each site before recurring work is scheduled."
        ),
        "status": "draft",
    },
]


def seed_counts() -> dict[str, int]:
    return {
        "organizations": 1,
        "clients": len(SEED_CLIENTS),
        "sites": len(SEED_SITES),
        "jobs": len(SEED_JOBS),
        "reminders": len(SEED_REMINDERS),
        "evidence_files": len(SEED_EVIDENCE_FILES),
        "email_import_batches": len(SEED_EMAIL_IMPORT_BATCHES),
        "email_messages": len(SEED_EMAIL_MESSAGES),
        "email_record_links": len(SEED_EMAIL_RECORD_LINKS),
        "ai_drafts": len(SEED_AI_DRAFTS),
    }


def _validate_seed_site_coordinates() -> None:
    for record in SEED_SITES:
        latitude = record.get("latitude")
        longitude = record.get("longitude")
        if latitude is None or longitude is None:
            raise RuntimeError(f"Seed site {record['legacy_id']} is missing map coordinates.")
        if not (Decimal("-90") <= latitude <= Decimal("90")):
            raise RuntimeError(f"Seed site {record['legacy_id']} has an invalid latitude.")
        if not (Decimal("-180") <= longitude <= Decimal("180")):
            raise RuntimeError(f"Seed site {record['legacy_id']} has an invalid longitude.")


def _ensure_organization(session: Session) -> Organization:
    organization = session.get(Organization, DEMO_ORGANIZATION_ID)
    if organization is None:
        organization = Organization(id=DEMO_ORGANIZATION_ID, name=DEMO_ORGANIZATION_NAME)
        session.add(organization)
        session.flush()
    else:
        organization.name = DEMO_ORGANIZATION_NAME
        session.add(organization)
        session.flush()
    return organization


def _find_seed_row(
    session: Session,
    model: type[Client] | type[Site] | type[Job] | type[EvidenceFile],
    legacy_id: str,
) -> Client | Site | Job | EvidenceFile | None:
    return session.scalar(
        select(model).where(
            model.organization_id == DEMO_ORGANIZATION_ID,
            model.legacy_source == LEGACY_SOURCE,
            model.legacy_id == legacy_id,
        ),
    )


def _upsert_seed_row(
    session: Session,
    model: type[Client] | type[Site] | type[Job] | type[EvidenceFile],
    record: dict[str, Any],
    values: dict[str, Any],
) -> Client | Site | Job | EvidenceFile:
    legacy_id = record["legacy_id"]
    instance = _find_seed_row(session, model, legacy_id)
    if instance is None:
        existing_by_id = session.get(model, record["id"])
        if existing_by_id is not None:
            raise RuntimeError(
                f"Refusing to overwrite non-seed {model.__tablename__} row with id {record['id']}.",
            )
        instance = model(
            id=record["id"],
            organization_id=DEMO_ORGANIZATION_ID,
            legacy_source=LEGACY_SOURCE,
            legacy_id=legacy_id,
            **values,
        )
        session.add(instance)
    else:
        for field, value in values.items():
            setattr(instance, field, value)
        instance.archived_at = None
        session.add(instance)

    session.flush()
    return instance


def _client_values(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in record.items()
        if key not in {"id", "legacy_id"}
    }


def _site_values(record: dict[str, Any], client_by_legacy_id: dict[str, Client]) -> dict[str, Any]:
    values = {
        key: value
        for key, value in record.items()
        if key not in {"id", "legacy_id", "client_legacy_id"}
    }
    values["client_id"] = client_by_legacy_id[record["client_legacy_id"]].id
    return values


def _job_values(
    record: dict[str, Any],
    client_by_legacy_id: dict[str, Client],
    site_by_legacy_id: dict[str, Site],
) -> dict[str, Any]:
    values = {
        key: value
        for key, value in record.items()
        if key not in {"id", "legacy_id", "client_legacy_id", "site_legacy_id"}
    }
    values["client_id"] = client_by_legacy_id[record["client_legacy_id"]].id
    values["site_id"] = site_by_legacy_id[record["site_legacy_id"]].id
    return values


def reset_seed(session: Session) -> dict[str, int]:
    deleted: dict[str, int] = {}
    for model, records in (
        (AiDraft, SEED_AI_DRAFTS),
        (EmailRecordLink, SEED_EMAIL_RECORD_LINKS),
        (EmailMessage, SEED_EMAIL_MESSAGES),
        (EmailImportBatch, SEED_EMAIL_IMPORT_BATCHES),
    ):
        result = session.execute(
            delete(model).where(
                model.organization_id == DEMO_ORGANIZATION_ID,
                model.id.in_([record["id"] for record in records]),
            ),
        )
        deleted[model.__tablename__] = result.rowcount or 0

    reminder_result = session.execute(
        delete(Reminder).where(
            Reminder.organization_id == DEMO_ORGANIZATION_ID,
            Reminder.id.in_([record["id"] for record in SEED_REMINDERS]),
        ),
    )
    deleted[Reminder.__tablename__] = reminder_result.rowcount or 0

    for model in (EvidenceFile, Job, Site, Client):
        result = session.execute(
            delete(model).where(
                model.organization_id == DEMO_ORGANIZATION_ID,
                model.legacy_source == LEGACY_SOURCE,
            ),
        )
        deleted[model.__tablename__] = result.rowcount or 0
    session.flush()
    return deleted


def _reminder_values(
    record: dict[str, Any],
    client_by_legacy_id: dict[str, Client],
    site_by_legacy_id: dict[str, Site],
    job_by_legacy_id: dict[str, Job],
) -> dict[str, Any]:
    values = {
        key: value
        for key, value in record.items()
        if key not in {"id", "target_type", "target_legacy_id"}
    }
    target_type = record["target_type"]
    target_legacy_id = record["target_legacy_id"]
    values["client_id"] = None
    values["site_id"] = None
    values["job_id"] = None
    if target_type == "client":
        values["client_id"] = client_by_legacy_id[target_legacy_id].id
    elif target_type == "site":
        values["site_id"] = site_by_legacy_id[target_legacy_id].id
    elif target_type == "job":
        values["job_id"] = job_by_legacy_id[target_legacy_id].id
    else:
        raise RuntimeError(f"Unsupported reminder target_type: {target_type}")
    return values


def _upsert_seed_reminder(
    session: Session,
    record: dict[str, Any],
    values: dict[str, Any],
) -> Reminder:
    instance = session.get(Reminder, record["id"])
    if instance is None:
        instance = Reminder(
            id=record["id"],
            organization_id=DEMO_ORGANIZATION_ID,
            **values,
        )
        session.add(instance)
    else:
        if instance.organization_id != DEMO_ORGANIZATION_ID:
            raise RuntimeError(f"Refusing to overwrite reminder row with id {record['id']}.")
        for field, value in values.items():
            setattr(instance, field, value)
        instance.archived_at = None
        session.add(instance)

    session.flush()
    return instance


def _evidence_file_values(
    record: dict[str, Any],
    client_by_legacy_id: dict[str, Client],
    site_by_legacy_id: dict[str, Site],
    job_by_legacy_id: dict[str, Job],
) -> dict[str, Any]:
    values = {
        key: value
        for key, value in record.items()
        if key
        not in {
            "id",
            "legacy_id",
            "scope",
            "client_legacy_id",
            "site_legacy_id",
            "job_legacy_id",
        }
    }
    client_legacy_id = record.get("client_legacy_id")
    site_legacy_id = record.get("site_legacy_id")
    job_legacy_id = record.get("job_legacy_id")
    values["client_id"] = (
        client_by_legacy_id[client_legacy_id].id if client_legacy_id else None
    )
    values["site_id"] = site_by_legacy_id[site_legacy_id].id if site_legacy_id else None
    values["job_id"] = job_by_legacy_id[job_legacy_id].id if job_legacy_id else None
    return values


def _scope_ids_from_target(
    record: dict[str, Any],
    client_by_legacy_id: dict[str, Client],
    site_by_legacy_id: dict[str, Site],
    job_by_legacy_id: dict[str, Job],
) -> dict[str, uuid.UUID | None]:
    target_type = record.get("target_type")
    target_legacy_id = record.get("target_legacy_id")
    scope: dict[str, uuid.UUID | None] = {
        "client_id": None,
        "site_id": None,
        "job_id": None,
    }
    if target_type is None:
        return scope
    if target_type == "client":
        scope["client_id"] = client_by_legacy_id[target_legacy_id].id
    elif target_type == "site":
        site = site_by_legacy_id[target_legacy_id]
        scope["client_id"] = site.client_id
        scope["site_id"] = site.id
    elif target_type == "job":
        job = job_by_legacy_id[target_legacy_id]
        scope["client_id"] = job.client_id
        scope["site_id"] = job.site_id
        scope["job_id"] = job.id
    else:
        raise RuntimeError(f"Unsupported target_type: {target_type}")
    return scope


def _email_import_batch_values(record: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in record.items()
        if key != "id"
    }


def _upsert_seed_import_batch(
    session: Session,
    record: dict[str, Any],
) -> EmailImportBatch:
    values = _email_import_batch_values(record)
    instance = session.get(EmailImportBatch, record["id"])
    if instance is None:
        instance = EmailImportBatch(
            id=record["id"],
            organization_id=DEMO_ORGANIZATION_ID,
            **values,
        )
        session.add(instance)
    else:
        if instance.organization_id != DEMO_ORGANIZATION_ID:
            raise RuntimeError(f"Refusing to overwrite email import batch row with id {record['id']}.")
        for field, value in values.items():
            setattr(instance, field, value)
        instance.archived_at = None
        session.add(instance)
    session.flush()
    return instance


def _email_message_values(
    record: dict[str, Any],
    client_by_legacy_id: dict[str, Client],
    site_by_legacy_id: dict[str, Site],
    job_by_legacy_id: dict[str, Job],
) -> dict[str, Any]:
    values = {
        key: value
        for key, value in record.items()
        if key not in {"id", "legacy_id", "target_type", "target_legacy_id"}
    }
    values.update(
        _scope_ids_from_target(
            record,
            client_by_legacy_id,
            site_by_legacy_id,
            job_by_legacy_id,
        ),
    )
    return values


def _upsert_seed_email_message(
    session: Session,
    record: dict[str, Any],
    values: dict[str, Any],
) -> EmailMessage:
    instance = session.get(EmailMessage, record["id"])
    if instance is None:
        instance = EmailMessage(
            id=record["id"],
            organization_id=DEMO_ORGANIZATION_ID,
            **values,
        )
        session.add(instance)
    else:
        if instance.organization_id != DEMO_ORGANIZATION_ID:
            raise RuntimeError(f"Refusing to overwrite email message row with id {record['id']}.")
        for field, value in values.items():
            setattr(instance, field, value)
        instance.archived_at = None
        session.add(instance)
    session.flush()
    return instance


def _email_record_link_values(
    record: dict[str, Any],
    email_by_legacy_id: dict[str, EmailMessage],
    client_by_legacy_id: dict[str, Client],
    site_by_legacy_id: dict[str, Site],
    job_by_legacy_id: dict[str, Job],
) -> dict[str, Any]:
    values = {
        key: value
        for key, value in record.items()
        if key not in {"id", "email_legacy_id", "target_type", "target_legacy_id"}
    }
    values["email_message_id"] = email_by_legacy_id[record["email_legacy_id"]].id
    target_scope = _scope_ids_from_target(
        record,
        client_by_legacy_id,
        site_by_legacy_id,
        job_by_legacy_id,
    )
    target_type = record["target_type"]
    values["client_id"] = target_scope["client_id"] if target_type == "client" else None
    values["site_id"] = target_scope["site_id"] if target_type == "site" else None
    values["job_id"] = target_scope["job_id"] if target_type == "job" else None
    return values


def _upsert_seed_email_record_link(
    session: Session,
    record: dict[str, Any],
    values: dict[str, Any],
) -> EmailRecordLink:
    instance = session.get(EmailRecordLink, record["id"])
    if instance is None:
        instance = EmailRecordLink(
            id=record["id"],
            organization_id=DEMO_ORGANIZATION_ID,
            **values,
        )
        session.add(instance)
    else:
        if instance.organization_id != DEMO_ORGANIZATION_ID:
            raise RuntimeError(f"Refusing to overwrite email record link row with id {record['id']}.")
        for field, value in values.items():
            setattr(instance, field, value)
        session.add(instance)
    session.flush()
    return instance


def _ai_draft_values(
    record: dict[str, Any],
    email_by_legacy_id: dict[str, EmailMessage],
    client_by_legacy_id: dict[str, Client],
    site_by_legacy_id: dict[str, Site],
    job_by_legacy_id: dict[str, Job],
) -> dict[str, Any]:
    values = {
        key: value
        for key, value in record.items()
        if key not in {"id", "target_type", "target_legacy_id", "email_legacy_id"}
    }
    values["email_message_id"] = email_by_legacy_id[record["email_legacy_id"]].id
    values.update(
        _scope_ids_from_target(
            record,
            client_by_legacy_id,
            site_by_legacy_id,
            job_by_legacy_id,
        ),
    )
    return values


def _upsert_seed_ai_draft(
    session: Session,
    record: dict[str, Any],
    values: dict[str, Any],
) -> AiDraft:
    instance = session.get(AiDraft, record["id"])
    if instance is None:
        instance = AiDraft(
            id=record["id"],
            organization_id=DEMO_ORGANIZATION_ID,
            **values,
        )
        session.add(instance)
    else:
        if instance.organization_id != DEMO_ORGANIZATION_ID:
            raise RuntimeError(f"Refusing to overwrite AI draft row with id {record['id']}.")
        for field, value in values.items():
            setattr(instance, field, value)
        instance.archived_at = None
        session.add(instance)
    session.flush()
    return instance


def seed(session: Session) -> Organization:
    _validate_seed_site_coordinates()
    organization = _ensure_organization(session)

    client_by_legacy_id: dict[str, Client] = {}
    for record in SEED_CLIENTS:
        client = _upsert_seed_row(session, Client, record, _client_values(record))
        client_by_legacy_id[record["legacy_id"]] = client

    site_by_legacy_id: dict[str, Site] = {}
    for record in SEED_SITES:
        site = _upsert_seed_row(session, Site, record, _site_values(record, client_by_legacy_id))
        site_by_legacy_id[record["legacy_id"]] = site

    job_by_legacy_id: dict[str, Job] = {}
    for record in SEED_JOBS:
        job = _upsert_seed_row(
            session,
            Job,
            record,
            _job_values(record, client_by_legacy_id, site_by_legacy_id),
        )
        job_by_legacy_id[record["legacy_id"]] = job

    for record in SEED_REMINDERS:
        _upsert_seed_reminder(
            session,
            record,
            _reminder_values(
                record,
                client_by_legacy_id,
                site_by_legacy_id,
                job_by_legacy_id,
            ),
        )

    for record in SEED_EVIDENCE_FILES:
        _upsert_seed_row(
            session,
            EvidenceFile,
            record,
            _evidence_file_values(
                record,
                client_by_legacy_id,
                site_by_legacy_id,
                job_by_legacy_id,
            ),
        )

    for record in SEED_EMAIL_IMPORT_BATCHES:
        _upsert_seed_import_batch(session, record)

    email_by_legacy_id: dict[str, EmailMessage] = {}
    for record in SEED_EMAIL_MESSAGES:
        email = _upsert_seed_email_message(
            session,
            record,
            _email_message_values(
                record,
                client_by_legacy_id,
                site_by_legacy_id,
                job_by_legacy_id,
            ),
        )
        email_by_legacy_id[record["legacy_id"]] = email

    for record in SEED_EMAIL_RECORD_LINKS:
        _upsert_seed_email_record_link(
            session,
            record,
            _email_record_link_values(
                record,
                email_by_legacy_id,
                client_by_legacy_id,
                site_by_legacy_id,
                job_by_legacy_id,
            ),
        )

    for record in SEED_AI_DRAFTS:
        _upsert_seed_ai_draft(
            session,
            record,
            _ai_draft_values(
                record,
                email_by_legacy_id,
                client_by_legacy_id,
                site_by_legacy_id,
                job_by_legacy_id,
            ),
        )

    session.commit()
    session.refresh(organization)
    return organization


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed deterministic CRM demo data.")
    parser.add_argument(
        "--reset-seed",
        action="store_true",
        help="Delete only seed_dev CRM rows for the demo organization before reseeding.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    session_factory = get_session_factory()
    with session_factory() as session:
        session.execute(text("select 1"))
        if args.reset_seed:
            deleted = reset_seed(session)
            session.commit()
            print(
                "Deleted seed_dev rows: "
                f"{deleted['clients']} clients, {deleted['sites']} sites, "
                f"{deleted['jobs']} jobs, {deleted['reminders']} reminders, "
                f"{deleted['evidence_files']} files, "
                f"{deleted['email_import_batches']} email batches, "
                f"{deleted['email_messages']} emails, "
                f"{deleted['email_record_links']} email links, "
                f"{deleted['ai_drafts']} AI drafts.",
            )

        organization = seed(session)
        counts = seed_counts()
        print(
            "Seeded demo CRM data: "
            f"{counts['organizations']} organization, {counts['clients']} clients, "
            f"{counts['sites']} sites, {counts['jobs']} jobs, "
            f"{counts['reminders']} reminders, {counts['evidence_files']} files, "
            f"{counts['email_import_batches']} email batch, "
            f"{counts['email_messages']} emails, "
            f"{counts['ai_drafts']} AI drafts.",
        )
        print(f"organization_id={organization.id}")
        print(f"NEXT_PUBLIC_DEMO_ORG_ID={organization.id}")


if __name__ == "__main__":
    main()
