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

For the full local V2 demo launcher, use this from the repo root:

```powershell
.\scripts\start-v2-demo.ps1 -Seed
```

Status and stop helpers:

```powershell
.\scripts\status-v2-demo.ps1
.\scripts\stop-v2-demo.ps1
```

See `..\..\docs\deployment\local-demo.md`,
`..\..\docs\deployment\staging-deploy-plan.md`, and
`..\..\docs\deployment\staging-auth-plan.md`.

Set `DATABASE_URL` in `.env` for local Postgres:

```text
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/stormwater_v2
```

Local demo auth defaults:

```text
AUTH_ENABLED=false
JWT_SECRET_KEY=
JWT_EXPIRES_MINUTES=720
AUTH_COOKIE_NAME=stormwater_v2_session
AUTH_COOKIE_SECURE=false
AUTH_COOKIE_SAMESITE=lax
DEMO_ADMIN_EMAIL=admin@stormwater.local
DEMO_ADMIN_PASSWORD=
```

For protected staging set `AUTH_ENABLED=true`, use a strong
`JWT_SECRET_KEY`, set `AUTH_COOKIE_SECURE=true` behind HTTPS, and provide
`DEMO_ADMIN_EMAIL` plus `DEMO_ADMIN_PASSWORD` before running the seed script.
The seed stores only a bcrypt hash.

Optional Outlook OAuth + Import Preview/Draft settings:

```text
MICROSOFT_TENANT_ID=<tenant id>
MICROSOFT_CLIENT_ID=<app client id>
MICROSOFT_CLIENT_SECRET=<app client secret>
MICROSOFT_REDIRECT_URI=http://localhost:8000/v1/outlook/auth/callback
MICROSOFT_GRAPH_BASE_URL=https://graph.microsoft.com/v1.0
TOKEN_ENCRYPTION_KEY=<optional strong local token protection key>
```

Register the Microsoft app with this redirect URI and delegated scopes `offline_access`, `User.Read`, and `Mail.ReadWrite`. `Mail.ReadWrite` is required for creating Outlook Draft messages; `Mail.Send` is not requested. These values are optional for normal API startup and tests. If they are missing, only the Outlook auth/import/draft endpoints return a clear configuration error. Do not commit real `.env` secrets.

Token data is stored only in the API database, never returned to the frontend. Set `TOKEN_ENCRYPTION_KEY` for local token protection; without it, development uses a server-side obfuscation fallback that is not production encryption.

Optional AI assistant settings:

```text
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
AI_FEATURES_ENABLED=
```

These values are optional. If `OPENAI_API_KEY` is missing, provider-backed draft generation is disabled and the `/v1/ai/*` routes return disabled responses where AI is required. Deterministic URL extraction, action candidates, and exact-match record suggestions still work locally. Tests mock provider behavior and do not call real OpenAI, Microsoft, or Google APIs.

Optional Google Drive Picker readiness settings:

```text
GOOGLE_CLIENT_ID=
GOOGLE_API_KEY=
```

These values are optional for normal startup and tests. `/v1/integrations/status`
reports whether Picker config is present, but it never returns the actual
client id or API key. Picker/manual selection is metadata-only; the API does
not crawl Drive folders, download file contents, upload files, OCR files,
analyze file contents with AI, or generate reports from files.

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

## Auth And CRM Organization Scope

CRM endpoints still require an explicit `organization_id` for compatibility:

- Create endpoints take `organization_id` in the JSON body.
- List/get/patch/delete and linked child endpoints take `organization_id` as a query parameter.

When `AUTH_ENABLED=false`, this is the local demo bridge. When
`AUTH_ENABLED=true`, `/v1/auth/login` sets an HttpOnly signed session cookie,
`/v1/auth/me` returns the current user/org membership, and every protected data
route verifies that the logged-in user belongs to the requested organization.
Normal list/get routes still exclude archived records.

For local frontend development, create a temporary organization and demo CRM records with:

```powershell
cd apps\api
.\.venv\Scripts\python scripts\seed_dev.py --reset-seed
```

The deterministic seed creates one organization, three clients, five sites with public approximate map coordinates, eight jobs, four local reminders, seven `evidence_files` metadata rows, one local email import batch, five local email messages, three email record links, three AI drafts, 21 product ideas, and eight product decisions. The seeded emails include Google Drive, OneDrive, SharePoint, action-item, and linked-record examples. The seeded roadmap examples capture internal ideas, deferred work, boss-demo-relevant items, and product decisions. Re-run without `--reset-seed` to update those rows in place. Re-run with `--reset-seed` to delete only the demo organization's seed rows before reseeding.

Copy the printed `NEXT_PUBLIC_DEMO_ORG_ID` value into `apps\web\.env.local`:

