# Stormwater V2

Stormwater V2 is the clean rewrite around the CRM as the source of truth:

Clients -> Sites -> Jobs / Visits -> BMP Systems -> Observations -> Photos / Files -> Reports / Quotes / Invoices.

The existing Streamlit app remains the V1 prototype/export lab while V2 grows into a mainstream web app.

## Repository Layout

```text
apps/
  web/                  # Next.js App Router frontend
  api/                  # FastAPI backend
packages/
  shared/               # Future TypeScript shared types/utilities
python/
  stormwater_core/      # Reusable Python report/photo/domain logic
docs/
  architecture/         # Architecture notes and decisions
  prompts/              # Build prompts and workflow notes
```

## Development

### Local End-To-End CRM

Start the local Postgres container if it already exists:

```powershell
docker start stormwater-v2-postgres
```

Or create it:

```powershell
docker run --name stormwater-v2-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres -e POSTGRES_DB=stormwater_v2 -p 5432:5432 -d postgres:16
```

Configure the API environment:

```powershell
cd apps\api
copy .env.example .env
```

Set `apps\api\.env`:

```text
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/stormwater_v2
```

Optional Outlook OAuth + Import Preview settings for `/work`:

```text
MICROSOFT_TENANT_ID=<tenant id>
MICROSOFT_CLIENT_ID=<app client id>
MICROSOFT_CLIENT_SECRET=<app client secret>
MICROSOFT_REDIRECT_URI=http://localhost:8000/v1/outlook/auth/callback
MICROSOFT_GRAPH_BASE_URL=https://graph.microsoft.com/v1.0
TOKEN_ENCRYPTION_KEY=<optional strong local token protection key>
```

Register the Microsoft app with the same redirect URI and delegated scopes `offline_access`, `User.Read`, and `Mail.Read`. Leave these blank to run the CRM without Outlook import. Real Microsoft secrets belong only in local `.env`, never in git. If `TOKEN_ENCRYPTION_KEY` is blank, tokens stay server-side but use the documented local-dev obfuscation mode.

Optional AI assistant settings for `/work`:

```text
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
AI_FEATURES_ENABLED=
```

Leave `OPENAI_API_KEY` blank to keep provider-backed AI drafting disabled. Local deterministic link extraction, action candidates, and record suggestions still work.

Run migrations and seed deterministic CRM demo data:

```powershell
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python scripts\seed_dev.py --reset-seed
```

The seed prints the demo organization id. For the current deterministic seed it is:

```text
850c47b8-6d32-58a0-8605-955527cadbf3
```

Copy the printed organization id into `apps\web\.env.local`:

```text
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_DEMO_ORG_ID=<printed seed org id>
```

Then run the API and web app in separate terminals:

```powershell
cd apps\api
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

```powershell
cd apps\web
npm run dev
```

Open:

- `http://127.0.0.1:3000/crm/clients`
- `http://127.0.0.1:3000/crm/sites`
- `http://127.0.0.1:3000/crm/jobs`
- `http://127.0.0.1:3000/schedule`
- `http://127.0.0.1:3000/map`
- `http://127.0.0.1:3000/work`

Optional API smoke after the API is running:

```powershell
cd apps\api
.\.venv\Scripts\python scripts\smoke_crm_api.py
```

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

The frontend runs at `http://localhost:3000`.

Create `apps/web/.env.local` from `apps/web/.env.example`:

```powershell
cd apps\web
copy .env.example .env.local
```

Set:

```text
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_DEMO_ORG_ID=<printed seed org id>
```

`NEXT_PUBLIC_DEMO_ORG_ID` is temporary while auth and membership-derived organization scoping are deferred. The frontend will show a setup message instead of calling the API if this value is missing.
Restart `npm run dev` after editing `apps/web/.env.local`.

The first usable CRM UI is available at:

- `http://localhost:3000/crm/clients`
- `http://localhost:3000/crm/sites`
- `http://localhost:3000/crm/jobs`
- `http://localhost:3000/schedule`
- `http://localhost:3000/map`
- `http://localhost:3000/work`

### API

```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`.

Health check:

```bash
curl http://localhost:8000/health
```

Database setup:

Start Postgres:

```powershell
docker start stormwater-v2-postgres
```

Or create it:

```powershell
docker run --name stormwater-v2-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres -e POSTGRES_DB=stormwater_v2 -p 5432:5432 -d postgres:16
```

