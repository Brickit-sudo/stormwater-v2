from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


CLIENT_STATUSES = {"active", "inactive", "prospect", "archived"}
SITE_STATUSES = {"active", "inactive", "on_hold", "archived"}
JOB_STATUSES = {"draft", "scheduled", "in_progress", "in_review", "completed", "archived", "cancelled", "canceled"}
EMAIL_STATUSES = {"unlinked", "linked", "archived"}
EMAIL_LINK_STATUSES = {"linked", "unlinked"}
PARENT_TYPES = {"client", "site", "job"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


TEMPLATE_CONFIGS: dict[str, dict[str, Any]] = {
    "clients": {
        "external_id_field": "client_external_id",
        "required_columns": {
            "source_system",
            "legacy_source",
            "legacy_id",
            "client_external_id",
            "canonical_name",
            "alias_values",
            "status",
            "primary_contact_name",
            "email",
            "phone",
            "billing_address",
            "drive_folder_url",
            "notes",
        },
        "required_fields": {"source_system", "client_external_id", "canonical_name", "status"},
        "status_field": "status",
        "allowed_statuses": CLIENT_STATUSES,
        "email_fields": {"email"},
        "url_fields": {"drive_folder_url"},
    },
    "contacts": {
        "external_id_field": "contact_external_id",
        "required_columns": {
            "source_system",
            "legacy_source",
            "legacy_id",
            "contact_external_id",
            "client_external_id",
            "site_external_id",
            "name",
            "email",
            "phone",
            "role",
            "notes",
        },
        "required_fields": {"source_system", "contact_external_id", "client_external_id", "name", "email"},
        "email_fields": {"email"},
    },
    "sites": {
        "external_id_field": "site_external_id",
        "required_columns": {
            "source_system",
            "legacy_source",
            "legacy_id",
            "site_external_id",
            "client_external_id",
            "canonical_name",
            "alias_values",
            "site_code",
            "status",
            "address",
            "city",
            "state",
            "zip",
            "latitude",
            "longitude",
            "drive_folder_url",
            "notes",
        },
        "required_fields": {"source_system", "site_external_id", "client_external_id", "canonical_name", "status"},
        "status_field": "status",
        "allowed_statuses": SITE_STATUSES,
        "url_fields": {"drive_folder_url"},
    },
    "jobs": {
        "external_id_field": "job_external_id",
        "required_columns": {
            "source_system",
            "legacy_source",
            "legacy_id",
            "job_external_id",
            "client_external_id",
            "site_external_id",
            "service_code",
            "service_type",
            "name",
            "status",
            "scheduled_date",
            "due_date",
            "completed_date",
            "scope",
            "drive_folder_url",
            "notes",
        },
        "required_fields": {"source_system", "job_external_id", "client_external_id", "site_external_id", "name", "status"},
        "status_field": "status",
        "allowed_statuses": JOB_STATUSES,
        "url_fields": {"drive_folder_url"},
        "date_fields": {"scheduled_date", "due_date", "completed_date"},
    },
    "documents": {
        "external_id_field": "document_external_id",
        "required_columns": {
            "source_system",
            "legacy_source",
            "legacy_id",
            "document_external_id",
            "file_name",
            "document_category",
            "parent_type",
            "parent_external_id",
            "client_external_id",
            "site_external_id",
            "job_external_id",
            "drive_file_url",
            "drive_folder_url",
            "mime_type",
            "caption",
            "notes",
        },
        "required_fields": {"source_system", "document_external_id", "file_name", "document_category"},
        "url_fields": {"drive_file_url", "drive_folder_url"},
        "requires_parent": True,
    },
    "emails": {
        "external_id_field": "email_external_id",
        "required_columns": {
            "source_system",
            "legacy_source",
            "legacy_id",
            "email_external_id",
            "provider",
            "provider_message_id",
            "subject",
            "sender",
            "recipient_emails",
            "received_at",
            "status",
            "link_status",
            "parent_type",
            "parent_external_id",
            "client_external_id",
            "site_external_id",
            "job_external_id",
            "web_link",
            "unlinked_reason",
            "notes",
        },
        "required_fields": {"source_system", "email_external_id", "provider", "subject", "sender", "status", "link_status"},
        "status_field": "status",
        "allowed_statuses": EMAIL_STATUSES,
        "email_fields": {"sender"},
        "email_list_fields": {"recipient_emails"},
        "url_fields": {"web_link"},
        "date_fields": {"received_at"},
        "requires_email_link_state": True,
    },
}


@dataclass(frozen=True)
class CsvDataset:
    import_type: str
    path: Path
    fieldnames: tuple[str, ...]
    rows: tuple[dict[str, str], ...]
    missing_columns: tuple[str, ...]


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def _normalized_key(value: Any) -> str:
    return _clean(value).lower()


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve())
    except OSError:
        return str(path)


