from __future__ import annotations

import csv
import shutil
from pathlib import Path
from typing import Any

from scripts.validate_import_templates import (
    TEMPLATE_CONFIGS,
    render_markdown_report,
    validate_import_templates,
    write_report_outputs,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_DIR = REPO_ROOT / "docs" / "import_templates" / "v2"
VALIDATE_SAMPLE_SCRIPT = REPO_ROOT / "scripts" / "validate-v2-import-sample.ps1"


def _template_paths(base: Path = TEMPLATE_DIR) -> dict[str, Path]:
    return {
        "clients": base / "clients_template.csv",
        "contacts": base / "contacts_template.csv",
        "sites": base / "sites_template.csv",
        "jobs": base / "jobs_template.csv",
        "documents": base / "documents_template.csv",
        "emails": base / "emails_template.csv",
    }


def _copy_templates(tmp_path: Path) -> dict[str, Path]:
    target_dir = tmp_path / "templates"
    target_dir.mkdir()
    paths = {}
    for import_type, source in _template_paths().items():
        target = target_dir / source.name
        shutil.copy(source, target)
        paths[import_type] = target
    return paths


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _run(paths: dict[str, Path]) -> dict[str, Any]:
    return validate_import_templates(**paths)


def _codes(report: dict[str, Any]) -> set[str]:
    return {
        error["code"]
        for row in report["invalid_rows"]
        for error in row["errors"]
    }


def test_templates_exist() -> None:
    for path in _template_paths().values():
        assert path.exists()
        assert path.is_file()
    assert (TEMPLATE_DIR / "README.md").exists()


def test_templates_have_required_columns() -> None:
    for import_type, path in _template_paths().items():
        fieldnames, _rows = _read_csv(path)
        assert TEMPLATE_CONFIGS[import_type]["required_columns"] <= set(fieldnames)


def test_fake_template_rows_validate() -> None:
    report = validate_import_templates(**_template_paths())

    assert report["ready"] is True
    assert report["safe_to_proceed"] is True
    assert report["totals"]["total_rows"] > 0
    assert report["invalid_rows"] == []
    assert report["duplicate_rows"] == []
    assert report["unresolved_references"] == []


def test_tiny_clients_sites_only_sample_validates() -> None:
    report = validate_import_templates(
        clients=TEMPLATE_DIR / "clients_template.csv",
        sites=TEMPLATE_DIR / "sites_template.csv",
    )

    assert report["ready"] is True
    assert report["safe_to_proceed"] is True
    assert report["summary"]["clients"]["provided"] is True
    assert report["summary"]["sites"]["provided"] is True
    assert report["summary"]["jobs"]["provided"] is False
    assert report["totals"] == {
        "total_rows": 4,
        "valid_rows": 4,
        "invalid_rows": 0,
        "duplicate_rows": 0,
        "unresolved_references": 0,
    }


def test_site_without_client_reference_fails(tmp_path: Path) -> None:
    paths = _copy_templates(tmp_path)
    fieldnames, rows = _read_csv(paths["sites"])
    rows[0]["client_external_id"] = ""
    _write_csv(paths["sites"], fieldnames, rows)

    report = _run(paths)

    assert report["ready"] is False
    assert "missing-required-field" in _codes(report)
    assert report["summary"]["sites"]["invalid_rows"] == 1


def test_unresolved_site_client_reference_summary(tmp_path: Path) -> None:
    paths = _copy_templates(tmp_path)
    fieldnames, rows = _read_csv(paths["sites"])
    rows[0]["client_external_id"] = "client-missing-999"
    _write_csv(paths["sites"], fieldnames, rows)

    report = _run(paths)

    assert report["ready"] is False
    assert report["safe_to_proceed"] is False
    assert "unresolved-reference" in _codes(report)
    assert report["totals"]["unresolved_references"] == 1
    assert report["unresolved_reference_summary"] == [
        {
            "import_type": "sites",
            "field": "client_external_id",
            "target_type": "client",
            "target_external_id": "client-missing-999",
            "rows": [2],
            "count": 1,
        },
    ]


def test_job_without_site_reference_fails(tmp_path: Path) -> None:
    paths = _copy_templates(tmp_path)
    fieldnames, rows = _read_csv(paths["jobs"])
    rows[0]["site_external_id"] = ""
    _write_csv(paths["jobs"], fieldnames, rows)

    report = _run(paths)

    assert report["ready"] is False
    assert "missing-required-field" in _codes(report)
    assert report["summary"]["jobs"]["invalid_rows"] == 1


def test_document_with_no_parent_fails(tmp_path: Path) -> None:
    paths = _copy_templates(tmp_path)
    fieldnames, rows = _read_csv(paths["documents"])
    rows[0]["parent_type"] = ""
    rows[0]["parent_external_id"] = ""
    _write_csv(paths["documents"], fieldnames, rows)

    report = _run(paths)

    assert report["ready"] is False
    assert "missing-parent" in _codes(report)
    assert report["summary"]["documents"]["invalid_rows"] == 1


def test_document_with_multiple_parents_fails(tmp_path: Path) -> None:
    paths = _copy_templates(tmp_path)
    fieldnames, rows = _read_csv(paths["documents"])
    rows[0]["client_external_id"] = "client-demo-001"
    _write_csv(paths["documents"], fieldnames, rows)

    report = _run(paths)

    assert report["ready"] is False
    assert "multiple-parents" in _codes(report)
    assert report["summary"]["documents"]["invalid_rows"] == 1


def test_duplicate_external_ids_detected(tmp_path: Path) -> None:
    paths = _copy_templates(tmp_path)
    fieldnames, rows = _read_csv(paths["clients"])
    rows[1]["client_external_id"] = rows[0]["client_external_id"]
    _write_csv(paths["clients"], fieldnames, rows)

    report = _run(paths)

    assert report["ready"] is False
    assert "duplicate-external-id" in _codes(report)
    assert report["summary"]["clients"]["duplicate_rows"] == 1
    assert report["duplicate_summary"] == [
        {
            "import_type": "clients",
            "field": "client_external_id",
            "value": rows[0]["client_external_id"],
            "first_row": 2,
            "duplicate_rows": [3],
            "count": 1,
        },
    ]


def test_invalid_email_url_and_status_are_flagged(tmp_path: Path) -> None:
    paths = _copy_templates(tmp_path)
    fieldnames, rows = _read_csv(paths["clients"])
    rows[0]["email"] = "not-an-email"
    rows[0]["drive_folder_url"] = "drive-folder-without-scheme"
    rows[0]["status"] = "maybe"
    _write_csv(paths["clients"], fieldnames, rows)

    report = _run(paths)
    codes = _codes(report)

    assert report["ready"] is False
    assert {"invalid-email", "invalid-url", "invalid-status"} <= codes
    assert report["summary"]["clients"]["invalid_rows"] == 1


def test_validator_does_not_write_db(tmp_path: Path) -> None:
    paths = _copy_templates(tmp_path)

    report = _run(paths)

    assert report["ready"] is True
    assert report["safety"] == {
        "db_writes": False,
        "provider_calls": False,
        "real_import": False,
    }
    assert list(tmp_path.rglob("*.db")) == []


def test_markdown_report_has_stop_conditions_and_next_action(tmp_path: Path) -> None:
    paths = _copy_templates(tmp_path)
    fieldnames, rows = _read_csv(paths["sites"])
    rows[0]["client_external_id"] = "client-missing-999"
    _write_csv(paths["sites"], fieldnames, rows)

    report = _run(paths)
    markdown = render_markdown_report(report)

    assert "## Stop Conditions" in markdown
    assert "- Safe to proceed: NO" in markdown
    assert "- Recommended next action:" in markdown
    assert "Fix unresolved relationships first" in markdown
    assert "| sites | client_external_id | client | client-missing-999 | 2 | 1 |" in markdown


def test_output_json_and_markdown_generated_safely(tmp_path: Path) -> None:
    paths = _copy_templates(tmp_path)
    report = _run(paths)
    output_json = tmp_path / "reports" / "validation.json"
    output_md = tmp_path / "reports" / "validation.md"

    write_report_outputs(report, output_json=output_json, output_md=output_md)

    assert output_json.exists()
    assert output_md.exists()
    assert '"db_writes": false' in output_json.read_text(encoding="utf-8")
    assert '"safe_to_proceed": true' in output_json.read_text(encoding="utf-8")
    markdown = output_md.read_text(encoding="utf-8")
    assert "No database connection is opened." in markdown
    assert "- Safe to proceed: YES" in markdown


def test_validate_sample_powershell_helper_static_safety() -> None:
    assert VALIDATE_SAMPLE_SCRIPT.exists()
    script = VALIDATE_SAMPLE_SCRIPT.read_text(encoding="utf-8")
    lowered = script.lower()

    forbidden_fragments = [
        "remove-item -recurse",
        "git add",
        "git commit",
        "alembic upgrade",
        "seed_dev",
        "invoke-restmethod",
        "invoke-webrequest",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in lowered


def test_gitignore_keeps_private_import_artifacts_ignored() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")

    required_patterns = [
        "docs/import_templates/v2/private/",
        "docs/import_templates/v2/filled/",
        "apps/api/import_data/",
        "import_validation_reports/",
        "*_real_import*.csv",
        "*_real_import*.xlsx",
        "*_private*.csv",
        "*_private*.xlsx",
        "*.db",
    ]
    for pattern in required_patterns:
        assert pattern in gitignore
