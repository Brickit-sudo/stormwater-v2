# V2 Drive/File Foundation Spec

## Purpose

This spec supports the Drive/File foundation in Stormwater V2, including the
manual Google Drive Picker layer added after the first metadata-only pass.
It defines the product behavior, field-level rules, UX copy, API expectations,
and forbidden buttons for the Drive/File panel that Codex is about to scaffold
on top of the existing CRM (`clients`, `sites`, `jobs`) and the existing
`evidence_files` model.

**This phase is metadata-only.** It does **not** implement:

- Server-side Google Drive OAuth/token storage
- Google Drive folder creation
- Drive folder/file sync
- Binary file uploads (no multipart, no progress bars, no storage writes)
- Folder scanning / listing actual Drive contents
- File content download
- OCR or AI file analysis
- Report generation (DOCX/PDF)
- Photosheet generation
- Photo management beyond a generic file link
- V1 → V2 migration of artifacts

It complements:

- `docs/architecture/v2-crm-ux-seed-spec.md` — CRM UX, labels, and seeds.
- `docs/architecture/v2-crm-manual-qa.md` — manual QA for the CRM pages.
- `docs/architecture/v1-to-v2-migration-blueprint.md` — future migration plan.

If anything here conflicts with `v2-crm-ux-seed-spec.md`, the CRM spec wins
for labels, status vocabulary, and CRM page behavior.

## Product Principle

- **CRM records are the source of truth.** Clients, Sites, and Jobs own
  everything. Files do not exist in V2 without a parent CRM record.
- **Files belong to selected Clients, Sites, or Jobs.** The Drive/File panel
  is always scoped to the currently selected entity. There is no global
  "All Files" view in this phase.
- **Drive folders and file links are contextual panels, not standalone
  clutter.** The panel is a side-car on each CRM detail view — not a top-level
  page.
- **No fake buttons.** If a feature is not implemented yet, no button for it
  appears. Setup/empty/error copy explains what is missing.

## Current Phase Scope

### What IS included

- Show `drive_folder_url` on a selected Client / Site / Job if one is set.
- Render an **Open Drive Folder** link only when a real URL is present.
- List linked file metadata rows (`evidence_files`) for the selected
  Client / Site / Job.
- **Add File Link** — a small form that creates a metadata-only
  `evidence_files` row.
- **Select from Google Drive** when browser Picker credentials are configured.
  This opens Google Picker only after a user click and saves selected file
  metadata only.
- (Optional, if time allows) **Edit File Link** — edit `file_name`, `caption`,
  `public_url`, `source`.
- (Optional, if time allows) **Archive File Link** — soft delete via
  `archived_at`.
- Seed a handful of file links so panels are not empty.
- Smoke test the file metadata API end-to-end.

### What is NOT included

- Uploading actual files (no multipart, no streaming, no progress UI).
- Syncing a Drive folder (no listing, no diffing).
- Scanning a folder for new files.
- Creating a Drive folder from V2.
- Backend Google Drive API calls, folder scans, or content downloads.
- Automatic Google Drive sync.
- Report or photosheet generation.
- A dedicated photo manager / gallery.
- V1 migration of `crm_report_artifacts` or `projects/{uuid}/photos`.
- Cross-entity bulk operations.
- File content preview / thumbnail rendering.

## Entity-Level File Behavior

The Drive/File panel appears on the right-side detail panel of the currently
selected record on the Clients, Sites, and Jobs pages. It is always scoped to
exactly one entity.

### Client Files

**When the panel appears:** A client is selected on the Clients page.

**What the panel shows:**

- `drive_folder_url` for the client, if set, rendered as
  **Open Drive Folder**.
- A list of `evidence_files` rows where `client_id = <selected client>` and
  `site_id IS NULL` and `job_id IS NULL` (i.e. **client-level** files only).
- An **Add File Link** action.

**What client-level files mean:** Documents and links that belong to the
client as a whole, not to any one site or job.

**Examples:**

- Master service agreement / contract
- Top-level Google Drive folder link for the client
- Certificate of insurance / W-9 / compliance documents
- Portfolio-level account notes (PDF)
- Vendor-onboarding paperwork

### Site Files

**When the panel appears:** A site is selected on the Sites page.

**What the panel shows:**

