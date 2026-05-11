# V2 CRM Manual QA Checklist

Use this checklist after schema changes, seed changes, or CRM frontend work.

## Setup

- [ ] Create the local Postgres database if needed.
- [ ] From `apps\api`, run Alembic upgrade:
  ```powershell
  .\.venv\Scripts\python -m alembic upgrade head
  ```
- [ ] From `apps\api`, run the deterministic seed:
  ```powershell
  .\.venv\Scripts\python scripts\seed_dev.py --reset-seed
  ```
- [ ] Copy the printed `NEXT_PUBLIC_DEMO_ORG_ID` value into `apps\web\.env.local`.
- [ ] Start the API:
  ```powershell
  .\.venv\Scripts\python -m uvicorn app.main:app --reload
  ```
- [ ] Start the web app:
  ```powershell
  npm run dev
  ```
- [ ] Open `http://localhost:3000/crm/clients`.

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
