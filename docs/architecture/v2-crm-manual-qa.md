# V2 CRM Manual QA Checklist

Use this checklist after schema changes, seed changes, or CRM frontend work.

## Setup

- [ ] Start the local Postgres container:
  ```powershell
  docker start stormwater-v2-postgres
  ```
- [ ] If the container does not exist, create it:
  ```powershell
  docker run --name stormwater-v2-postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres -e POSTGRES_DB=stormwater_v2 -p 5432:5432 -d postgres:16
  ```
- [ ] Create `apps\api\.env`:
  ```text
  DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/stormwater_v2
  ```
- [ ] From `apps\api`, run Alembic upgrade:
  ```powershell
  .\.venv\Scripts\python -m alembic upgrade head
  ```
- [ ] From `apps\api`, run the deterministic seed:
  ```powershell
  .\.venv\Scripts\python scripts\seed_dev.py --reset-seed
  ```
- [ ] Copy the printed `NEXT_PUBLIC_DEMO_ORG_ID` value into `apps\web\.env.local`.
  ```text
  NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
  NEXT_PUBLIC_DEMO_ORG_ID=<printed org id>
  ```
- [ ] Start the API:
  ```powershell
  cd apps\api
  .\.venv\Scripts\python -m uvicorn app.main:app --reload
  ```
- [ ] Smoke-test the seeded API:
  ```powershell
  .\.venv\Scripts\python scripts\smoke_crm_api.py
  ```
- [ ] Start the web app:
  ```powershell
  cd apps\web
  npm run dev
  ```
- [ ] Open `http://127.0.0.1:3000/crm/clients`.
- [ ] Open `http://127.0.0.1:3000/crm/sites`.
- [ ] Open `http://127.0.0.1:3000/crm/jobs`.

## Clients

- [ ] List clients.
- [ ] Search clients.
- [ ] Select a client.
- [ ] View linked sites/jobs.
- [ ] Create client.
- [ ] Edit client.
- [ ] Archive client.

## Sites

- [ ] List sites.
- [ ] Filter by client if supported.
- [ ] Select site.
- [ ] View linked jobs.
- [ ] Create site linked to client.
- [ ] Edit site.
- [ ] Archive site.
- [ ] Create job for site.

## Jobs

- [ ] List jobs.
- [ ] Filter status.
- [ ] Select job.
- [ ] Create job linked to client/site.
- [ ] Edit job.
- [ ] Update status.
- [ ] Archive job.

## Negative Checks

- [ ] Missing `NEXT_PUBLIC_DEMO_ORG_ID` shows the setup message.
- [ ] API down shows a clean error.
- [ ] No fake Drive/report/photo buttons are visible yet.
- [ ] Raw UUIDs do not dominate the normal UI where names can be shown.
