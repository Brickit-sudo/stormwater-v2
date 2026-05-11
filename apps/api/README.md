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

The deterministic seed creates one organization, three clients, five sites, and eight jobs with `legacy_source='seed_dev'`. Re-run without `--reset-seed` to update those rows in place. Re-run with `--reset-seed` to delete only the demo organization's `seed_dev` clients, sites, and jobs before reseeding.

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
