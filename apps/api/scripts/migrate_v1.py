from __future__ import annotations

import argparse
import csv
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
CLIENT_ALIAS_EXPECTED_COLUMNS = (
    "source_value",
    "source_field",
    "target_client_name",
    "target_client_status",
    "notes",
)
CLIENT_ALIAS_REQUIRED_COLUMNS = ("source_value", "source_field", "target_client_name")
CLIENT_ALIAS_SOURCE_FIELDS = (
    "site_name_exact",
    "site_name_prefix",
    "site_name_contains",
    "managed_by",
    "drive_parent_folder",
    "account",
    "client_id",
)
CLIENT_ALIAS_PRIORITY = {
    "client_id": 2,
    "account": 3,
    "managed_by": 4,
    "site_name_exact": 5,
    "site_name_prefix": 6,
    "site_name_contains": 7,
    "drive_parent_folder": 8,
}
CLIENT_ALIAS_CLIENT_STATUSES = {"active", "inactive", "prospect", "archived"}
ACCOUNT_FIELD_NAMES = ("account", "client", "client_name", "company", "company_name")
DRIVE_PARENT_FIELD_NAMES = (
    "drive_parent_folder",
    "drive_parent_folder_name",
    "drive_parent_folder_path",
    "drive_parent_folder_id",
    "drive_parent_folder_url",
    "parent_drive_folder",
    "parent_folder",
    "parent_folder_name",
    "parent_folder_id",
    "parent_folder_url",
)
UNRESOLVED_SITE_SAMPLE_LIMIT = 10
TOP_UNRESOLVED_PREFIX_LIMIT = 10
ALIAS_DRAFT_SAMPLE_LIMIT = 5
ALIAS_DRAFT_ROW_LIMIT = 200
M2_UNRESOLVED_SITE_THRESHOLD = 0
ALIAS_DRAFT_COLUMNS = (
    "source_value",
    "source_field",
    "target_client_name",
    "target_client_status",
    "notes",
    "review_status",
    "match_count",
    "sample_site_names",
    "sample_row_keys",
)


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


@dataclass(frozen=True)
class ClientAlias:
    row_number: int
    source_value: str
    normalized_source_value: str
    source_field: str
    target_client_name: str
    target_client_status: str
    notes: str | None = None


@dataclass(frozen=True)
class ClientAliasConfig:
    path: str | None
    aliases: list[ClientAlias]
    summary: dict[str, Any]
    warnings: list[dict[str, Any]]


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


def _append_alias_warning(report: dict[str, Any], warning: dict[str, Any]) -> None:
    report.setdefault("alias_warnings", []).append(warning)
    _append_warning(report, "client_aliases", warning)


def _site_columns(source: SourceData) -> set[str]:
    table = source.tables.get("crm_sites")
    return set(table.columns) if table else set()


def _supportable_alias_source_fields(source: SourceData) -> list[str]:
    columns = _site_columns(source)
    supported = []
    if "client_id" in columns:
        supported.append("client_id")
    if any(name in columns for name in ACCOUNT_FIELD_NAMES):
        supported.append("account")
    if "managed_by" in columns:
        supported.append("managed_by")
    if "name" in columns:
        supported.extend(("site_name_exact", "site_name_prefix", "site_name_contains"))
    if any(name in columns for name in DRIVE_PARENT_FIELD_NAMES):
        supported.append("drive_parent_folder")
    return [field for field in CLIENT_ALIAS_SOURCE_FIELDS if field in set(supported)]


def _empty_client_alias_config(source: SourceData, path: str | Path | None = None) -> ClientAliasConfig:
    supported_fields = _supportable_alias_source_fields(source)
    return ClientAliasConfig(
        path=str(Path(path).expanduser().resolve()) if path else None,
        aliases=[],
        summary={
            "file_path": str(Path(path).expanduser().resolve()) if path else None,
            "provided": path is not None,
            "rows_loaded": 0,
            "rows_valid": 0,
            "rows_invalid": 0,
            "blank_required_field_rows": 0,
            "unknown_source_field_rows": 0,
            "unsupported_source_field_rows": 0,
            "duplicate_alias_rows": 0,
            "aliases_matching_no_v1_sites": 0,
            "aliases_matching_multiple_client_proposals": 0,
            "aliases_creating_new_client_proposals": 0,
            "supported_source_fields": supported_fields,
            "unsupported_source_fields": [
                field for field in CLIENT_ALIAS_SOURCE_FIELDS if field not in supported_fields
            ],
        },
        warnings=[],
    )


