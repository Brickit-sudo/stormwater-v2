from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


EXPECTED_EXPORTS = {
    "contacts": "Contacts_1778108333.xlsx",
    "leads": "Leads_1778108311.xlsx",
    "orders": "Order_1778108323.xlsx",
    "sites": "Site_Information_1778107854.xlsx",
}

TINY_CLIENT_LIMIT = 5
TINY_SITE_LIMIT = 10

SITE_STATUS_MAPPING = {
    "active": "active",
    "inactive": "inactive",
    "on hold": "on_hold",
    "onhold": "on_hold",
    "archived": "archived",
    "archive": "archived",
}

SITE_STATUS_MAPPING_REVIEW_ROWS = (
    ("Active", "active", "Clear direct mapping."),
    ("Inactive", "inactive", "Clear direct mapping."),
    ("On Hold", "on_hold", "Clear direct mapping."),
    ("Archived", "archived", "Clear direct mapping."),
    ("Blank", "active for validation sample only", "Requires Bryce review before import."),
    ("Any other raw value", "active for validation sample only", "Do not import until Bryce reviews."),
)

UNRESOLVED_SITES_REVIEW_COLUMNS = (
    "source_row_number",
    "site_id",
    "site_name_or_label",
    "client_id",
    "client_candidate",
    "exclusion_reason",
    "diagnostic_bucket",
    "suggested_fix",
    "manual_client_external_id",
    "manual_status",
    "review_status",
    "notes",
)

CLIENT_STATUS_REVIEW_COLUMNS = (
    "source_row_number",
    "client_id",
    "client_name_or_label",
    "raw_client_status",
    "current_mapping",
    "suggested_status",
    "review_status",
    "notes",
)

DUPLICATE_SITES_REVIEW_COLUMNS = (
    "source_row_number",
    "site_id",
    "site_name_or_label",
    "duplicate_group",
    "suggested_action",
    "keep_or_skip",
    "notes",
)

STATUS_DEFAULTS_REVIEW_COLUMNS = (
    "source_row_number",
    "site_id",
    "site_name_or_label",
    "raw_site_status",
    "defaulted_status",
    "review_status",
    "manual_status",
    "notes",
)

APPROVED_REVIEW_STATUS = "approved"
SKIPPED_REVIEW_STATUSES = {"", "skip", "needs_source_fix", "needs_followup"}
KNOWN_REVIEW_STATUSES = SKIPPED_REVIEW_STATUSES | {APPROVED_REVIEW_STATUS}
CLIENT_STATUS_VALUES = {"active", "inactive", "prospect", "archived"}
SITE_STATUS_VALUES = {"active", "inactive", "on_hold", "archived"}
DUPLICATE_DECISIONS = {"keep", "skip", "needs_source_fix"}

SITE_REVIEW_BUCKET_LABELS = {
    "site_id_not_found_in_leads": "Site IDs not found in Leads",
    "site_has_no_client_id": "sites with no Client ID",
    "linked_client_unmapped_client_status": "linked to clients with unmapped client status",
    "no_reviewable_client_candidate": "no reviewable client candidate",
    "client_id_not_found_in_contacts": "Client IDs not found in Contacts",
    "duplicate_site_id_in_site_information": "duplicate Site ID rows",
    "blank_site_id": "blank Site ID rows",
    "ambiguous_site_to_client_link": "ambiguous Site ID to Client ID link",
    "linked_client_ambiguous_account_name": "linked client ambiguous account name",
    "missing_site_name": "missing site name",
}

SITE_REVIEW_SUGGESTED_FIXES = {
    "site_id_not_found_in_leads": (
        "Confirm the Leads Site ID link, then fill manual_client_external_id or update the Monday source."
    ),
    "site_has_no_client_id": "Fill the missing Client ID in Leads or provide manual_client_external_id.",
    "linked_client_unmapped_client_status": (
        "Review the linked client in client_status_review.csv, then set a reviewed client status."
    ),
    "no_reviewable_client_candidate": (
        "Create or choose a reviewable client candidate, then fill manual_client_external_id."
    ),
    "client_id_not_found_in_contacts": (
        "Confirm the Contacts Client ID exists or provide a reviewed existing client_external_id."
    ),
    "duplicate_site_id_in_site_information": "Use duplicate_sites_review.csv to choose keep, skip, or merge.",
    "blank_site_id": "Fill the Site ID in Monday or mark the row skip after review.",
    "ambiguous_site_to_client_link": "Resolve the single correct Client ID, then fill manual_client_external_id.",
    "linked_client_ambiguous_account_name": "Resolve the client's canonical account name before importing this site.",
    "missing_site_name": "Fill the site name in Monday or mark the row skip after review.",
}


@dataclass(frozen=True)
class TableData:
    path: Path
    headers: tuple[str, ...]
    rows: tuple[dict[str, str], ...]
    header_row: int


@dataclass(frozen=True)
class PrepSummary:
    clients_written: int
    sites_written: int
    candidate_sites: int
    site_rejections: dict[str, int]
    client_rejections: dict[str, int]
    site_status_defaulted: int
    site_urls_omitted: int
    clients_path: Path
    sites_path: Path
    report_path: Path


@dataclass(frozen=True)
class ReviewPackSummary:
    output_dir: Path
    files: dict[str, Path]
    diagnostic_bucket_counts: dict[str, int]
    client_status_rows: int
    duplicate_site_rows: int
    status_default_rows: int
    readme_path: Path


@dataclass(frozen=True)
class ReviewedSampleSummary:
    clients_written: int
    sites_written: int
    approved_unresolved_sites: int
    approved_status_defaults: int
    kept_duplicate_sites: int
    skipped_review_rows: dict[str, int]
    clients_path: Path
    sites_path: Path
    report_dir: Path
    application_report_path: Path
    validation_json_path: Path
    validation_md_path: Path
    validation_ready: bool
    validation_totals: dict[str, int]


@dataclass(frozen=True)
class MondayAnalysis:
    tables: dict[str, TableData]
    client_account_names: dict[str, set[str]]
    client_contact_rows: dict[str, list[dict[str, str]]]
    all_contact_client_ids: set[str]
    contact_skips: Counter[str]
    client_candidates: dict[str, dict[str, str]]
    client_rejections: Counter[str]
    client_rejection_reason_by_id: dict[str, str]
    site_to_client_ids: dict[str, set[str]]
    lead_blank_client_by_site: Counter[str]
    site_rejections: Counter[str]
    relationship_reasons: Counter[str]
    unresolved_site_ids: Counter[str]
    unresolved_client_ids: Counter[str]
    site_status_counts: Counter[str]
    site_rows_by_id: dict[str, list[dict[str, str]]]
    candidate_sites: list[tuple[str, str, dict[str, str]]]
    unresolved_site_review_rows: list[dict[str, str]]
    client_status_review_rows: list[dict[str, str]]
    duplicate_site_review_rows: list[dict[str, str]]


def clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value).strip()
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return re.sub(r"\s+", " ", str(value).strip())


def _normalized_name(value: Any) -> str:
    return clean(value).casefold()


def _unique_headers(raw_headers: Sequence[Any]) -> tuple[str, ...]:
    seen: dict[str, int] = {}
    headers: list[str] = []
    for index, header in enumerate(raw_headers, start=1):
        base = clean(header) or f"Column {index}"
        seen[base] = seen.get(base, 0) + 1
        headers.append(base if seen[base] == 1 else f"{base} ({seen[base]})")
    return tuple(headers)


def _detect_header_row(rows: Sequence[Sequence[Any]]) -> tuple[int, tuple[str, ...]]:
    early_rows = []
    for row_number, row in enumerate(rows[:25], start=1):
        values = [clean(value) for value in row]
        nonempty = sum(1 for value in values if value)
        early_rows.append((row_number, values, nonempty))

    candidates = [row for row in early_rows if row[2] >= 2]
    max_nonempty = max((row[2] for row in candidates), default=0)
    header_row, raw_headers = next(
        (
            (row_number, values)
            for row_number, values, nonempty in candidates
            if nonempty >= max(2, int(max_nonempty * 0.75))
        ),
        (1, early_rows[0][1] if early_rows else []),
    )
    return header_row, _unique_headers(raw_headers)


def _read_csv_table(path: Path) -> TableData:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        raw_rows = list(csv.reader(file))
    header_row, headers = _detect_header_row(raw_rows)
    rows = []
    for row_number, row in enumerate(raw_rows, start=1):
        if row_number <= header_row:
            continue
        values = [clean(value) for value in row]
        if all(value == "" for value in values):
            continue
        rows.append({"__rownum__": str(row_number), **dict(zip(headers, values[: len(headers)]))})
    return TableData(path=path, headers=headers, rows=tuple(rows), header_row=header_row)


def _read_xlsx_table(path: Path) -> TableData:
    try:
        from openpyxl import load_workbook
    except ImportError as error:
        raise RuntimeError(
            "Reading .xlsx Monday exports requires openpyxl. Export the board as CSV or run with "
            "a Python environment that has openpyxl installed.",
        ) from error

    workbook = load_workbook(path, read_only=True, data_only=True)
    sheet = workbook[workbook.sheetnames[0]]
    raw_rows = [[clean(value) for value in row] for row in sheet.iter_rows(values_only=True)]
    workbook.close()

    header_row, headers = _detect_header_row(raw_rows)
    rows = []
    for row_number, row in enumerate(raw_rows, start=1):
        if row_number <= header_row:
            continue
        values = [clean(value) for value in row]
        if all(value == "" for value in values):
            continue
        rows.append({"__rownum__": str(row_number), **dict(zip(headers, values[: len(headers)]))})
    return TableData(path=path, headers=headers, rows=tuple(rows), header_row=header_row)


