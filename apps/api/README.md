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

The deterministic seed creates one organization, three clients, five sites, eight jobs, four local reminders, and seven `evidence_files` metadata rows. The seven file rows include client-level, site-level, and job-level examples to exercise the Drive/File panel on each CRM detail view. The four reminders include overdue, due-today, upcoming, and completed examples for `/schedule`. Re-run without `--reset-seed` to update those rows in place. Re-run with `--reset-seed` to delete only the demo organization's seed rows before reseeding.

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

The `/v1/files` endpoints manage **metadata-only** rows in the `evidence_files` table. This phase does not implement binary upload, Google Drive OAuth, folder creation, folder scanning, or sync. `DELETE` is a soft archive (`archived_at`) - it never touches the actual file in Google Drive.

The `/v1/reminders` endpoints manage local-only reminders linked to exactly one Client, Site, or Job. This phase does not implement Outlook OAuth, Gmail OAuth, calendar sync, email sending, external calendar event creation, push notifications, or AI follow-up drafting. `DELETE` soft archives a reminder by setting `status=archived` and `archived_at`; normal lists exclude archived records unless `status=archived` is requested.

Filter the reminder list with `status`, `priority`, `client_id`, `site_id`, `job_id`, `due_before`, and `due_after` query params:

```
GET /v1/reminders?organization_id=<uuid>&job_id=<job-uuid>
```

Filter the list with `client_id`, `site_id`, or `job_id` query params:

```
GET /v1/files?organization_id=<uuid>&job_id=<job-uuid>
```

The `source` field is currently treated as an enum-like string. Allowed values: `drive_link` (default), `upload_placeholder`, `report_export`, `photo`, `other`.

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
