from __future__ import annotations

import csv
from pathlib import Path

from scripts.prepare_monday_tiny_sample import prepare_tiny_sample
from scripts.validate_import_templates import validate_import_templates


REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_DIR = REPO_ROOT / "docs" / "import_templates" / "v2"


def _write_monday_csv(path: Path, title: str, headers: list[str], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([title])
        writer.writerow(headers)
        writer.writerows(rows)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _fake_exports(tmp_path: Path) -> dict[str, Path]:
    contacts = tmp_path / "contacts.csv"
    leads = tmp_path / "leads.csv"
    orders = tmp_path / "orders.csv"
    sites = tmp_path / "sites.csv"
    _write_monday_csv(
        contacts,
        "Contacts",
        ["Name", "First Name", "Last Name", "Email", "Phone", "Active Status", "Account", "Client ID"],
        [
            ["Alex One", "Alex", "One", "alex.one@example.com", "555-0100", "Active", "Acme Group", "client-001"],
            ["Blair Two", "Blair", "Two", "blair.two@example.com", "555-0101", "Active", "Beta LLC", "client-002"],
            ["Casey Three", "Casey", "Three", "casey.three@example.com", "555-0102", "Inactive", "Cedar Inc", "client-003"],
        ],
    )
    _write_monday_csv(
        leads,
        "Leads",
        ["Name", "Site ID", "Client ID"],
        [
            ["Lead A", "site-001", "client-001"],
            ["Lead B", "site-002", "client-001"],
            ["Lead C", "site-003", "client-002"],
            ["Lead D", "site-004", "client-003"],
            ["Lead E", "site-005", "client-003"],
            ["Lead F", "site-006", "client-003"],
        ],
    )
    _write_monday_csv(
        sites,
        "Site Information",
        ["Name", "Site ID", "Address", "CITY", "STATE", "ZIP", "Gdrive", "Status"],
        [
            ["North Basin", "site-001", "1 North Way", "Portland", "ME", "04101", "https://example.com/folders/1", ""],
            ["South Basin", "site-002", "2 South Way", "Portland", "ME", "04102", "", ""],
            ["West Yard", "site-003", "3 West Way", "Boston", "MA", "02108", "not-a-url", ""],
            ["East Yard", "site-004", "4 East Way", "Dover", "NH", "03820", "", ""],
            ["Central Yard", "site-005", "5 Central Way", "Dover", "NH", "03821", "", ""],
            ["Overflow Yard", "site-006", "6 Overflow Way", "Dover", "NH", "03822", "", ""],
            ["Unlinked Yard", "site-999", "9 Missing Way", "Nowhere", "ME", "04000", "", ""],
        ],
    )
    _write_monday_csv(
        orders,
        "Order",
        ["Job Site", "SERVICE", "Scheduled date", "Job ID", "Site ID", "Client ID"],
        [["North Basin", "Inspection", "2026-01-01", "job-001", "site-001", "client-001"]],
    )
    return {"contacts": contacts, "leads": leads, "orders": orders, "sites": sites}


def test_prepare_tiny_sample_writes_valid_private_clients_and_sites(tmp_path: Path) -> None:
    exports = _fake_exports(tmp_path)
    clients_output = tmp_path / "private" / "clients_tiny_sample.csv"
    sites_output = tmp_path / "private" / "sites_tiny_sample.csv"
    report_output = tmp_path / "reports" / "monday-mapping-review.md"

    summary = prepare_tiny_sample(
        contacts_path=exports["contacts"],
        leads_path=exports["leads"],
        orders_path=exports["orders"],
        sites_path=exports["sites"],
        clients_template_path=TEMPLATE_DIR / "clients_template.csv",
        sites_template_path=TEMPLATE_DIR / "sites_template.csv",
        clients_output_path=clients_output,
        sites_output_path=sites_output,
        report_path=report_output,
        max_clients=3,
        max_sites=5,
    )

    assert summary.clients_written == 3
    assert summary.sites_written == 5
    clients = _read_csv(clients_output)
    sites = _read_csv(sites_output)
    client_ids = {row["client_external_id"] for row in clients}
    assert {row["source_system"] for row in clients + sites} == {"monday"}
    assert all(row["client_external_id"] in client_ids for row in sites)

    validation = validate_import_templates(clients=clients_output, sites=sites_output)
    assert validation["ready"] is True
    assert validation["totals"] == {
        "total_rows": 8,
        "valid_rows": 8,
        "invalid_rows": 0,
        "duplicate_rows": 0,
        "unresolved_references": 0,
    }

    report = report_output.read_text(encoding="utf-8")
    assert "Acme Group" not in report
    assert "North Basin" not in report
    assert "no_site_to_client_link" in report


def test_prepare_tiny_sample_excludes_unreviewable_clients(tmp_path: Path) -> None:
    exports = _fake_exports(tmp_path)
    with exports["contacts"].open("a", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Dana Four", "Dana", "Four", "dana.four@example.com", "555-0104", "", "Delta Co", "client-004"])
    with exports["leads"].open("a", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Lead G", "site-007", "client-004"])
    with exports["sites"].open("a", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Review Needed", "site-007", "7 Review Way", "Salem", "MA", "01970", "", ""])

    summary = prepare_tiny_sample(
        contacts_path=exports["contacts"],
        leads_path=exports["leads"],
        orders_path=exports["orders"],
        sites_path=exports["sites"],
        clients_template_path=TEMPLATE_DIR / "clients_template.csv",
        sites_template_path=TEMPLATE_DIR / "sites_template.csv",
        clients_output_path=tmp_path / "private" / "clients.csv",
        sites_output_path=tmp_path / "private" / "sites.csv",
        report_path=tmp_path / "reports" / "review.md",
        max_clients=5,
        max_sites=10,
    )

    assert summary.client_rejections["unmapped_client_status"] == 1
    assert summary.site_rejections["no_reviewable_client_candidate"] == 1
    assert summary.clients_written == 3
    assert summary.sites_written == 6