def _read_dataset(import_type: str, path: str | Path) -> CsvDataset:
    csv_path = Path(path).expanduser().resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"{import_type} template not found: {csv_path}")
    if not csv_path.is_file():
        raise FileNotFoundError(f"{import_type} path is not a file: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = tuple(reader.fieldnames or ())
        missing = tuple(sorted(TEMPLATE_CONFIGS[import_type]["required_columns"] - set(fieldnames)))
        rows = tuple(
            {
                key: _clean(value)
                for key, value in row.items()
                if key is not None
            }
            for row in reader
        )
    return CsvDataset(import_type, csv_path, fieldnames, rows, missing)


def _is_email(value: str) -> bool:
    return bool(EMAIL_RE.match(value))


def _split_emails(value: str) -> list[str]:
    if not value:
        return []
    return [
        item.strip()
        for item in re.split(r"[;,]", value)
        if item.strip()
    ]


def _is_url(value: str) -> bool:
    if not value:
        return True
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_iso_date_or_datetime(value: str) -> bool:
    if not value:
        return True
    candidate = value.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(candidate)
        return True
    except ValueError:
        pass
    try:
        datetime.fromisoformat(f"{candidate}T00:00:00")
        return True
    except ValueError:
        return False


def _entity_id(row: Mapping[str, str], import_type: str) -> str:
    return _clean(row.get(TEMPLATE_CONFIGS[import_type]["external_id_field"]))


def _row_key(import_type: str, row_number: int) -> str:
    return f"{import_type}:row:{row_number}"


def _add_issue(
    row_issues: dict[str, list[dict[str, Any]]],
    *,
    import_type: str,
    row_number: int,
    field: str | None,
    code: str,
    message: str,
) -> None:
    row_issues[_row_key(import_type, row_number)].append(
        {
            "import_type": import_type,
            "row_number": row_number,
            "field": field,
            "code": code,
            "message": message,
        },
    )


def _parent_signals(row: Mapping[str, str]) -> tuple[list[dict[str, str]], list[str]]:
    signals: list[dict[str, str]] = []
    errors: list[str] = []
    parent_type = _normalized_key(row.get("parent_type"))
    parent_external_id = _clean(row.get("parent_external_id"))

    if parent_type or parent_external_id:
        if not parent_type or not parent_external_id:
            errors.append("parent_type and parent_external_id must be provided together.")
        else:
            signals.append(
                {
                    "parent_type": parent_type,
                    "parent_external_id": parent_external_id,
                    "source": "parent_type_parent_external_id",
                },
            )

    for parent_type_name, field in (
        ("client", "client_external_id"),
        ("site", "site_external_id"),
        ("job", "job_external_id"),
    ):
        external_id = _clean(row.get(field))
        if external_id:
            signals.append(
                {
                    "parent_type": parent_type_name,
                    "parent_external_id": external_id,
                    "source": field,
                },
            )

    return signals, errors


def _append_unresolved(
    report: dict[str, Any],
    row_issues: dict[str, list[dict[str, Any]]],
    *,
    import_type: str,
    row_number: int,
    field: str,
    target_type: str,
    target_external_id: str,
) -> None:
    issue = {
        "import_type": import_type,
        "row_number": row_number,
        "field": field,
        "target_type": target_type,
        "target_external_id": target_external_id,
        "message": f"Unresolved {target_type} reference: {target_external_id}",
    }
    report["unresolved_references"].append(issue)
    _add_issue(
        row_issues,
        import_type=import_type,
        row_number=row_number,
        field=field,
        code="unresolved-reference",
        message=issue["message"],
    )


def _resolve_parent(
    report: dict[str, Any],
    row_issues: dict[str, list[dict[str, Any]]],
    *,
    import_type: str,
    row_number: int,
    parent: Mapping[str, str],
    indexes: Mapping[str, dict[str, dict[str, str]]],
) -> None:
    parent_type = parent["parent_type"]
    external_id = parent["parent_external_id"]
    if parent_type not in PARENT_TYPES:
        _add_issue(
            row_issues,
            import_type=import_type,
            row_number=row_number,
            field="parent_type",
            code="invalid-parent-type",
            message=f"parent_type must be one of: {', '.join(sorted(PARENT_TYPES))}.",
        )
        return

    target_index_name = f"{parent_type}s"
    if _normalized_key(external_id) not in indexes[target_index_name]:
        _append_unresolved(
            report,
            row_issues,
            import_type=import_type,
            row_number=row_number,
            field=parent["source"],
            target_type=parent_type,
            target_external_id=external_id,
        )


def _build_indexes(
    datasets: Mapping[str, CsvDataset],
) -> dict[str, dict[str, dict[str, str]]]:
    indexes: dict[str, dict[str, dict[str, str]]] = {
        "clients": {},
        "sites": {},
        "jobs": {},
    }
    for import_type in ("clients", "sites", "jobs"):
        dataset = datasets.get(import_type)
        if dataset is None:
            continue
        for row in dataset.rows:
            external_id = _entity_id(row, import_type)
            if external_id:
                indexes[import_type].setdefault(_normalized_key(external_id), row)
    return indexes


def _validate_common_row(
    report: dict[str, Any],
    row_issues: dict[str, list[dict[str, Any]]],
    *,
    import_type: str,
    row_number: int,
    row: Mapping[str, str],
) -> None:
    config = TEMPLATE_CONFIGS[import_type]
    for field in sorted(config["required_fields"]):
        if not _clean(row.get(field)):
            _add_issue(
                row_issues,
                import_type=import_type,
                row_number=row_number,
                field=field,
                code="missing-required-field",
                message=f"{field} is required.",
            )

    status_field = config.get("status_field")
    if status_field:
        status = _normalized_key(row.get(status_field))
        if status and status not in config["allowed_statuses"]:
            _add_issue(
                row_issues,
                import_type=import_type,
                row_number=row_number,
                field=status_field,
                code="invalid-status",
                message=(
                    f"{status_field} must be one of: "
                    f"{', '.join(sorted(config['allowed_statuses']))}."
                ),
            )

    for field in sorted(config.get("email_fields", set())):
        value = _clean(row.get(field))
        if value and not _is_email(value):
            _add_issue(
                row_issues,
                import_type=import_type,
                row_number=row_number,
                field=field,
                code="invalid-email",
                message=f"{field} must be a basic email address.",
            )

    for field in sorted(config.get("email_list_fields", set())):
        for email in _split_emails(_clean(row.get(field))):
            if not _is_email(email):
                _add_issue(
                    row_issues,
                    import_type=import_type,
                    row_number=row_number,
                    field=field,
                    code="invalid-email",
                    message=f"{field} contains an invalid email address: {email}",
                )

    for field in sorted(config.get("url_fields", set())):
        value = _clean(row.get(field))
        if value and not _is_url(value):
            _add_issue(
                row_issues,
                import_type=import_type,
                row_number=row_number,
                field=field,
                code="invalid-url",
                message=f"{field} must be an http(s) URL.",
            )

    for field in sorted(config.get("date_fields", set())):
        value = _clean(row.get(field))
        if value and not _is_iso_date_or_datetime(value):
            _add_issue(
                row_issues,
                import_type=import_type,
                row_number=row_number,
                field=field,
                code="invalid-date",
                message=f"{field} must be ISO date or datetime text.",
            )


def _detect_duplicates(
    report: dict[str, Any],
    row_issues: dict[str, list[dict[str, Any]]],
    datasets: Mapping[str, CsvDataset],
) -> None:
    for import_type, dataset in datasets.items():
        config = TEMPLATE_CONFIGS[import_type]
        external_id_field = config["external_id_field"]
        seen_external: dict[tuple[str, str], int] = {}
        seen_legacy: dict[tuple[str, str, str], int] = {}

        for offset, row in enumerate(dataset.rows, start=2):
            source_system = _normalized_key(row.get("source_system"))
            external_id = _normalized_key(row.get(external_id_field))
            if source_system and external_id:
                key = (source_system, external_id)
                first_row = seen_external.get(key)
                if first_row is None:
                    seen_external[key] = offset
                else:
                    duplicate = {
                        "import_type": import_type,
                        "row_number": offset,
                        "field": external_id_field,
                        "value": row.get(external_id_field),
                        "first_row": first_row,
                        "message": f"Duplicate {external_id_field}: {row.get(external_id_field)}",
                    }
                    report["duplicate_rows"].append(duplicate)
                    _add_issue(
                        row_issues,
                        import_type=import_type,
                        row_number=offset,
                        field=external_id_field,
                        code="duplicate-external-id",
                        message=duplicate["message"],
                    )

            legacy_id = _normalized_key(row.get("legacy_id"))
            legacy_source = _normalized_key(row.get("legacy_source"))
            if source_system and legacy_source and legacy_id:
                key = (source_system, legacy_source, legacy_id)
                first_row = seen_legacy.get(key)
                if first_row is None:
                    seen_legacy[key] = offset
                else:
                    duplicate = {
                        "import_type": import_type,
                        "row_number": offset,
                        "field": "legacy_id",
                        "value": row.get("legacy_id"),
                        "first_row": first_row,
                        "message": f"Duplicate legacy_id for source: {row.get('legacy_id')}",
                    }
                    report["duplicate_rows"].append(duplicate)
                    _add_issue(
                        row_issues,
                        import_type=import_type,
                        row_number=offset,
                        field="legacy_id",
                        code="duplicate-legacy-id",
                        message=duplicate["message"],
                    )


def _validate_relationships(
    report: dict[str, Any],
    row_issues: dict[str, list[dict[str, Any]]],
    datasets: Mapping[str, CsvDataset],
    indexes: Mapping[str, dict[str, dict[str, str]]],
) -> None:
    clients = indexes["clients"]
    sites = indexes["sites"]
    jobs = indexes["jobs"]

    for offset, row in enumerate(datasets.get("contacts", CsvDataset("contacts", Path(), (), (), ())).rows, start=2):
        client_id = _clean(row.get("client_external_id"))
        site_id = _clean(row.get("site_external_id"))
        if client_id and _normalized_key(client_id) not in clients:
            _append_unresolved(
                report,
                row_issues,
                import_type="contacts",
                row_number=offset,
                field="client_external_id",
                target_type="client",
                target_external_id=client_id,
            )
        if site_id:
            site = sites.get(_normalized_key(site_id))
            if site is None:
                _append_unresolved(
                    report,
                    row_issues,
                    import_type="contacts",
                    row_number=offset,
                    field="site_external_id",
                    target_type="site",
                    target_external_id=site_id,
                )
            elif client_id and _normalized_key(site.get("client_external_id")) != _normalized_key(client_id):
                _add_issue(
                    row_issues,
                    import_type="contacts",
                    row_number=offset,
                    field="site_external_id",
                    code="relationship-mismatch",
                    message="site_external_id does not belong to the provided client_external_id.",
                )

    for offset, row in enumerate(datasets.get("sites", CsvDataset("sites", Path(), (), (), ())).rows, start=2):
        client_id = _clean(row.get("client_external_id"))
        if client_id and _normalized_key(client_id) not in clients:
            _append_unresolved(
                report,
                row_issues,
                import_type="sites",
                row_number=offset,
                field="client_external_id",
                target_type="client",
                target_external_id=client_id,
            )

    for offset, row in enumerate(datasets.get("jobs", CsvDataset("jobs", Path(), (), (), ())).rows, start=2):
        client_id = _clean(row.get("client_external_id"))
        site_id = _clean(row.get("site_external_id"))
        if client_id and _normalized_key(client_id) not in clients:
            _append_unresolved(
                report,
                row_issues,
                import_type="jobs",
                row_number=offset,
                field="client_external_id",
                target_type="client",
                target_external_id=client_id,
            )
        site = sites.get(_normalized_key(site_id))
        if site_id and site is None:
            _append_unresolved(
                report,
                row_issues,
                import_type="jobs",
                row_number=offset,
                field="site_external_id",
                target_type="site",
                target_external_id=site_id,
            )
        elif site is not None and client_id and _normalized_key(site.get("client_external_id")) != _normalized_key(client_id):
            _add_issue(
                row_issues,
                import_type="jobs",
                row_number=offset,
                field="site_external_id",
                code="relationship-mismatch",
                message="job client_external_id must match the resolved site's client_external_id.",
            )

    for offset, row in enumerate(datasets.get("documents", CsvDataset("documents", Path(), (), (), ())).rows, start=2):
        signals, parent_errors = _parent_signals(row)
        for message in parent_errors:
            _add_issue(
                row_issues,
                import_type="documents",
                row_number=offset,
                field="parent_external_id",
                code="invalid-parent",
                message=message,
            )
        if not signals:
            _add_issue(
                row_issues,
                import_type="documents",
                row_number=offset,
                field="parent_external_id",
                code="missing-parent",
                message="Documents must have exactly one clear parent.",
            )
        elif len(signals) > 1:
            _add_issue(
                row_issues,
                import_type="documents",
                row_number=offset,
                field="parent_external_id",
                code="multiple-parents",
                message="Documents must not declare multiple parent references.",
            )
        else:
            _resolve_parent(
                report,
                row_issues,
                import_type="documents",
                row_number=offset,
                parent=signals[0],
                indexes=indexes,
            )

    for offset, row in enumerate(datasets.get("emails", CsvDataset("emails", Path(), (), (), ())).rows, start=2):
        signals, parent_errors = _parent_signals(row)
        link_status = _normalized_key(row.get("link_status"))
        status = _normalized_key(row.get("status"))
        for message in parent_errors:
            _add_issue(
                row_issues,
                import_type="emails",
                row_number=offset,
                field="parent_external_id",
                code="invalid-parent",
                message=message,
            )
        if link_status and link_status not in EMAIL_LINK_STATUSES:
            _add_issue(
                row_issues,
                import_type="emails",
                row_number=offset,
                field="link_status",
                code="invalid-link-status",
                message=f"link_status must be one of: {', '.join(sorted(EMAIL_LINK_STATUSES))}.",
            )
        if len(signals) > 1:
            _add_issue(
                row_issues,
                import_type="emails",
                row_number=offset,
                field="parent_external_id",
                code="multiple-parents",
                message="Emails must not declare multiple parent references.",
            )
        elif len(signals) == 1:
            if link_status != "linked" or status != "linked":
                _add_issue(
                    row_issues,
                    import_type="emails",
                    row_number=offset,
                    field="status",
                    code="invalid-link-state",
                    message="Emails with a parent must use status=linked and link_status=linked.",
                )
            _resolve_parent(
                report,
                row_issues,
                import_type="emails",
                row_number=offset,
                parent=signals[0],
                indexes=indexes,
            )
        else:
            if link_status != "unlinked" or status != "unlinked":
                _add_issue(
                    row_issues,
                    import_type="emails",
                    row_number=offset,
                    field="link_status",
                    code="missing-unlinked-review-state",
                    message="Emails without a parent must be explicitly marked unlinked.",
                )
            if not _clean(row.get("unlinked_reason")):
                _add_issue(
                    row_issues,
                    import_type="emails",
                    row_number=offset,
                    field="unlinked_reason",
                    code="missing-unlinked-reason",
                    message="Explicitly unlinked emails need an unlinked_reason for review.",
                )


def _build_summary(
    datasets: Mapping[str, CsvDataset],
    row_issues: Mapping[str, list[dict[str, Any]]],
) -> dict[str, dict[str, int | bool]]:
    summary: dict[str, dict[str, int | bool]] = {}
    for import_type in TEMPLATE_CONFIGS:
        dataset = datasets.get(import_type)
        if dataset is None:
            summary[import_type] = {
                "provided": False,
                "total_rows": 0,
                "valid_rows": 0,
                "invalid_rows": 0,
                "duplicate_rows": 0,
                "unmatched_rows": 0,
            }
            continue

        invalid_rows = 0
        duplicate_rows = 0
        unmatched_rows = 0
        for offset, _row in enumerate(dataset.rows, start=2):
            issues = row_issues.get(_row_key(import_type, offset), [])
            if not issues:
                continue
            invalid_rows += 1
            if any(issue["code"].startswith("duplicate") for issue in issues):
                duplicate_rows += 1
            if any(issue["code"] == "unresolved-reference" for issue in issues):
                unmatched_rows += 1

        total_rows = len(dataset.rows)
        summary[import_type] = {
            "provided": True,
            "total_rows": total_rows,
            "valid_rows": total_rows - invalid_rows,
            "invalid_rows": invalid_rows,
            "duplicate_rows": duplicate_rows,
            "unmatched_rows": unmatched_rows,
        }
    return summary


def validate_import_templates(
    *,
    clients: str | Path | None = None,
    contacts: str | Path | None = None,
    sites: str | Path | None = None,
    jobs: str | Path | None = None,
    documents: str | Path | None = None,
    emails: str | Path | None = None,
) -> dict[str, Any]:
    paths = {
        "clients": clients,
        "contacts": contacts,
        "sites": sites,
        "jobs": jobs,
        "documents": documents,
        "emails": emails,
    }
    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "ready": False,
        "inputs": {},
        "summary": {},
        "invalid_rows": [],
        "duplicate_rows": [],
        "unresolved_references": [],
        "stop_conditions": [],
        "safety": {
            "db_writes": False,
            "provider_calls": False,
            "real_import": False,
        },
    }
    datasets: dict[str, CsvDataset] = {}
    row_issues: dict[str, list[dict[str, Any]]] = defaultdict(list)

    provided_paths = {name: path for name, path in paths.items() if path}
    if not provided_paths:
        report["stop_conditions"].append("No template paths were provided.")

    for import_type, path in provided_paths.items():
        try:
            dataset = _read_dataset(import_type, path)
        except Exception as error:
            report["stop_conditions"].append(str(error))
            continue
        datasets[import_type] = dataset
        report["inputs"][import_type] = {
            "path": _display_path(dataset.path),
            "row_count": len(dataset.rows),
            "missing_columns": list(dataset.missing_columns),
        }
        if dataset.missing_columns:
            report["stop_conditions"].append(
                f"{import_type} is missing required columns: {', '.join(dataset.missing_columns)}",
            )

    indexes = _build_indexes(datasets)

    for import_type, dataset in datasets.items():
        for offset, row in enumerate(dataset.rows, start=2):
            _validate_common_row(report, row_issues, import_type=import_type, row_number=offset, row=row)

    _detect_duplicates(report, row_issues, datasets)
    _validate_relationships(report, row_issues, datasets, indexes)

    for issues in row_issues.values():
        if issues:
            first = issues[0]
            report["invalid_rows"].append(
                {
                    "import_type": first["import_type"],
                    "row_number": first["row_number"],
                    "errors": issues,
                },
            )

    report["invalid_rows"].sort(key=lambda item: (item["import_type"], item["row_number"]))
    report["summary"] = _build_summary(datasets, row_issues)

    total_invalid = sum(item["invalid_rows"] for item in report["summary"].values())
    if total_invalid:
        report["stop_conditions"].append(f"{total_invalid} row(s) failed validation.")
    if report["duplicate_rows"]:
        report["stop_conditions"].append(f"{len(report['duplicate_rows'])} duplicate row issue(s) detected.")
    if report["unresolved_references"]:
        report["stop_conditions"].append(
            f"{len(report['unresolved_references'])} unresolved reference(s) detected.",
        )

    report["ready"] = not report["stop_conditions"]
    return report


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


