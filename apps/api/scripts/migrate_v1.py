from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import uuid
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


LEGACY_SOURCE = "v1_monday"
REPORT_SCHEMA_VERSION = "m1-dry-run-v2"
EXPECTED_TABLES = (
    "crm_contacts",
    "crm_sites",
    "crm_jobs",
    "crm_leads",
    "crm_communications",
    "crm_report_artifacts",
)
_MIGRATION_UUID_NAMESPACE = uuid.UUID("7be0a39f-5581-461e-8b89-8f9d0bc3d2a4")
_DRIVE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,}$")


@dataclass(frozen=True)
class SourceTable:
    name: str
    columns: list[str]
    rows: list[dict[str, Any]]


@dataclass(frozen=True)
class SourceData:
    path: str
    tables_found: list[str]
    expected_tables: list[str]
    missing_tables: list[str]
    source_row_counts: dict[str, int]
    tables: dict[str, SourceTable]


@dataclass(frozen=True)
class DateParseResult:
    value: str | None
    warning: str | None = None


@dataclass(frozen=True)
class DriveParseResult:
    drive_folder_url: str | None
    drive_folder_id: str | None
    warning: str | None = None


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "null", "nan"}:
        return None
    return re.sub(r"\s+", " ", text)


def _clean_email(value: Any) -> str | None:
    text = _clean(value)
    return text.lower() if text else None


def _clean_phone(value: Any) -> str | None:
    text = _clean(value)
    if not text:
        return None
    return re.sub(r"\s+", " ", text)


def _first(row: dict[str, Any], names: Iterable[str]) -> Any:
    for name in names:
        if name in row and _clean(row.get(name)) is not None:
            return row.get(name)
    return None


def _normalize_key(value: Any) -> str:
    text = _clean(value) or ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "unknown"


def _proposed_uuid(*parts: str) -> str:
    key = ":".join(part for part in parts if part)
    return str(uuid.uuid5(_MIGRATION_UUID_NAMESPACE, key))


def _append_warning(report: dict[str, Any], category: str, warning: dict[str, Any]) -> None:
    report["warnings"].setdefault(category, []).append(warning)


def _warning_count(report: dict[str, Any]) -> int:
    return sum(len(items) for items in report.get("warnings", {}).values())


def parse_v1_date(value: Any) -> DateParseResult:
    text = _clean(value)
    if text is None:
        return DateParseResult(None)

    iso_candidate = text.replace("Z", "+00:00")
    try:
        return DateParseResult(datetime.fromisoformat(iso_candidate).date().isoformat())
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%-m/%-d/%Y", "%m/%d/%y", "%m-%d-%Y", "%-m-%-d-%Y"):
        try:
            return DateParseResult(datetime.strptime(text, fmt).date().isoformat())
        except ValueError:
            continue

    # Windows strptime does not support %-m / %-d. Non-padded dates still parse with %m/%d.
    for fmt in ("%m/%d/%Y", "%m-%d-%Y"):
        try:
            return DateParseResult(datetime.strptime(text, fmt).date().isoformat())
        except ValueError:
            continue

    return DateParseResult(None, "unparseable-date")


def parse_drive_url(value: Any) -> DriveParseResult:
    text = _clean(value)
    if text is None:
        return DriveParseResult(None, None, None)

    parsed = urlparse(text)
    host = parsed.netloc.lower()
    path = parsed.path.rstrip("/")

    if not parsed.scheme or not host:
        return DriveParseResult(text, None, "non-drive-host")

    if host == "docs.google.com" or host.endswith(".docs.google.com"):
        return DriveParseResult(text, None, "looks-like-file-not-folder")

    if host != "drive.google.com" and not host.endswith(".drive.google.com"):
        return DriveParseResult(text, None, "non-drive-host")

    folder_match = re.search(r"/(?:drive/(?:u/\d+/)?)?folders/([^/?#]+)", path)
    if folder_match:
        folder_id = folder_match.group(1)
        cleaned = f"https://drive.google.com/drive/folders/{folder_id}"
        return DriveParseResult(cleaned, folder_id, None)

    file_match = re.search(r"/file/d/([^/?#]+)", path)
    if file_match:
        return DriveParseResult(text, None, "looks-like-file-not-folder")

    query = parse_qs(parsed.query)
    if "id" in query and query["id"]:
        return DriveParseResult(text, None, "open-id-ambiguous")

    return DriveParseResult(text, None, "invalid-drive-url")


def _map_status(
    raw_status: Any,
    *,
    table: str,
    row_key: str,
    scheduled_date: str | None = None,
    completed_date: str | None = None,
    today: date | None = None,
) -> tuple[str, dict[str, Any] | None]:
    raw = (_clean(raw_status) or "").lower()
    today = today or date.today()

    client_statuses = {
        "active": "active",
        "client": "active",
        "current": "active",
        "customer": "active",
        "inactive": "inactive",
        "dormant": "inactive",
        "no contact": "inactive",
        "cold": "inactive",
        "prospect": "prospect",
        "lead": "prospect",
        "pending": "prospect",
        "archived": "archived",
        "dead": "archived",
        "lost": "archived",
        "do not contact": "archived",
        "cancelled": "archived",
        "canceled": "archived",
    }
    site_statuses = {
        "active": "active",
        "in service": "active",
        "current": "active",
        "inactive": "inactive",
        "on hold": "on_hold",
        "paused": "on_hold",
        "dispute": "on_hold",
        "archived": "archived",
        "dead": "archived",
        "closed": "archived",
    }
    job_statuses = {
        "draft": "draft",
        "scheduled": "scheduled",
        "to schedule": "scheduled",
        "pending dispatch": "scheduled",
        "in progress": "in_progress",
        "on site": "in_progress",
        "mobilizing": "in_progress",
        "field": "in_progress",
        "field complete": "in_review",
        "needs review": "in_review",
        "pending report": "in_review",
        "office review": "in_review",
        "qc": "in_review",
        "done": "completed",
        "done!": "completed",
        "complete": "completed",
        "completed": "completed",
        "billed": "completed",
        "invoiced": "completed",
        "archived": "archived",
        "cancelled": "archived",
        "canceled": "archived",
        "dead": "archived",
    }

    if table == "clients":
        mapped = client_statuses.get(raw)
        fallback = "inactive"
    elif table == "sites":
        mapped = site_statuses.get(raw)
        fallback = "inactive"
    elif table == "jobs":
        mapped = job_statuses.get(raw)
        fallback = "draft"
        if not raw:
            if completed_date:
                return "completed", {
                    "table": table,
                    "row_key": row_key,
                    "raw_status": raw_status,
                    "mapped_status": "completed",
                    "reason": "blank-job-status-with-completed-date",
                }
            if scheduled_date:
                try:
                    scheduled = date.fromisoformat(scheduled_date)
                except ValueError:
                    scheduled = None
                if scheduled and scheduled <= today - timedelta(days=548):
                    return "archived", {
                        "table": table,
                        "row_key": row_key,
                        "raw_status": raw_status,
                        "mapped_status": "archived",
                        "reason": "blank-job-status-with-old-schedule",
                    }
            return "draft", {
                "table": table,
                "row_key": row_key,
                "raw_status": raw_status,
                "mapped_status": "draft",
                "reason": "blank-job-status",
            }
    else:
        mapped = None
        fallback = "inactive"

    if mapped:
        return mapped, None

    return fallback, {
        "table": table,
        "row_key": row_key,
        "raw_status": raw_status,
        "mapped_status": fallback,
        "reason": "unknown-status" if raw else "blank-status",
    }


