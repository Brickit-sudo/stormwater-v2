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
NEXT_PUBLIC_DEMO_ORG_ID=<organization UUID>
```

`NEXT_PUBLIC_DEMO_ORG_ID` is temporary while auth and membership-derived organization scoping are deferred. The frontend will show a setup message instead of calling the API if this value is missing.
Restart `npm run dev` after editing `apps/web/.env.local`.

The first usable CRM UI is available at:

- `http://localhost:3000/crm/clients`
- `http://localhost:3000/crm/sites`
- `http://localhost:3000/crm/jobs`

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

```powershell
cd apps\api
copy .env.example .env
```

Set `DATABASE_URL` in `apps/api/.env`, then run migrations:

```powershell
.\.venv\Scripts\alembic heads
.\.venv\Scripts\alembic upgrade head
```

API checks:

```powershell
.\.venv\Scripts\python -m compileall app tests
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -c "from app.main import app; print([r.path for r in app.routes])"
```

First CRM API routes are available for clients, sites, and jobs under `/v1`. Until auth is added, create requests include `organization_id` in the JSON body, while list/get/patch/delete requests pass `organization_id` as a query parameter.

Optional dev seed data:

```powershell
cd apps\api
.\.venv\Scripts\python scripts\seed_dev.py
```

The seed script creates one organization, client, site, and job, then prints the `NEXT_PUBLIC_DEMO_ORG_ID` value to paste into `apps/web/.env.local`.

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