def render_markdown_report(report: Mapping[str, Any]) -> str:
    summary_rows = [
        (
            import_type,
            values["provided"],
            values["total_rows"],
            values["valid_rows"],
            values["invalid_rows"],
            values["duplicate_rows"],
            values["unmatched_rows"],
        )
        for import_type, values in report.get("summary", {}).items()
    ]
    invalid_rows = [
        (
            item["import_type"],
            item["row_number"],
            "; ".join(error["message"] for error in item["errors"]),
        )
        for item in report.get("invalid_rows", [])
    ]
    duplicate_rows = [
        (
            item["import_type"],
            item["row_number"],
            item["field"],
            item["value"],
            item["first_row"],
        )
        for item in report.get("duplicate_rows", [])
    ]
    unresolved_rows = [
        (
            item["import_type"],
            item["row_number"],
            item["field"],
            item["target_type"],
            item["target_external_id"],
        )
        for item in report.get("unresolved_references", [])
    ]
    stop_conditions = report.get("stop_conditions", [])
    stop_condition_lines = [f"- {condition}" for condition in stop_conditions] if stop_conditions else ["- None"]
    lines = [
        "# V2 Import Template Validation Report",
        "",
        f"- Generated at: `{report.get('generated_at')}`",
        f"- Ready: {'YES' if report.get('ready') else 'NO'}",
        f"- DB writes: {report.get('safety', {}).get('db_writes')}",
        f"- Provider calls: {report.get('safety', {}).get('provider_calls')}",
        "",
        "## Summary",
        *_markdown_table(
            ("Type", "Provided", "Total", "Valid", "Invalid", "Duplicates", "Unmatched"),
            summary_rows,
        ),
        "",
        "## Stop Conditions",
        *stop_condition_lines,
        "",
        "## Invalid Rows",
        *_markdown_table(("Type", "Row", "Errors"), invalid_rows),
        "",
        "## Duplicate Rows",
        *_markdown_table(("Type", "Row", "Field", "Value", "First Row"), duplicate_rows),
        "",
        "## Unresolved References",
        *_markdown_table(("Type", "Row", "Field", "Target Type", "Target External ID"), unresolved_rows),
        "",
        "## Safety",
        "- Validation only.",
        "- No database connection is opened.",
        "- No Outlook, Gmail, Google Drive, or OpenAI providers are called.",
        "- No real import or CRM writes are performed.",
        "",
    ]
    return "\n".join(lines)


def write_report_outputs(
    report: Mapping[str, Any],
    *,
    output_json: str | Path | None = None,
    output_md: str | Path | None = None,
) -> None:
    if output_json:
        path = Path(output_json).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    if output_md:
        path = Path(output_md).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_markdown_report(report), encoding="utf-8")


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate V2 import CSV templates without DB writes.")
    parser.add_argument("--clients")
    parser.add_argument("--contacts")
    parser.add_argument("--sites")
    parser.add_argument("--jobs")
    parser.add_argument("--documents")
    parser.add_argument("--emails")
    parser.add_argument("--output-json")
    parser.add_argument("--output-md")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    report = validate_import_templates(
        clients=args.clients,
        contacts=args.contacts,
        sites=args.sites,
        jobs=args.jobs,
        documents=args.documents,
        emails=args.emails,
    )
    write_report_outputs(report, output_json=args.output_json, output_md=args.output_md)
    print(render_markdown_report(report))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