def read_sqlite_source(v1_db: str | Path, expected_tables: Sequence[str] = EXPECTED_TABLES) -> SourceData:
    db_path = Path(v1_db).expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"V1 SQLite database not found: {db_path}")

    uri = f"file:{db_path.as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        conn.row_factory = sqlite3.Row
        table_rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
        ).fetchall()
        tables_found = [str(row["name"]) for row in table_rows]
        found_set = set(tables_found)
        missing_tables = [name for name in expected_tables if name not in found_set]

        tables: dict[str, SourceTable] = {}
        source_row_counts: dict[str, int] = {}
        for table_name in expected_tables:
            if table_name not in found_set:
                source_row_counts[table_name] = 0
                continue
            columns = [
                str(row["name"])
                for row in conn.execute(f'PRAGMA table_info("{table_name}")').fetchall()
            ]
            rows = [
                {column: row[column] for column in columns}
                for row in conn.execute(f'SELECT * FROM "{table_name}"').fetchall()
            ]
            tables[table_name] = SourceTable(table_name, columns, rows)
            source_row_counts[table_name] = len(rows)

    return SourceData(
        path=str(db_path),
        tables_found=tables_found,
        expected_tables=list(expected_tables),
        missing_tables=missing_tables,
        source_row_counts=source_row_counts,
        tables=tables,
    )


def _empty_report(source: SourceData, organization_name: str) -> dict[str, Any]:
    organization_name = _clean(organization_name) or "Sterling Stormwater"
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "mode": "dry_run",
        "source_database": source.path,
        "organization": {
            "name": organization_name,
            "proposed_id": _proposed_uuid("organization", organization_name.lower()),
        },
        "tables_found": source.tables_found,
        "expected_tables": source.expected_tables,
        "missing_tables": source.missing_tables,
        "source_row_counts": source.source_row_counts,
        "planned_counts": {
            "clients": 0,
            "contacts": 0,
            "sites": 0,
            "jobs": 0,
        },
        "planned": {
            "clients": [],
            "contacts": [],
            "sites": [],
            "jobs": [],
        },
        "lookup_maps": {
            "client_legacy_id_to_proposed_id": {},
            "client_name_to_proposed_id": {},
            "site_legacy_id_to_proposed_id": {},
            "job_legacy_id_to_proposed_id": {},
        },
        "warnings": {
            "missing_tables": [],
            "relationship": [],
            "duplicates": [],
            "status_mapping": [],
            "date_parsing": [],
            "drive_urls": [],
            "data_quality": [],
        },
        "orphans": {
            "sites": [],
            "jobs": [],
        },
        "deferred": {
            "leads": source.source_row_counts.get("crm_leads", 0),
            "reports": source.source_row_counts.get("crm_report_artifacts", 0),
            "photos_files": source.source_row_counts.get("crm_report_artifacts", 0),
            "communications": source.source_row_counts.get("crm_communications", 0),
        },
        "diagnostics": {},
        "errors": [],
        "go_no_go": {
            "status": "OK",
            "warning_count": 0,
            "error_count": 0,
            "summary": "Dry-run plan is ready for review.",
        },
    }


def _record_missing_tables(report: dict[str, Any], missing_tables: Sequence[str]) -> None:
    for table_name in missing_tables:
        _append_warning(
            report,
            "missing_tables",
            {
                "table": table_name,
                "reason": "expected-table-missing",
                "message": f"{table_name} was not found; continuing without it.",
            },
        )


def _ensure_synthetic_client(
    report: dict[str, Any],
    clients_by_norm: dict[str, dict[str, Any]],
    *,
    name: str = "Unknown client",
    reason: str,
) -> dict[str, Any]:
    norm = _normalize_key(name)
    existing = clients_by_norm.get(norm)
    if existing:
        return existing

    legacy_id = f"synthetic:client:{norm}"
    proposed = {
        "operation": "would_create",
        "target_table": "clients",
        "proposed_id": _proposed_uuid("client", legacy_id),
        "legacy_source": LEGACY_SOURCE,
        "legacy_id": legacy_id,
        "legacy_source_table": "synthetic",
        "alternate_legacy_ids": [],
        "fields": {
            "client_code": None,
            "name": name,
            "status": "inactive",
            "primary_contact_name": None,
            "email": None,
            "phone": None,
            "billing_address": None,
            "notes": f"Synthetic parent created by M1 dry-run for {reason}.",
            "drive_folder_url": None,
            "drive_folder_id": None,
        },
    }
    clients_by_norm[norm] = proposed
    report["planned"]["clients"].append(proposed)
    report["lookup_maps"]["client_legacy_id_to_proposed_id"][legacy_id] = proposed["proposed_id"]
    report["lookup_maps"]["client_name_to_proposed_id"][norm] = proposed["proposed_id"]
    return proposed