- `drive_folder_url` for the site, if set, rendered as **Open Drive Folder**.
- A list of `evidence_files` rows where `site_id = <selected site>` and
  `job_id IS NULL` (i.e. **site-level** files, not job-level).
- An **Add File Link** action.

**What site-level files mean:** Documents and links that describe the site
itself, independent of any one job.

**Examples:**

- Site plan PDF
- Stormwater permit / MS4 permit
- Inspection requirements / regulator notice
- Site-specific Drive folder
- Site map / aerial / drainage map
- Long-form site narrative / O&M manual

### Job Files

**When the panel appears:** A job is selected on the Jobs page.

**What the panel shows:**

- `drive_folder_url` for the job, if set, rendered as **Open Drive Folder**.
  If the job has none, fall back to the parent site's `drive_folder_url` and
  label it clearly (`Open Site Drive Folder`).
- A list of `evidence_files` rows where `job_id = <selected job>`.
- An **Add File Link** action.

**What job-level files mean:** Artifacts produced by or attached to a
specific unit of work.

**Examples:**

- Field notes / inspection notes PDF
- Maintenance verification photos (linked, not uploaded yet)
- Quote PDF (later)
- Invoice PDF (later)
- Generated inspection report DOCX/PDF (later, populated by report export)
- Generated photosheet DOCX (later)

## Evidence File Field Definitions

The `evidence_files` table already exists. This is the field-by-field UI
contract for the Drive/File panel and the Add File Link form.

| Field | UI Label | User-facing? | Required? | Notes | Migration Note |
|---|---|---|---|---|---|
| `id` | — | No (hidden) | auto | UUID PK | new V2 ID |
| `organization_id` | — | No (hidden) | auto | scoping; never shown | inherited from CRM record |
| `client_id` | — | No (hidden) | conditional | set when panel is Client-scoped or derived from parent | resolved from V1 parentage |
| `site_id` | — | No (hidden) | conditional | set when panel is Site-scoped or job's parent | resolved from V1 parentage |
| `job_id` | — | No (hidden) | conditional | set when panel is Job-scoped | resolved from V1 `crm_jobs` ref |
| `observation_id` | — | No (hidden) | No | future, leave null this phase | populated later when observations exist |
| `system_id` | — | No (hidden) | No | future, leave null this phase | populated later when BMP systems are wired in |
| `source` | Source | Yes (badge) | Yes (defaulted) | enum-like string; defaults to `drive_link` | from `crm_report_artifacts.kind` / heuristics |
| `file_name` | File name | Yes | **Yes** | required for any metadata-only link | from V1 artifact filename |
| `mime_type` | Type | Yes (optional show) | No | only render if useful (e.g. `application/pdf`) | from V1 artifact mime |
| `size_bytes` | Size | Yes (optional show) | No | only render if populated and > 0 | from V1 artifact size |
| `drive_file_id` | — | No in this phase | No | hidden unless dev/advanced; may be parsed from URL later | from V1 Drive file id |
| `drive_folder_id` | — | No (hidden / internal) | No | parsed from `drive_folder_url` on CRM records | from V1 parsed Drive folder id |
| `storage_bucket` | — | No (hidden) | No | reserved for future Supabase Storage / S3 | unused now |
| `storage_path` | — | No (hidden) | No | reserved for future binary storage | unused now |
| `public_url` | File URL | Yes | recommended | the user-pasted link (Drive URL, public URL, etc.) | from V1 `gdrive_url` for artifacts |
| `sort_order` | — | No (hidden) | auto | integer, defaults to 0; used for display ordering | preserved from V1 ordering if any |
| `caption` | Caption / note | Yes | No | short label shown under file name | from V1 photo caption later |
| `legacy_source` | — | No (hidden) | No | internal; shown read-only on edit only if present | `v1_monday` / `v1_report_artifact` |
| `legacy_id` | — | No (hidden) | No | internal; shown read-only on edit only if present | V1 artifact id |
| `archived_at` | — | No (hidden) | auto | set when Archive is used | unused on import |

**General rules for the UI:**

- `organization_id` is never shown.
- Raw UUIDs are never shown to users.
- `drive_file_id` is internal in this phase. Do not expose a "Drive File ID"
  input. Users paste a URL; URL parsing into `drive_file_id` is deferred.