def read_table(path: Path) -> TableData:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _read_csv_table(path)
    if suffix == ".xlsx":
        return _read_xlsx_table(path)
    raise ValueError(f"Unsupported Monday export file type: {path}")


def _read_template_headers(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.reader(file)
        return next(reader)


def _valid_email(value: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", value))


def _valid_url(value: str) -> bool:
    if not value:
        return True
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _map_client_status(value: str) -> str:
    text = clean(value).casefold()
    if not text:
        return ""
    if "inactive" in text:
        return "inactive"
    if "archiv" in text:
        return "archived"
    if "active" in text:
        return "active"
    if "prospect" in text or "lead" in text:
        return "prospect"
    return ""


def _status_key(value: Any) -> str:
    return re.sub(r"[\s_-]+", " ", clean(value).casefold()).strip()


def _raw_status_label(value: Any) -> str:
    return clean(value) or "<blank>"


def _map_site_status(value: Any) -> tuple[str, bool]:
    mapped = SITE_STATUS_MAPPING.get(_status_key(value))
    if mapped:
        return mapped, False
    return "active", True


def _site_status_rows(status_counts: Counter[str]) -> list[tuple[str, int, str, str]]:
    rows = []
    for raw_status, count in status_counts.most_common():
        status_value = "" if raw_status == "<blank>" else raw_status
        mapped, defaulted = _map_site_status(status_value)
        rows.append(
            (
                raw_status,
                count,
                mapped if not defaulted else "active",
                "mapped" if not defaulted else "defaulted for validation sample",
            ),
        )
    return rows


def _masked_id(kind: str, value: Any) -> str:
    text = clean(value)
    if not text:
        return f"{kind}#blank"
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]
    return f"{kind}#{digest}"


def _top_masked_rows(counter: Counter[str], kind: str, limit: int = 10) -> list[tuple[str, int]]:
    return [(_masked_id(kind, value), count) for value, count in counter.most_common(limit)]


def _invalid_address_fields(row: dict[str, str]) -> list[str]:
    issues = []
    state = _first_nonempty(row.get("STATE"), row.get("State"))
    if state and not re.match(r"^[A-Za-z]{2}$", state):
        issues.append("state")
    zip_code = _first_nonempty(row.get("ZIP"), row.get("Zip"))
    if zip_code and not re.match(r"^\d{5}(-\d{4})?$", zip_code):
        issues.append("zip")
    return issues


def _first_nonempty(*values: Any) -> str:
    for value in values:
        text = clean(value)
        if text:
            return text
    return ""


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _markdown_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> list[str]:
    if not rows:
        return ["- None"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |")
    return lines


def _source_rows(tables: dict[str, TableData]) -> list[tuple[str, str, int, str]]:
    return [
        (tables["contacts"].path.name, "contacts", len(tables["contacts"].rows), "high"),
        (tables["leads"].path.name, "clients / site-client link source", len(tables["leads"].rows), "high"),
        (tables["orders"].path.name, "jobs", len(tables["orders"].rows), "high"),
        (tables["sites"].path.name, "sites", len(tables["sites"].rows), "high"),
    ]


def _source_row_number(row: dict[str, str]) -> str:
    return clean(row.get("__rownum__"))


def _site_name_or_label(row: dict[str, str]) -> str:
    return clean(row.get("Name")) or clean(row.get("Site Name")) or clean(row.get("Item Name")) or "<blank site name>"


def _client_name_or_label(row: dict[str, str]) -> str:
    contact_name = " ".join(
        part for part in (clean(row.get("First Name")), clean(row.get("Last Name"))) if part
    )
    return clean(row.get("Account")) or contact_name or clean(row.get("Name")) or "<blank client name>"


def _client_candidate_label(
    client_id: str,
    client_contact_rows: dict[str, list[dict[str, str]]],
) -> str:
    rows = client_contact_rows.get(client_id, [])
    for row in rows:
        label = _client_name_or_label(row)
        if label and not label.startswith("<blank"):
            return label
    return ""


def _site_review_bucket(reason: str) -> str:
    return SITE_REVIEW_BUCKET_LABELS.get(reason, reason)


def _site_review_suggested_fix(reason: str) -> str:
    return SITE_REVIEW_SUGGESTED_FIXES.get(reason, "Review this row before any import.")


def _unresolved_site_review_row(
    *,
    site_row: dict[str, str],
    reason: str,
    client_id: str = "",
    client_candidate: str = "",
) -> dict[str, str]:
    return {
        "source_row_number": _source_row_number(site_row),
        "site_id": clean(site_row.get("Site ID")),
        "site_name_or_label": _site_name_or_label(site_row),
        "client_id": client_id,
        "client_candidate": client_candidate,
        "exclusion_reason": reason,
        "diagnostic_bucket": _site_review_bucket(reason),
        "suggested_fix": _site_review_suggested_fix(reason),
        "manual_client_external_id": "",
        "manual_status": "",
        "review_status": "",
        "notes": "",
    }


def _duplicate_site_review_row(site_row: dict[str, str], duplicate_group: str) -> dict[str, str]:
    return {
        "source_row_number": _source_row_number(site_row),
        "site_id": clean(site_row.get("Site ID")),
        "site_name_or_label": _site_name_or_label(site_row),
        "duplicate_group": duplicate_group,
        "suggested_action": "Choose one canonical row to keep, then mark the others skip or merge.",
        "keep_or_skip": "",
        "notes": "",
    }


def _client_status_review_row(row: dict[str, str]) -> dict[str, str]:
    raw_status = clean(row.get("Active Status"))
    return {
        "source_row_number": _source_row_number(row),
        "client_id": clean(row.get("Client ID")),
        "client_name_or_label": _client_name_or_label(row),
        "raw_client_status": raw_status,
        "current_mapping": _map_client_status(raw_status),
        "suggested_status": "",
        "review_status": "",
        "notes": "Fill suggested_status with active, inactive, prospect, or archived before import.",
    }


def _status_default_review_row(site_row: dict[str, str], defaulted_status: str) -> dict[str, str]:
    return {
        "source_row_number": _source_row_number(site_row),
        "site_id": clean(site_row.get("Site ID")),
        "site_name_or_label": _site_name_or_label(site_row),
        "raw_site_status": _raw_status_label(site_row.get("Status")),
        "defaulted_status": defaulted_status,
        "review_status": "",
        "manual_status": "",
        "notes": "Defaulted for validation only. Fill manual_status before import if needed.",
    }


def _analyze_monday_exports(tables: dict[str, TableData]) -> MondayAnalysis:
    client_account_names: dict[str, set[str]] = defaultdict(set)
    client_contact_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    all_contact_client_ids: set[str] = set()
    contact_skips: Counter[str] = Counter()
    for row in tables["contacts"].rows:
        client_id = clean(row.get("Client ID"))
        account = clean(row.get("Account"))
        if not client_id:
            contact_skips["blank_client_id"] += 1
            continue
        all_contact_client_ids.add(client_id)
        if not account:
            contact_skips["blank_account"] += 1
            continue
        client_account_names[client_id].add(_normalized_name(account))
        client_contact_rows[client_id].append(row)

    client_candidates: dict[str, dict[str, str]] = {}
    client_rejections: Counter[str] = Counter()
    client_rejection_reason_by_id: dict[str, str] = {}
    client_status_review_rows: list[dict[str, str]] = []
    for client_id, contact_rows in client_contact_rows.items():
        account_keys = client_account_names[client_id]
        if len(account_keys) != 1:
            client_rejections["ambiguous_account_name"] += len(contact_rows)
            client_rejection_reason_by_id[client_id] = "ambiguous_account_name"
            continue
        chosen = contact_rows[0]
        status = _map_client_status(chosen.get("Active Status", ""))
        if not status:
            client_rejections["unmapped_client_status"] += len(contact_rows)
            client_rejection_reason_by_id[client_id] = "unmapped_client_status"
            client_status_review_rows.extend(_client_status_review_row(row) for row in contact_rows)
            continue
        email = clean(chosen.get("Email"))
        if email and not _valid_email(email):
            email = ""
        contact_name = (
            " ".join(part for part in [clean(chosen.get("First Name")), clean(chosen.get("Last Name"))] if part)
            or clean(chosen.get("Name"))
        )
        client_candidates[client_id] = {
            "account": clean(chosen.get("Account")),
            "status": status,
            "primary_contact_name": contact_name,
            "email": email,
            "phone": clean(chosen.get("Phone")),
            "source_row": clean(chosen.get("__rownum__")),
        }

    site_to_client_ids: dict[str, set[str]] = defaultdict(set)
    lead_site_ids_seen: set[str] = set()
    lead_blank_client_by_site: Counter[str] = Counter()
    for row in tables["leads"].rows:
        site_id = clean(row.get("Site ID"))
        client_id = clean(row.get("Client ID"))
        if not site_id:
            continue
        lead_site_ids_seen.add(site_id)
        if client_id:
            site_to_client_ids[site_id].add(client_id)
        else:
            lead_blank_client_by_site[site_id] += 1

    site_rejections: Counter[str] = Counter()
    relationship_reasons: Counter[str] = Counter()
    unresolved_site_ids: Counter[str] = Counter()
    unresolved_client_ids: Counter[str] = Counter()
    site_status_counts: Counter[str] = Counter()
    site_rows_by_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    unresolved_site_review_rows: list[dict[str, str]] = []
    for row in tables["sites"].rows:
        site_status_counts[_raw_status_label(row.get("Status"))] += 1
        if _invalid_address_fields(row):
            relationship_reasons["invalid_address_fields"] += 1
        site_id = clean(row.get("Site ID"))
        if not site_id:
            site_rejections["blank_site_id"] += 1
            relationship_reasons["blank_site_id"] += 1
            unresolved_site_review_rows.append(
                _unresolved_site_review_row(site_row=row, reason="blank_site_id"),
            )
            continue
        site_rows_by_id[site_id].append(row)

    duplicate_site_review_rows: list[dict[str, str]] = []
    candidate_sites: list[tuple[str, str, dict[str, str]]] = []
    for site_id, site_rows in site_rows_by_id.items():
        if len(site_rows) != 1:
            reason = "duplicate_site_id_in_site_information"
            site_rejections[reason] += len(site_rows)
            unresolved_site_ids[site_id] += len(site_rows)
            duplicate_group = f"site_id:{site_id}"
            for site_row in site_rows:
                duplicate_site_review_rows.append(_duplicate_site_review_row(site_row, duplicate_group))
                unresolved_site_review_rows.append(
                    _unresolved_site_review_row(site_row=site_row, reason=reason),
                )
            continue
        site_row = site_rows[0]
        if not clean(site_row.get("Name")):
            reason = "missing_site_name"
            site_rejections[reason] += 1
            relationship_reasons[reason] += 1
            unresolved_site_ids[site_id] += 1
            unresolved_site_review_rows.append(
                _unresolved_site_review_row(site_row=site_row, reason=reason),
            )
            continue
        linked_clients = site_to_client_ids.get(site_id, set())
        if len(linked_clients) != 1:
            if len(linked_clients) > 1:
                reason = "ambiguous_site_to_client_link"
            elif site_id in lead_blank_client_by_site:
                reason = "site_has_no_client_id"
            else:
                reason = "site_id_not_found_in_leads"
            site_rejections[reason] += 1
            relationship_reasons[reason] += 1
            unresolved_site_ids[site_id] += 1
            unresolved_site_review_rows.append(
                _unresolved_site_review_row(site_row=site_row, reason=reason),
            )
            continue
        client_id = next(iter(linked_clients))
        if client_id not in client_candidates:
            client_reason = client_rejection_reason_by_id.get(client_id)
            if client_id not in all_contact_client_ids:
                reason = "client_id_not_found_in_contacts"
            elif client_reason == "ambiguous_account_name":
                reason = "linked_client_ambiguous_account_name"
            elif client_reason == "unmapped_client_status":
                reason = "linked_client_unmapped_client_status"
            else:
                reason = "no_reviewable_client_candidate"
            site_rejections[reason] += 1
            relationship_reasons[reason] += 1
            unresolved_client_ids[client_id] += 1
            unresolved_site_review_rows.append(
                _unresolved_site_review_row(
                    site_row=site_row,
                    reason=reason,
                    client_id=client_id,
                    client_candidate=_client_candidate_label(client_id, client_contact_rows),
                ),
            )
            continue
        candidate_sites.append((site_id, client_id, site_row))

    return MondayAnalysis(
        tables=tables,
        client_account_names=client_account_names,
        client_contact_rows=client_contact_rows,
        all_contact_client_ids=all_contact_client_ids,
        contact_skips=contact_skips,
        client_candidates=client_candidates,
        client_rejections=client_rejections,
        client_rejection_reason_by_id=client_rejection_reason_by_id,
        site_to_client_ids=site_to_client_ids,
        lead_blank_client_by_site=lead_blank_client_by_site,
        site_rejections=site_rejections,
        relationship_reasons=relationship_reasons,
        unresolved_site_ids=unresolved_site_ids,
        unresolved_client_ids=unresolved_client_ids,
        site_status_counts=site_status_counts,
        site_rows_by_id=site_rows_by_id,
        candidate_sites=candidate_sites,
        unresolved_site_review_rows=unresolved_site_review_rows,
        client_status_review_rows=client_status_review_rows,
        duplicate_site_review_rows=duplicate_site_review_rows,
    )


def _select_sample_sites(
    candidate_sites: Sequence[tuple[str, str, dict[str, str]]],
    *,
    max_clients: int,
    max_sites: int,
) -> tuple[list[str], list[tuple[str, str, dict[str, str]]]]:
    sites_by_client: dict[str, list[tuple[str, str, dict[str, str]]]] = defaultdict(list)
    client_order: list[str] = []
    for site in candidate_sites:
        _site_id, client_id, _site_row = site
        sites_by_client[client_id].append(site)
        if client_id not in client_order:
            client_order.append(client_id)

    selected_clients = client_order[:max_clients]
    selected_sites: list[tuple[str, str, dict[str, str]]] = []
    per_client_first_pass = max(1, min(2, max_sites))
    for client_id in selected_clients:
        for site in sites_by_client[client_id][:per_client_first_pass]:
            if len(selected_sites) < max_sites:
                selected_sites.append(site)
    for client_id in selected_clients:
        for site in sites_by_client[client_id][per_client_first_pass:]:
            if len(selected_sites) >= max_sites:
                break
            selected_sites.append(site)
        if len(selected_sites) >= max_sites:
            break

    selected_client_ids = list(dict.fromkeys(client_id for _site_id, client_id, _site_row in selected_sites))
    selected_client_ids = selected_client_ids[:max_clients]
    selected_sites = [site for site in selected_sites if site[1] in set(selected_client_ids)][:max_sites]
    return selected_client_ids, selected_sites


def _render_mapping_report(
    *,
    tables: dict[str, TableData],
    sample_label: str,
    client_rows: Sequence[dict[str, str]],
    site_rows: Sequence[dict[str, str]],
    candidate_sites: int,
    site_rejections: Counter[str],
    client_rejections: Counter[str],
    contact_skips: Counter[str],
    relationship_reasons: Counter[str],
    unresolved_site_ids: Counter[str],
    unresolved_client_ids: Counter[str],
    site_rows_by_id: dict[str, list[dict[str, str]]],
    client_account_names: dict[str, set[str]],
    site_status_counts: Counter[str],
    site_status_default_reasons: Counter[str],
    site_status_defaulted: int,
    site_urls_omitted: int,
) -> str:
    missing_required = []
    if "Client ID" not in tables["contacts"].headers or "Account" not in tables["contacts"].headers:
        missing_required.append("Contacts export needs Client ID and Account for reviewed client mapping.")
    if "Site ID" not in tables["sites"].headers or "Name" not in tables["sites"].headers:
        missing_required.append("Site Information export needs Site ID and Name for reviewed site mapping.")
    if "Site ID" not in tables["leads"].headers or "Client ID" not in tables["leads"].headers:
        missing_required.append("Leads export needs Site ID and Client ID for site-client linking.")
    missing_required_lines = (
        [f"- {item}" for item in missing_required]
        if missing_required
        else ["- None for the reviewed Clients/Sites mapping path."]
    )
    duplicate_site_groups = sum(1 for rows in site_rows_by_id.values() if len(rows) > 1)
    duplicate_contact_client_groups = sum(1 for names in client_account_names.values() if len(names) > 1)
    relationship_rows = [
        ("site has no Client ID", relationship_reasons.get("site_has_no_client_id", 0)),
        ("Site ID not found in Leads", relationship_reasons.get("site_id_not_found_in_leads", 0)),
        ("Client ID not found in Contacts", relationship_reasons.get("client_id_not_found_in_contacts", 0)),
        (
            "duplicate/ambiguous Client ID",
            relationship_reasons.get("linked_client_ambiguous_account_name", 0)
            + relationship_reasons.get("ambiguous_account_name", 0),
        ),
        ("blank Site ID", relationship_reasons.get("blank_site_id", 0)),
        ("blank site name", relationship_reasons.get("missing_site_name", 0)),
        ("invalid address fields (diagnostic only)", relationship_reasons.get("invalid_address_fields", 0)),
    ]
    safe_for_next_sample = not client_rejections and not site_rejections and site_status_defaulted == 0

    lines = [
        "# Monday Mapping Review",
        "",
        f"- Generated at: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Scope: private Monday export mapping to V2 {sample_label} Clients/Sites templates.",
        "- Privacy: no full source records, client names, site names, addresses, emails, URLs, or IDs are included here.",
        "- Safety: no database writes, no provider calls, no imports.",
        "",
        "## Files Inspected",
        *_markdown_table(["File", "Inferred Entity", "Rows", "Confidence"], _source_rows(tables)),
        "",
        "## Mapping Plan",
        *_markdown_table(
            ["V2 Target", "Source Export", "Source Columns", "Notes"],
            [
                ("clients.client_external_id / legacy_id", "Contacts", "Client ID", "Preserved from Monday source ID."),
                (
                    "clients.canonical_name",
                    "Contacts",
                    "Account",
                    "Only used when exactly one explicit Account value exists for the Client ID.",
                ),
                ("clients.status", "Contacts", "Active Status", "Mapped to V2 client statuses when possible."),
                (
                    "clients.primary_contact_name / email / phone",
                    "Contacts",
                    "First Name, Last Name, Name, Email, Phone",
                    "Optional fields; invalid email text is omitted.",
                ),
                ("sites.site_external_id / legacy_id", "Site Information", "Site ID", "Preserved from Monday source ID."),
                (
                    "sites.client_external_id",
                    "Leads",
                    "Site ID + Client ID",
                    "Only used when a Site ID maps to exactly one Client ID and that Client ID has a reviewed Account.",
                ),
                ("sites.canonical_name", "Site Information", "Name", "Required site display name."),
                ("sites.address/city/state/zip", "Site Information", "Address, CITY, STATE, ZIP", "Mapped when present."),
                ("sites.drive_folder_url", "Site Information", "Gdrive", "Only retained when it validates as http(s)."),
                (
                    "jobs",
                    "Order",
                    "Job Site, SERVICE, Scheduled date, Job ID, Site ID, Client ID",
                    "Mapping notes only; not normalized until Clients/Sites pass.",
                ),
            ],
        ),
        "",
        f"## Normalized {sample_label.title()} Sample",
        f"- Clients written: {len(client_rows)}",
        f"- Sites written: {len(site_rows)}",
        f"- Candidate sites ready before sample limit: {candidate_sites}",
        f"- Sites excluded or unresolved before sampling: {sum(site_rejections.values())}",
        f"- Client candidates excluded before sampling: {sum(client_rejections.values())}",
        f"- Site rows defaulted to `active` in selected sample pending Bryce review: {site_status_defaulted}",
        f"- Non-http(s) site Gdrive values omitted from selected sample: {site_urls_omitted}",
        "",
        "## Monday Site Status Values Found",
        *_markdown_table(
            ["Raw Monday Status", "Rows", "Proposed V2 Status", "Action"],
            _site_status_rows(site_status_counts),
        ),
        "",
        "## Proposed V2 Site Status Mapping",
        *_markdown_table(["Raw Monday Status", "V2 Status", "Notes"], SITE_STATUS_MAPPING_REVIEW_ROWS),
        "",
        "## Rows Defaulted To Active",
        f"- Selected sample rows defaulted to `active`: {site_status_defaulted}",
        *_markdown_table(["Default Reason", "Rows"], sorted(site_status_default_reasons.items())),
        "",
        "## Excluded / Unresolved Site Reasons",
        *_markdown_table(["Reason", "Rows Affected"], sorted(site_rejections.items())),
        "",
        "## Excluded Client Candidate Reasons",
        *_markdown_table(["Reason", "Rows Affected"], sorted(client_rejections.items())),
        "",
        "## Contact Rows Skipped Before Client Candidate Review",
        *_markdown_table(["Reason", "Rows Affected"], sorted(contact_skips.items())),
        "",
        "## Missing Relationship / Data Quality Signals",
        *_markdown_table(["Signal", "Rows Affected"], relationship_rows),
        "",
        "## Top Sanitized Unresolved Site IDs",
        *_markdown_table(["Sanitized Site Token", "Rows Affected"], _top_masked_rows(unresolved_site_ids, "site")),
        "",
        "## Top Sanitized Unresolved Client IDs",
        *_markdown_table(["Sanitized Client Token", "Rows Affected"], _top_masked_rows(unresolved_client_ids, "client")),
        "",
        "## Missing Required Columns",
        *missing_required_lines,
        "",
        "## Duplicate Candidates",
        f"- Site Information duplicate Site ID groups: {duplicate_site_groups}",
        f"- Contacts ambiguous Client ID to Account groups: {duplicate_contact_client_groups}",
        "",
        "## Columns That Need Bryce Review",
        "- Site Information `Status` is mostly blank or unclear in this export; any default to `active` is for validation only.",
        "- Confirm whether Contacts `Account` is the right canonical V2 Client name.",
        "- Confirm whether Site Information `Gdrive` is a site folder URL when it is an http(s) URL.",
        "- Review Order export mapping after Clients/Sites pass; jobs were intentionally not normalized now.",
        "- Decide how to treat Site Information rows with no Leads `Site ID` to `Client ID` link.",
        "",
        "## Recommendation",
        "- Bryce should manually review Monday Site Information `Status` values before any import.",
        "- Bryce should review excluded site/client relationship buckets before expanding beyond samples.",
        (
            "- Medium sample safety: clean for import readiness only if the generated CSVs pass validator and the "
            "status defaults are accepted as sample-only placeholders."
            if not safe_for_next_sample
            else "- Medium sample safety: relationship diagnostics are clean; still validate only and do not import."
        ),
        "",
        "## Recommended Next Action",
        "- Run the sample validator only. If clean, review the private CSVs manually before increasing sample size.",
        "- Do not import, do not write to the database, and do not normalize Jobs/Documents until Clients/Sites are accepted.",
    ]
    return "\n".join(lines)


def prepare_tiny_sample(
    *,
    contacts_path: Path,
    leads_path: Path,
    sites_path: Path,
    orders_path: Path,
    clients_template_path: Path,
    sites_template_path: Path,
    clients_output_path: Path,
    sites_output_path: Path,
    report_path: Path,
    max_clients: int = TINY_CLIENT_LIMIT,
    max_sites: int = TINY_SITE_LIMIT,
    sample_label: str = "tiny",
) -> PrepSummary:
    if max_clients < 1:
        raise ValueError("max_clients must be at least 1.")
    if max_sites < 1:
        raise ValueError("max_sites must be at least 1.")

    tables = {
        "contacts": read_table(contacts_path),
        "leads": read_table(leads_path),
        "orders": read_table(orders_path),
        "sites": read_table(sites_path),
    }

    analysis = _analyze_monday_exports(tables)
    selected_clients, selected_sites = _select_sample_sites(
        analysis.candidate_sites,
        max_clients=max_clients,
        max_sites=max_sites,
    )

    client_headers = _read_template_headers(clients_template_path)
    site_headers = _read_template_headers(sites_template_path)
    client_rows_out = []
    for client_id in selected_clients:
        client = analysis.client_candidates[client_id]
        row = {header: "" for header in client_headers}
        row.update(
            {
                "source_system": "monday",
                "legacy_source": "monday_contacts",
                "legacy_id": client_id,
                "client_external_id": client_id,
                "canonical_name": client["account"],
                "status": client["status"],
                "primary_contact_name": client["primary_contact_name"],
                "email": client["email"],
                "phone": client["phone"],
                "notes": (
                    f"{sample_label.title()} validation sample only. "
                    f"Client account sourced from Contacts row {client['source_row']}."
                ),
            },
        )
        client_rows_out.append(row)

    site_rows_out = []
    site_status_defaulted = 0
    site_status_default_reasons: Counter[str] = Counter()
    site_urls_omitted = 0
    for site_id, client_id, site in selected_sites:
        drive_url = clean(site.get("Gdrive"))
        if drive_url and not _valid_url(drive_url):
            drive_url = ""
            site_urls_omitted += 1
        site_status, status_defaulted = _map_site_status(site.get("Status", ""))
        raw_status = clean(site.get("Status"))
        if status_defaulted:
            site_status_defaulted += 1
            site_status_default_reasons["blank_status" if not raw_status else "unmapped_status"] += 1
        notes = (
            f"{sample_label.title()} validation sample only. "
            "Client link proven by Leads Site ID to Client ID. "
            f"Site Information row {clean(site.get('__rownum__'))}. "
        )
        if status_defaulted:
            notes += "Status defaulted to active for validation pending Bryce review."
        else:
            notes += f"Status mapped from Monday Status to {site_status}."
        if not drive_url and clean(site.get("Gdrive")):
            notes += " Source Gdrive value omitted because it was not an http(s) URL."
        row = {header: "" for header in site_headers}
        row.update(
            {
                "source_system": "monday",
                "legacy_source": "monday_site_information",
                "legacy_id": site_id,
                "site_external_id": site_id,
                "client_external_id": client_id,
                "canonical_name": clean(site.get("Name")),
                "site_code": site_id,
                "status": site_status,
                "address": clean(site.get("Address")),
                "city": _first_nonempty(site.get("CITY"), site.get("City")),
                "state": _first_nonempty(site.get("STATE"), site.get("State")),
                "zip": _first_nonempty(site.get("ZIP"), site.get("Zip")),
                "drive_folder_url": drive_url,
                "notes": notes,
            },
        )
        site_rows_out.append(row)

    _write_csv(clients_output_path, client_headers, client_rows_out)
    _write_csv(sites_output_path, site_headers, site_rows_out)

    report = _render_mapping_report(
        tables=tables,
        sample_label=sample_label,
        client_rows=client_rows_out,
        site_rows=site_rows_out,
        candidate_sites=len(analysis.candidate_sites),
        site_rejections=analysis.site_rejections,
        client_rejections=analysis.client_rejections,
        contact_skips=analysis.contact_skips,
        relationship_reasons=analysis.relationship_reasons,
        unresolved_site_ids=analysis.unresolved_site_ids,
        unresolved_client_ids=analysis.unresolved_client_ids,
        site_rows_by_id=analysis.site_rows_by_id,
        client_account_names=analysis.client_account_names,
        site_status_counts=analysis.site_status_counts,
        site_status_default_reasons=site_status_default_reasons,
        site_status_defaulted=site_status_defaulted,
        site_urls_omitted=site_urls_omitted,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    return PrepSummary(
        clients_written=len(client_rows_out),
        sites_written=len(site_rows_out),
        candidate_sites=len(analysis.candidate_sites),
        site_rejections=dict(analysis.site_rejections),
        client_rejections=dict(analysis.client_rejections),
        site_status_defaulted=site_status_defaulted,
        site_urls_omitted=site_urls_omitted,
        clients_path=clients_output_path,
        sites_path=sites_output_path,
        report_path=report_path,
    )


class ReviewedMappingError(ValueError):
    """Raised when reviewed mapping CSVs are incomplete or unsafe to apply."""


def _normalized_review_value(value: Any) -> str:
    return re.sub(r"[\s-]+", "_", clean(value).casefold()).strip("_")


def _review_status(row: dict[str, str]) -> str:
    return _normalized_review_value(row.get("review_status"))


def _review_csv_row(row: dict[str, str]) -> str:
    return clean(row.get("__csv_rownum__")) or "unknown"


def _read_review_csv(path: Path, required_columns: Sequence[str], label: str) -> list[dict[str, str]]:
    if not path.exists():
        raise ReviewedMappingError(f"Missing required review CSV: {path}")
    if not path.is_file():
        raise ReviewedMappingError(f"Review CSV path is not a file: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = tuple(reader.fieldnames or ())
        missing = [column for column in required_columns if column not in fieldnames]
        if missing:
            raise ReviewedMappingError(
                f"{label} is missing required review column(s): {', '.join(missing)}",
            )
        rows = []
        for row_number, row in enumerate(reader, start=2):
            rows.append(
                {
                    key: clean(value)
                    for key, value in row.items()
                    if key is not None
                }
                | {"__csv_rownum__": str(row_number)}
            )
    return rows


def _ensure_known_review_status(row: dict[str, str], label: str) -> str:
    status = _review_status(row)
    if status not in KNOWN_REVIEW_STATUSES:
        raise ReviewedMappingError(
            f"{label} row {_review_csv_row(row)} has unsupported review_status `{clean(row.get('review_status'))}`.",
        )
    return status


def _review_file_paths(review_pack_dir: Path) -> dict[str, Path]:
    return {
        "unresolved_sites": review_pack_dir / "unresolved_sites_review.csv",
        "client_status": review_pack_dir / "client_status_review.csv",
        "duplicate_sites": review_pack_dir / "duplicate_sites_review.csv",
        "status_defaults": review_pack_dir / "status_defaults_review.csv",
    }


def _site_rows_by_source(tables: dict[str, TableData]) -> dict[str, dict[str, str]]:
    rows_by_source: dict[str, dict[str, str]] = {}
    for row in tables["sites"].rows:
        source_row = _source_row_number(row)
        if source_row:
            rows_by_source[source_row] = row
    return rows_by_source


def _client_candidate_from_reviewed_status(
    analysis: MondayAnalysis,
    *,
    client_id: str,
    status: str,
) -> dict[str, str]:
    contact_rows = analysis.client_contact_rows.get(client_id, [])
    if not contact_rows:
        raise ReviewedMappingError(
            "An approved client status row references a Client ID that is not present in Contacts.",
        )

    normalized_accounts = {name for name in analysis.client_account_names.get(client_id, set()) if name}
    if len(normalized_accounts) != 1:
        raise ReviewedMappingError(
            "An approved client status row cannot build a client because the Contacts Account is blank or ambiguous.",
        )

    chosen = contact_rows[0]
    account = clean(chosen.get("Account"))
    if not account:
        raise ReviewedMappingError(
            "An approved client status row cannot build a client because the Contacts Account is blank.",
        )
    email = clean(chosen.get("Email"))
    if email and not _valid_email(email):
        email = ""
    contact_name = (
        " ".join(part for part in [clean(chosen.get("First Name")), clean(chosen.get("Last Name"))] if part)
        or clean(chosen.get("Name"))
    )
    return {
        "account": account,
        "status": status,
        "primary_contact_name": contact_name,
        "email": email,
        "phone": clean(chosen.get("Phone")),
        "source_row": clean(chosen.get("__rownum__")),
    }


def _build_reviewed_client_candidates(
    analysis: MondayAnalysis,
    client_status_rows: Sequence[dict[str, str]],
    skipped_review_rows: Counter[str],
) -> dict[str, dict[str, str]]:
    candidates = dict(analysis.client_candidates)
    approved_statuses: dict[str, str] = {}
    for row in client_status_rows:
        status = _ensure_known_review_status(row, "client_status_review.csv")
        if status != APPROVED_REVIEW_STATUS:
            skipped_review_rows[f"client_status:{status or 'blank'}"] += 1
            continue

        client_id = clean(row.get("client_id"))
        suggested_status = _normalized_review_value(row.get("suggested_status"))
        if not client_id:
            raise ReviewedMappingError(
                f"client_status_review.csv row {_review_csv_row(row)} is approved but lacks client_id.",
            )
        if not suggested_status:
            raise ReviewedMappingError(
                f"client_status_review.csv row {_review_csv_row(row)} is approved but lacks suggested_status.",
            )
        if suggested_status not in CLIENT_STATUS_VALUES:
            raise ReviewedMappingError(
                f"client_status_review.csv row {_review_csv_row(row)} has invalid suggested_status `{suggested_status}`.",
            )
        existing = approved_statuses.get(client_id)
        if existing and existing != suggested_status:
            raise ReviewedMappingError(
                "client_status_review.csv has conflicting approved statuses for the same Client ID.",
            )
        approved_statuses[client_id] = suggested_status

    for client_id, status in approved_statuses.items():
        candidates[client_id] = _client_candidate_from_reviewed_status(
            analysis,
            client_id=client_id,
            status=status,
        )
    return candidates


def _approved_unresolved_site_rows(
    unresolved_rows: Sequence[dict[str, str]],
    skipped_review_rows: Counter[str],
) -> dict[str, dict[str, str]]:
    approved: dict[str, dict[str, str]] = {}
    for row in unresolved_rows:
        status = _ensure_known_review_status(row, "unresolved_sites_review.csv")
        if status != APPROVED_REVIEW_STATUS:
            skipped_review_rows[f"unresolved_sites:{status or 'blank'}"] += 1
            continue

        source_row = clean(row.get("source_row_number"))
        manual_client = clean(row.get("manual_client_external_id"))
        if not source_row:
            raise ReviewedMappingError(
                f"unresolved_sites_review.csv row {_review_csv_row(row)} is approved but lacks source_row_number.",
            )
        if not manual_client:
            raise ReviewedMappingError(
                f"unresolved_sites_review.csv row {_review_csv_row(row)} is approved but lacks manual_client_external_id.",
            )
        if source_row in approved:
            raise ReviewedMappingError(
                "unresolved_sites_review.csv has multiple approved rows for the same source_row_number.",
            )
        approved[source_row] = row
    return approved


def _approved_status_default_rows(
    status_default_rows: Sequence[dict[str, str]],
    skipped_review_rows: Counter[str],
) -> dict[str, str]:
    approved: dict[str, str] = {}
    for row in status_default_rows:
        status = _ensure_known_review_status(row, "status_defaults_review.csv")
        if status != APPROVED_REVIEW_STATUS:
            skipped_review_rows[f"status_defaults:{status or 'blank'}"] += 1
            continue

        source_row = clean(row.get("source_row_number"))
        manual_status = _normalized_review_value(row.get("manual_status"))
        if not source_row:
            raise ReviewedMappingError(
                f"status_defaults_review.csv row {_review_csv_row(row)} is approved but lacks source_row_number.",
            )
        if not manual_status:
            raise ReviewedMappingError(
                f"status_defaults_review.csv row {_review_csv_row(row)} is approved but lacks manual_status.",
            )
        if manual_status not in SITE_STATUS_VALUES:
            raise ReviewedMappingError(
                f"status_defaults_review.csv row {_review_csv_row(row)} has invalid manual_status `{manual_status}`.",
            )
        if source_row in approved and approved[source_row] != manual_status:
            raise ReviewedMappingError(
                "status_defaults_review.csv has conflicting approved statuses for the same source_row_number.",
            )
        approved[source_row] = manual_status
    return approved


def _duplicate_decision_rows(
    duplicate_rows: Sequence[dict[str, str]],
    skipped_review_rows: Counter[str],
) -> dict[str, str]:
    decisions: dict[str, str] = {}
    grouped: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for row in duplicate_rows:
        source_row = clean(row.get("source_row_number"))
        decision = _normalized_review_value(row.get("keep_or_skip"))
        if not source_row:
            raise ReviewedMappingError(
                f"duplicate_sites_review.csv row {_review_csv_row(row)} lacks source_row_number.",
            )
        if decision not in DUPLICATE_DECISIONS:
            raise ReviewedMappingError(
                f"duplicate_sites_review.csv row {_review_csv_row(row)} has no clear keep/skip/needs_source_fix decision.",
            )
        if source_row in decisions:
            raise ReviewedMappingError(
                "duplicate_sites_review.csv has multiple decisions for the same source_row_number.",
            )
        decisions[source_row] = decision
        grouped[clean(row.get("duplicate_group"))].append((source_row, decision))
        if decision != "keep":
            skipped_review_rows[f"duplicate_sites:{decision}"] += 1

    for duplicate_group, group_decisions in grouped.items():
        keep_rows = [source_row for source_row, decision in group_decisions if decision == "keep"]
        if len(keep_rows) > 1:
            raise ReviewedMappingError(
                f"duplicate_sites_review.csv group `{duplicate_group}` has more than one keep decision.",
            )
    return decisions


def _reviewed_manual_site_status(
    *,
    site_row: dict[str, str],
    unresolved_review_row: dict[str, str] | None,
    approved_status_defaults: dict[str, str],
) -> tuple[str, bool]:
    source_row = _source_row_number(site_row)
    manual_status = ""
    if unresolved_review_row is not None:
        manual_status = _normalized_review_value(unresolved_review_row.get("manual_status"))
    if not manual_status:
        manual_status = approved_status_defaults.get(source_row, "")
    if manual_status:
        if manual_status not in SITE_STATUS_VALUES:
            raise ReviewedMappingError(
                f"Approved site source row {source_row} has invalid manual_status `{manual_status}`.",
            )
        return manual_status, True

    mapped_status, defaulted = _map_site_status(site_row.get("Status", ""))
    if defaulted:
        raise ReviewedMappingError(
            f"Approved site source row {source_row} still has an unknown site status after review.",
        )
    return mapped_status, False


def _client_output_row(
    *,
    client_id: str,
    client: dict[str, str],
    client_headers: Sequence[str],
    sample_label: str,
) -> dict[str, str]:
    row = {header: "" for header in client_headers}
    row.update(
        {
            "source_system": "monday",
            "legacy_source": "monday_contacts",
            "legacy_id": client_id,
            "client_external_id": client_id,
            "canonical_name": client["account"],
            "status": client["status"],
            "primary_contact_name": client["primary_contact_name"],
            "email": client["email"],
            "phone": client["phone"],
            "notes": (
                f"{sample_label.title()} validation sample only. "
                f"Client account sourced from Contacts row {client['source_row']} after reviewed mapping."
            ),
        },
    )
    return row


def _site_output_row(
    *,
    site_id: str,
    client_id: str,
    site: dict[str, str],
    site_status: str,
    status_was_manual: bool,
    site_headers: Sequence[str],
    sample_label: str,
) -> tuple[dict[str, str], bool]:
    drive_url = clean(site.get("Gdrive"))
    site_url_omitted = False
    if drive_url and not _valid_url(drive_url):
        drive_url = ""
        site_url_omitted = True
    notes = (
        f"{sample_label.title()} validation sample only. "
        "Client link and status are from reviewed Monday mapping decisions. "
        f"Site Information row {clean(site.get('__rownum__'))}. "
    )
    if status_was_manual:
        notes += f"Status manually reviewed as {site_status}."
    else:
        notes += f"Status mapped from Monday Status to {site_status}."
    if site_url_omitted:
        notes += " Source Gdrive value omitted because it was not an http(s) URL."

    row = {header: "" for header in site_headers}
    row.update(
        {
            "source_system": "monday",
            "legacy_source": "monday_site_information",
            "legacy_id": site_id,
            "site_external_id": site_id,
            "client_external_id": client_id,
            "canonical_name": clean(site.get("Name")),
            "site_code": site_id,
            "status": site_status,
            "address": clean(site.get("Address")),
            "city": _first_nonempty(site.get("CITY"), site.get("City")),
            "state": _first_nonempty(site.get("STATE"), site.get("State")),
            "zip": _first_nonempty(site.get("ZIP"), site.get("Zip")),
            "drive_folder_url": drive_url,
            "notes": notes,
        },
    )
    return row, site_url_omitted


def _run_reviewed_sample_validation(
    *,
    clients_path: Path,
    sites_path: Path,
    report_dir: Path,
) -> tuple[dict[str, Any], Path, Path]:
    try:
        from scripts.validate_import_templates import validate_import_templates, write_report_outputs
    except ModuleNotFoundError:
        api_root = Path(__file__).resolve().parents[1]
        if str(api_root) not in sys.path:
            sys.path.insert(0, str(api_root))
        from scripts.validate_import_templates import validate_import_templates, write_report_outputs

    report = validate_import_templates(clients=clients_path, sites=sites_path)
    output_json = report_dir / "reviewed_sample_validation.json"
    output_md = report_dir / "reviewed_sample_validation.md"
    write_report_outputs(report, output_json=output_json, output_md=output_md)
    return report, output_json, output_md


def _render_reviewed_sample_report(
    *,
    output_dir: Path,
    clients_path: Path,
    sites_path: Path,
    clients_written: int,
    sites_written: int,
    approved_unresolved_sites: int,
    approved_status_defaults: int,
    kept_duplicate_sites: int,
    skipped_review_rows: Counter[str],
    site_urls_omitted: int,
    validation: Mapping[str, Any],
) -> str:
    validation_totals = validation.get("totals", {})
    return "\n".join(
        [
            "# Reviewed Monday Mapping Application Report",
            "",
            f"- Generated at: `{datetime.now(timezone.utc).isoformat()}`",
            f"- Output folder: `{output_dir}`",
            "- Purpose: private reviewed Clients/Sites validation sample generation only.",
            "- Safety: no database writes, no provider calls, no V1 migration apply, and no real import.",
            "",
            "## Outputs",
            *_markdown_table(
                ["Output", "Path", "Rows"],
                [
                    ("clients", clients_path, clients_written),
                    ("sites", sites_path, sites_written),
                ],
            ),
            "",
            "## Reviewed Rows Applied",
            *_markdown_table(
                ["Source", "Rows"],
                [
                    ("approved unresolved site mappings", approved_unresolved_sites),
                    ("approved status default mappings", approved_status_defaults),
                    ("duplicate rows kept", kept_duplicate_sites),
                    ("non-http(s) site URLs omitted", site_urls_omitted),
                ],
            ),
            "",
            "## Rows Skipped By Review Decision",
            *_markdown_table(["Decision", "Rows"], sorted(skipped_review_rows.items())),
            "",
            "## Validation Summary",
            f"- Ready: {'YES' if validation.get('ready') else 'NO'}",
            f"- Total rows: {validation_totals.get('total_rows', 0)}",
            f"- Valid rows: {validation_totals.get('valid_rows', 0)}",
            f"- Invalid rows: {validation_totals.get('invalid_rows', 0)}",
            f"- Duplicate rows: {validation_totals.get('duplicate_rows', 0)}",
            f"- Unresolved references: {validation_totals.get('unresolved_references', 0)}",
            "",
            "## Stop Conditions",
            *([f"- {condition}" for condition in validation.get("stop_conditions", [])] or ["- None"]),
            "",
            "## Safety",
            "- Validation sample only.",
            "- No Clients, Sites, Jobs, Documents, Emails, or database records were written.",
            "- Review outputs may contain private paths and must remain ignored.",
            "",
        ],
    )


def prepare_reviewed_sample(
    *,
    contacts_path: Path,
    leads_path: Path,
    sites_path: Path,
    orders_path: Path,
    clients_template_path: Path,
    sites_template_path: Path,
    review_pack_dir: Path,
    clients_output_path: Path,
    sites_output_path: Path,
    report_dir: Path,
    max_clients: int | None = None,
    max_sites: int | None = None,
) -> ReviewedSampleSummary:
    if max_clients is not None and max_clients < 1:
        raise ReviewedMappingError("max_clients must be at least 1 when provided.")
    if max_sites is not None and max_sites < 1:
        raise ReviewedMappingError("max_sites must be at least 1 when provided.")

    tables = {
        "contacts": read_table(contacts_path),
        "leads": read_table(leads_path),
        "orders": read_table(orders_path),
        "sites": read_table(sites_path),
    }
    analysis = _analyze_monday_exports(tables)

    review_paths = _review_file_paths(review_pack_dir)
    unresolved_rows = _read_review_csv(
        review_paths["unresolved_sites"],
        UNRESOLVED_SITES_REVIEW_COLUMNS,
        "unresolved_sites_review.csv",
    )
    client_status_rows = _read_review_csv(
        review_paths["client_status"],
        CLIENT_STATUS_REVIEW_COLUMNS,
        "client_status_review.csv",
    )
    duplicate_rows = _read_review_csv(
        review_paths["duplicate_sites"],
        DUPLICATE_SITES_REVIEW_COLUMNS,
        "duplicate_sites_review.csv",
    )
    status_default_rows = _read_review_csv(
        review_paths["status_defaults"],
        STATUS_DEFAULTS_REVIEW_COLUMNS,
        "status_defaults_review.csv",
    )

    skipped_review_rows: Counter[str] = Counter()
    reviewed_client_candidates = _build_reviewed_client_candidates(
        analysis,
        client_status_rows,
        skipped_review_rows,
    )
    approved_unresolved = _approved_unresolved_site_rows(unresolved_rows, skipped_review_rows)
    approved_status_defaults = _approved_status_default_rows(status_default_rows, skipped_review_rows)
    duplicate_decisions = _duplicate_decision_rows(duplicate_rows, skipped_review_rows)
    for source_row, decision in duplicate_decisions.items():
        if decision == "keep" and source_row not in approved_unresolved:
            raise ReviewedMappingError(
                "duplicate_sites_review.csv has a keep decision without an approved unresolved site mapping row.",
            )

    rows_by_source = _site_rows_by_source(tables)
    reviewed_sites: list[tuple[str, str, dict[str, str], str, bool]] = []
    included_sources: set[str] = set()
    kept_duplicate_sites = 0

    for source_row, review_row in approved_unresolved.items():
        duplicate_decision = duplicate_decisions.get(source_row)
        if duplicate_decision and duplicate_decision != "keep":
            skipped_review_rows[f"approved_unresolved_blocked_by_duplicate:{duplicate_decision}"] += 1
            continue
        site_row = rows_by_source.get(source_row)
        if site_row is None:
            raise ReviewedMappingError(
                f"Approved unresolved site source row {source_row} was not found in the Site Information export.",
            )
        site_id = clean(site_row.get("Site ID"))
        if not site_id:
            raise ReviewedMappingError(
                f"Approved unresolved site source row {source_row} cannot be sampled because Site ID is blank.",
            )
        if not clean(site_row.get("Name")):
            raise ReviewedMappingError(
                f"Approved unresolved site source row {source_row} cannot be sampled because site name is blank.",
            )
        client_id = clean(review_row.get("manual_client_external_id"))
        site_status, status_was_manual = _reviewed_manual_site_status(
            site_row=site_row,
            unresolved_review_row=review_row,
            approved_status_defaults=approved_status_defaults,
        )
        reviewed_sites.append((site_id, client_id, site_row, site_status, status_was_manual))
        included_sources.add(source_row)
        if duplicate_decision == "keep":
            kept_duplicate_sites += 1

    for source_row, manual_status in approved_status_defaults.items():
        if source_row in included_sources:
            continue
        if source_row in duplicate_decisions and duplicate_decisions[source_row] != "keep":
            skipped_review_rows[f"approved_status_blocked_by_duplicate:{duplicate_decisions[source_row]}"] += 1
            continue
        site_row = rows_by_source.get(source_row)
        if site_row is None:
            raise ReviewedMappingError(
                f"Approved status default source row {source_row} was not found in the Site Information export.",
            )
        site_id = clean(site_row.get("Site ID"))
        if not site_id:
            raise ReviewedMappingError(
                f"Approved status default source row {source_row} cannot be sampled because Site ID is blank.",
            )
        if not clean(site_row.get("Name")):
            raise ReviewedMappingError(
                f"Approved status default source row {source_row} cannot be sampled because site name is blank.",
            )
        linked_clients = analysis.site_to_client_ids.get(site_id, set())
        if len(linked_clients) != 1:
            raise ReviewedMappingError(
                f"Approved status default source row {source_row} does not have one clear Leads client link.",
            )
        client_id = next(iter(linked_clients))
        reviewed_sites.append((site_id, client_id, site_row, manual_status, True))
        included_sources.add(source_row)

    if max_clients is not None or max_sites is not None:
        selected_clients, selected_site_base = _select_sample_sites(
            [(site_id, client_id, site_row) for site_id, client_id, site_row, _status, _manual in reviewed_sites],
            max_clients=max_clients or len({client_id for _site_id, client_id, _site_row, _status, _manual in reviewed_sites}),
            max_sites=max_sites or len(reviewed_sites),
        )
        selected_source_rows = {_source_row_number(site_row) for _site_id, _client_id, site_row in selected_site_base}
        reviewed_sites = [
            site
            for site in reviewed_sites
            if _source_row_number(site[2]) in selected_source_rows and site[1] in set(selected_clients)
        ][: max_sites or len(reviewed_sites)]

    if not reviewed_sites:
        raise ReviewedMappingError("Reviewed sample would contain zero sites.")

    selected_client_ids = list(dict.fromkeys(client_id for _site_id, client_id, _site_row, _status, _manual in reviewed_sites))
    missing_clients = [client_id for client_id in selected_client_ids if client_id not in reviewed_client_candidates]
    if missing_clients:
        raise ReviewedMappingError(
            "Approved site references a client that is not present in output clients. "
            "Review the manual_client_external_id and client status mappings.",
        )
    if not selected_client_ids:
        raise ReviewedMappingError("Reviewed sample would contain zero clients.")

    client_headers = _read_template_headers(clients_template_path)
    site_headers = _read_template_headers(sites_template_path)
    client_rows_out = [
        _client_output_row(
            client_id=client_id,
            client=reviewed_client_candidates[client_id],
            client_headers=client_headers,
            sample_label="reviewed",
        )
        for client_id in selected_client_ids
    ]
    site_rows_out = []
    site_urls_omitted = 0
    for site_id, client_id, site_row, site_status, status_was_manual in reviewed_sites:
        row, url_omitted = _site_output_row(
            site_id=site_id,
            client_id=client_id,
            site=site_row,
            site_status=site_status,
            status_was_manual=status_was_manual,
            site_headers=site_headers,
            sample_label="reviewed",
        )
        site_rows_out.append(row)
        if url_omitted:
            site_urls_omitted += 1

    _write_csv(clients_output_path, client_headers, client_rows_out)
    _write_csv(sites_output_path, site_headers, site_rows_out)

    report_dir.mkdir(parents=True, exist_ok=True)
    validation, validation_json_path, validation_md_path = _run_reviewed_sample_validation(
        clients_path=clients_output_path,
        sites_path=sites_output_path,
        report_dir=report_dir,
    )
    application_report_path = report_dir / "reviewed_mapping_application.md"
    application_report_path.write_text(
        _render_reviewed_sample_report(
            output_dir=report_dir,
            clients_path=clients_output_path,
            sites_path=sites_output_path,
            clients_written=len(client_rows_out),
            sites_written=len(site_rows_out),
            approved_unresolved_sites=len(approved_unresolved),
            approved_status_defaults=len(approved_status_defaults),
            kept_duplicate_sites=kept_duplicate_sites,
            skipped_review_rows=skipped_review_rows,
            site_urls_omitted=site_urls_omitted,
            validation=validation,
        ),
        encoding="utf-8",
    )

    return ReviewedSampleSummary(
        clients_written=len(client_rows_out),
        sites_written=len(site_rows_out),
        approved_unresolved_sites=len(approved_unresolved),
        approved_status_defaults=len(approved_status_defaults),
        kept_duplicate_sites=kept_duplicate_sites,
        skipped_review_rows=dict(skipped_review_rows),
        clients_path=clients_output_path,
        sites_path=sites_output_path,
        report_dir=report_dir,
        application_report_path=application_report_path,
        validation_json_path=validation_json_path,
        validation_md_path=validation_md_path,
        validation_ready=bool(validation.get("ready")),
        validation_totals=dict(validation.get("totals", {})),
    )


def _limit_review_rows(
    rows: Sequence[dict[str, str]],
    max_review_rows: int | None,
) -> list[dict[str, str]]:
    if max_review_rows is None:
        return list(rows)
    if max_review_rows < 1:
        raise ValueError("max_review_rows must be at least 1 when provided.")
    return list(rows[:max_review_rows])


def _review_pack_readme(
    *,
    output_dir: Path,
    files: dict[str, Path],
    diagnostic_bucket_counts: Counter[str],
    total_unresolved_site_rows: int,
    total_client_status_rows: int,
    total_duplicate_site_rows: int,
    total_status_default_rows: int,
    written_unresolved_site_rows: int,
    written_client_status_rows: int,
    written_duplicate_site_rows: int,
    written_status_default_rows: int,
    max_review_rows: int | None,
) -> str:
    bucket_rows = sorted(diagnostic_bucket_counts.items())
    cap_lines = (
        [
            f"- Row cap: first {max_review_rows} rows per review CSV were written.",
            "- Counts below still describe the full analyzed source exports.",
        ]
        if max_review_rows is not None
        else ["- Row cap: none."]
    )
    lines = [
        "# Monday Mapping Review Pack",
        "",
        f"- Generated at: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Output folder: `{output_dir}`",
        "- Purpose: private review of unresolved Monday client, site, and status mappings before any import.",
        "- Safety: no database writes, no provider calls, no V1 migration apply, and no real import.",
        "",
        "## Generated Files",
        *_markdown_table(
            ["File", "Rows Written", "Full Rows Analyzed", "Review Purpose"],
            [
                (
                    files["unresolved_sites"].name,
                    written_unresolved_site_rows,
                    total_unresolved_site_rows,
                    "Sites excluded from clear mapping buckets.",
                ),
                (
                    files["client_status"].name,
                    written_client_status_rows,
                    total_client_status_rows,
                    "Clients whose raw Monday status is not mapped to a V2 status.",
                ),
                (
                    files["duplicate_sites"].name,
                    written_duplicate_site_rows,
                    total_duplicate_site_rows,
                    "Duplicate Site ID rows from Site Information.",
                ),
                (
                    files["status_defaults"].name,
                    written_status_default_rows,
                    total_status_default_rows,
                    "Selected sample sites defaulted to active for validation only.",
                ),
            ],
        ),
        "",
        "## Row Limits",
        *cap_lines,
        "",
        "## Counts By Diagnostic Bucket",
        *_markdown_table(["Bucket", "Rows"], bucket_rows),
        "",
        "## What Bryce Must Review",
        "- In `unresolved_sites_review.csv`, resolve each site by filling `manual_client_external_id`, marking `review_status`, or noting why it should be skipped.",
        "- In `client_status_review.csv`, fill `suggested_status` with one of `active`, `inactive`, `prospect`, or `archived`, then mark `review_status`.",
        "- In `duplicate_sites_review.csv`, choose at most one row to `keep` for each duplicate group and mark the others `skip` or `needs_source_fix`.",
        "- In `status_defaults_review.csv`, fill `manual_status` with the reviewed V2 site status before marking the row approved.",
        "",
        "## Suggested Review Status Values",
        "- `approved`: Bryce reviewed the row and the manual fields are ready to apply.",
        "- `skip`: do not import this source row.",
        "- `needs_source_fix`: fix Monday/source export first, then regenerate.",
        "- `needs_followup`: not ready for sample expansion or import.",
        "",
        "## Stop Conditions",
        "- Any unresolved site row remains without a reviewed client decision.",
        "- Any unmapped client status remains without a reviewed V2 status.",
        "- Any duplicate Site ID group lacks one clear keep/skip/needs_source_fix decision per row.",
        "- Any defaulted site status remains without an approved manual_status.",
        "- Any private export, generated review CSV, validation report, environment file, or local DB file appears staged in git.",
        "",
        "## Recommended Next Step",
        "- After Bryce fills the review CSVs, generate a larger private validation sample using only reviewed mappings.",
        "- Do not import, write database rows, normalize Jobs/Documents, or call providers from this review pack.",
        "",
    ]
    return "\n".join(lines)


def generate_monday_review_pack(
    *,
    contacts_path: Path,
    leads_path: Path,
    sites_path: Path,
    orders_path: Path,
    output_dir: Path,
    max_clients: int = TINY_CLIENT_LIMIT,
    max_sites: int = TINY_SITE_LIMIT,
    max_review_rows: int | None = None,
) -> ReviewPackSummary:
    if max_clients < 1:
        raise ValueError("max_clients must be at least 1.")
    if max_sites < 1:
        raise ValueError("max_sites must be at least 1.")
    if max_review_rows is not None and max_review_rows < 1:
        raise ValueError("max_review_rows must be at least 1 when provided.")

    tables = {
        "contacts": read_table(contacts_path),
        "leads": read_table(leads_path),
        "orders": read_table(orders_path),
        "sites": read_table(sites_path),
    }
    analysis = _analyze_monday_exports(tables)
    _selected_clients, selected_sites = _select_sample_sites(
        analysis.candidate_sites,
        max_clients=max_clients,
        max_sites=max_sites,
    )
    status_default_review_rows = []
    for _site_id, _client_id, site_row in selected_sites:
        defaulted_status, status_defaulted = _map_site_status(site_row.get("Status", ""))
        if status_defaulted:
            status_default_review_rows.append(_status_default_review_row(site_row, defaulted_status))

    diagnostic_bucket_counts: Counter[str] = Counter(
        row["diagnostic_bucket"] for row in analysis.unresolved_site_review_rows
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "unresolved_sites": output_dir / "unresolved_sites_review.csv",
        "client_status": output_dir / "client_status_review.csv",
        "duplicate_sites": output_dir / "duplicate_sites_review.csv",
        "status_defaults": output_dir / "status_defaults_review.csv",
        "readme": output_dir / "README.md",
    }

    unresolved_rows = _limit_review_rows(analysis.unresolved_site_review_rows, max_review_rows)
    client_status_rows = _limit_review_rows(analysis.client_status_review_rows, max_review_rows)
    duplicate_site_rows = _limit_review_rows(analysis.duplicate_site_review_rows, max_review_rows)
    status_default_rows = _limit_review_rows(status_default_review_rows, max_review_rows)

    _write_csv(files["unresolved_sites"], UNRESOLVED_SITES_REVIEW_COLUMNS, unresolved_rows)
    _write_csv(files["client_status"], CLIENT_STATUS_REVIEW_COLUMNS, client_status_rows)
    _write_csv(files["duplicate_sites"], DUPLICATE_SITES_REVIEW_COLUMNS, duplicate_site_rows)
    _write_csv(files["status_defaults"], STATUS_DEFAULTS_REVIEW_COLUMNS, status_default_rows)

    readme = _review_pack_readme(
        output_dir=output_dir,
        files=files,
        diagnostic_bucket_counts=diagnostic_bucket_counts,
        total_unresolved_site_rows=len(analysis.unresolved_site_review_rows),
        total_client_status_rows=len(analysis.client_status_review_rows),
        total_duplicate_site_rows=len(analysis.duplicate_site_review_rows),
        total_status_default_rows=len(status_default_review_rows),
        written_unresolved_site_rows=len(unresolved_rows),
        written_client_status_rows=len(client_status_rows),
        written_duplicate_site_rows=len(duplicate_site_rows),
        written_status_default_rows=len(status_default_rows),
        max_review_rows=max_review_rows,
    )
    files["readme"].write_text(readme, encoding="utf-8")

    return ReviewPackSummary(
        output_dir=output_dir,
        files=files,
        diagnostic_bucket_counts=dict(diagnostic_bucket_counts),
        client_status_rows=len(analysis.client_status_review_rows),
        duplicate_site_rows=len(analysis.duplicate_site_review_rows),
        status_default_rows=len(status_default_review_rows),
        readme_path=files["readme"],
    )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_export_path(export_dir: Path, key: str) -> Path:
    return export_dir / EXPECTED_EXPORTS[key]


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    repo_root = _repo_root()
    default_export_dir = repo_root / "docs" / "import_templates" / "v2" / "private" / "monday_exports"
    private_dir = repo_root / "docs" / "import_templates" / "v2" / "private"
    parser = argparse.ArgumentParser(
        description="Prepare a private Monday Clients/Sites sample for V2 validation. No imports or DB writes.",
    )
    parser.add_argument("--export-dir", type=Path, default=default_export_dir)
    parser.add_argument("--contacts", type=Path)
    parser.add_argument("--leads", type=Path)
    parser.add_argument("--orders", type=Path)
    parser.add_argument("--sites", type=Path)
    parser.add_argument("--client-limit", dest="client_limit", type=int)
    parser.add_argument("--site-limit", dest="site_limit", type=int)
    parser.add_argument("--max-clients", dest="max_clients", type=int)
    parser.add_argument("--max-sites", dest="max_sites", type=int)
    parser.add_argument("--clients-output", "--output-clients", dest="clients_output", type=Path)
    parser.add_argument("--sites-output", "--output-sites", dest="sites_output", type=Path)
    parser.add_argument(
        "--report-output",
        type=Path,
        default=repo_root / "import_validation_reports" / "monday-mapping-review.md",
    )
    parser.add_argument(
        "--apply-reviewed-mappings",
        action="store_true",
        help="Apply Bryce-approved review CSV decisions to create a private reviewed validation sample.",
    )
    parser.add_argument(
        "--review-pack-dir",
        type=Path,
        default=repo_root / "import_validation_reports" / "monday_review_pack",
    )
    parser.add_argument(
        "--reviewed-report-dir",
        type=Path,
        default=repo_root / "import_validation_reports" / "reviewed_sample",
    )
    parser.add_argument(
        "--write-review-pack",
        action="store_true",
        help="Write private mapping review CSVs and README under import_validation_reports/monday_review_pack.",
    )
    parser.add_argument(
        "--review-output-dir",
        type=Path,
        default=repo_root / "import_validation_reports" / "monday_review_pack",
    )
    parser.add_argument(
        "--max-review-rows",
        type=int,
        help="Optional cap on rows written per review CSV; summary counts still cover the full analyzed exports.",
    )
    parser.add_argument(
        "--clients-template",
        type=Path,
        default=repo_root / "docs" / "import_templates" / "v2" / "clients_template.csv",
    )
    parser.add_argument(
        "--sites-template",
        type=Path,
        default=repo_root / "docs" / "import_templates" / "v2" / "sites_template.csv",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = _repo_root()
    private_dir = repo_root / "docs" / "import_templates" / "v2" / "private"
    export_dir = args.export_dir
    contacts_path = args.contacts or _default_export_path(export_dir, "contacts")
    leads_path = args.leads or _default_export_path(export_dir, "leads")
    orders_path = args.orders or _default_export_path(export_dir, "orders")
    sites_path = args.sites or _default_export_path(export_dir, "sites")
    for path in (contacts_path, leads_path, orders_path, sites_path):
        if not path.exists():
            print(f"Missing Monday export file: {path}", file=sys.stderr)
            return 2

    if args.apply_reviewed_mappings:
        clients_output = args.clients_output or private_dir / "clients_reviewed_sample.csv"
        sites_output = args.sites_output or private_dir / "sites_reviewed_sample.csv"
        reviewed_max_clients = args.max_clients if args.max_clients is not None else args.client_limit
        reviewed_max_sites = args.max_sites if args.max_sites is not None else args.site_limit
        try:
            summary = prepare_reviewed_sample(
                contacts_path=contacts_path,
                leads_path=leads_path,
                orders_path=orders_path,
                sites_path=sites_path,
                clients_template_path=args.clients_template,
                sites_template_path=args.sites_template,
                review_pack_dir=args.review_pack_dir,
                clients_output_path=clients_output,
                sites_output_path=sites_output,
                report_dir=args.reviewed_report_dir,
                max_clients=reviewed_max_clients,
                max_sites=reviewed_max_sites,
            )
        except ReviewedMappingError as error:
            print(f"NOT READY: {error}", file=sys.stderr)
            print("Safety: no database writes, no imports, no provider calls.", file=sys.stderr)
            return 2

        print("Applied reviewed Monday mappings for validation sample only.")
        print(f"  Clients rows: {summary.clients_written}")
        print(f"  Sites rows:   {summary.sites_written}")
        print(f"  Approved unresolved site rows: {summary.approved_unresolved_sites}")
        print(f"  Approved status default rows:  {summary.approved_status_defaults}")
        print(f"  Duplicate rows kept:           {summary.kept_duplicate_sites}")
        print(f"  Clients CSV:  {summary.clients_path}")
        print(f"  Sites CSV:    {summary.sites_path}")
        print(f"  Reports:      {summary.report_dir}")
        print(f"  Validation:   {'READY' if summary.validation_ready else 'NOT READY'}")
        print("Safety: no database writes, no imports, no provider calls.")
        return 0 if summary.validation_ready else 1

    client_limit = args.client_limit if args.client_limit is not None else args.max_clients
    site_limit = args.site_limit if args.site_limit is not None else args.max_sites
    client_limit = client_limit if client_limit is not None else TINY_CLIENT_LIMIT
    site_limit = site_limit if site_limit is not None else TINY_SITE_LIMIT
    clients_output = args.clients_output or private_dir / "clients_tiny_sample.csv"
    sites_output = args.sites_output or private_dir / "sites_tiny_sample.csv"

    summary = prepare_tiny_sample(
        contacts_path=contacts_path,
        leads_path=leads_path,
        orders_path=orders_path,
        sites_path=sites_path,
        clients_template_path=args.clients_template,
        sites_template_path=args.sites_template,
        clients_output_path=clients_output,
        sites_output_path=sites_output,
        report_path=args.report_output,
        max_clients=client_limit,
        max_sites=site_limit,
        sample_label="tiny"
        if client_limit <= TINY_CLIENT_LIMIT and site_limit <= TINY_SITE_LIMIT
        else "medium",
    )
    review_summary = None
    if args.write_review_pack:
        review_summary = generate_monday_review_pack(
            contacts_path=contacts_path,
            leads_path=leads_path,
            orders_path=orders_path,
            sites_path=sites_path,
            output_dir=args.review_output_dir,
            max_clients=client_limit,
            max_sites=site_limit,
            max_review_rows=args.max_review_rows,
        )
    print("Prepared Monday sample for validation only.")
    print(f"  Clients rows: {summary.clients_written}")
    print(f"  Sites rows:   {summary.sites_written}")
    print(f"  Candidate sites ready before sample limit: {summary.candidate_sites}")
    print(f"  Site statuses defaulted to active: {summary.site_status_defaulted}")
    print(f"  Clients CSV:  {summary.clients_path}")
    print(f"  Sites CSV:    {summary.sites_path}")
    print(f"  Review:       {summary.report_path}")
    if review_summary is not None:
        print(f"  Review pack:  {review_summary.output_dir}")
        print(f"    Unresolved site rows: {sum(review_summary.diagnostic_bucket_counts.values())}")
        print(f"    Client status rows:   {review_summary.client_status_rows}")
        print(f"    Duplicate site rows:  {review_summary.duplicate_site_rows}")
        print(f"    Status default rows:  {review_summary.status_default_rows}")
    print("Safety: no database writes, no imports, no provider calls.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
