# Stormwater V2 API

FastAPI backend for the V2 CRM database and future report/file workflows.

## Setup

```powershell
cd apps\api
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
```

Set `DATABASE_URL` in `.env` for local Postgres:

```text
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/stormwater_v2
```

Optional Outlook Import Preview settings:

```text
MICROSOFT_TENANT_ID=<tenant id>
MICROSOFT_CLIENT_ID=<app client id>
MICROSOFT_CLIENT_SECRET=<app client secret>
MICROSOFT_REDIRECT_URI=http://localhost:8000/v1/outlook/oauth/callback
MICROSOFT_GRAPH_BASE_URL=https://graph.microsoft.com/v1.0
```

These values are optional for normal API startup and tests. If they are missing, only the Outlook import endpoints return a clear configuration error. Do not commit real `.env` secrets.

## Database

Alembic is configured under `apps/api/alembic` and reads the same `DATABASE_URL`.

Start the local Postgres container if it already exists:

```powershell
docker start stormwater-v2-postgres
```

Or create it:

```powershell
docker run --name stormwater-v2-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres -e POSTGRES_DB=stormwater_v2 -p 5432:5432 -d postgres:16
```

Create `apps\api\.env`:

```text
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/stormwater_v2
```

```powershell
cd apps\api
.\.venv\Scripts\python -m alembic heads
.\.venv\Scripts\python -m alembic upgrade head
```

`alembic upgrade head` requires a reachable Postgres database. Importing the app and model metadata does not.

## Run API

```powershell
cd apps\api
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`.

Interactive docs are available at `http://localhost:8000/docs`.

## CRM Organization Scope

Authentication and membership-derived organization scoping are deferred. For now, CRM endpoints require an explicit `organization_id`:

- Create endpoints take `organization_id` in the JSON body.
- List/get/patch/delete and linked child endpoints take `organization_id` as a query parameter.

Every service query filters by `organization_id`, and normal list/get routes exclude archived records.

For local frontend development, create a temporary organization and demo CRM records with:

```powershell
cd apps\api
.\.venv\Scripts\python scripts\seed_dev.py --reset-seed
```

The deterministic seed creates one organization, three clients, five sites with public approximate map coordinates, eight jobs, four local reminders, seven `evidence_files` metadata rows, one local email import batch, five local email messages, three email record links, and three manual AI drafts. The file rows exercise the Drive/File panel; the reminder rows exercise `/schedule`; the email rows exercise `/work`. Re-run without `--reset-seed` to update those rows in place. Re-run with `--reset-seed` to delete only the demo organization's seed rows before reseeding.

Copy the printed `NEXT_PUBLIC_DEMO_ORG_ID` value into `apps\web\.env.local`:

```text
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_DEMO_ORG_ID=<printed seed org id>
```

This is only a development bridge until auth and organization scoping are added.

## Tests And Checks

```powershell
cd apps\api
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m compileall app scripts tests
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -c "from app.main import app; print([r.path for r in app.routes])"
.\.venv\Scripts\python -m alembic heads
```

With the API running, verify the seeded CRM HTTP surface:

```powershell
.\.venv\Scripts\python scripts\smoke_crm_api.py
```

The route tests use an in-memory SQLite engine for only the CRM tables under test, so normal smoke tests do not require local Postgres. `alembic upgrade head` still requires a reachable Postgres database.

## V1 CRM Migration Dry-Run

Phase M1 is a read-only planning pass for the V1 SQLite CRM tables. It reads V1 `crm_contacts`, `crm_sites`, `crm_jobs`, and optional deferred tables, then prints what V2 clients, contacts, sites, and jobs would be created or updated. It does not connect to V2 Postgres and performs no writes.

```powershell
cd apps\api
.\.venv\Scripts\python scripts\migrate_v1.py --v1-db "PATH\TO\v1.sqlite" --organization-name "Sterling Stormwater" --dry-run --output-md migration-report.md
```

Optional JSON output is available with `--output-json migration-report.json`. `--apply` is accepted only to make the future CLI shape explicit; in M1 it exits with a not-implemented message and does not write anything.