def _build_clients_and_contacts(
    report: dict[str, Any],
    source: SourceData,
) -> dict[str, dict[str, Any]]:
    clients_by_norm: dict[str, dict[str, Any]] = {}
    contacts_seen: set[tuple[str, str, str]] = set()
    contacts_table = source.tables.get("crm_contacts")
    if contacts_table is None:
        return clients_by_norm

    for row_number, row in enumerate(contacts_table.rows, start=1):
        legacy_id = _clean(_first(row, ("client_id", "contact_id", "id")))
        row_key = legacy_id or f"crm_contacts:row:{row_number}"
        account = _clean(_first(row, ("account", "company", "company_name", "client_name", "client")))
        first_name = _clean(row.get("first_name"))
        last_name = _clean(row.get("last_name"))
        full_name = _clean(_first(row, ("contact_name", "name")))
        contact_name = _clean(" ".join(part for part in (first_name, last_name) if part)) or full_name
        email = _clean_email(row.get("email"))
        phone = _clean_phone(row.get("phone"))

        if not legacy_id:
            legacy_id = f"synthetic:contact-row:{row_number}"
            _append_warning(
                report,
                "data_quality",
                {
                    "table": "crm_contacts",
                    "row_key": row_key,
                    "reason": "missing-legacy-id",
                    "synthetic_legacy_id": legacy_id,
                },
            )

        linked_client: dict[str, Any] | None = None
        if account:
            norm_account = _normalize_key(account)
            status, status_warning = _map_status(
                _first(row, ("active_status", "status")),
                table="clients",
                row_key=row_key,
            )
            if status_warning:
                _append_warning(report, "status_mapping", status_warning)

            linked_client = clients_by_norm.get(norm_account)
            if linked_client is None:
                drive = parse_drive_url(_first(row, ("gdrive_url", "drive_folder_url")))
                if drive.warning:
                    _append_warning(
                        report,
                        "drive_urls",
                        {
                            "table": "crm_contacts",
                            "row_key": row_key,
                            "field": "gdrive_url",
                            "raw_value": _first(row, ("gdrive_url", "drive_folder_url")),
                            "warning": drive.warning,
                        },
                    )
                linked_client = {
                    "operation": "would_create",
                    "target_table": "clients",
                    "proposed_id": _proposed_uuid("client", legacy_id),
                    "legacy_source": LEGACY_SOURCE,
                    "legacy_id": legacy_id,
                    "legacy_source_table": "crm_contacts",
                    "alternate_legacy_ids": [],
                    "fields": {
                        "client_code": legacy_id if legacy_id.startswith("SSC-") else None,
                        "name": account,
                        "status": status,
                        "primary_contact_name": contact_name,
                        "email": email,
                        "phone": phone,
                        "billing_address": _clean(row.get("state")),
                        "notes": _clean(row.get("notes")),
                        "drive_folder_url": drive.drive_folder_url,
                        "drive_folder_id": drive.drive_folder_id,
                    },
                }
                clients_by_norm[norm_account] = linked_client
                report["planned"]["clients"].append(linked_client)
                report["lookup_maps"]["client_name_to_proposed_id"][norm_account] = linked_client[
                    "proposed_id"
                ]
            elif legacy_id != linked_client["legacy_id"]:
                if legacy_id not in linked_client["alternate_legacy_ids"]:
                    linked_client["alternate_legacy_ids"].append(legacy_id)
                    _append_warning(
                        report,
                        "duplicates",
                        {
                            "table": "crm_contacts",
                            "row_key": row_key,
                            "reason": "duplicate-client-name",
                            "normalized_name": norm_account,
                            "primary_legacy_id": linked_client["legacy_id"],
                            "alternate_legacy_id": legacy_id,
                        },
                    )
                fields = linked_client["fields"]
                fields["primary_contact_name"] = fields["primary_contact_name"] or contact_name
                fields["email"] = fields["email"] or email
                fields["phone"] = fields["phone"] or phone
                fields["notes"] = fields["notes"] or _clean(row.get("notes"))

            report["lookup_maps"]["client_legacy_id_to_proposed_id"][legacy_id] = linked_client[
                "proposed_id"
            ]
        else:
            _append_warning(
                report,
                "data_quality",
                {
                    "table": "crm_contacts",
                    "row_key": row_key,
                    "reason": "missing-account",
                    "message": "No client proposal was created from this row.",
                },
            )

        if not contact_name:
            if email or phone:
                _append_warning(
                    report,
                    "data_quality",
                    {
                        "table": "crm_contacts",
                        "row_key": row_key,
                        "reason": "missing-contact-name",
                        "email": email,
                    },
                )
            continue

        if not email:
            _append_warning(
                report,
                "data_quality",
                {
                    "table": "crm_contacts",
                    "row_key": row_key,
                    "reason": "missing-contact-email",
                    "contact_name": contact_name,
                },
            )

        dedupe_key = (_normalize_key(contact_name), email or "", phone or "")
        if dedupe_key in contacts_seen:
            _append_warning(
                report,
                "duplicates",
                {
                    "table": "crm_contacts",
                    "row_key": row_key,
                    "reason": "duplicate-contact",
                    "contact_name": contact_name,
                    "email": email,
                },
            )
            continue
        contacts_seen.add(dedupe_key)

        report["planned"]["contacts"].append(
            {
                "operation": "would_create",
                "target_table": "contacts",
                "proposed_id": _proposed_uuid("contact", legacy_id, contact_name, email or ""),
                "legacy_source": LEGACY_SOURCE,
                "legacy_id": legacy_id,
                "legacy_source_table": "crm_contacts",
                "fields": {
                    "client_id": linked_client["proposed_id"] if linked_client else None,
                    "site_id": None,
                    "name": contact_name,
                    "email": email,
                    "phone": phone,
                    "role": (_clean(row.get("managed_by")) or "").lower() or None,
                    "notes": _clean(row.get("notes")),
                },
            },
        )

    return clients_by_norm


def _parse_decimal(value: Any, *, lower: float, upper: float) -> str | None:
    text = _clean(value)
    if text is None:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if number == 0 or not lower <= number <= upper:
        return None
    return f"{number:.6f}"


def _record_drive_warning(
    report: dict[str, Any],
    *,
    table: str,
    row_key: str,
    field: str,
    raw_value: Any,
    warning: str | None,
) -> None:
    if warning:
        _append_warning(
            report,
            "drive_urls",
            {
                "table": table,
                "row_key": row_key,
                "field": field,
                "raw_value": _clean(raw_value),
                "warning": warning,
            },
        )


def _record_date_warning(
    report: dict[str, Any],
    *,
    table: str,
    row_key: str,
    field: str,
    raw_value: Any,
    warning: str | None,
) -> None:
    if warning:
        _append_warning(
            report,
            "date_parsing",
            {
                "table": table,
                "row_key": row_key,
                "field": field,
                "raw_value": _clean(raw_value),
                "warning": warning,
            },
        )


