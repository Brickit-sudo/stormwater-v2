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
NEXT_PUBLIC_DEMO_ORG_ID=<organization UUID>
```

`NEXT_PUBLIC_DEMO_ORG_ID` is temporary. Auth and membership-derived organization scoping are deferred, so the CRM uses this value when calling the `/v1` API. If it is missing, the app shows a setup message instead of making API calls.
Restart `npm run dev` after changing `.env.local`.

To create local demo data, run this from `apps/api` after database migrations:

```powershell
.\.venv\Scripts\python scripts\seed_dev.py
```

Copy the printed organization UUID into `NEXT_PUBLIC_DEMO_ORG_ID`.

## Run

Start the API:

```powershell
cd apps\api
.\.venv\Scripts\uvicorn app.main:app --reload
```

Start the web app:

```powershell
cd apps\web
npm run dev
```

Open `http://localhost:3000`.

## CRM Routes

- `/crm/clients` lists, creates, edits, archives, and shows linked sites/jobs.
- `/crm/sites` lists, creates, edits, archives, filters by client, and shows linked jobs.
- `/crm/jobs` lists, creates, edits, archives, and updates job status.

Reports, photos, Drive integration, auth, and offline/local-first sync are intentionally deferred.