def read_client_aliases(path: str | Path, source: SourceData) -> ClientAliasConfig:
    alias_path = Path(path).expanduser().resolve()
    if not alias_path.exists():
        raise FileNotFoundError(f"Client alias mapping file not found: {alias_path}")
    if not alias_path.is_file():
        raise FileNotFoundError(f"Client alias mapping path is not a file: {alias_path}")

    supported_fields = set(_supportable_alias_source_fields(source))
    warnings: list[dict[str, Any]] = []
    aliases: list[ClientAlias] = []
    rows_loaded = 0
    rows_invalid = 0
    unsupported_rows = 0
    unknown_source_field_rows = 0
    blank_required_field_rows = 0
    duplicate_alias_rows = 0
    seen_alias_keys: dict[tuple[str, str], int] = {}

    with alias_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = tuple(reader.fieldnames or ())
        missing_required = [name for name in CLIENT_ALIAS_REQUIRED_COLUMNS if name not in fieldnames]
        if missing_required:
            raise ValueError(
                "Client alias mapping file is missing required columns: "
                + ", ".join(missing_required),
            )

        for optional_column in (
            name for name in CLIENT_ALIAS_EXPECTED_COLUMNS if name not in fieldnames
        ):
            warnings.append(
                {
                    "table": "client_aliases",
                    "row_key": str(alias_path),
                    "reason": "missing-optional-column",
                    "column": optional_column,
                    "message": f"{optional_column} column is absent; default behavior will be used.",
                },
            )

        for row_number, row in enumerate(reader, start=2):
            cleaned = {key: _clean(value) for key, value in row.items() if key is not None}
            if not any(cleaned.get(name) for name in CLIENT_ALIAS_EXPECTED_COLUMNS):
                continue

            rows_loaded += 1
            source_value = cleaned.get("source_value")
            source_field = (cleaned.get("source_field") or "").lower()
            target_client_name = cleaned.get("target_client_name")
            missing_values = [
                name
                for name, value in (
                    ("source_value", source_value),
                    ("source_field", source_field),
                    ("target_client_name", target_client_name),
                )
                if not value
            ]
            if missing_values:
                rows_invalid += 1
                blank_required_field_rows += 1
                warnings.append(
                    {
                        "table": "client_aliases",
                        "row_key": f"row:{row_number}",
                        "reason": "invalid-alias-row",
                        "missing_columns": missing_values,
                    },
                )
                continue

            if source_field not in CLIENT_ALIAS_SOURCE_FIELDS:
                rows_invalid += 1
                unknown_source_field_rows += 1
                warnings.append(
                    {
                        "table": "client_aliases",
                        "row_key": f"row:{row_number}",
                        "reason": "unknown-source-field",
                        "source_field": source_field,
                        "supported_source_fields": list(CLIENT_ALIAS_SOURCE_FIELDS),
                    },
                )
                continue

            if source_field not in supported_fields:
                rows_invalid += 1
                unsupported_rows += 1
                warnings.append(
                    {
                        "table": "client_aliases",
                        "row_key": f"row:{row_number}",
                        "reason": "unsupported-source-field",
                        "source_field": source_field,
                        "message": (
                            f"{source_field} is recognized but cannot be resolved from the "
                            "available crm_sites columns in this V1 database."
                        ),
                    },
                )
                continue

            alias_key = (source_field, _normalize_key(source_value))
            first_row_number = seen_alias_keys.get(alias_key)
            if first_row_number is not None:
                rows_invalid += 1
                duplicate_alias_rows += 1
                warnings.append(
                    {
                        "table": "client_aliases",
                        "row_key": f"row:{row_number}",
                        "reason": "duplicate-alias-row",
                        "source_field": source_field,
                        "source_value": source_value,
                        "first_row": first_row_number,
                    },
                )
                continue
            seen_alias_keys[alias_key] = row_number

            raw_status = (cleaned.get("target_client_status") or "").lower()
            if raw_status in CLIENT_ALIAS_CLIENT_STATUSES:
                target_status = raw_status
            else:
                target_status = "active"
                warnings.append(
                    {
                        "table": "client_aliases",
                        "row_key": f"row:{row_number}",
                        "reason": "invalid-target-client-status",
                        "raw_status": cleaned.get("target_client_status"),
                        "mapped_status": target_status,
                        "message": "target_client_status must be active, inactive, prospect, or archived.",
                    },
                )

            aliases.append(
                ClientAlias(
                    row_number=row_number,
                    source_value=source_value,
                    normalized_source_value=_normalize_key(source_value),
                    source_field=source_field,
                    target_client_name=target_client_name,
                    target_client_status=target_status,
                    notes=cleaned.get("notes"),
                ),
            )

    return ClientAliasConfig(
        path=str(alias_path),
        aliases=aliases,
        summary={
            "file_path": str(alias_path),
            "provided": True,
            "rows_loaded": rows_loaded,
            "rows_valid": len(aliases),
            "rows_invalid": rows_invalid,
            "blank_required_field_rows": blank_required_field_rows,
            "unknown_source_field_rows": unknown_source_field_rows,
            "unsupported_source_field_rows": unsupported_rows,
            "duplicate_alias_rows": duplicate_alias_rows,
            "aliases_matching_no_v1_sites": 0,
            "aliases_matching_multiple_client_proposals": 0,
            "aliases_creating_new_client_proposals": 0,
            "supported_source_fields": _supportable_alias_source_fields(source),
            "unsupported_source_fields": [
                field for field in CLIENT_ALIAS_SOURCE_FIELDS if field not in supported_fields
            ],
        },
        warnings=warnings,
    )


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
            "client_aliases": [],
        },
        "alias_summary": {},
        "alias_warnings": [],
        "alias_draft_recommendations": [],
        "client_resolution_summary": {},
        "unresolved_site_samples": [],
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
        "m2_apply_gate": {
            "safe_to_proceed": False,
            "unresolved_site_threshold": M2_UNRESOLVED_SITE_THRESHOLD,
            "reasons": ["--apply is intentionally blocked until M2."],
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


def _client_alias_provenance(alias: ClientAlias) -> dict[str, Any]:
    return {
        "alias_row_number": alias.row_number,
        "source_field": alias.source_field,
        "source_value": alias.source_value,
        "target_client_name": alias.target_client_name,
        "target_client_status": alias.target_client_status,
        "notes": alias.notes,
    }


def _ensure_alias_client(
    report: dict[str, Any],
    clients_by_norm: dict[str, dict[str, Any]],
    alias: ClientAlias,
) -> dict[str, Any]:
    norm = _normalize_key(alias.target_client_name)
    provenance = _client_alias_provenance(alias)
    existing = clients_by_norm.get(norm)
    if existing:
        existing_aliases = existing.setdefault("client_aliases", [])
        if provenance not in existing_aliases:
            existing_aliases.append(provenance)
        existing_status = existing.get("fields", {}).get("status")
        if (
            existing.get("legacy_source_table") == "client_aliases"
            and existing_status
            and existing_status != alias.target_client_status
        ):
            _append_alias_warning(
                report,
                {
                    "table": "client_aliases",
                    "row_key": f"row:{alias.row_number}",
                    "reason": "target-client-status-conflict",
                    "target_client_name": alias.target_client_name,
                    "kept_status": existing_status,
                    "ignored_status": alias.target_client_status,
                },
            )
        return existing

    legacy_id = f"synthetic:client:{norm}"
    notes = "Proposed by M1.6 client alias mapping."
    if alias.notes:
        notes = f"{notes}\n\nAlias notes: {alias.notes}"
    proposed = {
        "operation": "would_create",
        "target_table": "clients",
        "proposed_id": _proposed_uuid("client", legacy_id),
        "legacy_source": LEGACY_SOURCE,
        "legacy_id": legacy_id,
        "legacy_source_table": "client_aliases",
        "alternate_legacy_ids": [],
        "client_aliases": [provenance],
        "fields": {
            "client_code": None,
            "name": alias.target_client_name,
            "status": alias.target_client_status,
            "primary_contact_name": None,
            "email": None,
            "phone": None,
            "billing_address": None,
            "notes": notes,
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


def _values_for_fields(row: dict[str, Any], fields: Sequence[str]) -> list[str]:
    values: list[str] = []
    for field in fields:
        value = _clean(row.get(field))
        if value:
            values.append(value)
    return values


def _drive_parent_values(row: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for value in _values_for_fields(row, DRIVE_PARENT_FIELD_NAMES):
        values.append(value)
        parsed = parse_drive_url(value)
        if parsed.drive_folder_id:
            values.append(parsed.drive_folder_id)
        if parsed.drive_folder_url:
            values.append(parsed.drive_folder_url)
    return values


def _alias_value_match(alias: ClientAlias, candidate: Any) -> bool:
    candidate_text = _clean(candidate)
    return bool(candidate_text and _normalize_key(candidate_text) == alias.normalized_source_value)


def _site_name_value(row: dict[str, Any]) -> str | None:
    return _clean(_first(row, ("name", "site_name")))


def _site_name_prefix_matches(alias: ClientAlias, site_name: str | None) -> bool:
    if not site_name:
        return False
    site_norm = _normalize_key(site_name)
    prefix = _site_name_prefix(site_name)
    prefix_norm = _normalize_key(prefix) if prefix else ""
    return (
        prefix_norm == alias.normalized_source_value
        or site_norm == alias.normalized_source_value
        or site_norm.startswith(f"{alias.normalized_source_value}-")
    )


def _site_alias_match_value(alias: ClientAlias, row: dict[str, Any]) -> str | None:
    site_name = _site_name_value(row)

    if alias.source_field == "site_name_exact":
        return site_name if _alias_value_match(alias, site_name) else None

    if alias.source_field == "site_name_prefix":
        if _site_name_prefix_matches(alias, site_name):
            return _site_name_prefix(site_name) or site_name
        return None

    if alias.source_field == "site_name_contains":
        site_norm = _normalize_key(site_name) if site_name else ""
        return site_name if alias.normalized_source_value in site_norm else None

    field_values: list[str]
    if alias.source_field == "client_id":
        field_values = _values_for_fields(row, ("client_id",))
    elif alias.source_field == "account":
        field_values = _values_for_fields(row, ACCOUNT_FIELD_NAMES)
    elif alias.source_field == "managed_by":
        field_values = _values_for_fields(row, ("managed_by",))
    elif alias.source_field == "drive_parent_folder":
        field_values = _drive_parent_values(row)
    else:
        field_values = []

    for value in field_values:
        if _alias_value_match(alias, value):
            return value
    return None


def _site_alias_matches(
    row: dict[str, Any],
    alias_config: ClientAliasConfig,
) -> list[tuple[ClientAlias, str]]:
    matches = []
    for alias in alias_config.aliases:
        matched_value = _site_alias_match_value(alias, row)
        if matched_value:
            matches.append((alias, matched_value))
    return sorted(
        matches,
        key=lambda item: (CLIENT_ALIAS_PRIORITY[item[0].source_field], item[0].row_number),
    )


def _resolve_site_client(
    report: dict[str, Any],
    row: dict[str, Any],
    row_key: str,
    clients_by_norm: dict[str, dict[str, Any]],
    alias_config: ClientAliasConfig,
) -> dict[str, Any]:
    raw_client_id = _clean(row.get("client_id"))
    direct_client_id = (
        report["lookup_maps"]["client_legacy_id_to_proposed_id"].get(raw_client_id)
        if raw_client_id
        else None
    )
    if direct_client_id:
        return {
            "client_proposed_id": direct_client_id,
            "method": "direct_client_id",
            "source_field": "client_id",
            "source_value": raw_client_id,
            "matched_value": raw_client_id,
            "target_client_name": None,
            "alias_row_number": None,
            "warning": None,
        }

    alias_matches = _site_alias_matches(row, alias_config)
    if alias_matches:
        chosen_alias, matched_value = alias_matches[0]
        warning_reason = None
        if len(alias_matches) > 1:
            warning_reason = "multiple-alias-matches"
            _append_alias_warning(
                report,
                {
                    "table": "crm_sites",
                    "row_key": row_key,
                    "reason": warning_reason,
                    "selected_alias_row": chosen_alias.row_number,
                    "selected_source_field": chosen_alias.source_field,
                    "selected_source_value": chosen_alias.source_value,
                    "selected_target_client_name": chosen_alias.target_client_name,
                    "matched_alias_count": len(alias_matches),
                    "matched_aliases": [
                        {
                            "alias_row_number": alias.row_number,
                            "source_field": alias.source_field,
                            "source_value": alias.source_value,
                            "target_client_name": alias.target_client_name,
                        }
                        for alias, _ in alias_matches[:10]
                    ],
                },
            )

        client = _ensure_alias_client(report, clients_by_norm, chosen_alias)
        return {
            "client_proposed_id": client["proposed_id"],
            "method": f"alias_{chosen_alias.source_field}",
            "source_field": chosen_alias.source_field,
            "source_value": chosen_alias.source_value,
            "matched_value": matched_value,
            "target_client_name": chosen_alias.target_client_name,
            "alias_row_number": chosen_alias.row_number,
            "warning": warning_reason,
        }

    return {
        "client_proposed_id": None,
        "method": "synthetic_unresolved_client",
        "source_field": "client_id",
        "source_value": raw_client_id,
        "matched_value": raw_client_id,
        "target_client_name": "Unknown client",
        "alias_row_number": None,
        "warning": "missing-or-unresolved-client-link",
    }


def _build_sites(
    report: dict[str, Any],
    source: SourceData,
    clients_by_norm: dict[str, dict[str, Any]],
    alias_config: ClientAliasConfig,
) -> dict[str, dict[str, Any]]:
    sites_by_legacy_id: dict[str, dict[str, Any]] = {}
    sites_by_duplicate_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    sites_table = source.tables.get("crm_sites")
    if sites_table is None:
        return sites_by_legacy_id

    for row_number, row in enumerate(sites_table.rows, start=1):
        legacy_id = _clean(_first(row, ("site_id", "id"))) or f"synthetic:site:row:{row_number}"
        row_key = legacy_id
        resolution = _resolve_site_client(report, row, row_key, clients_by_norm, alias_config)
        client_proposed_id = resolution["client_proposed_id"]
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
                "client_id": resolution["source_value"],
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
        resolution_record = {
            "table": "crm_sites",
            "row_key": row_key,
            "site_name": name,
            "site_name_prefix": _site_name_prefix(name),
            "managed_by": _clean(row.get("managed_by")),
            "account": _clean(_first(row, ACCOUNT_FIELD_NAMES)),
            "drive_parent_folder": next(iter(_drive_parent_values(row)), None),
            "has_drive": _has_any_value(row, ("gdrive_url", "drive_folder_url", "drive_folder_id")),
            "client_proposed_id": client_proposed_id,
            "client_resolution_method": resolution["method"],
            "client_resolution_source_value": resolution["source_value"],
            "client_resolution_warning": resolution["warning"],
            "client_resolution": {
                "method": resolution["method"],
                "source_field": resolution["source_field"],
                "source_value": resolution["source_value"],
                "matched_value": resolution["matched_value"],
                "target_client_name": resolution["target_client_name"],
                "alias_row_number": resolution["alias_row_number"],
                "warning": resolution["warning"],
            },
        }
        report.setdefault("_client_resolution_rows", []).append(resolution_record)
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
            "client_resolution_method": resolution["method"],
            "client_resolution_source_value": resolution["source_value"],
            "client_resolution": resolution_record["client_resolution"],
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
        if resolution["warning"]:
            proposed["client_resolution_warning"] = resolution["warning"]
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
    client_aliases: str | Path | None = None,
) -> dict[str, Any]:
    report = _empty_report(source, organization_name)
    report["verbose"] = bool(verbose)
    alias_config = (
        read_client_aliases(client_aliases, source)
        if client_aliases
        else _empty_client_alias_config(source)
    )
    report["alias_summary"] = alias_config.summary
    for warning in alias_config.warnings:
        _append_alias_warning(report, warning)
    _record_missing_tables(report, source.missing_tables)
    clients_by_norm = _build_clients_and_contacts(report, source)
    sites_by_legacy_id = _build_sites(report, source, clients_by_norm, alias_config)
    _build_jobs(report, source, clients_by_norm, sites_by_legacy_id)

    for table_name in ("clients", "contacts", "sites", "jobs"):
        report["planned_counts"][table_name] = len(report["planned"][table_name])

    report["alias_summary"] = _build_alias_validation_summary(source, report, alias_config)
    report["client_resolution_summary"] = _build_client_resolution_summary(report)
    report["unresolved_site_samples"] = _build_unresolved_site_samples(report)
    report["alias_draft_recommendations"] = _build_alias_draft_recommendations(report)
    report["diagnostics"] = _build_diagnostics(source, report)
    report.pop("_client_resolution_rows", None)
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
    report["m2_apply_gate"] = _build_m2_apply_gate(report)
    return report


def run_dry_run(
    *,
    v1_db: str | Path,
    organization_name: str = "Sterling Stormwater",
    verbose: bool = False,
    client_aliases: str | Path | None = None,
) -> dict[str, Any]:
    source = read_sqlite_source(v1_db)
    return build_migration_plan(
        source,
        organization_name=organization_name,
        verbose=verbose,
        client_aliases=client_aliases,
    )


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


def _client_resolution_rows(report: dict[str, Any]) -> list[dict[str, Any]]:
    return list(report.get("_client_resolution_rows", []))


def _build_unresolved_site_samples(report: dict[str, Any]) -> list[dict[str, Any]]:
    samples = []
    for row in _client_resolution_rows(report):
        if row.get("client_resolution_method") != "synthetic_unresolved_client":
            continue
        samples.append(
            {
                "row_key": row.get("row_key"),
                "site_name": row.get("site_name"),
                "site_name_prefix": row.get("site_name_prefix"),
                "managed_by": row.get("managed_by"),
                "account": row.get("account"),
                "has_drive": row.get("has_drive"),
                "client_resolution_source_value": row.get("client_resolution_source_value"),
                "client_resolution_warning": row.get("client_resolution_warning"),
            },
        )
        if len(samples) >= UNRESOLVED_SITE_SAMPLE_LIMIT:
            break
    return samples


def _build_client_resolution_summary(report: dict[str, Any]) -> dict[str, Any]:
    rows = _client_resolution_rows(report)
    method_counts = Counter(row.get("client_resolution_method") or "unknown" for row in rows)
    client_by_id = {
        client["proposed_id"]: client
        for client in report.get("planned", {}).get("clients", [])
    }
    alias_site_counts = Counter(
        row.get("client_proposed_id")
        for row in rows
        if (row.get("client_resolution_method") or "").startswith("alias_")
    )
    alias_client_groups = []
    for proposed_id, site_count in alias_site_counts.most_common():
        client = client_by_id.get(proposed_id)
        if not client:
            continue
        alias_client_groups.append(
            {
                "target_client_name": client["fields"]["name"],
                "target_client_status": client["fields"]["status"],
                "proposed_id": proposed_id,
                "resolved_site_rows": site_count,
                "created_from_alias": client.get("legacy_source_table") == "client_aliases",
            },
        )

    unresolved_prefix_counts = Counter(
        row.get("site_name_prefix") or row.get("site_name") or "(missing site name)"
        for row in rows
        if row.get("client_resolution_method") == "synthetic_unresolved_client"
    )
    unresolved_name_counts = Counter(
        row.get("site_name") or "(missing site name)"
        for row in rows
        if row.get("client_resolution_method") == "synthetic_unresolved_client"
    )
    multiple_alias_warnings = [
        warning
        for warning in report.get("alias_warnings", [])
        if warning.get("reason") == "multiple-alias-matches"
    ]
    return {
        "total_site_rows": len(rows),
        "sites_resolved_direct_client_id": method_counts.get("direct_client_id", 0),
        "sites_resolved_by_alias": sum(
            count for method, count in method_counts.items() if method.startswith("alias_")
        ),
        "sites_unresolved_after_aliases": method_counts.get("synthetic_unresolved_client", 0),
        "sites_with_multiple_alias_matches": len(multiple_alias_warnings),
        "client_proposals_created_from_aliases": len(
            [
                client
                for client in report.get("planned", {}).get("clients", [])
                if client.get("legacy_source_table") == "client_aliases"
            ],
        ),
        "by_method": dict(sorted(method_counts.items())),
        "alias_client_groups": alias_client_groups,
        "top_unresolved_site_prefixes": [
            {"site_name_prefix": prefix, "site_rows": count}
            for prefix, count in unresolved_prefix_counts.most_common(TOP_UNRESOLVED_PREFIX_LIMIT)
        ],
        "top_unresolved_site_names": [
            {"site_name": name, "site_rows": count}
            for name, count in unresolved_name_counts.most_common(TOP_UNRESOLVED_PREFIX_LIMIT)
        ],
    }


def _site_row_key(row: dict[str, Any], row_number: int) -> str:
    return _clean(_first(row, ("site_id", "id"))) or f"synthetic:site:row:{row_number}"


def _build_alias_validation_summary(
    source: SourceData,
    report: dict[str, Any],
    alias_config: ClientAliasConfig,
) -> dict[str, Any]:
    summary = dict(report.get("alias_summary", {}))
    summary.setdefault("aliases_matching_no_v1_sites", 0)
    summary.setdefault("aliases_matching_multiple_client_proposals", 0)
    summary.setdefault("aliases_creating_new_client_proposals", 0)
    summary.setdefault("aliases_matching_v1_sites", 0)
    summary.setdefault("aliases_matching_no_v1_sites_examples", [])
    summary.setdefault("aliases_matching_multiple_client_proposals_examples", [])
    summary.setdefault("aliases_creating_new_client_proposals_examples", [])

    sites_table = source.tables.get("crm_sites")
    site_rows = sites_table.rows if sites_table else []
    resolution_by_row_key = {
        row.get("row_key"): row
        for row in _client_resolution_rows(report)
        if row.get("row_key")
    }
    client_by_id = {
        client["proposed_id"]: client
        for client in report.get("planned", {}).get("clients", [])
    }

    no_match_examples: list[dict[str, Any]] = []
    multiple_client_examples: list[dict[str, Any]] = []
    alias_created_client_examples: list[dict[str, Any]] = []
    aliases_matching_no_sites = 0
    aliases_matching_multiple_clients = 0
    aliases_creating_new_clients = 0
    aliases_matching_sites = 0

    for alias in alias_config.aliases:
        matched_row_keys: list[str] = []
        matched_client_ids: set[str] = set()
        sample_site_names: list[str] = []
        for row_number, row in enumerate(site_rows, start=1):
            matched_value = _site_alias_match_value(alias, row)
            if not matched_value:
                continue
            row_key = _site_row_key(row, row_number)
            matched_row_keys.append(row_key)
            site_name = _site_name_value(row)
            if site_name and site_name not in sample_site_names:
                sample_site_names.append(site_name)
            resolution = resolution_by_row_key.get(row_key, {})
            client_id = resolution.get("client_proposed_id")
            if client_id:
                matched_client_ids.add(client_id)

        alias_detail = {
            "alias_row_number": alias.row_number,
            "source_field": alias.source_field,
            "source_value": alias.source_value,
            "target_client_name": alias.target_client_name,
        }
        if matched_row_keys:
            aliases_matching_sites += 1
        else:
            aliases_matching_no_sites += 1
            no_match_examples.append(alias_detail)
            _append_alias_warning(
                report,
                {
                    "table": "client_aliases",
                    "row_key": f"row:{alias.row_number}",
                    "reason": "alias-matches-no-v1-sites",
                    "source_field": alias.source_field,
                    "source_value": alias.source_value,
                    "target_client_name": alias.target_client_name,
                },
            )

        if len(matched_client_ids) > 1:
            aliases_matching_multiple_clients += 1
            client_names = [
                client_by_id[client_id]["fields"]["name"]
                for client_id in sorted(matched_client_ids)
                if client_id in client_by_id
            ]
            multiple_client_examples.append(
                {
                    **alias_detail,
                    "matched_client_proposal_count": len(matched_client_ids),
                    "matched_client_names": client_names[:ALIAS_DRAFT_SAMPLE_LIMIT],
                    "matched_site_rows": len(matched_row_keys),
                    "sample_site_names": sample_site_names[:ALIAS_DRAFT_SAMPLE_LIMIT],
                },
            )
            _append_alias_warning(
                report,
                {
                    "table": "client_aliases",
                    "row_key": f"row:{alias.row_number}",
                    "reason": "alias-matches-multiple-client-proposals",
                    "source_field": alias.source_field,
                    "source_value": alias.source_value,
                    "target_client_name": alias.target_client_name,
                    "matched_client_proposal_count": len(matched_client_ids),
                    "matched_client_names": client_names[:ALIAS_DRAFT_SAMPLE_LIMIT],
                },
            )

        target_client_id = report["lookup_maps"]["client_name_to_proposed_id"].get(
            _normalize_key(alias.target_client_name),
        )
        target_client = client_by_id.get(target_client_id or "")
        if target_client and target_client.get("legacy_source_table") == "client_aliases":
            aliases_creating_new_clients += 1
            alias_created_client_examples.append(
                {
                    **alias_detail,
                    "target_client_status": target_client.get("fields", {}).get("status"),
                },
            )

    summary.update(
        {
            "aliases_matching_v1_sites": aliases_matching_sites,
            "aliases_matching_no_v1_sites": aliases_matching_no_sites,
            "aliases_matching_multiple_client_proposals": aliases_matching_multiple_clients,
            "aliases_creating_new_client_proposals": aliases_creating_new_clients,
            "aliases_matching_no_v1_sites_examples": no_match_examples[:25],
            "aliases_matching_multiple_client_proposals_examples": multiple_client_examples[:25],
            "aliases_creating_new_client_proposals_examples": alias_created_client_examples[:25],
        },
    )
    return summary


def _add_alias_draft_candidate(
    candidates: dict[tuple[str, str], dict[str, Any]],
    *,
    source_field: str,
    source_value: Any,
    row: dict[str, Any],
) -> None:
    cleaned_value = _clean(source_value)
    if not cleaned_value:
        return
    key = (source_field, _normalize_key(cleaned_value))
    candidate = candidates.setdefault(
        key,
        {
            "source_value": cleaned_value,
            "source_field": source_field,
            "target_client_name": "",
            "target_client_status": "active",
            "notes": "Drafted from unresolved V1 site rows; fill target_client_name after review.",
            "review_status": "needs_review",
            "match_count": 0,
            "_sample_site_names": [],
            "_sample_row_keys": [],
        },
    )
    candidate["match_count"] += 1
    site_name = _clean(row.get("site_name"))
    row_key = _clean(row.get("row_key"))
    if (
        site_name
        and site_name not in candidate["_sample_site_names"]
        and len(candidate["_sample_site_names"]) < ALIAS_DRAFT_SAMPLE_LIMIT
    ):
        candidate["_sample_site_names"].append(site_name)
    if (
        row_key
        and row_key not in candidate["_sample_row_keys"]
        and len(candidate["_sample_row_keys"]) < ALIAS_DRAFT_SAMPLE_LIMIT
    ):
        candidate["_sample_row_keys"].append(row_key)


def _build_alias_draft_recommendations(report: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: dict[tuple[str, str], dict[str, Any]] = {}
    unresolved_rows = [
        row
        for row in _client_resolution_rows(report)
        if row.get("client_resolution_method") == "synthetic_unresolved_client"
    ]
    for row in unresolved_rows:
        for source_field, source_value in (
            ("account", row.get("account")),
            ("managed_by", row.get("managed_by")),
            ("drive_parent_folder", row.get("drive_parent_folder")),
            ("client_id", row.get("client_resolution_source_value")),
            ("site_name_prefix", row.get("site_name_prefix")),
        ):
            _add_alias_draft_candidate(
                candidates,
                source_field=source_field,
                source_value=source_value,
                row=row,
            )
        if not _clean(row.get("site_name_prefix")):
            _add_alias_draft_candidate(
                candidates,
                source_field="site_name_exact",
                source_value=row.get("site_name"),
                row=row,
            )

    field_order = {
        "account": 0,
        "managed_by": 1,
        "site_name_prefix": 2,
        "site_name_exact": 3,
        "client_id": 4,
        "drive_parent_folder": 5,
    }
    rows = sorted(
        candidates.values(),
        key=lambda item: (
            -int(item.get("match_count", 0)),
            field_order.get(str(item.get("source_field")), 99),
            str(item.get("source_value", "")).lower(),
        ),
    )
    draft_rows = []
    for row in rows[:ALIAS_DRAFT_ROW_LIMIT]:
        draft_rows.append(
            {
                "source_value": row["source_value"],
                "source_field": row["source_field"],
                "target_client_name": row["target_client_name"],
                "target_client_status": row["target_client_status"],
                "notes": row["notes"],
                "review_status": row["review_status"],
                "match_count": row["match_count"],
                "sample_site_names": " | ".join(row["_sample_site_names"]),
                "sample_row_keys": " | ".join(row["_sample_row_keys"]),
            },
        )
    return draft_rows


def _build_m2_apply_gate(report: dict[str, Any]) -> dict[str, Any]:
    alias_summary = report.get("alias_summary", {})
    resolution_summary = report.get("client_resolution_summary", {})
    unresolved_sites = int(resolution_summary.get("sites_unresolved_after_aliases", 0) or 0)
    invalid_alias_rows = int(alias_summary.get("rows_invalid", 0) or 0)
    unsupported_rows = int(alias_summary.get("unsupported_source_field_rows", 0) or 0)
    unknown_rows = int(alias_summary.get("unknown_source_field_rows", 0) or 0)
    site_multiple_matches = int(
        resolution_summary.get("sites_with_multiple_alias_matches", 0) or 0,
    )
    alias_multiple_clients = int(
        alias_summary.get("aliases_matching_multiple_client_proposals", 0) or 0,
    )
    reasons = []
    if unresolved_sites > M2_UNRESOLVED_SITE_THRESHOLD:
        reasons.append(
            "Unresolved site count "
            f"{unresolved_sites} is above threshold {M2_UNRESOLVED_SITE_THRESHOLD}.",
        )
    if invalid_alias_rows:
        reasons.append(f"Alias file has {invalid_alias_rows} invalid row(s).")
    if unsupported_rows or unknown_rows:
        reasons.append(
            "Alias file has unsupported or unknown source_field row(s): "
            f"{unsupported_rows + unknown_rows}.",
        )
    if site_multiple_matches or alias_multiple_clients:
        reasons.append(
            "Alias validation found multiple-match warning(s): "
            f"{site_multiple_matches + alias_multiple_clients}.",
        )
    if report.get("errors"):
        reasons.append(f"Dry-run found {len(report['errors'])} structural error(s).")
    reasons.append("--apply is intentionally blocked until M2.")
    return {
        "safe_to_proceed": False,
        "unresolved_site_threshold": M2_UNRESOLVED_SITE_THRESHOLD,
        "reasons": reasons,
    }


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

    possible_client_text_fields = ACCOUNT_FIELD_NAMES
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
        "alias_summary": report.get("alias_summary", {}),
        "client_resolution_summary": report.get("client_resolution_summary", {}),
    }


def _markdown_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> list[str]:
    if not rows:
        return ["- None"]
    def cell(value: Any) -> str:
        return str(value).replace("\n", "<br>").replace("|", "\\|")

    lines = [
        "| " + " | ".join(cell(header) for header in headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(cell(value) for value in row) + " |")
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


def _format_alias_client_groups(summary: dict[str, Any]) -> list[str]:
    return _markdown_table(
        ("Target Client", "Status", "Resolved Site Rows", "Created From Alias"),
        [
            (
                group.get("target_client_name"),
                group.get("target_client_status"),
                group.get("resolved_site_rows"),
                group.get("created_from_alias"),
            )
            for group in summary.get("alias_client_groups", [])[:25]
        ],
    )


def _format_alias_created_client_examples(alias_summary: dict[str, Any]) -> list[str]:
    return _markdown_table(
        ("Alias Row", "Source Field", "Source Value", "Target Client", "Status"),
        [
            (
                item.get("alias_row_number"),
                item.get("source_field"),
                item.get("source_value"),
                item.get("target_client_name"),
                item.get("target_client_status"),
            )
            for item in alias_summary.get("aliases_creating_new_client_proposals_examples", [])
        ],
    )


def _format_alias_no_match_examples(alias_summary: dict[str, Any]) -> list[str]:
    return _markdown_table(
        ("Alias Row", "Source Field", "Source Value", "Target Client"),
        [
            (
                item.get("alias_row_number"),
                item.get("source_field"),
                item.get("source_value"),
                item.get("target_client_name"),
            )
            for item in alias_summary.get("aliases_matching_no_v1_sites_examples", [])
        ],
    )


def _format_alias_multiple_client_examples(alias_summary: dict[str, Any]) -> list[str]:
    return _markdown_table(
        (
            "Alias Row",
            "Source Field",
            "Source Value",
            "Target Client",
            "Matched Client Proposals",
            "Sample Sites",
        ),
        [
            (
                item.get("alias_row_number"),
                item.get("source_field"),
                item.get("source_value"),
                item.get("target_client_name"),
                ", ".join(item.get("matched_client_names", [])) or item.get(
                    "matched_client_proposal_count",
                ),
                " | ".join(item.get("sample_site_names", [])),
            )
            for item in alias_summary.get("aliases_matching_multiple_client_proposals_examples", [])
        ],
    )


def _format_top_unresolved_prefixes(summary: dict[str, Any]) -> list[str]:
    return _markdown_table(
        ("Site Name / Prefix", "Rows"),
        [
            (item.get("site_name_prefix"), item.get("site_rows"))
            for item in summary.get("top_unresolved_site_prefixes", [])
        ],
    )


def _format_alias_draft_recommendations(rows: Sequence[dict[str, Any]]) -> list[str]:
    return _markdown_table(
        ("Source Field", "Source Value", "Unresolved Rows", "Sample Sites", "Sample Row Keys"),
        [
            (
                row.get("source_field"),
                row.get("source_value"),
                row.get("match_count"),
                row.get("sample_site_names"),
                row.get("sample_row_keys"),
            )
            for row in rows[:25]
        ],
    )


def _format_unresolved_site_samples(samples: Sequence[dict[str, Any]]) -> list[str]:
    return _markdown_table(
        ("Row", "Site Name", "Prefix", "Managed By", "Account", "Drive"),
        [
            (
                sample.get("row_key"),
                sample.get("site_name"),
                sample.get("site_name_prefix"),
                sample.get("managed_by"),
                sample.get("account"),
                sample.get("has_drive"),
            )
            for sample in samples
        ],
    )


def _alias_warning_lines(report: dict[str, Any], *, limit: int = 25) -> list[str]:
    warnings = report.get("alias_warnings", [])
    if not warnings:
        return ["- None"]
    lines = []
    for warning in warnings[:limit]:
        row_key = warning.get("row_key") or warning.get("table") or "n/a"
        reason = warning.get("reason") or "warning"
        detail = (
            warning.get("message")
            or warning.get("source_field")
            or warning.get("selected_target_client_name")
            or warning.get("target_client_name")
            or ""
        )
        suffix = f" - {detail}" if detail else ""
        lines.append(f"- {row_key}: {reason}{suffix}")
    remaining = len(warnings) - limit
    if remaining > 0:
        lines.append(f"- ... {remaining} additional alias warnings omitted from markdown.")
    return lines


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
    alias_summary = report.get("alias_summary", {})
    client_resolution_summary = report.get("client_resolution_summary", {})
    m2_apply_gate = report.get("m2_apply_gate", {})
    safe_to_proceed = "Yes" if m2_apply_gate.get("safe_to_proceed") else "No"
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
        "## 4. Alias Mapping Summary",
        "### Alias File Used",
        f"- {alias_summary.get('file_path') or '(not provided)'}",
        "",
        "### Alias Row Validation",
        *_format_diagnostic_counts(
            {
                "Alias rows loaded": alias_summary.get("rows_loaded", 0),
                "Alias rows valid": alias_summary.get("rows_valid", 0),
                "Alias rows invalid": alias_summary.get("rows_invalid", 0),
                "Blank required field rows": alias_summary.get("blank_required_field_rows", 0),
                "Unknown source_field rows": alias_summary.get("unknown_source_field_rows", 0),
                "Unsupported source_field rows": alias_summary.get("unsupported_source_field_rows", 0),
                "Duplicate alias rows": alias_summary.get("duplicate_alias_rows", 0),
                "Aliases matching no V1 sites": alias_summary.get("aliases_matching_no_v1_sites", 0),
                "Aliases matching multiple V2 client proposals": alias_summary.get(
                    "aliases_matching_multiple_client_proposals",
                    0,
                ),
                "Aliases creating new client proposals": alias_summary.get(
                    "aliases_creating_new_client_proposals",
                    0,
                ),
                "Sites resolved by alias": client_resolution_summary.get("sites_resolved_by_alias", 0),
                "Sites unresolved after aliases": client_resolution_summary.get(
                    "sites_unresolved_after_aliases",
                    0,
                ),
                "Sites with multiple alias matches": client_resolution_summary.get(
                    "sites_with_multiple_alias_matches",
                    0,
                ),
                "Client proposals created from aliases": client_resolution_summary.get(
                    "client_proposals_created_from_aliases",
                    0,
                ),
            },
        ),
        "",
        "### Client Resolution Methods",
        *_format_diagnostic_counts(client_resolution_summary.get("by_method", {})),
        "",
        "### Sites Resolved By Alias",
        *_format_alias_client_groups(client_resolution_summary),
        "",
        "### Sites Still Unresolved",
        f"- Remaining unresolved count: {client_resolution_summary.get('sites_unresolved_after_aliases', 0)}",
        *_format_unresolved_site_samples(report.get("unresolved_site_samples", [])),
        "",
        "### Alias-Created Client Proposals",
        *_format_alias_created_client_examples(alias_summary),
        "",
        "### Multiple-Match Warnings",
        *_format_alias_multiple_client_examples(alias_summary),
        "",
        "### Aliases Matching No V1 Sites",
        *_format_alias_no_match_examples(alias_summary),
        "",
        "### Top Unresolved Site Prefixes",
        *_format_top_unresolved_prefixes(client_resolution_summary),
        "",
        "### Recommended Alias Rows To Add",
        *_format_alias_draft_recommendations(report.get("alias_draft_recommendations", [])),
        "",
        "### Alias Warnings",
        *_alias_warning_lines(report),
        "",
        "## 5. Diagnostic Summary",
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
        *_format_unresolved_site_samples(report.get("unresolved_site_samples", [])),
        "",
        "## 6. Planned Clients",
        f"- Would create/update: {report['planned_counts']['clients']}",
        "",
        "## 7. Planned Contacts",
        f"- Would create/update: {report['planned_counts']['contacts']}",
        "",
        "## 8. Planned Sites",
        f"- Would create/update: {report['planned_counts']['sites']}",
        "",
        "## 9. Planned Jobs",
        f"- Would create/update: {report['planned_counts']['jobs']}",
        "",
        "## 10. Relationship Warnings",
        *_warning_lines(report, "relationship"),
        "",
        "## 11. Duplicate Warnings",
        *_warning_lines(report, "duplicates"),
        "",
        "## 12. Status Mapping Warnings",
        *_warning_lines(report, "status_mapping"),
        "",
        "## 13. Date Parsing Warnings",
        *_warning_lines(report, "date_parsing"),
        "",
        "## 14. Drive URL Warnings",
        *_warning_lines(report, "drive_urls"),
        "",
        "## 15. Orphan Records",
        f"- Sites: {len(report['orphans']['sites'])}",
        f"- Jobs: {len(report['orphans']['jobs'])}",
        "",
        "## 16. Deferred Records",
        f"- Leads: {deferred['leads']}",
        f"- Reports: {deferred['reports']}",
        f"- Photos/files: {deferred['photos_files']}",
        f"- Communications: {deferred['communications']}",
        "",
        "## 17. Final Go/No-Go Summary",
        f"- Status: {report['go_no_go']['status']}",
        f"- Warnings: {report['go_no_go']['warning_count']}",
        f"- Errors: {report['go_no_go']['error_count']}",
        f"- Summary: {report['go_no_go']['summary']}",
        "",
        "## 18. Safe to Proceed to M2 Apply?",
        f"- Safe to proceed to M2 apply? {safe_to_proceed}",
        f"- Unresolved site threshold: {m2_apply_gate.get('unresolved_site_threshold', M2_UNRESOLVED_SITE_THRESHOLD)}",
        *[f"- {reason}" for reason in m2_apply_gate.get("reasons", [])],
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


def write_alias_draft(
    report: dict[str, Any],
    output_path: str | Path,
    *,
    force: bool = False,
) -> Path:
    path = Path(output_path).expanduser().resolve()
    if path.exists() and not force:
        raise FileExistsError(
            f"Alias draft already exists and was not overwritten: {path}. "
            "Pass --force only after confirming the file is safe to replace.",
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = report.get("alias_draft_recommendations", [])
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(ALIAS_DRAFT_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in ALIAS_DRAFT_COLUMNS})
    return path


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
    parser.add_argument(
        "--client-aliases",
        help="Optional read-only CSV mapping file for deterministic site-to-client alias resolution.",
    )
    parser.add_argument(
        "--write-alias-draft",
        help="Optional path for a private draft client alias CSV built from unresolved dry-run sites.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow --write-alias-draft to overwrite an existing draft file.",
    )
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
            client_aliases=args.client_aliases,
        )
        write_report_outputs(
            report,
            output_json=args.output_json,
            output_md=args.output_md,
        )
        if args.write_alias_draft:
            draft_path = write_alias_draft(
                report,
                args.write_alias_draft,
                force=args.force,
            )
            print(f"\nAlias draft written: {draft_path}\n")
        print(render_text_report(report))
    except Exception as error:
        print(f"V1 migration dry-run failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