- `drive_folder_id` is internal everywhere. Users see only `drive_folder_url`.
- `file_name` is required and is the primary display label.
- `source` defaults to `drive_link` and is shown as a small badge.

## Source Vocabulary

`source` is a free-form `String(64)` on the model. For this phase we treat it
as an enum-like vocabulary so the UI can render meaningful badges.

| Source | Meaning | User choose it now? | Notes |
|---|---|---|---|
| `drive_link` | A Google Drive (or generic) URL the user pasted in. | **Yes — default.** | The normal value for this phase. Renders as a "Drive link" badge. |
| `google_drive` | A file selected manually through Google Drive Picker. | No form dropdown; system-set by Picker. | Stores Picker metadata only: file name, MIME type, Drive file id, and URL when available. |
| `upload_placeholder` | Reserved for a binary file we have not actually uploaded yet (metadata only). | No — hidden in the dropdown for now. | Useful later when we introduce a "pending upload" UX. Keep available in the enum but do not surface it. |
| `report_export` | A generated DOCX/PDF report artifact produced by the report builder. | No — system-generated only. | Will be set automatically when report generation lands. |
| `photo` | A photo attached to a job/observation/system. | No — system-generated only. | Will be set automatically when the photo flow lands. |
| `other` | Catch-all for anything that doesn't fit the above. | Yes, as a fallback. | Use sparingly; prompt the user to pick a more specific source when possible. |

**Be conservative.** In this phase, the dropdown the user sees should
effectively be `drive_link` (default) plus `other`. Everything else is either
system-set or deferred.

## Drive Folder URL Behavior

`drive_folder_url` is already a column on `clients`, `sites`, and `jobs`.
This phase does not create or sync Drive folders. It only renders the URL
when one is set on the CRM record.

**Rules:**

- `drive_folder_url` belongs on the **CRM record** (Client / Site / Job),
  not on `evidence_files`. Do not duplicate it onto file rows.
- If `drive_folder_url` is present on the selected record, render an
  **Open Drive Folder** button that opens the URL in a new tab.
- If `drive_folder_url` is absent, render a short empty-state line — no
  button.
- No **Create Drive Folder** button.
- No **Sync** button.
- No **Scan Folder** button.
- No attempt to fetch folder contents.

**Good UI copy:**

- Button label: `Open Drive Folder`
- Empty state (no URL set): `No Drive folder linked yet.`
- Setup note (shown once on the panel, can be subtle / muted):
  `Drive integration is not connected yet. You can store a folder URL for
  now.`

The "Drive folder URL" field itself is edited from the CRM record's
edit form, not from the Drive/File panel. The Drive/File panel only
reads it.

## Add File Link UX

A small inline form (or modal) launched from an **Add file link** button at
the top of the Drive/File panel.

**Form fields:**

| Field | Required | Notes |
|---|---|---|
| File name | **Yes** | Free text, max 255 chars. Becomes `file_name`. |
| File URL | Recommended | Free text. Stored as `public_url`. Used for the "Open" link. |
| Source | Defaulted | Dropdown: `Drive link` (default) and `Other`. Stored as `source`. |
| MIME type | No | Optional free text (`application/pdf`, `image/jpeg`). Stored as `mime_type`. |
| Caption / note | No | Short free text. Stored as `caption`. |

**Validation:**

- `file_name` is required and trimmed.
- At least one of `public_url` *or* `drive_file_id` should be present to
  later form an openable link. In this phase the form only collects
  `public_url`; if it is blank, save still succeeds but the file row will
  not render an "Open" action.
- `source` defaults to `drive_link`. UI sends `drive_link` if the user
  leaves the dropdown alone.
- **No binary file upload field. No multipart form. No progress indicator.**
- Validation errors render inline below the offending field with the
  CRM-style red copy from `v2-crm-ux-seed-spec.md`.

**Save behavior:**

- Backend creates an `evidence_files` row scoped to the selected entity
  (`client_id`, `site_id`, or `job_id` set accordingly; the other two left
  null for this phase, plus `organization_id` inherited from the parent).
- Frontend refreshes the panel and the new row appears at the top of the
  list (most-recent-first sort within `sort_order` ties).
- Success copy: `Saved.` (same as CRM spec).
- Failure copy: `Couldn't save your changes. Try again, or check the
  highlighted fields.`