def _build_sites(
    report: dict[str, Any],
    source: SourceData,
    clients_by_norm: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    sites_by_legacy_id: dict[str, dict[str, Any]] = {}
    sites_by_duplicate_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    sites_table = source.tables.get("crm_sites")
    if sites_table is None:
        return sites_by_legacy_id

    for row_number, row in enumerate(sites_table.rows, start=1):
        legacy_id = _clean(_first(row, ("site_id", "id"))) or f"synthetic:site:row:{row_number}"
        row_key = legacy_id
        raw_client_id = _clean(row.get("client_id"))
        client_proposed_id = (
            report["lookup_maps"]["client_legacy_id_to_proposed_id"].get(raw_client_id)
            if raw_client_id
            else None
        )
        if client_proposed_id is None:
            synthetic_client = _ensure_synthetic_client(
                report,
                clients_by_norm,
                reason=f"site {row_key} with missing or unresolved client_id",
            )
            client_proposed_id = synthetic_client["proposed_id"]
            orphan = {
                "table": "crm_sites",
                "row_key": row_key,
                "client_id": raw_client_id,
                "synthetic_client_id": client_proposed_id,
            }
            report["orphans"]["sites"].append(orphan)
            _append_warning(
                report,
                "relationship",
                {
                    **orphan,
                    "reason": "missing-or-unresolved-client-link",
                },
            )

        name = _clean(row.get("name"))
        if not name:
            name = f"Unnamed site ({legacy_id})"
            _append_warning(
                report,
                "data_quality",
                {
                    "table": "crm_sites",
                    "row_key": row_key,
                    "reason": "missing-site-name",
                    "fallback_name": name,
                },
            )
        city = _clean(row.get("city"))
        duplicate_key = (client_proposed_id, _normalize_key(name), _normalize_key(city))
        existing = sites_by_duplicate_key.get(duplicate_key)
        if existing:
            existing["alternate_legacy_ids"].append(legacy_id)
            sites_by_legacy_id[legacy_id] = existing
            report["lookup_maps"]["site_legacy_id_to_proposed_id"][legacy_id] = existing[
                "proposed_id"
            ]
            _append_warning(
                report,
                "duplicates",
                {
                    "table": "crm_sites",
                    "row_key": row_key,
                    "reason": "duplicate-site-name-under-client",
                    "primary_legacy_id": existing["legacy_id"],
                    "alternate_legacy_id": legacy_id,
                    "name": name,
                    "city": city,
                },
            )
            continue

        raw_status = _first(row, ("status", "active_status"))
        status, status_warning = _map_status(raw_status, table="sites", row_key=row_key)
        if status_warning:
            _append_warning(report, "status_mapping", status_warning)

        raw_url = _first(row, ("gdrive_url", "drive_folder_url"))
        drive = parse_drive_url(raw_url)
        _record_drive_warning(
            report,
            table="crm_sites",
            row_key=row_key,
            field="gdrive_url",
            raw_value=raw_url,
            warning=drive.warning,
        )
        explicit_folder_id = _clean(row.get("drive_folder_id"))
        drive_folder_id = explicit_folder_id if explicit_folder_id and _DRIVE_ID_RE.match(explicit_folder_id) else drive.drive_folder_id
        if explicit_folder_id and not _DRIVE_ID_RE.match(explicit_folder_id):
            _append_warning(
                report,
                "drive_urls",
                {
                    "table": "crm_sites",
                    "row_key": row_key,
                    "field": "drive_folder_id",
                    "raw_value": explicit_folder_id,
                    "warning": "invalid-drive-folder-id",
                },
            )

        for field in (
            "last_inspection_date",
            "next_service_date",
            "contract_start",
            "contract_end",
            "submittal_due_date",
        ):
            parsed_date = parse_v1_date(row.get(field))
            _record_date_warning(
                report,
                table="crm_sites",
                row_key=row_key,
                field=field,
                raw_value=row.get(field),
                warning=parsed_date.warning,
            )

        proposed = {
            "operation": "would_create",
            "target_table": "sites",
            "proposed_id": _proposed_uuid("site", legacy_id),
            "legacy_source": LEGACY_SOURCE,
            "legacy_id": legacy_id,
            "legacy_source_table": "crm_sites",
            "alternate_legacy_ids": [],
            "fields": {
                "client_id": client_proposed_id,
                "site_code": legacy_id if legacy_id.startswith("SSW-") else None,
                "name": name,
                "address": _clean(row.get("address")),
                "city": city,
                "state": (_clean(row.get("state")) or "").upper() or None,
                "zip": _clean(row.get("zip")),
                "latitude": _parse_decimal(row.get("lat"), lower=-90, upper=90),
                "longitude": _parse_decimal(row.get("lng"), lower=-180, upper=180),
                "status": status,
                "notes": _clean(row.get("notes")),
                "drive_folder_url": drive.drive_folder_url,
                "drive_folder_id": drive_folder_id,
            },
        }
        sites_by_legacy_id[legacy_id] = proposed
        sites_by_duplicate_key[duplicate_key] = proposed
        report["planned"]["sites"].append(proposed)
        report["lookup_maps"]["site_legacy_id_to_proposed_id"][legacy_id] = proposed[
            "proposed_id"
        ]

        site_contact_name = _clean(_first(row, ("contact", "contact_name")))
        site_email = _clean_email(row.get("email"))
        site_phone = _clean_phone(row.get("phone"))
        if site_contact_name or site_email or site_phone:
            contact_name = site_contact_name or site_email or f"Site contact for {name}"
            report["planned"]["contacts"].append(
                {
                    "operation": "would_create",
                    "target_table": "contacts",
                    "proposed_id": _proposed_uuid("site-contact", legacy_id, contact_name),
                    "legacy_source": LEGACY_SOURCE,
                    "legacy_id": f"{legacy_id}:site-contact",
                    "legacy_source_table": "crm_sites",
                    "fields": {
                        "client_id": client_proposed_id,
                        "site_id": proposed["proposed_id"],
                        "name": contact_name,
                        "email": site_email,
                        "phone": site_phone,
                        "role": "site contact",
                        "notes": None,
                    },
                },
            )

    return sites_by_legacy_id


def _ensure_synthetic_site(
    report: dict[str, Any],
    clients_by_norm: dict[str, dict[str, Any]],
    sites_by_legacy_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    legacy_id = "synthetic:site:unassigned"
    existing = sites_by_legacy_id.get(legacy_id)
    if existing:
        return existing
    synthetic_client = _ensure_synthetic_client(
        report,
        clients_by_norm,
        name="Unknown client",
        reason="orphan jobs",
    )
    proposed = {
        "operation": "would_create",
        "target_table": "sites",
        "proposed_id": _proposed_uuid("site", legacy_id),
        "legacy_source": LEGACY_SOURCE,
        "legacy_id": legacy_id,
        "legacy_source_table": "synthetic",
        "alternate_legacy_ids": [],
        "fields": {
            "client_id": synthetic_client["proposed_id"],
            "site_code": None,
            "name": "Unassigned site",
            "address": None,
            "city": None,
            "state": None,
            "zip": None,
            "latitude": None,
            "longitude": None,
            "status": "inactive",
            "notes": "Synthetic parent created by M1 dry-run for orphan jobs.",
            "drive_folder_url": None,
            "drive_folder_id": None,
        },
    }
    sites_by_legacy_id[legacy_id] = proposed
    report["planned"]["sites"].append(proposed)
    report["lookup_maps"]["site_legacy_id_to_proposed_id"][legacy_id] = proposed["proposed_id"]
    return proposed


def _join_notes(parts: Iterable[tuple[str, Any]]) -> str | None:
    chunks = []
    for label, value in parts:
        text = _clean(value)
        if text:
            chunks.append(f"{label}: {text}")
    return "\n\n---\n\n".join(chunks) or None


def _build_jobs(
    report: dict[str, Any],
    source: SourceData,
    clients_by_norm: dict[str, dict[str, Any]],
    sites_by_legacy_id: dict[str, dict[str, Any]],
) -> None:
    jobs_table = source.tables.get("crm_jobs")
    if jobs_table is None:
        return

    seen_job_legacy_ids: set[str] = set()
    for row_number, row in enumerate(jobs_table.rows, start=1):
        legacy_id = _clean(_first(row, ("job_id", "id"))) or f"synthetic:job:row:{row_number}"
        row_key = legacy_id
        if legacy_id in seen_job_legacy_ids:
            report["errors"].append(
                {
                    "table": "crm_jobs",
                    "row_key": row_key,
                    "reason": "duplicate-job-legacy-id",
                },
            )
            continue
        seen_job_legacy_ids.add(legacy_id)

        raw_site_id = _clean(row.get("site_id"))
        site = sites_by_legacy_id.get(raw_site_id or "")
        if site is None:
            site = _ensure_synthetic_site(report, clients_by_norm, sites_by_legacy_id)
            orphan = {
                "table": "crm_jobs",
                "row_key": row_key,
                "site_id": raw_site_id,
                "synthetic_site_id": site["proposed_id"],
            }
            report["orphans"]["jobs"].append(orphan)
            _append_warning(
                report,
                "relationship",
                {
                    **orphan,
                    "reason": "missing-or-unresolved-site-link",
                },
            )

        site_client_id = site["fields"]["client_id"]
        raw_client_id = _clean(row.get("client_id"))
        explicit_client_id = (
            report["lookup_maps"]["client_legacy_id_to_proposed_id"].get(raw_client_id)
            if raw_client_id
            else None
        )
        if explicit_client_id and explicit_client_id != site_client_id:
            _append_warning(
                report,
                "relationship",
                {
                    "table": "crm_jobs",
                    "row_key": row_key,
                    "reason": "job-client-mismatch-site-client-used",
                    "job_client_id": raw_client_id,
                    "job_client_proposed_id": explicit_client_id,
                    "site_client_proposed_id": site_client_id,
                },
            )
        elif raw_client_id and explicit_client_id is None:
            _append_warning(
                report,
                "relationship",
                {
                    "table": "crm_jobs",
                    "row_key": row_key,
                    "reason": "unresolved-job-client-site-client-used",
                    "job_client_id": raw_client_id,
                    "site_client_proposed_id": site_client_id,
                },
            )

        parsed_scheduled = parse_v1_date(row.get("scheduled_date"))
        parsed_due = parse_v1_date(_first(row, ("internal_due_date", "next_action_date")))
        parsed_completed = parse_v1_date(row.get("completed_date"))
        for field_name, result, raw_value in (
            ("scheduled_date", parsed_scheduled, row.get("scheduled_date")),
            ("due_date", parsed_due, _first(row, ("internal_due_date", "next_action_date"))),
            ("completed_date", parsed_completed, row.get("completed_date")),
        ):
            _record_date_warning(
                report,
                table="crm_jobs",
                row_key=row_key,
                field=field_name,
                raw_value=raw_value,
                warning=result.warning,
            )

        status, status_warning = _map_status(
            row.get("job_status"),
            table="jobs",
            row_key=row_key,
            scheduled_date=parsed_scheduled.value,
            completed_date=parsed_completed.value,
        )
        if status_warning:
            _append_warning(report, "status_mapping", status_warning)

        raw_url = _first(row, ("gdrive_url", "drive_folder_url"))
        drive = parse_drive_url(raw_url)
        _record_drive_warning(
            report,
            table="crm_jobs",
            row_key=row_key,
            field="gdrive_url",
            raw_value=raw_url,
            warning=drive.warning,
        )

        name = _clean(_first(row, ("job_site", "name", "location")))
        service_type = _clean(_first(row, ("service", "service_type"))) or "Other"
        if not name:
            name = f"{service_type} at {site['fields']['name']}"
            _append_warning(
                report,
                "data_quality",
                {
                    "table": "crm_jobs",
                    "row_key": row_key,
                    "reason": "missing-job-name",
                    "fallback_name": name,
                },
            )

        notes = _join_notes(
            (
                ("Notes", row.get("notes")),
                ("Completion notes", row.get("completion_notes")),
                ("Blocked reason", row.get("blocked_reason")),
                ("V1 owner", row.get("owner")),
                ("V1 next action owner", row.get("next_action_owner")),
                ("V1 completed by", row.get("completed_by")),
                ("V1 report id", row.get("report_id")),
            ),
        )
        if raw_client_id and explicit_client_id and explicit_client_id != site_client_id:
            mismatch_note = f"V1 client_id {raw_client_id} disagreed with site client; site client used."
            notes = f"{notes}\n\n---\n\n{mismatch_note}" if notes else mismatch_note

        proposed = {
            "operation": "would_create",
            "target_table": "jobs",
            "proposed_id": _proposed_uuid("job", legacy_id),
            "legacy_source": LEGACY_SOURCE,
            "legacy_id": legacy_id,
            "legacy_source_table": "crm_jobs",
            "fields": {
                "client_id": site_client_id,
                "site_id": site["proposed_id"],
                "job_code": legacy_id if legacy_id.startswith("SSO-") else None,
                "name": name,
                "service_type": service_type,
                "status": status,
                "assigned_to": None,
                "scheduled_date": parsed_scheduled.value,
                "due_date": parsed_due.value,
                "completed_date": parsed_completed.value,
                "scope": _clean(row.get("scope")),
                "notes": notes,
                "drive_folder_url": drive.drive_folder_url,
                "drive_folder_id": drive.drive_folder_id,
            },
        }
        report["planned"]["jobs"].append(proposed)
        report["lookup_maps"]["job_legacy_id_to_proposed_id"][legacy_id] = proposed[
            "proposed_id"
        ]


def build_migration_plan(
    source: SourceData,
    *,
    organization_name: str = "Sterling Stormwater",
    verbose: bool = False,
) -> dict[str, Any]:
    report = _empty_report(source, organization_name)
    report["verbose"] = bool(verbose)
    _record_missing_tables(report, source.missing_tables)
    clients_by_norm = _build_clients_and_contacts(report, source)
    sites_by_legacy_id = _build_sites(report, source, clients_by_norm)
    _build_jobs(report, source, clients_by_norm, sites_by_legacy_id)

    for table_name in ("clients", "contacts", "sites", "jobs"):
        report["planned_counts"][table_name] = len(report["planned"][table_name])

    report["diagnostics"] = _build_diagnostics(source, report)
    report["go_no_go"]["warning_count"] = _warning_count(report)
    report["go_no_go"]["error_count"] = len(report["errors"])
    if report["errors"]:
        report["go_no_go"]["status"] = "NO-GO"
        report["go_no_go"]["summary"] = "Dry-run found structural errors that must be resolved."
    elif report["go_no_go"]["warning_count"]:
        report["go_no_go"]["status"] = "NEEDS REVIEW"
        report["go_no_go"]["summary"] = "Dry-run completed with warnings to review before M2."
    else:
        report["go_no_go"]["status"] = "OK"
        report["go_no_go"]["summary"] = "Dry-run completed without warnings."
    return report


def run_dry_run(
    *,
    v1_db: str | Path,
    organization_name: str = "Sterling Stormwater",
    verbose: bool = False,
) -> dict[str, Any]:
    source = read_sqlite_source(v1_db)
    return build_migration_plan(source, organization_name=organization_name, verbose=verbose)


def _format_count_lines(counts: dict[str, int]) -> list[str]:
    return [f"- {name}: {count}" for name, count in counts.items()]


def _has_any_value(row: dict[str, Any], names: Sequence[str]) -> bool:
    return any(name in row and _clean(row.get(name)) is not None for name in names)


def _norm_or_blank(value: Any) -> str:
    text = _clean(value)
    return _normalize_key(text) if text else ""


def _site_name_prefix(value: Any) -> str:
    text = _clean(value) or ""
    if not text:
        return ""

    for separator in (" - ", " \u2013 ", " \u2014 ", " | ", ": "):
        if separator in text:
            return _clean(text.split(separator, 1)[0]) or ""

    numbered = re.match(r"^(.+?)\s+#?\d+[A-Za-z]?\b", text)
    if numbered:
        return _clean(numbered.group(1)) or ""
    return ""


def _group_size_summary(values: Iterable[str], *, limit: int = 10) -> dict[str, Any]:
    counts = Counter(value for value in values if value)
    repeated_sizes = [count for count in counts.values() if count >= 2]
    return {
        "distinct_values": len(counts),
        "groups_with_2_or_more": len(repeated_sizes),
        "rows_in_groups_with_2_or_more": sum(repeated_sizes),
        "top_group_sizes": sorted(counts.values(), reverse=True)[:limit],
    }


def _count_rows(rows: Sequence[dict[str, Any]], predicate) -> int:
    return sum(1 for row in rows if predicate(row))


def _build_site_diagnostics(source: SourceData, report: dict[str, Any]) -> dict[str, Any]:
    sites_table = source.tables.get("crm_sites")
    site_rows = sites_table.rows if sites_table else []
    client_lookup = report["lookup_maps"]["client_legacy_id_to_proposed_id"]

    rows_by_key: dict[str, dict[str, Any]] = {}
    for row_number, row in enumerate(site_rows, start=1):
        row_key = _clean(_first(row, ("site_id", "id"))) or f"synthetic:site:row:{row_number}"
        rows_by_key[row_key] = row

    def raw_client_id(row: dict[str, Any]) -> str | None:
        return _clean(row.get("client_id"))

    sites_with_client_id = _count_rows(site_rows, lambda row: raw_client_id(row) is not None)
    sites_with_resolvable_client_id = _count_rows(
        site_rows,
        lambda row: bool(raw_client_id(row) and raw_client_id(row) in client_lookup),
    )
    sites_with_unresolved_client_id = _count_rows(
        site_rows,
        lambda row: bool(raw_client_id(row) and raw_client_id(row) not in client_lookup),
    )
    sites_missing_client_id = len(site_rows) - sites_with_client_id
    distinct_client_ids = {raw_client_id(row) for row in site_rows if raw_client_id(row)}
    distinct_unresolved_client_ids = {
        client_id for client_id in distinct_client_ids if client_id not in client_lookup
    }

    possible_client_text_fields = ("account", "client", "client_name", "company", "company_name")
    drive_fields = ("gdrive_url", "drive_folder_url", "drive_folder_id")
    field_presence = {
        "client_id": sites_with_client_id,
        "possible_client_text_field": _count_rows(
            site_rows,
            lambda row: _has_any_value(row, possible_client_text_fields),
        ),
        "managed_by": _count_rows(site_rows, lambda row: _has_any_value(row, ("managed_by",))),
        "contact": _count_rows(site_rows, lambda row: _has_any_value(row, ("contact", "contact_name"))),
        "email": _count_rows(site_rows, lambda row: _has_any_value(row, ("email",))),
        "phone": _count_rows(site_rows, lambda row: _has_any_value(row, ("phone",))),
        "address": _count_rows(site_rows, lambda row: _has_any_value(row, ("address",))),
        "city_state": _count_rows(
            site_rows,
            lambda row: _has_any_value(row, ("city",)) and _has_any_value(row, ("state",)),
        ),
        "systems": _count_rows(site_rows, lambda row: _has_any_value(row, ("systems",))),
        "service_month": _count_rows(site_rows, lambda row: _has_any_value(row, ("service_month",))),
        "status": _count_rows(site_rows, lambda row: _has_any_value(row, ("status", "active_status"))),
        "notes": _count_rows(site_rows, lambda row: _has_any_value(row, ("notes",))),
        "any_drive": _count_rows(site_rows, lambda row: _has_any_value(row, drive_fields)),
        "gdrive_url": _count_rows(site_rows, lambda row: _has_any_value(row, ("gdrive_url",))),
        "drive_folder_url": _count_rows(site_rows, lambda row: _has_any_value(row, ("drive_folder_url",))),
        "drive_folder_id": _count_rows(site_rows, lambda row: _has_any_value(row, ("drive_folder_id",))),
    }

    parsed_drive_folders = 0
    explicit_valid_drive_folder_ids = 0
    drive_warning_counts: Counter[str] = Counter()
    for row in site_rows:
        raw_url = _first(row, ("gdrive_url", "drive_folder_url"))
        parsed = parse_drive_url(raw_url)
        if parsed.drive_folder_id:
            parsed_drive_folders += 1
        if parsed.warning:
            drive_warning_counts[parsed.warning] += 1
        explicit_folder_id = _clean(row.get("drive_folder_id"))
        if explicit_folder_id and _DRIVE_ID_RE.match(explicit_folder_id):
            explicit_valid_drive_folder_ids += 1

    name_counts = Counter(_norm_or_blank(row.get("name")) for row in site_rows if _norm_or_blank(row.get("name")))
    name_address_counts = Counter(
        (_norm_or_blank(row.get("name")), _norm_or_blank(row.get("address")))
        for row in site_rows
        if _norm_or_blank(row.get("name"))
    )

    prefix_values = [_norm_or_blank(_site_name_prefix(row.get("name"))) for row in site_rows]
    managed_by_values = [_norm_or_blank(row.get("managed_by")) for row in site_rows]
    city_state_values = [
        ":".join((_norm_or_blank(row.get("city")), _norm_or_blank(row.get("state"))))
        for row in site_rows
        if _norm_or_blank(row.get("city")) and _norm_or_blank(row.get("state"))
    ]
    prefix_managed_values = [
        ":".join((_norm_or_blank(_site_name_prefix(row.get("name"))), _norm_or_blank(row.get("managed_by"))))
        for row in site_rows
        if _norm_or_blank(_site_name_prefix(row.get("name"))) and _norm_or_blank(row.get("managed_by"))
    ]

    unresolved_samples = []
    for orphan in report["orphans"].get("sites", [])[:10]:
        row_key = orphan.get("row_key")
        row = rows_by_key.get(row_key, {})
        client_id = raw_client_id(row)
        unresolved_samples.append(
            {
                "row_key": row_key,
                "client_id_status": (
                    "missing"
                    if client_id is None
                    else "resolved"
                    if client_id in client_lookup
                    else "unresolved"
                ),
                "has_managed_by": _has_any_value(row, ("managed_by",)),
                "has_site_name_prefix": bool(_site_name_prefix(row.get("name"))),
                "has_city_state": _has_any_value(row, ("city",)) and _has_any_value(row, ("state",)),
                "has_drive": _has_any_value(row, drive_fields),
                "has_systems": _has_any_value(row, ("systems",)),
            },
        )

    return {
        "relationship_counts": {
            "total_sites": len(site_rows),
            "planned_sites": report["planned_counts"].get("sites", len(report["planned"]["sites"])),
            "orphan_site_rows": len(report["orphans"].get("sites", [])),
            "sites_with_client_id": sites_with_client_id,
            "sites_with_resolvable_client_id": sites_with_resolvable_client_id,
            "sites_with_unresolved_client_id": sites_with_unresolved_client_id,
            "sites_missing_client_id": sites_missing_client_id,
            "distinct_nonempty_client_ids": len(distinct_client_ids),
            "distinct_unresolved_client_ids": len(distinct_unresolved_client_ids),
        },
        "field_presence_counts": field_presence,
        "drive_counts": {
            "sites_with_any_drive": field_presence["any_drive"],
            "sites_with_parsed_drive_folder_url": parsed_drive_folders,
            "sites_with_explicit_valid_drive_folder_id": explicit_valid_drive_folder_ids,
            "drive_warning_counts": dict(sorted(drive_warning_counts.items())),
        },
        "duplicate_counts": {
            "exact_site_name_groups": sum(1 for count in name_counts.values() if count >= 2),
            "exact_site_name_rows": sum(count for count in name_counts.values() if count >= 2),
            "exact_site_name_address_groups": sum(1 for count in name_address_counts.values() if count >= 2),
            "exact_site_name_address_rows": sum(count for count in name_address_counts.values() if count >= 2),
            "migration_duplicate_warnings": len(
                [
                    warning
                    for warning in report["warnings"].get("duplicates", [])
                    if warning.get("table") == "crm_sites"
                ],
            ),
        },
        "grouping_clues": {
            "site_name_prefix": _group_size_summary(prefix_values),
            "managed_by": _group_size_summary(managed_by_values),
            "city_state": _group_size_summary(city_state_values),
            "site_name_prefix_plus_managed_by": _group_size_summary(prefix_managed_values),
        },
        "sample_unresolved_sites": unresolved_samples,
    }


def _build_contact_diagnostics(source: SourceData, report: dict[str, Any]) -> dict[str, Any]:
    contacts_table = source.tables.get("crm_contacts")
    contact_rows = contacts_table.rows if contacts_table else []
    planned_clients = report["planned"].get("clients", [])
    planned_contacts = report["planned"].get("contacts", [])

    return {
        "total_contacts": len(contact_rows),
        "contacts_with_client_id": _count_rows(
            contact_rows,
            lambda row: _has_any_value(row, ("client_id", "contact_id", "id")),
        ),
        "contacts_with_account": _count_rows(
            contact_rows,
            lambda row: _has_any_value(row, ("account", "company", "company_name", "client_name", "client")),
        ),
        "contacts_with_sites_managed": _count_rows(
            contact_rows,
            lambda row: _has_any_value(row, ("sites_managed", "site_s_managed")),
        ),
        "contacts_with_email": _count_rows(contact_rows, lambda row: _has_any_value(row, ("email",))),
        "contacts_with_phone": _count_rows(contact_rows, lambda row: _has_any_value(row, ("phone",))),
        "contacts_with_status": _count_rows(
            contact_rows,
            lambda row: _has_any_value(row, ("active_status", "status")),
        ),
        "planned_clients_from_contacts": len(
            [client for client in planned_clients if client.get("legacy_source_table") == "crm_contacts"],
        ),
        "planned_synthetic_clients": len(
            [client for client in planned_clients if client.get("legacy_source_table") == "synthetic"],
        ),
        "planned_contacts": len(planned_contacts),
    }


def _build_report_artifact_diagnostics(source: SourceData, report: dict[str, Any]) -> dict[str, Any]:
    artifacts_table = source.tables.get("crm_report_artifacts")
    artifacts = artifacts_table.rows if artifacts_table else []
    site_rows = source.tables.get("crm_sites").rows if source.tables.get("crm_sites") else []
    job_rows = source.tables.get("crm_jobs").rows if source.tables.get("crm_jobs") else []
    client_lookup = report["lookup_maps"]["client_legacy_id_to_proposed_id"]
    site_ids = {_clean(_first(row, ("site_id", "id"))) for row in site_rows}
    job_ids = {_clean(_first(row, ("job_id", "id"))) for row in job_rows}
    site_ids.discard(None)
    job_ids.discard(None)

    return {
        "total_report_artifacts": len(artifacts),
        "artifacts_with_project_id": _count_rows(
            artifacts,
            lambda row: _has_any_value(row, ("project_id",)),
        ),
        "artifacts_with_site_id": _count_rows(artifacts, lambda row: _has_any_value(row, ("site_id",))),
        "artifacts_with_resolvable_site_id": _count_rows(
            artifacts,
            lambda row: bool(_clean(row.get("site_id")) and _clean(row.get("site_id")) in site_ids),
        ),
        "artifacts_with_client_id": _count_rows(artifacts, lambda row: _has_any_value(row, ("client_id",))),
        "artifacts_with_resolvable_client_id": _count_rows(
            artifacts,
            lambda row: bool(_clean(row.get("client_id")) and _clean(row.get("client_id")) in client_lookup),
        ),
        "artifacts_with_job_id": _count_rows(artifacts, lambda row: _has_any_value(row, ("job_id",))),
        "artifacts_with_resolvable_job_id": _count_rows(
            artifacts,
            lambda row: bool(_clean(row.get("job_id")) and _clean(row.get("job_id")) in job_ids),
        ),
        "artifacts_with_file_path": _count_rows(artifacts, lambda row: _has_any_value(row, ("file_path",))),
        "artifacts_with_drive_folder_id": _count_rows(
            artifacts,
            lambda row: _has_any_value(row, ("drive_folder_id",)),
        ),
        "artifacts_with_drive_web_url": _count_rows(
            artifacts,
            lambda row: _has_any_value(row, ("drive_web_url",)),
        ),
    }


def _build_diagnostics(source: SourceData, report: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_table_counts": source.source_row_counts,
        "warning_counts": {
            category: len(warnings)
            for category, warnings in sorted(report.get("warnings", {}).items())
        },
        "contacts": _build_contact_diagnostics(source, report),
        "sites": _build_site_diagnostics(source, report),
        "report_artifacts": _build_report_artifact_diagnostics(source, report),
    }


def _markdown_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> list[str]:
    if not rows:
        return ["- None"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value) for value in row) + " |")
    return lines


