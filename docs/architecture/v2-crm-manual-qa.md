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

## Drive/File Panel

This panel is metadata-only. There is no binary upload, no Drive OAuth, no folder creation, no folder scanning, no sync. The Archive action soft-deletes the metadata row and **never** touches the actual file in Google Drive.

### Client panel

- [ ] Select a seeded client with a `drive_folder_url` (e.g. Pine Tree Property Management). The **Open Drive Folder** link is visible and opens in a new tab.
- [ ] Select a seeded client without a `drive_folder_url` (e.g. Northeast Retail Portfolio). The empty state `No Drive folder linked yet.` is shown; no Open button is rendered.
- [ ] Seeded client-level file row(s) are listed (e.g. `Master Service Agreement (2026).pdf` for Pine Tree).
- [ ] **Add File Link**: blank `File name` shows an inline validation error.
- [ ] On successful save the new row appears in the panel.
- [ ] **Archive** removes the row from the default list and surfaces a confirmation dialog that mentions the Drive file is **not** deleted.

### Site panel

- [ ] Select a seeded site with a `drive_folder_url` (e.g. Bayside Retail Plaza). The **Open Drive Folder** link is visible.
- [ ] Site-level seeded file rows are listed (e.g. `Site Plan v3.pdf`, `MS4 Permit Notice.pdf`).
- [ ] Caption is shown where populated; MIME type is shown where populated (e.g. `application/pdf`).
- [ ] Add a site-level file link. New row appears.
- [ ] Archive a site-level link.

### Job panel

- [ ] Select a seeded job. Only that job's files are listed - sibling jobs' files do not leak into the panel.
- [ ] A seeded job (`Industrial Yard SWPPP Support`) has a file row with a blank URL (`Pending Field Notes`); the **Open** action is not rendered for that row.
- [ ] If a job has no `drive_folder_url` but its parent site does, the panel falls back to the parent site's Drive folder URL.
- [ ] Add a job-level file link. New row appears.
- [ ] Archive a job-level link.

## Negative Checks

- [ ] Missing `NEXT_PUBLIC_DEMO_ORG_ID` shows the setup message.
- [ ] API down shows a clean error.
- [ ] No **Upload File** button anywhere.
- [ ] No **Sync Drive** button anywhere.
- [ ] No **Scan Folder** / **Create Drive Folder** button anywhere.
- [ ] No **Generate Report** / **Generate Photosheet** button anywhere.
- [ ] No raw `organization_id` / file UUIDs shown in the UI.
- [ ] No multipart upload field in the Add File Link form.
- [ ] No fake progress bar, spinner-after-save, or "Uploading..." copy.
- [ ] Raw UUIDs do not dominate the normal UI where names can be shown.