## Google Drive Picker UX

Google Picker is manual-selection only. It does not crawl Drive folders, scan
all files, download file contents, upload files, OCR documents, analyze files
with AI, or generate reports.

Configuration is optional. If the browser-safe Picker env vars are missing,
the UI shows a disabled **Configure Google Drive Picker** state and the
existing **Add File Link** form remains usable.

When configured:

- Google scripts are injected only after the user clicks **Select from Google
  Drive**.
- The browser requests the narrow `drive.file` style scope
  (`https://www.googleapis.com/auth/drive.file`).
- The Picker callback returns file metadata to the frontend.
- The frontend saves metadata through `POST /v1/files` with
  `source = "google_drive"`.
- The selected file must still be linked to exactly one Client, Site, or Job.

No private Google secret is exposed to the frontend. The browser API key should
be restricted in Google Cloud.

## Edit File Link UX (optional in this pass)

If implemented:

- Editable fields: `file_name`, `public_url`, `source`, `mime_type`,
  `caption`.
- All hidden/internal fields stay hidden (no `drive_file_id`,
  `drive_folder_id`, `storage_*`, `legacy_*` exposure).
- Same validation rules as Add File Link.
- Cancel discards changes; Save persists and refreshes the panel.

## Archive File Link UX (optional in this pass)

If implemented:

- The action is labeled **Archive**, not **Delete**.
- Confirmation copy: `Archive this file link? It will be hidden from the
  default view. You can restore it later.`
- Sets `archived_at` to now. Does not touch the actual file in Google Drive
  (no API call there at all).
- Archived rows are excluded from the default panel list. They are
  restorable later but a Restore UI is not required in this pass.
- Never call this action **Delete file**, never use red-button styling,
  never imply that the Drive file is being removed.

## Display Rules

The Drive/File panel renders a simple list (no thumbnails this phase). Per
file row:

- **File name** (primary line, from `file_name`)
- **Source badge** (small chip from `source`)
- **Caption** (secondary line, from `caption`, only if set)
- **Open link** (right-aligned action) — rendered only if a URL can be
  formed:
  - Prefer `public_url`.
  - Otherwise, if `drive_file_id` is present, future logic may construct
    `https://drive.google.com/file/d/<id>/view`. For this phase it is
    acceptable to require `public_url` and skip the link when missing.
- **MIME type** — only render if `mime_type` is populated *and* meaningful
  (e.g. `application/pdf`, not blank or `application/octet-stream`).
- **Size** — only render if `size_bytes` is populated and > 0; otherwise
  omit.

**Sort:**

- Primary sort: `sort_order` ascending.
- Tiebreaker: `created_at` descending (newest first).

**Empty states:**

- Client panel: `No files linked to this client yet.`
- Site panel: `No files linked to this site yet.`
- Job panel: `No files linked to this job yet.`

**Loading:** skeleton list rows (3), matching the CRM page style.

**Error:** `Couldn't load files. Try again.`

## Forbidden Buttons / Anti-Clutter Rules

In this phase, the following buttons **must not appear** anywhere in the
Drive/File panel or in any CRM detail view:

- Upload File
- Sync Drive
- Scan Drive Folder
- Create Drive Folder
- Generate Report
- Generate Photosheet
- Import Photos
- Auto-caption
- AI Analyze
- Send to Client
- Create Invoice
- Create Quote
- Convert to PDF
- Share with…
- Email file

**Why:** These are real future features. Showing disabled or placeholder
buttons trains users that the app is broken. Until the underlying flow
exists, the button does not exist either. If a feature is on the roadmap
but not built, it lives in a docs file, not in the UI.

## API Expectations

The backend should expose JSON endpoints similar in shape to the existing
CRM endpoints. All requests must include `organization_id` (header, query
param, or session — match the existing CRM convention).

### Core endpoints

| Method | Path | Purpose | Notes |
|---|---|---|---|
| `GET` | `/v1/files` | List files for the current org with filters. | Filters: `client_id`, `site_id`, `job_id`, `source`, `include_archived` (default `false`). Server-side pagination (`limit`, `offset`). |
| `POST` | `/v1/files` | Create a file metadata row. | Body: `file_name` (required), `public_url`, `source`, `mime_type`, `caption`, and exactly one of `client_id` / `site_id` / `job_id`. **No multipart.** |
| `PATCH` | `/v1/files/{file_id}` | Edit metadata fields on an existing row. | Body: any of `file_name`, `public_url`, `source`, `mime_type`, `caption`. Parent scope (`client_id` / `site_id` / `job_id`) is immutable in this phase. |
| `DELETE` | `/v1/files/{file_id}` | Archive (soft delete) the row. | Sets `archived_at`. Does not hard-delete. No Drive call. |