```text
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_AUTH_ENABLED=false
NEXT_PUBLIC_DEMO_ORG_ID=<printed seed org id>
NEXT_PUBLIC_GOOGLE_CLIENT_ID=
NEXT_PUBLIC_GOOGLE_API_KEY=
NEXT_PUBLIC_GOOGLE_APP_ID=
```

`NEXT_PUBLIC_DEMO_ORG_ID` is only a development bridge when auth is disabled.
Protected staging should use `NEXT_PUBLIC_AUTH_ENABLED=true` and leave the demo
org bridge blank.

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

## V2 Import Readiness Contract

The V2 import foundation is separate from the older V1 migration dry-run. It defines the future CRM import contract, reference tables, safe fake templates, and a CSV validator for Clients, Contacts, Sites, Jobs, Documents, and Emails.

- Contract: `..\..\docs\architecture\v2-database-import-contract.md`
- Templates: `..\..\docs\import_templates\v2\`
- Tiny real Clients/Sites workflow: `..\..\docs\import_templates\v2\tiny-real-sample-workflow.md`
- Validator: `scripts\validate_import_templates.py`

First tiny private Clients/Sites validation from the repo root:

```powershell
cd C:\Users\brolf\Desktop\Stormwater_APP_Clean\stormwater-v2
.\scripts\validate-v2-import-sample.ps1
```

Explicit private sample paths:

```powershell
.\scripts\validate-v2-import-sample.ps1 `
  -ClientsPath "docs\import_templates\v2\private\clients_tiny_sample.csv" `
  -SitesPath "docs\import_templates\v2\private\sites_tiny_sample.csv"