Set `DATABASE_URL` in `apps/api/.env`, then run migrations:

```powershell
cd apps\api
.\.venv\Scripts\python -m alembic heads
.\.venv\Scripts\python -m alembic upgrade head
```

API checks:

```powershell
.\.venv\Scripts\python -m compileall app scripts tests
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -c "from app.main import app; print([r.path for r in app.routes])"
.\.venv\Scripts\python scripts\smoke_crm_api.py
```

First CRM API routes are available for clients, sites, jobs, files, and reminders under `/v1`. Until auth is added, create requests include `organization_id` in the JSON body, while list/get/patch/delete requests pass `organization_id` as a query parameter.

Optional dev seed data:

```powershell
cd apps\api
.\.venv\Scripts\python scripts\seed_dev.py --reset-seed
```

The seed script creates one deterministic organization, three clients, five sites, eight jobs, four local reminders, seven file metadata rows, one local email import batch, five local email messages, and three AI drafts, then prints the `NEXT_PUBLIC_DEMO_ORG_ID` value to paste into `apps/web/.env.local`. Re-run without `--reset-seed` to update seed rows in place, or with `--reset-seed` to delete only seed demo rows for the demo organization before reseeding.

### Work Hub And Email Intelligence

The `/work` route is the only place Outlook import, provider readiness, and Smart Hub AI actions appear. It shows existing file links, seeded/local email records, AI drafts, local import batch metadata, and an Outlook Import view.

Outlook import is preview/import-selected only: status reads local env and connection state, Connect Outlook starts Microsoft OAuth, callback stores server-side token data, preview calls Microsoft Graph only after a button click, and import writes only selected preview messages to local `email_messages` with an `email_import_batches` row. A hidden advanced request-token path remains for local development and tests.

Smart Hub AI is review-first. With no `OPENAI_API_KEY`, local deterministic helpers still extract Drive/OneDrive/SharePoint/web links, suggest action items, and suggest exact-match Client/Site/Job links. With `OPENAI_API_KEY`, explicit buttons can save email summaries, reply drafts, report sections, maintenance recommendations, and client-facing summaries as local `ai_drafts`. The app does not send email, create Outlook/Gmail drafts, generate final reports, download attachments, scan Drive/OneDrive folders, or auto-create reminders/links.

Future phases can add Microsoft Graph delta query/change notifications, Gmail push notifications, Google Drive/OneDrive picker flows, and pushing approved local drafts to Outlook drafts.

### Local Scheduling And Reminders

The `/schedule` page manages local-only reminders linked to exactly one Client, Site, or Job. It groups reminders by Overdue, Today, Upcoming, and Completed, supports create/edit, mark complete, archive, and filters by status or priority. The Jobs detail panel also shows job-linked reminders and can add a reminder for the selected job.

This phase deliberately does not add Outlook, Gmail, Calendar sync, external event creation, email sending, push notifications, or AI follow-up buttons. The list view shipped before a calendar grid so the core reminder workflow stays fast and safe while provider sync remains deferred.

### Lazy Site Map

The `/map` route shows seeded sites that already have latitude and longitude. It calls the lightweight `GET /v1/sites/map` endpoint, loads Leaflet only from the map route through a dynamic component, and does not load map code in the CRM pages, dashboard, layout, or app shell.

The map uses a no-key OpenStreetMap tile layer for local development and canvas-backed site markers. It does not geocode on render, auto-refresh, optimize routes, dispatch crews, sync calendars, or create reports. Google Maps, Mapbox, routing, geocoding, and production tile-provider decisions are deferred.

V1 CRM migration Phase M1 is dry-run only. It inspects the V1 SQLite CRM data and writes no V2 database rows:

```powershell
cd apps\api
.\.venv\Scripts\python scripts\migrate_v1.py --v1-db "PATH\TO\v1.sqlite" --organization-name "Sterling Stormwater" --dry-run --output-md migration-report.md
```

`--apply` is intentionally blocked until the M2 apply phase.

Example:

```powershell
$org = "00000000-0000-0000-0000-000000000000"
Invoke-RestMethod http://localhost:8000/v1/clients?organization_id=$org
```

### Reusable Python Core

```bash
cd python/stormwater_core
python -m pip install -e .
```

This package is intentionally empty of Streamlit dependencies. V1 logic should only move here when it can run without `streamlit`, `st.session_state`, page modules, or sidebar/UI imports.
