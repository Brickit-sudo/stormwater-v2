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

Copy the printed organization UUID into `NEXT_PUBLIC_DEMO_ORG_ID`. The current deterministic seed prints `850c47b8-6d32-58a0-8605-955527cadbf3` and creates one organization, three clients, five sites, and eight jobs.

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

## CRM Routes

- `/crm/clients` lists, creates, edits, archives, and shows linked sites/jobs.
- `/crm/sites` lists, creates, edits, archives, filters by client, and shows linked jobs.
- `/crm/jobs` lists, creates, edits, archives, and updates job status.

Reports, photos, Drive integration, auth, and offline/local-first sync are intentionally deferred.
