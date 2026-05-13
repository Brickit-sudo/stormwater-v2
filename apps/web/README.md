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
NEXT_PUBLIC_GOOGLE_CLIENT_ID=
NEXT_PUBLIC_GOOGLE_API_KEY=
NEXT_PUBLIC_GOOGLE_APP_ID=
```

`NEXT_PUBLIC_DEMO_ORG_ID` is temporary. Auth and membership-derived organization scoping are deferred, so the CRM uses this value when calling the `/v1` API. If it is missing, the app shows a setup message instead of making API calls.
The Google Picker values are optional. Leave them blank to show the configure
state and keep using Add File Link. If configured, restrict the browser API key
in Google Cloud.
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

Copy the printed organization UUID into `NEXT_PUBLIC_DEMO_ORG_ID`. The current deterministic seed prints `850c47b8-6d32-58a0-8605-955527cadbf3` and creates one organization, three clients, five sites, eight jobs, four local reminders, seven `evidence_files` metadata rows, one local email import batch, five local email messages, and three AI drafts that drive the CRM, `/schedule`, `/map`, and `/work`.

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

- `http://127.0.0.1:3000/search`
- `http://127.0.0.1:3000/crm/clients`
- `http://127.0.0.1:3000/crm/sites`
- `http://127.0.0.1:3000/crm/jobs`
- `http://127.0.0.1:3000/schedule`
- `http://127.0.0.1:3000/map`
- `http://127.0.0.1:3000/work`

## CRM Routes

- `/search` searches bounded local V2 CRM records across Clients, Sites, Jobs, evidence file metadata, imported email records, AI drafts, and reminders. It runs only on explicit submit, uses `GET /v1/search`, and does not call Outlook, Gmail, Google Drive, OneDrive, SharePoint, OpenAI, or external provider search.
- `/crm/clients` lists, creates, edits, archives, and shows linked sites/jobs.
- `/crm/sites` lists, creates, edits, archives, filters by client, and shows linked jobs.
- `/crm/jobs` lists, creates, edits, archives, and updates job status.
- `/schedule` lists local reminders grouped by Overdue, Today, Upcoming, and Completed; it supports New, Edit, Mark Complete, Archive, status filtering, and priority filtering.
- `/map` shows non-archived sites with stored coordinates on a lazy-loaded Leaflet map, supports real status/client filters, manual Refresh Map, marker selection, and an Open Sites link.
- `/work` shows Files, Emails, Outlook Import, AI Drafts, Import Batches, and provider readiness. Emails are local records with paginated search/filtering, selected-message preview, deterministic link/action/record suggestions, reviewed reminder creation, reviewed file-link saving, and config-gated AI drafting. Outlook Import has real Connect, Disconnect, explicit preview, and import-selected actions only. Import Batches show local metadata from seed and imports.

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
- **Select from Google Drive** when Picker credentials are configured. This
  loads Google scripts only after click, lets the user choose one Drive file,
  and saves returned metadata with `source = "google_drive"`.
- **Archive** - soft-deletes the link via `archived_at`. **It does not touch the actual file in Google Drive.**
- **Refresh** - re-fetches the list.

This phase is metadata-only. There is no binary upload, no server-side Google
Drive OAuth/token storage, no folder creation, no folder scanning, no sync, no
file download, no OCR, no AI file analysis, and no report or photosheet
generation. Those are deferred and intentionally not exposed as disabled
placeholder buttons.

## Work Hub

Work Hub is local-first in this phase. Outlook Import lives only under `/work`; it does not run from CRM pages, does not poll on page load, and does not import automatically. Provider readiness reads API configuration and, on `/work`, the active Outlook connection state. Preview Outlook Emails and Refresh Preview are disabled until Microsoft Graph env vars are present and Outlook is connected, then they make explicit bounded preview requests. Import Selected Emails writes only checked preview rows into local `email_messages`.

The Work Hub Files view can save a Google Picker selection only after the user
chooses a target Client, Site, or Job. It saves metadata only and then refreshes
the local file list. It does not show a global Drive dump.

Connect Outlook calls `GET /v1/outlook/auth/start` and opens the Microsoft authorization URL. The API callback stores tokens server-side only; the frontend receives connection status and account identity, never access or refresh token values. A hidden advanced request-token field remains for local development and tests.

Smart Hub AI requires `OPENAI_API_KEY` for provider-backed draft generation, but deterministic link extraction, action candidates, and exact-match CRM suggestions work without AI configuration.

Reviewed email-style AI drafts can be pushed to Outlook Drafts when Outlook is connected with Microsoft Graph `Mail.ReadWrite`. The Work Hub requires To, Subject, and body review fields, calls the backend only after Create Outlook Draft, saves the Outlook draft metadata on the local AI draft, and leaves review/send in Outlook. It does not expose a Send button and `Mail.Send` is not requested.

There is no Gmail sync, no Sync All Mailbox, no sending, no automatic Outlook draft creation, no attachment download, no full mailbox import, no Drive/OneDrive/SharePoint scan, no file upload, no file download, no OCR, no AI file analysis, no final report generation, and no automatic reminders or auto-linking.

Future Outlook draft work can add push revisions, explicit reviewed send, and sent-state sync.

Every visible Work Hub action does real work: switch views, refresh provider status, search/filter local emails, preview Outlook emails when configured, import selected preview rows, paginate lists, link an email to a Client/Site/Job, summarize/extract/suggest from local messages, create reminders from selected suggestions, save file metadata links, create/edit/archive drafts, mark drafts reviewed/used, archive email records, and open stored file/link URLs.

## Global Search

Global Search is a local-only foundation. The sidebar and dashboard link to `/search`; the topbar search field navigates there on Enter. Results are grouped by record type and capped by the API. Search links only to real supported routes: Clients, Sites, Jobs, Work Hub, and Schedule. Provider search, full-text indexing, record-specific deep links for every surface, and a command palette are deferred.