def _format_diagnostic_counts(counts: dict[str, Any]) -> list[str]:
    return _markdown_table(("Metric", "Count"), [(name, value) for name, value in counts.items()])


def _format_grouping_clues(grouping_clues: dict[str, dict[str, Any]]) -> list[str]:
    return _markdown_table(
        ("Signal", "Distinct", "Groups >= 2", "Rows in Groups >= 2", "Top Group Sizes"),
        [
            (
                name,
                summary.get("distinct_values", 0),
                summary.get("groups_with_2_or_more", 0),
                summary.get("rows_in_groups_with_2_or_more", 0),
                ", ".join(str(value) for value in summary.get("top_group_sizes", [])) or "-",
            )
            for name, summary in grouping_clues.items()
        ],
    )


def _warning_lines(report: dict[str, Any], category: str) -> list[str]:
    warnings = report["warnings"].get(category, [])
    if not warnings:
        return ["- None"]
    lines = []
    for warning in warnings:
        row_key = warning.get("row_key") or warning.get("table") or "n/a"
        reason = warning.get("reason") or warning.get("warning") or "warning"
        detail = warning.get("message") or warning.get("raw_value") or warning.get("name") or ""
        suffix = f" - {detail}" if detail else ""
        lines.append(f"- {row_key}: {reason}{suffix}")
    return lines


