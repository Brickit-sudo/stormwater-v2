from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Any

from scripts import migrate_v1


def _create_v1_fixture(path: Path, *, include_optional: bool = True) -> Path:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE crm_contacts (
            client_id TEXT,
            first_name TEXT,
            last_name TEXT,
            email TEXT,
            phone TEXT,
            sites_managed TEXT,
            managed_by TEXT,
            active_status TEXT,
            account TEXT,
            state TEXT,
            notes TEXT
        );

        CREATE TABLE crm_sites (
            site_id TEXT,
            name TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            zip TEXT,
            contact TEXT,
            client_id TEXT,
            email TEXT,
            phone TEXT,
            gdrive_url TEXT,
            status TEXT,
            notes TEXT,
            lat REAL,
            lng REAL,
            drive_folder_id TEXT,
            last_inspection_date TEXT,
            next_service_date TEXT,
            contract_start TEXT,
            contract_end TEXT,
            submittal_due_date TEXT
        );

        CREATE TABLE crm_jobs (
            job_id TEXT,
            job_site TEXT,
            location TEXT,
            job_status TEXT,
            service TEXT,
            scope TEXT,
            scheduled_date TEXT,
            site_id TEXT,
            client_id TEXT,
            gdrive_url TEXT,
            notes TEXT,
            completed_date TEXT,
            internal_due_date TEXT,
            next_action_date TEXT,
            completion_notes TEXT,
            blocked_reason TEXT,
            owner TEXT,
            report_id TEXT
        );
        """,
    )
    conn.executemany(
        "INSERT INTO crm_contacts VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                "SSC-0001",
                "Jane",
                "Manager",
                "JANE@ACME.EXAMPLE",
                "207 555 0100",
                "",
                "Property Manager",
                "Active",
                "Acme Properties",
                "ME",
                "Primary property manager.",
            ),
            (
                "SSC-0002",
                "Bob",
                "Coordinator",
                "",
                "207 555 0101",
                "",
                "Coordinator",
                "current",
                "Acme Properties",
                "ME",
                "Duplicate account row.",
            ),
        ],
    )
    conn.executemany(
        "INSERT INTO crm_sites VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                "SSW-0001",
                "North Yard",
                "10 Basin Road",
                "Portland",
                "me",
                "04101",
                "Nina Site",
                "SSC-0001",
                "nina@example.com",
                "207-555-0200",
                "https://drive.google.com/drive/folders/1FolderABC",
                "in service",
                "Active site.",
                43.66,
                -70.25,
                "",
                "2026-05-01",
                "06/01/2026",
                "",
                "",
                "",
            ),
            (
                "SSW-0002",
                "North Yard",
                "10 Basin Road",
                "Portland",
                "ME",
                "04101",
                "",
                "SSC-0001",
                "",
                "",
                "",
                "active",
                "Duplicate site name.",
                None,
                None,
                "",
                "",
                "",
                "",
                "",
                "",
            ),
        ],
    )
    conn.executemany(
        "INSERT INTO crm_jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                "SSO-0001",
                "",
                "",
                "Scheduled",
                "Annual Inspection",
                "Inspect BMPs.",
                "2026-05-11T09:30:00",
                "SSW-0001",
                "",
                "https://drive.google.com/drive/u/0/folders/1JobFolderABC",
                "Crew scheduled.",
                "",
                "05/20/2026",
                "",
                "",
                "",
                "Bryce",
                "report-1",
            ),
            (
                "SSO-ORPHAN",
                "Loose Job",
                "",
                "Mystery",
                "Maintenance",
                "",
                "13/45/2026",
                "SSW-MISSING",
                "SSC-MISSING",
                "https://drive.google.com/file/d/1FileABC/view",
                "",
                "",
                "",
                "",
                "",
                "Gate locked",
                "Unknown Owner",
                "",
            ),
        ],
    )
    if include_optional:
        conn.executescript(
            """
            CREATE TABLE crm_leads (lead_id TEXT, name TEXT);
            CREATE TABLE crm_communications (comm_id TEXT, entity_type TEXT, entity_id TEXT);
            CREATE TABLE crm_report_artifacts (artifact_id TEXT, file_path TEXT);
            """
        )
        conn.execute("INSERT INTO crm_leads VALUES (?, ?)", ("SWL-0001", "Future Lead"))
        conn.execute(
            "INSERT INTO crm_communications VALUES (?, ?, ?)",
            ("COMM-0001", "site", "SSW-0001"),
        )
        conn.execute(
            "INSERT INTO crm_report_artifacts VALUES (?, ?)",
            ("ART-0001", "report.docx"),
        )
    conn.commit()
    conn.close()
    return path


def _create_alias_fixture(path: Path, site_rows: list[dict[str, Any]] | None = None) -> Path:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE crm_contacts (
            client_id TEXT,
            first_name TEXT,
            last_name TEXT,
            email TEXT,
            phone TEXT,
            sites_managed TEXT,
            managed_by TEXT,
            active_status TEXT,
            account TEXT,
            state TEXT,
            notes TEXT
        );

        CREATE TABLE crm_sites (
            site_id TEXT,
            name TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            zip TEXT,
            contact TEXT,
            client_id TEXT,
            email TEXT,
            phone TEXT,
            gdrive_url TEXT,
            status TEXT,
            notes TEXT,
            lat REAL,
            lng REAL,
            drive_folder_id TEXT,
            last_inspection_date TEXT,
            next_service_date TEXT,
            contract_start TEXT,
            contract_end TEXT,
            submittal_due_date TEXT,
            account TEXT,
            managed_by TEXT,
            drive_parent_folder TEXT
        );

        CREATE TABLE crm_jobs (
            job_id TEXT,
            job_site TEXT,
            location TEXT,
            job_status TEXT,
            service TEXT,
            scope TEXT,
            scheduled_date TEXT,
            site_id TEXT,
            client_id TEXT,
            gdrive_url TEXT,
            notes TEXT,
            completed_date TEXT,
            internal_due_date TEXT,
            next_action_date TEXT,
            completion_notes TEXT,
            blocked_reason TEXT,
            owner TEXT,
            report_id TEXT
        );

        CREATE TABLE crm_leads (lead_id TEXT, name TEXT);
        CREATE TABLE crm_communications (comm_id TEXT, entity_type TEXT, entity_id TEXT);
        CREATE TABLE crm_report_artifacts (artifact_id TEXT, file_path TEXT);
        """
    )
    defaults = {
        "site_id": "SSW-ALIAS-1",
        "name": "Alias Test Site",
        "address": "1 Alias Way",
        "city": "Portland",
        "state": "ME",
        "zip": "04101",
        "contact": "",
        "client_id": "",
        "email": "",
        "phone": "",
        "gdrive_url": "https://drive.google.com/drive/folders/1AliasFolder",
        "status": "active",
        "notes": "",
        "lat": None,
        "lng": None,
        "drive_folder_id": "",
        "last_inspection_date": "",
        "next_service_date": "",
        "contract_start": "",
        "contract_end": "",
        "submittal_due_date": "",
        "account": "",
        "managed_by": "",
        "drive_parent_folder": "",
    }
    rows = site_rows or [defaults]
    prepared_rows = []
    for row in rows:
        merged = {**defaults, **row}
        prepared_rows.append(tuple(merged[name] for name in defaults))
    conn.executemany(
        """
        INSERT INTO crm_sites VALUES (
            ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
        )
        """,
        prepared_rows,
    )
    conn.commit()
    conn.close()
    return path


