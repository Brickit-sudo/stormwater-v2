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
    "map_sites": 5,
    "jobs": 8,
    "reminders": 4,
    "open_reminders": 3,
    "files": 7,
    "email_messages": 5,
    "ai_drafts": 3,
    "email_import_batches": 1,
    "product_ideas": 21,
    "product_decisions": 8,
}
VALID_READINESS_STATUSES = {"ready", "needs_attention", "blocked"}


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


def _post_json(base_url: str, path: str, payload: dict[str, Any]) -> Any:
    url = _build_url(base_url, path)
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
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


def _require_timeline(name: str, response: dict[str, Any]) -> None:
    if not isinstance(response.get("items"), list):
        raise SmokeFailure(f"{name} timeline response did not include an items list.")
    if response.get("limit") != 10:
        raise SmokeFailure(f"{name} timeline response did not preserve limit=10.")


def run_smoke(base_url: str, organization_id: str) -> None:
    health = _get_json(base_url, "/health")
    if health != {"status": "ok", "service": "stormwater-v2-api"}:
        raise SmokeFailure(f"Unexpected health response: {health!r}")

    query = {"organization_id": organization_id, "limit": 100}
    clients = _get_json(base_url, "/v1/clients", query)
    sites = _get_json(base_url, "/v1/sites", query)
    map_sites = _get_json(base_url, "/v1/sites/map", query)
    jobs = _get_json(base_url, "/v1/jobs", query)
    reminders = _get_json(base_url, "/v1/reminders", query)
    open_reminders = _get_json(
        base_url,
        "/v1/reminders",
        {**query, "status": "open"},
    )
    files = _get_json(base_url, "/v1/files", query)
    email_messages = _get_json(base_url, "/v1/email-messages", query)
    ai_drafts = _get_json(base_url, "/v1/ai-drafts", query)
    email_import_batches = _get_json(base_url, "/v1/email-import-batches", query)
    product_ideas = _get_json(base_url, "/v1/product-ideas", query)
    boss_demo_ideas = _get_json(base_url, "/v1/product-ideas", {**query, "boss_demo_relevant": "true"})
    product_decisions = _get_json(base_url, "/v1/product-decisions", query)
    integrations_status = _get_json(base_url, "/v1/integrations/status")
    ai_status = _get_json(base_url, "/v1/ai/status")

    _require_count("clients", clients, EXPECTED_COUNTS["clients"])
    _require_count("sites", sites, EXPECTED_COUNTS["sites"])
    _require_count("mapped sites", map_sites, EXPECTED_COUNTS["map_sites"])
    _require_count("jobs", jobs, EXPECTED_COUNTS["jobs"])
    _require_count("reminders", reminders, EXPECTED_COUNTS["reminders"])
    _require_count("open reminders", open_reminders, EXPECTED_COUNTS["open_reminders"])
    _require_count("files", files, EXPECTED_COUNTS["files"])
    _require_count("email messages", email_messages, EXPECTED_COUNTS["email_messages"])
    _require_count("AI drafts", ai_drafts, EXPECTED_COUNTS["ai_drafts"])
    _require_count("email import batches", email_import_batches, EXPECTED_COUNTS["email_import_batches"])
    _require_count("product ideas", product_ideas, EXPECTED_COUNTS["product_ideas"])
    if boss_demo_ideas.get("total", 0) < 1:
        raise SmokeFailure("Expected at least one boss-demo-relevant product idea.")
    _require_count("product decisions", product_decisions, EXPECTED_COUNTS["product_decisions"])
    if "outlook" not in integrations_status or "ai" not in integrations_status:
        raise SmokeFailure("Integration status response did not include outlook and ai.")
    if "enabled" not in ai_status:
        raise SmokeFailure("AI status response did not include enabled.")

    link_extraction = _post_json(
        base_url,
        "/v1/ai/extract-file-links",
        {
            "organization_id": organization_id,
            "text": "https://drive.google.com/file/d/smoke/view and https://example.com/smoke",
        },
    )
    if len(link_extraction.get("links", [])) != 2:
        raise SmokeFailure(f"Expected 2 deterministic extracted links, got {link_extraction!r}.")

    first_client = clients["items"][0]
    first_site = sites["items"][0]
    first_job = jobs["items"][0]
    client_sites = _get_json(base_url, f"/v1/clients/{first_client['id']}/sites", query)
    client_jobs = _get_json(base_url, f"/v1/clients/{first_client['id']}/jobs", query)
    site_jobs = _get_json(base_url, f"/v1/sites/{first_site['id']}/jobs", query)
    timeline_query = {"organization_id": organization_id, "limit": 10}
    client_timeline = _get_json(
        base_url,
        "/v1/timeline",
        {**timeline_query, "client_id": first_client["id"]},
    )
    site_timeline = _get_json(
        base_url,
        "/v1/timeline",
        {**timeline_query, "site_id": first_site["id"]},
    )
    job_timeline = _get_json(
        base_url,
        "/v1/timeline",
        {**timeline_query, "job_id": first_job["id"]},
    )
    job_readiness = _get_json(
        base_url,
        f"/v1/jobs/{first_job['id']}/report-readiness",
        {"organization_id": organization_id},
    )
    _require_timeline("client", client_timeline)
    _require_timeline("site", site_timeline)
    _require_timeline("job", job_timeline)
    if job_readiness.get("overall_status") not in VALID_READINESS_STATUSES:
        raise SmokeFailure(f"Unexpected report readiness response: {job_readiness!r}.")

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
    print(f"mapped sites: {map_sites['total']} - {_sample_names(map_sites)}")
    print(f"jobs: {jobs['total']} - {_sample_names(jobs)}")
    print(f"reminders: {reminders['total']} ({open_reminders['total']} open)")
    print(f"files: {files['total']}")
    print(f"email messages: {email_messages['total']}")
    print(f"AI drafts: {ai_drafts['total']}")
    print(f"email import batches: {email_import_batches['total']}")
    print(f"product ideas: {product_ideas['total']} ({boss_demo_ideas['total']} boss-demo relevant)")
    print(f"product decisions: {product_decisions['total']}")
    print(
        "integrations: "
        f"outlook={integrations_status['outlook']['status']}, "
        f"ai={'enabled' if ai_status['enabled'] else 'disabled'}",
    )
    print(f"deterministic link extraction: {len(link_extraction['links'])} links")
    print(f"linked client sites: {client_sites['total']} for {first_client['name']}")
    print(f"linked client jobs: {client_jobs['total']} for {first_client['name']}")
    print(f"linked site jobs: {site_jobs['total']} for {first_site['name']}")
    print(
        "timelines: "
        f"client={len(client_timeline['items'])}, "
        f"site={len(site_timeline['items'])}, "
        f"job={len(job_timeline['items'])}",
    )
    print(
        "job report readiness: "
        f"{job_readiness['overall_status']} "
        f"({job_readiness.get('score', 'n/a')}%) for {first_job['name']}",
    )
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