def render_markdown_report(report: dict[str, Any]) -> str:
    deferred = report["deferred"]
    diagnostics = report.get("diagnostics", {})
    contact_diagnostics = diagnostics.get("contacts", {})
    site_diagnostics = diagnostics.get("sites", {})
    report_artifact_diagnostics = diagnostics.get("report_artifacts", {})
    sections = [
        "# V1 to V2 Migration M1 Dry-Run Report",
        "",
        "## 1. Source Database Path",
        f"`{report['source_database']}`",
        "",
        "## 2. Tables Found",
        *[f"- {name}" for name in report["tables_found"]],
        "",
        "## 3. Source Row Counts",
        *_format_count_lines(report["source_row_counts"]),
        "",
        "## 4. Diagnostic Summary",
        "### Contact Client Clues",
        *_format_diagnostic_counts(contact_diagnostics),
        "",
        "### Site Client Relationship Counts",
        *_format_diagnostic_counts(site_diagnostics.get("relationship_counts", {})),
        "",
        "### Site Field Presence Counts",
        *_format_diagnostic_counts(site_diagnostics.get("field_presence_counts", {})),
        "",
        "### Site Drive Counts",
        *_format_diagnostic_counts(site_diagnostics.get("drive_counts", {})),
        "",
        "### Site Duplicate Counts",
        *_format_diagnostic_counts(site_diagnostics.get("duplicate_counts", {})),
        "",
        "### Site Grouping Clues",
        *_format_grouping_clues(site_diagnostics.get("grouping_clues", {})),
        "",
        "### Report Artifact Linkage Counts",
        *_format_diagnostic_counts(report_artifact_diagnostics),
        "",
        "### Warning Counts",
        *_format_diagnostic_counts(diagnostics.get("warning_counts", {})),
        "",
        "### Sanitized Unresolved Site Samples",
        *_markdown_table(
            (
                "Row",
                "Client ID",
                "Managed By",
                "Prefix",
                "City/State",
                "Drive",
                "Systems",
            ),
            [
                (
                    sample.get("row_key"),
                    sample.get("client_id_status"),
                    sample.get("has_managed_by"),
                    sample.get("has_site_name_prefix"),
                    sample.get("has_city_state"),
                    sample.get("has_drive"),
                    sample.get("has_systems"),
                )
                for sample in site_diagnostics.get("sample_unresolved_sites", [])
            ],
        ),
        "",
        "## 5. Planned Clients",
        f"- Would create/update: {report['planned_counts']['clients']}",
        "",
        "## 6. Planned Contacts",
        f"- Would create/update: {report['planned_counts']['contacts']}",
        "",
        "## 7. Planned Sites",
        f"- Would create/update: {report['planned_counts']['sites']}",
        "",
        "## 8. Planned Jobs",
        f"- Would create/update: {report['planned_counts']['jobs']}",
        "",
        "## 9. Relationship Warnings",
        *_warning_lines(report, "relationship"),
        "",
        "## 10. Duplicate Warnings",
        *_warning_lines(report, "duplicates"),
        "",
        "## 11. Status Mapping Warnings",
        *_warning_lines(report, "status_mapping"),
        "",
        "## 12. Date Parsing Warnings",
        *_warning_lines(report, "date_parsing"),
        "",
        "## 13. Drive URL Warnings",
        *_warning_lines(report, "drive_urls"),
        "",
        "## 14. Orphan Records",
        f"- Sites: {len(report['orphans']['sites'])}",
        f"- Jobs: {len(report['orphans']['jobs'])}",
        "",
        "## 15. Deferred Records",
        f"- Leads: {deferred['leads']}",
        f"- Reports: {deferred['reports']}",
        f"- Photos/files: {deferred['photos_files']}",
        f"- Communications: {deferred['communications']}",
        "",
        "## 16. Final Go/No-Go Summary",
        f"- Status: {report['go_no_go']['status']}",
        f"- Warnings: {report['go_no_go']['warning_count']}",
        f"- Errors: {report['go_no_go']['error_count']}",
        f"- Summary: {report['go_no_go']['summary']}",
        "",
        "## Safety",
        "- M1 is dry-run only.",
        "- No V2 database connection is opened.",
        "- No V2 Postgres writes are performed.",
        "- `--apply` is intentionally blocked until M2.",
        "",
    ]
    return "\n".join(sections)