def _write_aliases(path: Path, rows: list[dict[str, Any]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "source_value",
                "source_field",
                "target_client_name",
                "target_client_status",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


def _alias_row(
    source_value: str,
    source_field: str,
    target_client_name: str = "Mapped Client",
    target_client_status: str = "active",
) -> dict[str, str]:
    return {
        "source_value": source_value,
        "source_field": source_field,
        "target_client_name": target_client_name,
        "target_client_status": target_client_status,
        "notes": "Test alias only",
    }


def test_script_imports_cleanly() -> None:
    assert migrate_v1.REPORT_SCHEMA_VERSION == "m1-dry-run-v2"


def test_reads_available_tables(tmp_path: Path) -> None:
    db_path = _create_v1_fixture(tmp_path / "v1.sqlite")

    source = migrate_v1.read_sqlite_source(db_path)

    assert {"crm_contacts", "crm_sites", "crm_jobs"}.issubset(source.tables_found)
    assert source.source_row_counts["crm_contacts"] == 2
    assert source.source_row_counts["crm_jobs"] == 2


def test_missing_optional_table_does_not_crash(tmp_path: Path) -> None:
    db_path = _create_v1_fixture(tmp_path / "v1.sqlite", include_optional=False)

    report = migrate_v1.run_dry_run(v1_db=db_path, organization_name="Sterling Stormwater")

    assert report["source_row_counts"]["crm_leads"] == 0
    assert any(warning["table"] == "crm_leads" for warning in report["warnings"]["missing_tables"])
    assert report["planned_counts"]["clients"] == 2  # Acme plus orphan-job synthetic parent


def test_maps_contacts_accounts_to_client_and_contact_proposals(tmp_path: Path) -> None:
    db_path = _create_v1_fixture(tmp_path / "v1.sqlite")

    report = migrate_v1.run_dry_run(v1_db=db_path, organization_name="Sterling Stormwater")

    acme_clients = [
        client
        for client in report["planned"]["clients"]
        if client["fields"]["name"] == "Acme Properties"
    ]
    assert len(acme_clients) == 1
    assert acme_clients[0]["fields"]["email"] == "jane@acme.example"
    assert acme_clients[0]["alternate_legacy_ids"] == ["SSC-0002"]
    assert len([contact for contact in report["planned"]["contacts"] if contact["legacy_source_table"] == "crm_contacts"]) == 2


def test_maps_sites_with_client_lookup(tmp_path: Path) -> None:
    db_path = _create_v1_fixture(tmp_path / "v1.sqlite")

    report = migrate_v1.run_dry_run(v1_db=db_path, organization_name="Sterling Stormwater")
    site = next(site for site in report["planned"]["sites"] if site["legacy_id"] == "SSW-0001")
    client_id = report["lookup_maps"]["client_legacy_id_to_proposed_id"]["SSC-0001"]

    assert site["fields"]["client_id"] == client_id
    assert site["fields"]["state"] == "ME"
    assert site["fields"]["drive_folder_id"] == "1FolderABC"


def test_maps_jobs_with_site_client_lookup(tmp_path: Path) -> None:
    db_path = _create_v1_fixture(tmp_path / "v1.sqlite")

    report = migrate_v1.run_dry_run(v1_db=db_path, organization_name="Sterling Stormwater")
    job = next(job for job in report["planned"]["jobs"] if job["legacy_id"] == "SSO-0001")
    site = next(site for site in report["planned"]["sites"] if site["legacy_id"] == "SSW-0001")

    assert job["fields"]["site_id"] == site["proposed_id"]
    assert job["fields"]["client_id"] == site["fields"]["client_id"]
    assert job["fields"]["status"] == "scheduled"
    assert job["fields"]["scheduled_date"] == "2026-05-11"
    assert job["fields"]["due_date"] == "2026-05-20"


def test_detects_orphan_job(tmp_path: Path) -> None:
    db_path = _create_v1_fixture(tmp_path / "v1.sqlite")

    report = migrate_v1.run_dry_run(v1_db=db_path, organization_name="Sterling Stormwater")
    orphan_job = next(job for job in report["planned"]["jobs"] if job["legacy_id"] == "SSO-ORPHAN")

    assert report["orphans"]["jobs"]
    assert orphan_job["fields"]["site_id"] == report["lookup_maps"]["site_legacy_id_to_proposed_id"][
        "synthetic:site:unassigned"
    ]


def test_maps_statuses() -> None:
    assert migrate_v1._map_status("client", table="clients", row_key="SSC")[0] == "active"
    assert migrate_v1._map_status("paused", table="sites", row_key="SSW")[0] == "on_hold"
    assert migrate_v1._map_status("field complete", table="jobs", row_key="SSO")[0] == "in_review"
    status, warning = migrate_v1._map_status("???", table="jobs", row_key="SSO")

    assert status == "draft"
    assert warning is not None
    assert warning["reason"] == "unknown-status"


def test_parses_dates() -> None:
    assert migrate_v1.parse_v1_date("2026-05-11").value == "2026-05-11"
    assert migrate_v1.parse_v1_date("5/11/2026").value == "2026-05-11"
    assert migrate_v1.parse_v1_date("05-11-2026").value == "2026-05-11"
    assert migrate_v1.parse_v1_date("2026-05-11T09:30:00").value == "2026-05-11"
    assert migrate_v1.parse_v1_date("").value is None
    assert migrate_v1.parse_v1_date("not-a-date").warning == "unparseable-date"


def test_parses_drive_folder_urls() -> None:
    parsed = migrate_v1.parse_drive_url("https://drive.google.com/drive/folders/1ABCxyz?usp=sharing")

    assert parsed.drive_folder_url == "https://drive.google.com/drive/folders/1ABCxyz"
    assert parsed.drive_folder_id == "1ABCxyz"
    assert parsed.warning is None


def test_detects_file_url_warning() -> None:
    parsed = migrate_v1.parse_drive_url("https://drive.google.com/file/d/1ABCxyz/view")

    assert parsed.drive_folder_id is None
    assert parsed.warning == "looks-like-file-not-folder"


def test_dry_run_does_not_require_or_write_v2_database(tmp_path: Path, monkeypatch) -> None:
    db_path = _create_v1_fixture(tmp_path / "v1.sqlite")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://invalid/should-not-be-used")

    report = migrate_v1.run_dry_run(v1_db=db_path, organization_name="Sterling Stormwater")

    assert report["mode"] == "dry_run"
    assert report["organization"]["name"] == "Sterling Stormwater"


def test_no_alias_file_preserves_old_behavior(tmp_path: Path) -> None:
    db_path = _create_v1_fixture(tmp_path / "v1.sqlite")

    report = migrate_v1.run_dry_run(v1_db=db_path, organization_name="Sterling Stormwater")
    site = next(site for site in report["planned"]["sites"] if site["legacy_id"] == "SSW-0001")

    assert report["alias_summary"]["provided"] is False
    assert report["alias_summary"]["rows_loaded"] == 0
    assert report["planned_counts"] == {
        "clients": 2,
        "contacts": 3,
        "jobs": 2,
        "sites": 2,
    }
    assert site["client_resolution_method"] == "direct_client_id"


def test_alias_file_loads_valid_rows(tmp_path: Path) -> None:
    db_path = _create_alias_fixture(tmp_path / "v1.sqlite")
    source = migrate_v1.read_sqlite_source(db_path)
    alias_path = _write_aliases(
        tmp_path / "client_aliases.csv",
        [_alias_row("Alias Test", "site_name_prefix", "Alias Owner")],
    )

    config = migrate_v1.read_client_aliases(alias_path, source)

    assert config.summary["rows_loaded"] == 1
    assert config.summary["rows_valid"] == 1
    assert config.aliases[0].target_client_name == "Alias Owner"


def test_invalid_alias_row_produces_warning(tmp_path: Path) -> None:
    db_path = _create_alias_fixture(tmp_path / "v1.sqlite")
    source = migrate_v1.read_sqlite_source(db_path)
    alias_path = _write_aliases(
        tmp_path / "client_aliases.csv",
        [_alias_row("", "site_name_exact", "Alias Owner")],
    )

    config = migrate_v1.read_client_aliases(alias_path, source)

    assert config.summary["rows_invalid"] == 1
    assert any(warning["reason"] == "invalid-alias-row" for warning in config.warnings)


def test_unsupported_alias_source_field_produces_warning(tmp_path: Path) -> None:
    db_path = _create_v1_fixture(tmp_path / "v1.sqlite")
    source = migrate_v1.read_sqlite_source(db_path)
    alias_path = _write_aliases(
        tmp_path / "client_aliases.csv",
        [_alias_row("Parent Folder", "drive_parent_folder", "Alias Owner")],
    )

    config = migrate_v1.read_client_aliases(alias_path, source)

    assert config.summary["unsupported_source_field_rows"] == 1
    assert any(warning["reason"] == "unsupported-source-field" for warning in config.warnings)


def test_site_name_exact_alias_resolves_client(tmp_path: Path) -> None:
    db_path = _create_alias_fixture(
        tmp_path / "v1.sqlite",
        [{"site_id": "SSW-EXACT", "name": "Exact Match Site"}],
    )
    alias_path = _write_aliases(
        tmp_path / "client_aliases.csv",
        [_alias_row("Exact Match Site", "site_name_exact", "Exact Client")],
    )

    report = migrate_v1.run_dry_run(
        v1_db=db_path,
        organization_name="Sterling Stormwater",
        client_aliases=alias_path,
    )
    site = next(site for site in report["planned"]["sites"] if site["legacy_id"] == "SSW-EXACT")
    client = next(client for client in report["planned"]["clients"] if client["fields"]["name"] == "Exact Client")

    assert site["fields"]["client_id"] == client["proposed_id"]
    assert site["client_resolution_method"] == "alias_site_name_exact"
    assert report["client_resolution_summary"]["sites_resolved_by_alias"] == 1
    assert report["client_resolution_summary"]["sites_unresolved_after_aliases"] == 0


def test_site_name_prefix_alias_resolves_client(tmp_path: Path) -> None:
    db_path = _create_alias_fixture(
        tmp_path / "v1.sqlite",
        [{"site_id": "SSW-PREFIX", "name": "Long Creek Basin 1"}],
    )
    alias_path = _write_aliases(
        tmp_path / "client_aliases.csv",
        [_alias_row("Long Creek", "site_name_prefix", "Long Creek Client")],
    )

    report = migrate_v1.run_dry_run(
        v1_db=db_path,
        organization_name="Sterling Stormwater",
        client_aliases=alias_path,
    )
    site = next(site for site in report["planned"]["sites"] if site["legacy_id"] == "SSW-PREFIX")

    assert site["client_resolution_method"] == "alias_site_name_prefix"
    assert site["client_resolution_source_value"] == "Long Creek"


def test_site_name_contains_alias_resolves_client(tmp_path: Path) -> None:
    db_path = _create_alias_fixture(
        tmp_path / "v1.sqlite",
        [{"site_id": "SSW-CONTAINS", "name": "North Retail Pond"}],
    )
    alias_path = _write_aliases(
        tmp_path / "client_aliases.csv",
        [_alias_row("Retail", "site_name_contains", "Retail Client")],
    )

    report = migrate_v1.run_dry_run(
        v1_db=db_path,
        organization_name="Sterling Stormwater",
        client_aliases=alias_path,
    )
    site = next(site for site in report["planned"]["sites"] if site["legacy_id"] == "SSW-CONTAINS")

    assert site["client_resolution_method"] == "alias_site_name_contains"


def test_account_alias_resolves_client_when_source_field_exists(tmp_path: Path) -> None:
    db_path = _create_alias_fixture(
        tmp_path / "v1.sqlite",
        [{"site_id": "SSW-ACCOUNT", "name": "Account Site", "account": "Portfolio Account"}],
    )
    alias_path = _write_aliases(
        tmp_path / "client_aliases.csv",
        [_alias_row("Portfolio Account", "account", "Portfolio Client")],
    )

    report = migrate_v1.run_dry_run(
        v1_db=db_path,
        organization_name="Sterling Stormwater",
        client_aliases=alias_path,
    )
    site = next(site for site in report["planned"]["sites"] if site["legacy_id"] == "SSW-ACCOUNT")

    assert site["client_resolution_method"] == "alias_account"


def test_managed_by_alias_resolves_client_when_source_field_exists(tmp_path: Path) -> None:
    db_path = _create_alias_fixture(
        tmp_path / "v1.sqlite",
        [{"site_id": "SSW-MANAGED", "name": "Managed Site", "managed_by": "Demo Manager"}],
    )
    alias_path = _write_aliases(
        tmp_path / "client_aliases.csv",
        [_alias_row("Demo Manager", "managed_by", "Managed Client")],
    )

    report = migrate_v1.run_dry_run(
        v1_db=db_path,
        organization_name="Sterling Stormwater",
        client_aliases=alias_path,
    )
    site = next(site for site in report["planned"]["sites"] if site["legacy_id"] == "SSW-MANAGED")

    assert site["client_resolution_method"] == "alias_managed_by"


def test_multiple_alias_matches_selects_priority_and_warns(tmp_path: Path) -> None:
    db_path = _create_alias_fixture(
        tmp_path / "v1.sqlite",
        [{"site_id": "SSW-PRIORITY", "name": "Priority Site"}],
    )
    alias_path = _write_aliases(
        tmp_path / "client_aliases.csv",
        [
            _alias_row("Priority", "site_name_contains", "Contains Client"),
            _alias_row("Priority Site", "site_name_exact", "Exact Priority Client"),
        ],
    )

    report = migrate_v1.run_dry_run(
        v1_db=db_path,
        organization_name="Sterling Stormwater",
        client_aliases=alias_path,
    )
    site = next(site for site in report["planned"]["sites"] if site["legacy_id"] == "SSW-PRIORITY")
    selected_client = next(
        client
        for client in report["planned"]["clients"]
        if client["proposed_id"] == site["fields"]["client_id"]
    )

    assert selected_client["fields"]["name"] == "Exact Priority Client"
    assert site["client_resolution_warning"] == "multiple-alias-matches"
    assert any(warning["reason"] == "multiple-alias-matches" for warning in report["alias_warnings"])


def test_invalid_alias_target_client_status_warns_and_defaults(tmp_path: Path) -> None:
    db_path = _create_alias_fixture(
        tmp_path / "v1.sqlite",
        [{"site_id": "SSW-STATUS", "name": "Status Site"}],
    )
    alias_path = _write_aliases(
        tmp_path / "client_aliases.csv",
        [_alias_row("Status Site", "site_name_exact", "Status Client", "not-real")],
    )

    report = migrate_v1.run_dry_run(
        v1_db=db_path,
        organization_name="Sterling Stormwater",
        client_aliases=alias_path,
    )
    client = next(client for client in report["planned"]["clients"] if client["fields"]["name"] == "Status Client")

    assert client["fields"]["status"] == "active"
    assert any(warning["reason"] == "invalid-target-client-status" for warning in report["alias_warnings"])


def test_json_report_shape_is_stable(tmp_path: Path) -> None:
    db_path = _create_v1_fixture(tmp_path / "v1.sqlite")
    output_path = tmp_path / "migration-report.json"
    report = migrate_v1.run_dry_run(v1_db=db_path, organization_name="Sterling Stormwater")

    migrate_v1.write_report_outputs(report, output_json=output_path)
    saved = json.loads(output_path.read_text(encoding="utf-8"))

    assert list(saved.keys()) == [
        "alias_summary",
        "alias_warnings",
        "client_resolution_summary",
        "deferred",
        "diagnostics",
        "errors",
        "expected_tables",
        "go_no_go",
        "lookup_maps",
        "missing_tables",
        "mode",
        "organization",
        "orphans",
        "planned",
        "planned_counts",
        "schema_version",
        "source_database",
        "source_row_counts",
        "tables_found",
        "unresolved_site_samples",
        "verbose",
        "warnings",
    ]
    assert saved["planned_counts"] == {
        "clients": 2,
        "contacts": 3,
        "jobs": 2,
        "sites": 2,
    }


def test_json_report_includes_alias_summary(tmp_path: Path) -> None:
    db_path = _create_alias_fixture(
        tmp_path / "v1.sqlite",
        [{"site_id": "SSW-JSON", "name": "JSON Alias Site"}],
    )
    alias_path = _write_aliases(
        tmp_path / "client_aliases.csv",
        [_alias_row("JSON Alias Site", "site_name_exact", "JSON Client")],
    )
    output_path = tmp_path / "migration-report.json"
    report = migrate_v1.run_dry_run(
        v1_db=db_path,
        organization_name="Sterling Stormwater",
        client_aliases=alias_path,
    )

    migrate_v1.write_report_outputs(report, output_json=output_path)
    saved = json.loads(output_path.read_text(encoding="utf-8"))

    assert saved["alias_summary"]["rows_valid"] == 1
    assert saved["client_resolution_summary"]["sites_resolved_by_alias"] == 1
    assert saved["unresolved_site_samples"] == []


def test_markdown_report_includes_alias_summary(tmp_path: Path) -> None:
    db_path = _create_alias_fixture(
        tmp_path / "v1.sqlite",
        [{"site_id": "SSW-MD", "name": "Markdown Alias Site"}],
    )
    alias_path = _write_aliases(
        tmp_path / "client_aliases.csv",
        [_alias_row("Markdown Alias Site", "site_name_exact", "Markdown Client")],
    )
    report = migrate_v1.run_dry_run(
        v1_db=db_path,
        organization_name="Sterling Stormwater",
        client_aliases=alias_path,
    )

    markdown = migrate_v1.render_markdown_report(report)

    assert "## 4. Alias Mapping Summary" in markdown
    assert "Alias rows valid" in markdown
    assert "Markdown Client" in markdown


def test_private_mapping_file_is_not_required_for_tests(tmp_path: Path) -> None:
    db_path = _create_alias_fixture(tmp_path / "v1.sqlite")

    report = migrate_v1.run_dry_run(v1_db=db_path, organization_name="Sterling Stormwater")

    assert report["alias_summary"]["provided"] is False
    assert report["alias_warnings"] == []


def test_diagnostics_explain_site_client_relationships(tmp_path: Path) -> None:
    db_path = _create_v1_fixture(tmp_path / "v1.sqlite")

    report = migrate_v1.run_dry_run(v1_db=db_path, organization_name="Sterling Stormwater")
    contact_diagnostics = report["diagnostics"]["contacts"]
    site_diagnostics = report["diagnostics"]["sites"]

    assert contact_diagnostics["total_contacts"] == 2
    assert contact_diagnostics["contacts_with_account"] == 2
    assert contact_diagnostics["planned_clients_from_contacts"] == 1
    assert contact_diagnostics["planned_synthetic_clients"] == 1
    assert site_diagnostics["relationship_counts"]["total_sites"] == 2
    assert site_diagnostics["relationship_counts"]["sites_with_client_id"] == 2
    assert site_diagnostics["relationship_counts"]["sites_with_resolvable_client_id"] == 2
    assert site_diagnostics["relationship_counts"]["sites_missing_client_id"] == 0
    assert site_diagnostics["field_presence_counts"]["any_drive"] == 1
    assert site_diagnostics["drive_counts"]["sites_with_parsed_drive_folder_url"] == 1
    assert site_diagnostics["duplicate_counts"]["migration_duplicate_warnings"] == 1
    assert site_diagnostics["sample_unresolved_sites"] == []


def test_apply_exits_not_implemented(tmp_path: Path, capsys) -> None:
    db_path = _create_v1_fixture(tmp_path / "v1.sqlite")

    exit_code = migrate_v1.main(
        [
            "--v1-db",
            str(db_path),
            "--organization-name",
            "Sterling Stormwater",
            "--apply",
        ],
    )
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "--apply is not implemented in Phase M1" in captured.err