```

Example validation against the committed fake templates:

```powershell
cd apps\api
.\.venv\Scripts\python scripts\validate_import_templates.py --clients "..\..\docs\import_templates\v2\clients_template.csv" --contacts "..\..\docs\import_templates\v2\contacts_template.csv" --sites "..\..\docs\import_templates\v2\sites_template.csv" --jobs "..\..\docs\import_templates\v2\jobs_template.csv" --documents "..\..\docs\import_templates\v2\documents_template.csv" --emails "..\..\docs\import_templates\v2\emails_template.csv"
```

The validator reads CSV files only. It does not open a database connection, write CRM rows, call Outlook/Gmail/Drive/OpenAI, run a V1 apply migration, or import real data. Private real-data copies belong under ignored paths such as `docs\import_templates\v2\private\`, `docs\import_templates\v2\filled\`, or `apps\api\import_data\`. Generated validation reports belong under ignored `import_validation_reports\`.

## Current Endpoints

- `GET /health`
- `POST /v1/auth/login`
- `POST /v1/auth/logout`
- `GET /v1/auth/me`
- `GET /v1/search`
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
- `GET /v1/product-ideas`
- `POST /v1/product-ideas`
- `GET /v1/product-ideas/{idea_id}`
- `PATCH /v1/product-ideas/{idea_id}`
- `DELETE /v1/product-ideas/{idea_id}`
- `GET /v1/product-decisions`
- `POST /v1/product-decisions`
- `PATCH /v1/product-decisions/{decision_id}`
- `DELETE /v1/product-decisions/{decision_id}`
- `GET /v1/files`
- `POST /v1/files`
- `GET /v1/files/{file_id}`
- `PATCH /v1/files/{file_id}`
- `DELETE /v1/files/{file_id}`
- `GET /v1/email-import-batches`
- `POST /v1/email-import-batches`
- `GET /v1/email-import-batches/{batch_id}`
- `GET /v1/integrations/status`
- `GET /v1/ai/status`
- `POST /v1/ai/email-summary`
- `POST /v1/ai/email-action-items`
- `POST /v1/ai/extract-file-links`
- `POST /v1/ai/suggest-record-links`
- `POST /v1/ai/draft-reply`
- `POST /v1/ai/report-section-draft`
- `POST /v1/ai/maintenance-recommendation-draft`
- `POST /v1/ai/client-summary-draft`
- `GET /v1/outlook/status`
- `GET /v1/outlook/auth/status`
- `GET /v1/outlook/auth/start`
- `GET /v1/outlook/auth/callback`
- `POST /v1/outlook/auth/disconnect`
- `POST /v1/outlook/preview`
- `POST /v1/outlook/import-selected`
- `POST /v1/outlook/drafts/from-ai-draft`
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

The `/v1/files` endpoints manage **metadata-only** rows in the `evidence_files` table. This phase does not implement binary upload, server-side Google Drive OAuth/token storage, folder creation, folder scanning, Drive sync, file download, OCR, AI file analysis, or report generation from files. `DELETE` is a soft archive (`archived_at`) - it never touches the actual file in Google Drive.

The `/v1/reminders` endpoints manage local-only reminders linked to exactly one Client, Site, or Job. This phase does not implement Outlook OAuth, Gmail OAuth, calendar sync, email sending, external calendar event creation, push notifications, or AI follow-up drafting. `DELETE` soft archives a reminder by setting `status=archived` and `archived_at`; normal lists exclude archived records unless `status=archived` is requested.

The `/v1/search` endpoint is local-only global search. It searches bounded, organization-scoped V2 database rows for Clients, Sites, Jobs, evidence file metadata, local email message records, AI drafts, and reminders. It never calls Outlook, Gmail, Google Drive, OneDrive, SharePoint, OpenAI, scans folders, downloads files, syncs mailboxes, or indexes external providers. `q` is required with at least two characters. `limit` defaults to `10` per type and is capped at `25`; `types` can narrow the grouped response to `clients`, `sites`, `jobs`, `files`, `emails`, `ai_drafts`, and `reminders`. Email and draft text matching uses capped local text prefixes instead of unbounded provider/body scans.

The `/v1/product-ideas` and `/v1/product-decisions` endpoints manage the
internal roadmap tracker. They are organization-scoped, soft-archive records,
and normal lists exclude archived rows. Ideas can be filtered by `status`,
`priority`, `category`, `lane`, and `boss_demo_relevant`. This is product
memory only: do not store secrets, OAuth tokens, passwords, or private client
details in roadmap notes.

The Work Hub email endpoints are local-first. `/v1/email-messages` stores seeded, manual, or explicitly imported Outlook message records, supports paginated search/filtering, and archives by setting `status=archived` and `archived_at`. `/v1/email-record-links` links an email to exactly one Client, Site, or Job and updates the email's direct scope fields. `/v1/ai-drafts` stores review-first draft text linked to Client/Site/Job/Email records. `/v1/outlook/drafts/from-ai-draft` creates an Outlook Draft from a reviewed email-style AI draft, stores provider metadata on that local draft, and never sends. `/v1/ai/*` can generate or suggest structured outputs, but it never sends email, generates final reports, downloads attachments, or auto-links records. `/v1/email-import-batches` stores local batch metadata.

### Outlook OAuth, Import Preview, And Draft Push

Outlook import and draft push are bounded to explicit Work Hub requests:

- `GET /v1/outlook/status` reports Microsoft Graph env status and never returns secrets.
- `GET /v1/outlook/auth/status?organization_id=<uuid>` reports configured, connected, expired, disconnected, or error state and never returns tokens.
- `GET /v1/outlook/auth/start?organization_id=<uuid>` returns the Microsoft authorization URL. It requests only `offline_access`, `User.Read`, and `Mail.ReadWrite`; it never requests `Mail.Send`.
- `GET /v1/outlook/auth/callback` validates signed state, exchanges the authorization code, reads basic user profile identity, and stores protected token data server-side.
- `POST /v1/outlook/auth/disconnect` disconnects the active Outlook connection, archives it, and clears stored token values from the active row.
- `POST /v1/outlook/preview` requires `organization_id`, a request body, configured Microsoft env vars, and either a stored Outlook connection or an advanced request token. It calls Microsoft Graph only for that explicit preview, caps `limit` at 100, and writes nothing locally.
- `POST /v1/outlook/import-selected` accepts selected preview messages, creates an `email_import_batches` row, creates new `email_messages`, and skips duplicates by `provider_message_id` and `internet_message_id`.
- `POST /v1/outlook/drafts/from-ai-draft` requires a stored Outlook connection, an email-style AI draft, To recipients, a subject, and usable body text. It posts to Microsoft Graph `/me/messages` to create a draft, saves the provider draft ID/web link/status on `ai_drafts`, and leaves review/send in Outlook.

This phase does not implement background mailbox sync, delta query, polling, Gmail, email sending, automatic Outlook draft creation, attachment downloads, full mailbox import, or OneDrive/SharePoint scanning. Smart Hub AI can run later against local imported email records, not during Outlook import. Tests mock Graph and OAuth exchange and do not require a real Outlook account.

Future Outlook draft work can add push revisions, explicit reviewed send, and sent-state sync.

Filter the reminder list with `status`, `priority`, `client_id`, `site_id`, `job_id`, `due_before`, and `due_after` query params:

```
GET /v1/reminders?organization_id=<uuid>&job_id=<job-uuid>
```

Filter the list with `client_id`, `site_id`, or `job_id` query params:

```
GET /v1/files?organization_id=<uuid>&job_id=<job-uuid>
```

The `source` field is currently treated as an enum-like string. Allowed values: `drive_link` (default), `google_drive`, `upload_placeholder`, `report_export`, `photo`, `other`.

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