### Client Alias Mapping

M1.6 can read an optional, private client alias CSV to deterministically resolve V1 site rows to proposed V2 clients before any apply migration exists.

Start from the fake template:

```powershell
copy apps\api\migration_maps\client_aliases.example.csv apps\api\migration_maps\client_aliases.csv
```

Edit `client_aliases.csv` locally with reviewed real mappings. Do not commit real client names or private mapping files; all CSVs under `migration_maps\` are ignored except `client_aliases.example.csv`. Generated `migration*.json`, `migration*.md`, `migration_reports\`, and `reports\migration\` outputs are also ignored.

To draft a private alias map from unresolved dry-run diagnostics:

```powershell
cd apps\api
.\.venv\Scripts\python scripts\migrate_v1.py --v1-db "PATH\TO\v1.sqlite" --organization-name "Sterling Stormwater" --dry-run --output-json migration-dry-run.json --output-md migration-report.md --write-alias-draft migration_maps\client_aliases.draft.csv
```

The draft contains private V1 site clues and leaves `target_client_name` blank for human review. It will not overwrite an existing draft unless `--force` is supplied.

```powershell
cd apps\api
.\.venv\Scripts\python scripts\migrate_v1.py --v1-db "PATH\TO\v1.sqlite" --organization-name "Sterling Stormwater" --dry-run --client-aliases migration_maps\client_aliases.csv --output-json migration-alias-dry-run.json --output-md migration-alias-report.md
```

The alias dry-run validates total/valid/invalid rows, blank required fields, unsupported `source_field` values, duplicate aliases, aliases that match no V1 sites, aliases that match multiple proposed clients, alias-created client proposals, and unresolved sites remaining after aliases.

Supported deterministic `source_field` values are `client_id`, `account`, `managed_by`, `site_name_exact`, `site_name_prefix`, `site_name_contains`, and `drive_parent_folder`. `drive_parent_folder` only resolves when the V1 site table has an explicit parent-folder field; the dry-run does not infer client ownership from city/state or from a site folder URL alone. `--apply` remains blocked in M1 even when aliases are supplied.

## Current Endpoints

- `GET /health`
- `GET /v1/clients`
- `POST /v1/clients`
- `GET /v1/clients/{client_id}`
- `PATCH /v1/clients/{client_id}`
- `DELETE /v1/clients/{client_id}`
- `GET /v1/clients/{client_id}/sites`
- `GET /v1/clients/{client_id}/jobs`
- `GET /v1/sites`
- `GET /v1/sites/map`
- `POST /v1/sites`
- `GET /v1/sites/{site_id}`
- `PATCH /v1/sites/{site_id}`
- `DELETE /v1/sites/{site_id}`
- `GET /v1/sites/{site_id}/jobs`
- `GET /v1/jobs`
- `POST /v1/jobs`
- `GET /v1/jobs/{job_id}`
- `PATCH /v1/jobs/{job_id}`
- `DELETE /v1/jobs/{job_id}`
- `GET /v1/reminders`
- `POST /v1/reminders`
- `GET /v1/reminders/{reminder_id}`
- `PATCH /v1/reminders/{reminder_id}`
- `DELETE /v1/reminders/{reminder_id}`
- `GET /v1/files`
- `POST /v1/files`
- `GET /v1/files/{file_id}`
- `PATCH /v1/files/{file_id}`
- `DELETE /v1/files/{file_id}`
- `GET /v1/email-import-batches`
- `POST /v1/email-import-batches`
- `GET /v1/email-import-batches/{batch_id}`
- `GET /v1/outlook/status`
- `POST /v1/outlook/preview`
- `POST /v1/outlook/import-selected`
- `GET /v1/email-messages`
- `POST /v1/email-messages`
- `GET /v1/email-messages/{email_message_id}`
- `PATCH /v1/email-messages/{email_message_id}`
- `DELETE /v1/email-messages/{email_message_id}`
- `POST /v1/email-record-links`
- `GET /v1/email-record-links`
- `DELETE /v1/email-record-links/{link_id}`
- `GET /v1/ai-drafts`
- `POST /v1/ai-drafts`
- `GET /v1/ai-drafts/{draft_id}`
- `PATCH /v1/ai-drafts/{draft_id}`
- `DELETE /v1/ai-drafts/{draft_id}`

The `/v1/files` endpoints manage **metadata-only** rows in the `evidence_files` table. This phase does not implement binary upload, Google Drive OAuth, folder creation, folder scanning, or sync. `DELETE` is a soft archive (`archived_at`) - it never touches the actual file in Google Drive.

The `/v1/reminders` endpoints manage local-only reminders linked to exactly one Client, Site, or Job. This phase does not implement Outlook OAuth, Gmail OAuth, calendar sync, email sending, external calendar event creation, push notifications, or AI follow-up drafting. `DELETE` soft archives a reminder by setting `status=archived` and `archived_at`; normal lists exclude archived records unless `status=archived` is requested.

The Work Hub email endpoints are local-first. `/v1/email-messages` stores seeded, manual, or explicitly imported Outlook message records, supports paginated search/filtering, and archives by setting `status=archived` and `archived_at`. `/v1/email-record-links` links an email to exactly one Client, Site, or Job and updates the email's direct scope fields. `/v1/ai-drafts` stores manual draft text linked to Client/Site/Job/Email records; it does not generate text, send email, or create Outlook drafts. `/v1/email-import-batches` stores local batch metadata.

### Outlook Import Preview MVP

Outlook import is bounded to explicit Work Hub requests:

- `GET /v1/outlook/status` reports Microsoft Graph env status and never returns secrets.
- `POST /v1/outlook/preview` requires `organization_id`, a request body, configured Microsoft env vars, and a request-supplied access token for this MVP. It calls Microsoft Graph only for that explicit preview, caps `limit` at 100, and writes nothing locally.
- `POST /v1/outlook/import-selected` accepts selected preview messages, creates an `email_import_batches` row, creates new `email_messages`, and skips duplicates by `provider_message_id` and `internet_message_id`.

This phase does not implement background mailbox sync, delta query, polling, Gmail, email sending, Outlook draft creation, attachment downloads, OneDrive/SharePoint scanning, or AI generation. Tests mock Graph and do not require a real Outlook account.

Filter the reminder list with `status`, `priority`, `client_id`, `site_id`, `job_id`, `due_before`, and `due_after` query params:

```
GET /v1/reminders?organization_id=<uuid>&job_id=<job-uuid>
```

Filter the list with `client_id`, `site_id`, or `job_id` query params:

```
GET /v1/files?organization_id=<uuid>&job_id=<job-uuid>
```

The `source` field is currently treated as an enum-like string. Allowed values: `drive_link` (default), `upload_placeholder`, `report_export`, `photo`, `other`.

## Lazy Site Map Endpoint

`GET /v1/sites/map` is the route-only map payload for the V2 frontend. It requires `organization_id`, excludes archived sites, and returns only sites that already have `latitude` and `longitude`.

Optional filters are `status`, `client_id`, `north`, `south`, `east`, `west`, `limit`, and `offset`. `limit` defaults to `1000` and is capped at `5000`.

The response is intentionally lightweight: `id`, `name`, `client_id`, `client_name`, `status`, `address`, `city`, `state`, `latitude`, and `longitude`. It does not include notes, Drive fields, evidence files, reports, jobs, or other linked arrays. It also does not geocode on request; Google Maps, Mapbox, routing, and geocoding workflows are deferred.

## Basic Examples

```powershell
$org = "00000000-0000-0000-0000-000000000000"

Invoke-RestMethod http://localhost:8000/v1/clients?organization_id=$org

Invoke-RestMethod `
  -Method Post `
  -ContentType "application/json" `
  -Uri http://localhost:8000/v1/clients `
  -Body (@{
    organization_id = $org
    name = "Acme Property Group"
    client_code = "ACME"
  } | ConvertTo-Json)
```