def render_text_report(report: dict[str, Any]) -> str:
    return render_markdown_report(report)


def write_report_outputs(
    report: dict[str, Any],
    *,
    output_json: str | Path | None = None,
    output_md: str | Path | None = None,
) -> None:
    if output_json:
        path = Path(output_json)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if output_md:
        path = Path(output_md)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_markdown_report(report), encoding="utf-8")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a dry-run V1 SQLite CRM to V2 CRM migration plan.",
    )
    parser.add_argument("--v1-db", required=True, help="Path to the V1 SQLite database.")
    parser.add_argument(
        "--organization-name",
        default="Sterling Stormwater",
        help="Target organization display name for proposed mappings.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Dry-run mode. This is the default and the only M1 behavior.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Accepted for future M2 use; exits as not implemented in M1.",
    )
    parser.add_argument("--verbose", action="store_true", help="Include verbose report metadata.")
    parser.add_argument("--output-json", help="Optional path for structured JSON report.")
    parser.add_argument("--output-md", help="Optional path for markdown report.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.apply:
        print(
            "--apply is not implemented in Phase M1. Re-run without --apply for a dry-run report.",
            file=sys.stderr,
        )
        return 2

    try:
        report = run_dry_run(
            v1_db=args.v1_db,
            organization_name=args.organization_name,
            verbose=args.verbose,
        )
        write_report_outputs(
            report,
            output_json=args.output_json,
            output_md=args.output_md,
        )
        print(render_text_report(report))
    except Exception as error:
        print(f"V1 migration dry-run failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
