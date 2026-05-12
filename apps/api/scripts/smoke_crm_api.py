from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Sequence
from pathlib import Path
from typing import Any

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from scripts.seed_dev import DEMO_ORGANIZATION_ID  # noqa: E402


DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_ORGANIZATION_ID = str(DEMO_ORGANIZATION_ID)
EXPECTED_COUNTS = {
    "clients": 3,
    "sites": 5,
    "jobs": 8,
    "reminders": 4,
    "open_reminders": 3,
    "files": 7,
}


class SmokeFailure(RuntimeError):
    pass


def _build_url(base_url: str, path: str, query: dict[str, str | int] | None = None) -> str:
    url = f"{base_url.rstrip('/')}{path}"
    if not query:
        return url
    return f"{url}?{urllib.parse.urlencode(query)}"


def _get_json(base_url: str, path: str, query: dict[str, str | int] | None = None) -> Any:
    url = _build_url(base_url, path, query)
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise SmokeFailure(f"{url} returned HTTP {error.code}: {body}") from error
    except urllib.error.URLError as error:
        raise SmokeFailure(f"{url} failed: {error.reason}") from error


def _require_count(name: str, response: dict[str, Any], expected: int) -> None:
    actual = response.get("total")
    if actual != expected:
        raise SmokeFailure(f"Expected {expected} {name}, got {actual}.")


def _sample_names(response: dict[str, Any]) -> str:
    names = [str(item.get("name", "(unnamed)")) for item in response.get("items", [])[:3]]
    return ", ".join(names)


def run_smoke(base_url: str, organization_id: str) -> None:
    health = _get_json(base_url, "/health")
    if health != {"status": "ok", "service": "stormwater-v2-api"}:
        raise SmokeFailure(f"Unexpected health response: {health!r}")

    query = {"organization_id": organization_id, "limit": 100}
    clients = _get_json(base_url, "/v1/clients", query)
    sites = _get_json(base_url, "/v1/sites", query)
    jobs = _get_json(base_url, "/v1/jobs", query)
    reminders = _get_json(base_url, "/v1/reminders", query)
    open_reminders = _get_json(
        base_url,
        "/v1/reminders",
        {**query, "status": "open"},
    )
    files = _get_json(base_url, "/v1/files", query)

    _require_count("clients", clients, EXPECTED_COUNTS["clients"])
    _require_count("sites", sites, EXPECTED_COUNTS["sites"])
    _require_count("jobs", jobs, EXPECTED_COUNTS["jobs"])
    _require_count("reminders", reminders, EXPECTED_COUNTS["reminders"])
    _require_count("open reminders", open_reminders, EXPECTED_COUNTS["open_reminders"])
    _require_count("files", files, EXPECTED_COUNTS["files"])

    first_client = clients["items"][0]
    first_site = sites["items"][0]
    client_sites = _get_json(base_url, f"/v1/clients/{first_client['id']}/sites", query)
    client_jobs = _get_json(base_url, f"/v1/clients/{first_client['id']}/jobs", query)
    site_jobs = _get_json(base_url, f"/v1/sites/{first_site['id']}/jobs", query)

    spring_inspection_job = next(
        (job for job in jobs["items"] if job.get("job_code") == "BAY-2026-INS"),
        None,
    )
    catch_basin_job = next(
        (job for job in jobs["items"] if job.get("job_code") == "BAY-2026-CB"),
        None,
    )
    if spring_inspection_job is not None:
        job_files_query = {"organization_id": organization_id, "job_id": spring_inspection_job["id"]}
        job_files = _get_json(base_url, "/v1/files", job_files_query)
        if job_files.get("total") != 1:
            raise SmokeFailure(
                f"Expected 1 seeded file for job {spring_inspection_job['name']}, "
                f"got {job_files.get('total')}.",
            )
    else:
        job_files = {"total": 0, "items": []}

    if catch_basin_job is not None:
        job_reminders_query = {"organization_id": organization_id, "job_id": catch_basin_job["id"]}
        job_reminders = _get_json(base_url, "/v1/reminders", job_reminders_query)
        if job_reminders.get("total") != 1:
            raise SmokeFailure(
                f"Expected 1 seeded reminder for job {catch_basin_job['name']}, "
                f"got {job_reminders.get('total')}.",
            )
    else:
        job_reminders = {"total": 0, "items": []}

    print(f"health: {health['status']} ({health['service']})")
    print(f"clients: {clients['total']} - {_sample_names(clients)}")
    print(f"sites: {sites['total']} - {_sample_names(sites)}")
    print(f"jobs: {jobs['total']} - {_sample_names(jobs)}")
    print(f"reminders: {reminders['total']} ({open_reminders['total']} open)")
    print(f"files: {files['total']}")
    print(f"linked client sites: {client_sites['total']} for {first_client['name']}")
    print(f"linked client jobs: {client_jobs['total']} for {first_client['name']}")
    print(f"linked site jobs: {site_jobs['total']} for {first_site['name']}")
    if spring_inspection_job is not None:
        print(
            f"job-scoped files: {job_files['total']} for "
            f"{spring_inspection_job['name']}",
        )
    if catch_basin_job is not None:
        print(
            f"job-scoped reminders: {job_reminders['total']} for "
            f"{catch_basin_job['name']}",
        )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test the seeded CRM API.")
    parser.add_argument("--base-url", default=DEFAULT_API_BASE_URL)
    parser.add_argument("--organization-id", default=DEFAULT_ORGANIZATION_ID)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        run_smoke(args.base_url, args.organization_id)
    except SmokeFailure as error:
        print(f"CRM API smoke failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
