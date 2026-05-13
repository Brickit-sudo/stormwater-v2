# Stormwater V2 Web

Next.js App Router frontend for the V2 CRM.

## Setup

```powershell
cd apps\web
npm install
copy .env.example .env.local
```

Set `apps/web/.env.local`:

```text
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_DEMO_ORG_ID=<printed seed org id>
```

`NEXT_PUBLIC_DEMO_ORG_ID` is temporary. Auth and membership-derived organization scoping are deferred, so the CRM uses this value when calling the `/v1` API. If it is missing, the app shows a setup message instead of making API calls.
Restart `npm run dev` after changing `.env.local`.

To create local demo data, set `apps\api\.env`, run migrations, then run this from `apps\api`:

```powershell
docker start stormwater-v2-postgres
.\.venv\Scripts\python -m alembic upgrade head
.\.venv\Scripts\python scripts\seed_dev.py
```

If the Postgres container does not exist yet:

```powershell
docker run --name stormwater-v2-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres -e POSTGRES_DB=stormwater_v2 -p 5432:5432 -d postgres:16
```

Use `--reset-seed` when you want to remove only existing `legacy_source='seed_dev'` demo CRM rows before reseeding:

```powershell
.\.venv\Scripts\python scripts\seed_dev.py --reset-seed
```

Copy the printed organization UUID into `NEXT_PUBLIC_DEMO_ORG_ID`. The current deterministic seed prints `850c47b8-6d32-58a0-8605-955527cadbf3` and creates one organization, three clients, five sites, eight jobs, four local reminders, seven `evidence_files` metadata rows, one local email import batch, five local email messages, and three manual AI drafts that drive the CRM, `/schedule`, `/map`, and `/work`.

## Run

Start the API:

```powershell
cd apps\api
.\.venv\Scripts\python -m uvicorn app.main:app --reload
```

Start the web app:

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

## CRM Routes

- `/crm/clients` lists, creates, edits, archives, and shows linked sites/jobs.
- `/crm/sites` lists, creates, edits, archives, filters by client, and shows linked jobs.
- `/crm/jobs` lists, creates, edits, archives, and updates job status.
- `/schedule` lists local reminders grouped by Overdue, Today, Upcoming, and Completed; it supports New, Edit, Mark Complete, Archive, status filtering, and priority filtering.
- `/map` shows non-archived sites with stored coordinates on a lazy-loaded Leaflet map, supports real status/client filters, manual Refresh Map, marker selection, and an Open Sites link.
- `/work` shows Files, Emails, Outlook Import, AI Drafts, and Import Batches. Emails are local records with paginated search/filtering and selected-message preview. Outlook Import is explicit preview/import-selected only. AI Drafts are manual storage only. Import Batches show local metadata from seed and imports.

The Jobs detail panel also shows a compact reminders section for the selected job. It can add a reminder for that job, mark job reminders complete, and archive them. Editing reminders stays on `/schedule`.

Reminders are local-only in this phase. There is no Outlook sync, Gmail sync, external calendar event creation, email sending, push notification, AI follow-up, or fake provider button. The list view shipped before a calendar grid to keep scheduling fast and safe while future integration details are still deferred.

## Lazy Site Map

The map route calls `GET /v1/sites/map`, which returns only lightweight site location fields. Leaflet and React Leaflet are dynamically imported by `/map`; normal CRM pages, the dashboard, layout, and app shell do not import map code.

This phase uses a no-key OpenStreetMap tile layer for local development and canvas-backed markers for the capped map result set. The page never geocodes on render, never auto-refreshes, and does not expose route optimization, dispatch, calendar sync, report, or photosheet actions. Google Maps, Mapbox, routing, geocoding, and production tile-provider choices are deferred.

## Drive/File Panel

Each CRM detail view (Client, Site, Job) renders a Drive/File panel scoped to the selected record. It supports:

- An **Open Drive Folder** link when the selected record (or, for jobs, the parent site) has a `drive_folder_url` set; otherwise a `No Drive folder linked yet.` empty state.
- A list of linked file metadata rows (`evidence_files`) filtered to the selected entity.
- **Add File Link** - a metadata-only form that creates an `evidence_files` row. Required: file name. Optional: file URL, source (Drive link / Other), MIME type, caption.
- **Archive** - soft-deletes the link via `archived_at`. **It does not touch the actual file in Google Drive.**
- **Refresh** - re-fetches the list.

This phase is metadata-only. There is no binary upload, no Google Drive OAuth, no folder creation, no folder scanning, no sync, no report or photosheet generation. Those are deferred and intentionally not exposed as disabled placeholder buttons.

## Work Hub

Work Hub is local-first in this phase. Outlook Import lives only under `/work`; it does not run from CRM pages, does not poll on page load, and does not import automatically. The status card reads API configuration, Preview Outlook Emails and Refresh Preview make explicit bounded preview requests, and Import Selected Emails writes only checked preview rows into local `email_messages`.

The preview MVP requires Microsoft Graph env vars in `apps/api/.env` plus a request-supplied access token. There is no full OAuth UI yet, no Gmail, no Sync All Mailbox, no sending, no Outlook draft creation, no attachment download, no OneDrive/SharePoint scan, and no AI generation.

Every visible Work Hub action does real work: switch views, search/filter local emails, preview Outlook emails on request, import selected preview rows, paginate lists, link an email to a Client/Site/Job, create/edit/archive manual drafts, mark drafts reviewed/used, archive email records, and open stored file/link URLs.