### Optional convenience endpoints

If they simplify the frontend without ballooning scope:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/v1/clients/{client_id}/files` | Files where `client_id = X` and `site_id IS NULL` and `job_id IS NULL`. |
| `GET` | `/v1/sites/{site_id}/files` | Files where `site_id = X` and `job_id IS NULL`. |
| `GET` | `/v1/jobs/{job_id}/files` | Files where `job_id = X`. |

### Expected behavior

- All endpoints require `organization_id` and return 4xx (not 5xx) on
  missing/invalid scoping.
- All endpoints exclude `archived_at IS NOT NULL` rows by default.
- All endpoints return JSON with the fields named in the **Evidence File
  Field Definitions** table. Hidden fields (`organization_id`,
  `drive_folder_id`, `storage_*`) may be returned but should not be relied
  upon by the UI.
- **No binary request/response bodies.** The Content-Type for POST/PATCH is
  `application/json` only.
- Errors follow the CRM error shape so the frontend can reuse error UI.

## Frontend Expectations

A single reusable React component (TypeScript), e.g. `DriveFilePanel`, lives
in `apps/web` and is mounted inside each CRM detail panel (Client / Site /
Job).

**Props:**

| Prop | Type | Required | Notes |
|---|---|---|---|
| `organizationId` | `UUID` | Yes | Same value as `NEXT_PUBLIC_DEMO_ORG_ID` flow used by CRM pages. |
| `clientId` | `UUID \| undefined` | Conditional | Set when used on the Clients page. |
| `siteId` | `UUID \| undefined` | Conditional | Set when used on the Sites page. |
| `jobId` | `UUID \| undefined` | Conditional | Set when used on the Jobs page. |
| `driveFolderUrl` | `string \| null` | Optional | Passed in by parent so the panel can render Open Drive Folder. |
| `selectedRecordLabel` | `string` | Optional | Used in empty-state and confirm copy (e.g. "this client"). |

**Behavior:**

- The component loads files for the selected entity **only**. It never
  fetches the org-wide file list.
- Exactly one of `clientId` / `siteId` / `jobId` must be set; if none are
  set, the panel renders nothing (no error).
- Setup/empty/error states use the copy in this spec.
- After Add or Archive, refetch the panel's file list. No optimistic UI
  this phase.
- The panel never renders any of the **Forbidden Buttons**.
- The panel never displays raw UUIDs (no `client_id` strings, no
  `file_id` strings in the UI).

## Seed Data Expectations

`apps/api/scripts/seed_dev.py` already creates the Sterling Stormwater Demo
org, three clients, multiple sites, and multiple jobs. Extend the seed with
a small set of file links so the panel is exercised in local dev.

**Required coverage:**

- At least **1 client-level** file.
- At least **1 site-level** file.
- At least **2 job-level** files (so the job panel shows more than one
  row).
- At least one row whose parent has `drive_folder_url` populated (so the
  Open Drive Folder button renders).
- At least one row whose parent has no `drive_folder_url` (so the empty
  state for the Drive folder renders).
- At least one row with a populated `caption`.
- At least one row with a populated `mime_type`.

**Seed file link examples:**

| Parent Type | Parent Example | File Name | Source | URL present? | Purpose |
|---|---|---|---|---|---|
| Client | Pine Tree Property Management | Master Service Agreement (2026).pdf | `drive_link` | Yes | Contract; exercises client-level panel + Drive link. |
| Client | Kennebec Millworks | Certificate of Insurance.pdf | `drive_link` | Yes | Compliance doc on inactive client. |
| Site | Bayside Retail Plaza | Site Plan v3.pdf | `drive_link` | Yes | Site plan; exercises site-level panel + Drive link. |
| Site | Augusta Logistics Yard | MS4 Permit Notice.pdf | `other` | Yes | Regulator notice; exercises non-default `source`. |
| Job | (any inspection job at Bayside Retail Plaza) | Inspection Photo Set Placeholder | `drive_link` | Yes | Stand-in for future photo flow; caption populated. |
| Job | (any maintenance job) | Maintenance Verification Notes.pdf | `drive_link` | Yes | Field notes; populated `mime_type` (`application/pdf`). |
| Job | (any draft job) | Pending Field Notes | `other` | No (URL blank) | Exercises the "no Open link" rendering path. |

Names above are examples — the exact parent rows should be pulled by
`legacy_id` from the existing seed so the file rows attach deterministically
on every `--reset-seed`.

**Seed properties:**

- `legacy_source = "seed_dev"`, `legacy_id` follows the existing seed
  convention (e.g. `evidence_file:bayside-site-plan-v3`).
- `organization_id = DEMO_ORGANIZATION_ID`.
- `sort_order = 0` for all seeds unless explicitly testing sort.
- `archived_at = null`.
- Seed must be idempotent under `--reset-seed`.

## Manual QA Checklist

This is the smoke test the Codex pass should pass end-to-end. It assumes a
fresh checkout.

### Setup

- [ ] Run Alembic migrations against the local Postgres instance — schema
      has not changed, but confirm `evidence_files` table is present.
- [ ] Run `apps/api/scripts/seed_dev.py --reset-seed` and confirm seeded
      file links appear in the DB.
- [ ] Run `apps/api/scripts/smoke_crm_api.py` and confirm CRM endpoints
      respond.
- [ ] Smoke the new file metadata endpoints (`GET/POST/PATCH/DELETE
      /v1/files`) against the seeded data.
- [ ] Start the API (`uvicorn` per existing docs).
- [ ] Start the web app (`pnpm dev` or equivalent).

### Client panel

- [ ] Open the Clients page and select a seeded client with a
      `drive_folder_url`. **Open Drive Folder** button is visible.
- [ ] Select a seeded client *without* a `drive_folder_url`. Empty-state
      copy `No Drive folder linked yet.` is shown; no button.
- [ ] Seeded client-level file row(s) are listed.
- [ ] Add a new file link via the form. Validation: blank `file_name`
      shows an inline error.
- [ ] On successful save the new row appears in the panel.
- [ ] (If implemented) Archive a file link. The row disappears from the
      default list.

### Site panel

- [ ] Open the Sites page and select a seeded site with a
      `drive_folder_url`. **Open Drive Folder** button is visible.
- [ ] Site-level seeded file rows are listed, with `caption` shown where
      populated and `mime_type` shown where populated.
- [ ] Add a site-level file link. New row appears.
- [ ] (If implemented) Archive a site-level link.

### Job panel

- [ ] Open the Jobs page and select a seeded job.
- [ ] Only that job's files are listed — sibling jobs' files do not leak
      into the panel.
- [ ] One seeded row has a blank URL; the "Open" action is not rendered
      for it, and no broken link is shown.
- [ ] Add a job-level file link. New row appears.

### Negative checks

- [ ] No **Upload File** button anywhere.
- [ ] No **Sync Drive** button anywhere.
- [ ] No **Scan Folder** / **Create Drive Folder** button anywhere.
- [ ] No **Generate Report** / **Generate Photosheet** button anywhere.
- [ ] No raw `organization_id` / UUIDs shown in the UI.
- [ ] No multipart upload field in the Add File Link form.
- [ ] No fake progress bar, spinner-after-save, or "Uploading…" copy.
- [ ] API errors render as the configured error copy, not a stack trace.
- [ ] Missing `NEXT_PUBLIC_DEMO_ORG_ID` falls through the CRM setup
      message (the panel does not render its own error noise).

## Migration Notes

This phase intentionally builds the shell that future V1 migration can
target. Concretely:

- **V1 `gdrive_url` → V2 `drive_folder_url`.** V1's free-text Drive URLs
  on contacts/sites/jobs were already mapped onto `clients.drive_folder_url`,
  `sites.drive_folder_url`, and `jobs.drive_folder_url` in the migration
  blueprint. This phase honors that contract by reading `drive_folder_url`
  on each CRM record and not introducing a competing field on
  `evidence_files`.
- **V1 `crm_report_artifacts` → V2 `evidence_files`.** Each V1 artifact
  becomes one `evidence_files` row attached to its job. Mapping:
  - `file_name` ← V1 artifact filename
  - `mime_type` ← V1 artifact mime
  - `size_bytes` ← V1 artifact size
  - `drive_file_id` ← V1 artifact drive file id (if available)
  - `public_url` ← V1 `gdrive_url` for the artifact
  - `source` ← `report_export` for generated DOCX/PDF, `other` for the rest
  - `legacy_source` ← `v1_report_artifact`
  - `legacy_id` ← V1 artifact id
- **V1 `projects/{uuid}/photos/*` → V2 `evidence_files`.** Each photo
  becomes one row with `source = "photo"`. Caption metadata may need a
  schema extension later (the current `caption` column is the holding
  place).
- **Report linkage.** When the `reports` table is wired in (M5/M6), it
  references `evidence_files.id` for `generated_docx_file_id` and
  `generated_pdf_file_id`. This spec does not implement that link; it only
  promises that the file metadata shape is compatible.
- **URL parsing is deferred.** This phase stores `public_url` as the user
  pasted it. Parsing it into `drive_file_id` / `drive_folder_id` is a
  separate concern handled at migration time or when OAuth lands.

In other words: this phase creates only the **shell and the file-metadata
pattern**. Nothing in this phase has to be undone to support migration.

## Open Decisions

These are deliberately not resolved here. They should be resolved before
the next phase that actually touches Google Drive.

- **Google Drive OAuth strategy.** Per-user vs. per-org service account vs.
  shared drive credentials. Affects token storage, refresh, and revocation.
- **Where Drive folder creation lives.** API-side (backend creates and
  records `drive_folder_id`) vs. frontend (user pastes a URL we parse).
- **Where binary files live long-term.** Google Drive only, Supabase
  Storage only, or a hybrid (Drive for shared customer artifacts, Supabase
  for internal-only blobs).
- **Photos: separate table or `evidence_files`.** The current model
  supports photos via `evidence_files` with `source = "photo"`. A dedicated
  `photos` table may be warranted once caption metadata, ordering, and
  per-system attribution come into play.
- **Photo caption schema.** V1 has structured photo captions (system / ID /
  view / note). The current single `caption` column collapses that.
- **Report artifact storage path.** Whether DOCX/PDF live in Drive
  (folder-per-job convention?), in Supabase Storage, or both.
- **Folder naming conventions in Drive.** Whether V2 should create
  client/site/job folders following a convention.
- **Whether Drive IDs are parsed from URLs or entered separately.** This
  spec keeps it URL-only for now; a future task can add an explicit
  `drive_file_id` field once OAuth provides a way to validate it.

## Recommended Next Codex Prompt

Once the Drive/File panel foundation in this spec is implemented and the
manual QA checklist passes, the **strongest next move is the V1 migration
script Phase M1 dry-run** — *not* OAuth, *not* report extraction.

Reasoning:

- M1 (clients + contacts + sites + jobs) is the largest remaining piece of
  unmigrated value and is already fully specced in
  `v1-to-v2-migration-blueprint.md`.
- The Drive/File panel becomes much more useful — and far easier to
  validate — once real customer/site/job records and their V1 Drive URLs
  are present, instead of only the seeded demo data.
- OAuth and report extraction both depend on the migrated `legacy_id → V2
  UUID` map for jobs and sites. Doing migration first unblocks them
  cleanly.
- A dry-run (read V1, plan writes, write to a transcript) is low risk and
  surfaces the messy real-world data (orphan jobs, malformed Drive URLs,
  duplicate clients) early.

Suggested prompt:

> Implement Phase M1 of the V1 → V2 migration as a **dry run** in
> `stormwater-v2/scripts/migrate_v1.py`. Follow
> `docs/architecture/v1-to-v2-migration-blueprint.md` exactly: read V1
> `crm_contacts`, `crm_sites`, `crm_jobs`; resolve clients vs. contacts;
> map status vocabulary; preserve `legacy_source` + `legacy_id`; emit a
> validation report (planned inserts, conflicts, orphans) but do **not**
> write to the V2 database yet. Honor `v2-crm-ux-seed-spec.md` and
> `v2-drive-file-foundation-spec.md` for field shapes; do not touch
> reports, photos, evidence_files, OAuth, or Drive APIs in this pass.
