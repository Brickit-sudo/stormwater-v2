# V1 to V2 Migration Blueprint

## Purpose

This document is the implementation contract for the future V1 → V2 migration
script. It does **not** implement the migration. It locks in the field
mappings, status vocabulary, ID strategy, conflict handling, validation
output, and phasing decisions that the script must follow so that:

- Codex (or a follow-up implementation pass) can build `scripts/migrate_v1.py`
  without re-deriving product decisions.
- The migration is deterministic, idempotent, and re-runnable.
- V1 Monday-style records (SSC / SSW / SSO / SWL) and V1 report/session
  snapshots land in V2 without losing CRM context, Drive linkage, or
  traceability back to the original V1 ID.

It complements:

- `docs/architecture/v1-extraction-inventory.md` — what V1 *code* is safe to
  extract.
- `docs/architecture/v2-crm-ux-seed-spec.md` — V2 CRM UX and field labels.
- `docs/architecture/v2-crm-manual-qa.md` — manual QA for the V2 CRM pages.

If anything in this blueprint conflicts with `v2-crm-ux-seed-spec.md`, the
UX/seed spec wins for UI labels and status vocabulary.

## Current Migration Strategy

The migration runs in this order, and CRM must complete before reports /
photos are touched:

1. Create or find the Sterling organization (`organizations`).
2. Import clients (`clients`).
3. Import contacts (`contacts`).
4. Import sites (`sites`).
5. Import jobs (`jobs`).
6. Import BMP systems (`bmp_systems`) parsed from `crm_sites.systems`.
7. Import observations (`observations`) **only if** source data exists.
8. Import evidence / file / photo metadata (`evidence_files`) — later phase.
9. Import reports / session snapshots (`reports`) — later phase.
10. Validate row counts, foreign keys, and `legacy_id` uniqueness.

**Rule:** CRM migration comes before report / photo migration. Reports and
photos hang off `jobs` (and through them, `sites` and `clients`). Without
a stable `legacy_id → V2 UUID` map for jobs and sites, report / photo
migration cannot run.

## Source Systems

V1 data sources the migration must read. All are read-only inputs.

| Source | What it contains | Migration phase | Risk |
|---|---|---|---|
| `crm_contacts` | Monday Contacts board (`SSC-####`). Mixes people and companies under one row (`account` = company, `first_name/last_name` = person). | M1 (clients + contacts) | High — must be split into V2 `clients` and `contacts`. |
| `crm_sites` | Monday Site Information (`SSW-####`). Site facts, address, Drive URL, `systems` CSV, contract/budget/service month, status, notes. | M1 (sites) + M4 (bmp_systems) | Medium — needs address split, status mapping, BMP CSV parse. |
| `crm_jobs` | Monday Orders board (`SSO-####`). Job/service rows, status, owner, quoted/actual, schedule, completion, blocked reason, `report_id`. | M1 (jobs) | High — orphan jobs (no `site_id`/`client_id`), free-text statuses. |
| `crm_leads` | Monday Leads board (`SWL-####`). Prospects with no firm site/job. | Deferred (see Leads section) | Medium — no V2 home yet. |
| `crm_communications` | Free-form notes / calls / emails keyed on (`entity_type`, `entity_id`). | Optional (M2 → `activity_log`) | Low — informational only. |
| `crm_report_artifacts` | V1 report DOCX/PDF metadata (path, kind, drive_file_id). | M5/M6 (evidence_files + reports linkage) | Medium — filesystem paths may not survive. |
| `crm_followups` | V1 follow-up tasks linked to artifacts/jobs. | Deferred — no V2 equivalent yet. | Medium — important operational data. |
| V1 SQLite (`db.py`) report tables (clients / sites / reports) if present | Earlier non-CRM clients/sites used by the report builder. | M1 (merge candidates) | Medium — likely duplicates of `crm_contacts.account` / `crm_sites`. |
| `projects/{uuid}/session.json` | Report builder session snapshots (meta + systems + write-ups + photos). | M5 (reports) | High — UUIDs are project-local, not CRM-stable. |
| `projects/{uuid}/photos/*` | Photo files referenced by `session.json`. | M6 (evidence_files) | Medium — disk path coupling, EXIF metadata. |
| `gdrive_url` free-text fields on sites / jobs / leads / artifacts | Drive folder or file URLs, sometimes blank, sometimes malformed. | M3 (Drive parser) | Medium — folder vs. file detection. |

## Target V2 Tables

V2 tables the migration must write to. All require `organization_id`.

| Target table | Purpose | Required relationships | Migration notes |
|---|---|---|---|
| `organizations` | Tenant root. | none | Exactly one created or looked up; all rows below carry its `id`. |
| `clients` | Customer / property owner. | `organization_id` | Source = `crm_contacts.account` (deduped) plus any extra report-side clients. |
| `contacts` | Person attached to a client or site. | `organization_id`, optional `client_id`, optional `site_id` | Source = `crm_contacts` rows where `first_name`/`last_name`/`email` are populated. |
| `sites` | Physical property / facility. | `organization_id`, `client_id` (NOT NULL) | Source = `crm_sites` plus any report-side sites; must resolve client. |
| `jobs` | Unit of stormwater work at a site. | `organization_id`, `client_id` (NOT NULL), `site_id` (NOT NULL) | Source = `crm_jobs`; orphans handled by synthetic parents. |
| `bmp_systems` | BMP / stormwater system installed at a site. | `organization_id`, `site_id` (NOT NULL) | Source = parsed `crm_sites.systems` CSV. |
| `observations` | Finding/recommendation at a job. | `organization_id`, `job_id` (NOT NULL), optional `system_id` | No legacy fields on this model — flagged below. |
| `evidence_files` | Photos / DOCX / PDF / generic files. | `organization_id`, optional client/site/job/observation/system | Source = `crm_report_artifacts` + project photo folders. |
| `reports` | Snapshot + generated DOCX/PDF references. | `organization_id`, optional `job_id`, optional `site_id` | Source = `projects/{uuid}/session.json` + `crm_report_artifacts`. |
| `activity_log` | Free-form event log. | `organization_id` | Optional target for `crm_communications`. |

**Note:** `observations` has no `legacy_source` / `legacy_id` columns in the
current V2 model. If observation-level traceability is needed, the schema
must be extended before M4 lands. The migration should not silently invent
observation IDs.

## ID Strategy

- **V2 primary keys are UUIDs.** Never reuse V1 Monday-style IDs as
  primary keys.
- **V1 IDs are preserved** in `legacy_source` + `legacy_id` on every row
  that has those columns (clients, contacts, sites, jobs, bmp_systems,
  evidence_files, reports — *not* observations or activity_log).
- **`legacy_source`** is the constant string for V1: use `v1_monday` for
  CRM rows, `v1_session_json` for report-snapshot rows, `v1_report_db`
  for rows coming from V1 SQLite report tables. Pick one per row type
  and stay consistent across phases.
- **Idempotency key** for upsert is the `(organization_id, legacy_source,
  legacy_id)` tuple. The migration must upsert on this, never duplicate.
- **In-memory lookup maps** are built during the run:
  - `v1_client_id → v2_client_uuid` (keyed on `SSC-####`, plus normalized
    company name for clients that came from `crm_contacts.account`
    without an SSC).
  - `v1_site_id → v2_site_uuid` (`SSW-####`).
  - `v1_job_id → v2_job_uuid` (`SSO-####`).
  - `v1_lead_id → v2_client_uuid` (only if the leads decision lands on
    "import as prospect clients" — otherwise this map stays empty).
  - `v1_project_uuid → v2_report_uuid` (project session UUIDs).
  - `v1_artifact_id → v2_evidence_file_uuid`.
- **Missing IDs** must be handled deterministically. A site or client
  with no `SSC-####` / `SSW-####` gets a synthetic `legacy_id` of the
  form `synthetic:client:<normalized-name>` so that re-running the
  migration still upserts the same row.

### V1 ID type table

| V1 ID type | Example | V2 mapping | Notes |
|---|---|---|---|
| `SSC-####` | `SSC-0142` | `clients.legacy_id` (source `v1_monday`) | Only when `crm_contacts` row represents a company (`account` populated). |
| `SSC-####` (person row) | `SSC-0143` | `contacts.legacy_id` (source `v1_monday`) | When the row is a person, not a company. |
| `SSW-####` | `SSW-0088` | `sites.legacy_id` (source `v1_monday`) | One-to-one with `crm_sites.site_id`. |
| `SSO-####` | `SSO-1204` | `jobs.legacy_id` (source `v1_monday`) | One-to-one with `crm_jobs.job_id`. |
| `SWL-####` | `SWL-0033` | Deferred (see Leads). If imported, lands as `clients.legacy_id` with `legacy_source='v1_monday_lead'`. | Distinct source string so leads stay queryable separately from real clients. |
| UUIDv4 (project) | `b6e1c2…` | `reports.legacy_id` (source `v1_session_json`) | From `projects/{uuid}/` folder names. |
| UUIDv4 (artifact) | `a7d3…` | `evidence_files.legacy_id` (source `v1_monday`) | From `crm_report_artifacts.artifact_id`. |
| Synthetic | `synthetic:client:acme-inc` | Whichever target table needs a deterministic placeholder. | Used for orphan recovery and dedupe so re-runs are stable. |

## Organization Strategy

- Exactly **one** organization is created during initial migration:
  `Sterling Stormwater` (real name, not the demo seed name).
- Lookup precedence:
  1. CLI flag `--organization-name "Sterling Stormwater"` → match on
     `organizations.name`.
  2. If not found, create it. The created organization's `id` is a UUID5
     derived from a fixed namespace and the name, so the same name on a
     re-run resolves to the same `organization_id`.
- Every imported row receives that `organization_id`. No migration step
  proceeds without it.
- The seed-data organization (`Sterling Stormwater (Demo)` /
  `Sterling Stormwater Demo`) is **separate** and must never be the
  target of real-data migration. Migration must refuse to run if the
  resolved organization name contains "demo" (case-insensitive) unless
  `--allow-demo-org` is also passed.

## Field Mapping — Clients and Contacts

V1 `crm_contacts` mixes companies (in `account`) and people (in
`first_name` / `last_name`) in the same row. V2 separates `clients`
(companies) from `contacts` (people). The migration splits each
`crm_contacts` row into up to two V2 rows:

- A `clients` row keyed on `account` (if `account` is populated and not
  already imported under a normalized-name dedupe).
- A `contacts` row keyed on `(first_name, last_name, email)`, linked to
  that client.

| V1 source field | V2 table | V2 field | Transform | Required? | Risk | Notes |
|---|---|---|---|---|---|---|
| `crm_contacts.client_id` | `clients` | `legacy_id` | as-is | yes if `account` present | low | `legacy_source = 'v1_monday'`. |
| `crm_contacts.account` | `clients` | `name` | trim, collapse whitespace | yes (skip row if blank) | medium | Dedupe by normalized lower-case name. |
| `crm_contacts.active_status` | `clients` | `status` | map via Status Vocabulary | yes | medium | Unknown → `inactive`, log warning. |
| `crm_contacts.first_name + last_name` | `clients` | `primary_contact_name` | `"{first} {last}".strip()` | no | low | Only when not already set by a prior row for the same client. |
| `crm_contacts.email` | `clients` | `email` | lowercase, trim | no | low | Also written to `contacts.email`. |
| `crm_contacts.phone` | `clients` | `phone` | normalize digits, keep `+` and dashes | no | low | Light normalization only; no E.164 conversion. |
| `crm_contacts.state` | `clients` | `billing_address` | append as `"{existing}\n{state}"` if no address present | no | low | V1 has no full billing address — leave blank if no signal. |
| `crm_contacts.notes` | `clients` | `notes` | as-is | no | low | |
| `crm_contacts.client_id` | `contacts` | `legacy_id` | as-is | yes if person row | low | `legacy_source = 'v1_monday'`. Same legacy_id can appear on a `clients` row *and* a `contacts` row, distinguished by table. |
| `crm_contacts.first_name + last_name` | `contacts` | `name` | trim | yes (skip if both blank) | medium | If only a company row, no contact is created. |
| `crm_contacts.email` | `contacts` | `email` | lowercase, trim | no | low | |
| `crm_contacts.phone` | `contacts` | `phone` | as on client | no | low | |
| `crm_contacts.managed_by` | `contacts` | `role` | as-is, lowercase | no | low | Free text; treat as role/label, not user FK. |
| `crm_contacts.notes` | `contacts` | `notes` | as-is | no | low | Duplicated to client only when there is no contact row. |
| `crm_contacts.sites_managed` (CSV) | — | — | parse for lookup only | no | medium | **Do not store** the CSV. Use during sites import to attach the contact to a site via `contacts.site_id`. |

### Dedupe behavior

- Within a single run, multiple `crm_contacts` rows can share the same
  `account`. The migration creates exactly one `clients` row per
  normalized account name and attaches every person to it as a separate
  `contacts` row.
- Across runs, dedupe is enforced by `(organization_id, legacy_source,
  legacy_id)` on `clients` and `contacts`. A re-run is an upsert.

## Field Mapping — Sites

| V1 source field | V2 table | V2 field | Transform | Required? | Risk | Notes |
|---|---|---|---|---|---|---|
| `crm_sites.site_id` | `sites` | `legacy_id` | as-is | yes | low | `legacy_source = 'v1_monday'`. |
| `crm_sites.site_id` | `sites` | `site_code` | as-is | no | low | Preserve the SSW code in the dedicated column for UI later. |
| `crm_sites.client_id` | `sites` | `client_id` | lookup via `v1_client_id → v2_client_uuid` | yes | high | Orphan handling below. |
| `crm_sites.name` | `sites` | `name` | trim | yes | low | |
| `crm_sites.address` | `sites` | `address` | trim | no | low | V2 stores single `address` text — no line1/line2 split is required. |
| `crm_sites.city` | `sites` | `city` | trim | no | low | |
| `crm_sites.state` | `sites` | `state` | trim, uppercase if 2 chars | no | low | |
| `crm_sites.zip` | `sites` | `zip` | trim | no | low | |
| `crm_sites.lat` / `crm_sites.lng` | `sites` | `latitude` / `longitude` | `Decimal(str(value))`, reject if not in plausible range | no | medium | Skip silently if 0/null/non-numeric. |
| `crm_sites.gdrive_url` | `sites` | `drive_folder_url` | as-is | no | medium | See Drive URL Parsing. |
| `crm_sites.gdrive_url` | `sites` | `drive_folder_id` | parsed (folder URLs only) | no | medium | If URL parses as a file, leave folder_id null and log warning. |
| `crm_sites.drive_folder_id` (V1 extended col) | `sites` | `drive_folder_id` | prefer over parsed value if present and looks like a folder ID | no | medium | V1 already parsed it for some rows. |
| `crm_sites.status` | `sites` | `status` | map via Status Vocabulary | yes | medium | Unknown → `inactive`, log warning. |
| `crm_sites.notes` | `sites` | `notes` | as-is | no | low | |
| `crm_sites.contact` / `email` / `phone` | `contacts` | new row | create site-scoped contact if email or phone has signal | no | medium | `contacts.site_id` = new site; `contacts.client_id` = site's client. |
| `crm_sites.systems` (CSV) | `bmp_systems` | new rows | parse CSV (see BMP section) | no | medium | Deferred to phase M4. |
| `crm_sites.contract_start` / `contract_end` / `budget` / `service_month` / `submittal_due_date` / `last_inspection_date` / `next_service_date` | — | — | not migrated in M1 | n/a | high | V2 schema has no contract/budget/service-month columns yet. See Open Decisions. |
| `crm_sites.county` / `managed_by` / `geocode_source` / `drive_folder_name` / `drive_folder_updated_at` | — | — | not migrated | n/a | low | Drop with a warning at debug level. |

## Field Mapping — Jobs

| V1 source field | V2 table | V2 field | Transform | Required? | Risk | Notes |
|---|---|---|---|---|---|---|
| `crm_jobs.job_id` | `jobs` | `legacy_id` | as-is | yes | low | `legacy_source = 'v1_monday'`. |
| `crm_jobs.job_id` | `jobs` | `job_code` | as-is | no | low | Preserve SSO/SWL code. |
| `crm_jobs.site_id` | `jobs` | `site_id` | lookup via map | yes (NOT NULL) | high | Orphan handling below. |
| `crm_jobs.client_id` | `jobs` | `client_id` | lookup; fall back to `site.client_id` | yes (NOT NULL) | high | Site fallback is the primary path; explicit V1 `client_id` only used to detect mismatches. |
| `crm_jobs.job_site` | `jobs` | `name` | trim; fall back to `service + " at " + site.name` | yes | medium | V1 sometimes leaves job name blank. |
| `crm_jobs.service` | `jobs` | `service_type` | normalize to one of the V2 service-type values (see UX seed spec) | no | medium | Anything unmapped becomes `Other`, log warning. |
| `crm_jobs.scope` | `jobs` | `scope` | as-is | no | low | |
| `crm_jobs.notes` + `completion_notes` + `blocked_reason` | `jobs` | `notes` | join with `\n\n---\n\n` separators, drop blanks | no | low | Keep narrative context; do not delete blocked_reason silently. |
| `crm_jobs.job_status` | `jobs` | `status` | map via Status Vocabulary | yes | high | Unknown → `draft` if old (no schedule data) else `archived`; log warning either way. |
| `crm_jobs.scheduled_date` | `jobs` | `scheduled_date` | parse via Date Parsing Rules | no | medium | Blank → null. |
| `crm_jobs.internal_due_date` else `crm_jobs.next_action_date` | `jobs` | `due_date` | parse | no | medium | Take whichever is populated; `internal_due_date` wins. |
| `crm_jobs.completed_date` | `jobs` | `completed_date` | parse | no | medium | |
| `crm_jobs.owner` / `next_action_owner` / `completed_by` | `jobs` | `assigned_to` | only if matches a V2 `users.name` / `users.email`; else null | no | high | V2 `assigned_to` is a `users.id` UUID. Free-text owners do not become users automatically. Save the free-text in `notes` if it can't be resolved. |
| `crm_jobs.gdrive_url` | `jobs` | `drive_folder_url` | as-is | no | medium | See Drive URL Parsing. |
| `crm_jobs.gdrive_url` | `jobs` | `drive_folder_id` | parsed (folder URLs only) | no | medium | |
| `crm_jobs.report_id` | — | — | hold in lookup map, do not write yet | no | high | Used during M5 (reports) to link `reports.job_id`. |
| `crm_jobs.lead_id` | — | — | deferred | no | medium | Re-attach only if leads decision lands. |
| `crm_jobs.quoted_amount` / `actual_amount` | — | — | not migrated | n/a | high | V2 schema has no money columns yet. See Open Decisions. |
| `crm_jobs.scheduled_month` | — | — | dropped; derivable from `scheduled_date` | n/a | low | |

## Field Mapping — Leads

V2 has no leads table. This is the current blocker. The blueprint
documents two options and **recommends Option A** but does not implement
either:

### Option A — dedicated `leads` table (recommended)

- Add a new `leads` table in a follow-up Alembic migration with the V1
  lead fields preserved (`lead_id` → `legacy_id`, name, contact_name,
  email, phone, location/city/state, services, next_activity, poc,
  total_amount, submittal_deadline, expires, notes, gdrive_url).
- Migration creates `leads` rows on import; conversion to `clients` is
  an explicit later product action, not silent.
- Pros: keeps lead data faithful, preserves the operational `next_activity`
  / `total_amount` / `submittal_deadline` semantics, lets the leads UI
  evolve independently of clients.
- Cons: requires schema change before the migration script can run.

### Option B — import leads as `clients` with `status='prospect'`

- Each `SWL-####` becomes a `clients` row with `status='prospect'` and
  `legacy_source='v1_monday_lead'`.
- Money / deadline / services / next_activity fields are concatenated
  into `notes` to avoid silent data loss.
- Pros: zero schema work; immediately visible in the existing Clients
  page filtered by `prospect`.
- Cons: blurs the line between qualified clients and unqualified leads;
  loses structured access to deadline/expiration data; "convert lead to
  client" becomes a status flip rather than a deliberate workflow.

### Recommendation

Adopt **Option A** because the V1 leads board encodes operational data
(`next_activity`, `submittal_deadline`, `expires`, `total_amount`) that
V2 will eventually need to query and surface — and stuffing those into
`clients.notes` makes them unindexable. Lock the decision before M1
applies, otherwise leads stay out of scope until then.

### Lead fields that must not be lost

| V1 field | Why it matters |
|---|---|
| `lead_id` (`SWL-####`) | Traceability back to V1; idempotency key. |
| `name` | Lead/company name. |
| `contact_name`, `email`, `phone`, `poc` | First point of contact. |
| `location`, `city`, `state` | Geographic targeting / regional reporting. |
| `services` | What was pitched. |
| `next_activity` | Next CRM step / follow-up cadence. |
| `total_amount` | Estimated deal size. |
| `submittal_deadline` | Deadline-driven proposal work. |
| `expires` | When the lead goes stale. |
| `notes` | Free-form context. |
| `gdrive_url` | Proposal / supporting documents folder. |

## Field Mapping — Reports / Photos / Evidence

This is a **later phase**, after CRM migration is complete and the
`legacy_id → V2 uuid` maps for jobs and sites are stable.

| V1 source | V2 target | Notes |
|---|---|---|
| `projects/{uuid}/session.json` | `reports.snapshot_json` (JSONB) | Whole file is stored verbatim. `legacy_source='v1_session_json'`, `legacy_id={uuid}`. |
| Project meta site name | `reports.site_id` | Resolved by fuzzy-matching site name + client name against V2 sites; ambiguous matches go to manual review. |
| Project meta job linkage | `reports.job_id` | Resolved via `crm_jobs.report_id` lookup map. If no job, `report_id` is null and the report is site-only. |
| Generated DOCX (`crm_report_artifacts` where `artifact_kind='docx'`) | `evidence_files` row + `reports.generated_docx_file_id` | `evidence_files.source='report'`, `legacy_source='v1_monday'`, `legacy_id=artifact_id`. |
| Generated PDF (`crm_report_artifacts` where `artifact_kind='pdf'`) | `evidence_files` row + `reports.generated_pdf_file_id` | Same pattern. |
| `crm_report_artifacts.drive_file_id` | `evidence_files.drive_file_id` | Preserved as-is. |
| `crm_report_artifacts.file_path` | `evidence_files.storage_path` | Local path. Only useful if the file is still on disk at migration time. |
| Project photo files in `projects/{uuid}/photos/` | `evidence_files` rows | `source='photo'`, `job_id` from snapshot mapping, `sort_order` preserved. |
| Photo caption (component fields: system / caption_id / caption_view / caption_note) | `evidence_files.caption` | Joined per V1 logic (` – ` separator). |

**Caption metadata gap.** V1 photosheet captions are component-based
(`caption_id`, `caption_view`, `caption_note`, `system`). V2
`evidence_files.caption` is a single text column. Migration either:

- flattens to the combined V1 caption string (lossy but simple), or
- requires schema extension to keep components addressable.

This decision belongs in M5/M6 scoping, not in the CRM migration. See
Open Decisions.

## Status Mapping

V1 statuses are messy (Monday-style boards with overlapping freeform
values). Migration must include explicit mapping tables and fall through
conservatively. Unknown values are always logged with the raw V1 value
preserved.

### Client / contact V1 status → V2 status

| V1 raw (case-insensitive, trimmed) | V2 `clients.status` | Severity |
|---|---|---|
| `active`, `client`, `current`, `customer` | `active` | info |
| `inactive`, `dormant`, `no contact`, `cold` | `inactive` | info |
| `prospect`, `lead`, `pending` | `prospect` | info |
| `archived`, `dead`, `lost`, `do not contact`, `cancelled` | `archived` | info |
| _blank / unknown_ | `inactive` | warning |

### Site V1 status → V2 status

| V1 raw | V2 `sites.status` | Severity |
|---|---|---|
| `active`, `in service`, `current` | `active` | info |
| `inactive` | `inactive` | info |
| `on hold`, `paused`, `dispute` | `on_hold` | info |
| `archived`, `dead`, `closed` | `archived` | info |
| _blank / unknown_ | `inactive` | warning |

### Job V1 status → V2 status

V2 job target statuses (from UX seed spec): `draft`, `scheduled`,
`in_progress`, `in_review`, `completed`, `archived`.

| V1 raw | V2 `jobs.status` | Severity |
|---|---|---|
| `draft`, _blank, no schedule date_ | `draft` | info |
| `scheduled`, `to schedule`, `pending dispatch` | `scheduled` | info |
| `in progress`, `on site`, `mobilizing`, `field` | `in_progress` | info |
| `needs review`, `pending report`, `office review`, `qc` | `in_review` | info |
| `done`, `done!`, `complete`, `completed`, `billed`, `invoiced` | `completed` | info |
| `archived`, `cancelled`, `dead` | `archived` | info |
| _blank with no schedule_ | `draft` | warning |
| _blank with `completed_date` set_ | `completed` | warning |
| _blank with old (≥18 months) schedule and no completion_ | `archived` | warning |
| _anything else unknown_ | `draft` | warning |

### Failure mode

Critical migrations (clients, sites, jobs) **never fail** on an unknown
status — they fall through and log a warning. The dry-run summary lists
every distinct unknown value so they can be added to the table on the
next pass.

## Date Parsing Rules

- Accepted input forms: ISO-8601 dates (`2025-04-22`), ISO-8601 datetimes
  (`2025-04-22T13:45:00`, `2025-04-22 13:45:00`), and US short dates
  (`4/22/2025`, `04/22/25`).
- All other strings are treated as unparseable.
- Blank / `None` / `"None"` / `"null"` → `None`, no warning.
- Unparseable non-blank values → `None`, log warning with the raw value
  and the V1 row key. Migration does **not** fail.
- Parsed `datetime` values destined for V2 `Date` columns are truncated
  to date.
- The standard library is sufficient (`datetime.fromisoformat`, plus a
  small list of US-short-date `strptime` formats). Do **not** add
  `python-dateutil` as a new dependency just for this — recommend adding
  it later only if a real volume of weird date formats is discovered in
  M1 dry-run output.

Fields that need parsing: `crm_jobs.scheduled_date`,
`crm_jobs.completed_date`, `crm_jobs.internal_due_date`,
`crm_jobs.next_action_date`, `crm_sites.last_inspection_date`,
`crm_sites.next_service_date`, `crm_sites.contract_start` /
`contract_end` (when contract fields land), `crm_leads.submittal_deadline`,
`crm_leads.expires`, `crm_report_artifacts.inspection_date` /
`completed_date` / `next_service_date`.

## Drive URL Parsing Rules

A single parser is used everywhere a Drive URL appears
(`crm_sites.gdrive_url`, `crm_jobs.gdrive_url`,
`crm_leads.gdrive_url`, `crm_report_artifacts.*`).

Parser contract (matches the spirit of V1
`drive_artifact_service.parse_drive_folder_id`):

- Input: a free-text string.
- Output: `(drive_folder_url, drive_folder_id, warning)`.
- Blank input → `(None, None, None)`.
- Non-blank but unparseable → `(original, None, "invalid-drive-url")`.
- Folder URLs (`drive.google.com/drive/folders/{id}` or
  `drive.google.com/drive/u/0/folders/{id}`) → folder_url normalized,
  folder_id extracted.
- File URLs (`drive.google.com/file/d/{id}/...`) → folder_url preserved
  as-is, folder_id **null**, warning `"looks-like-file-not-folder"`.
- `open?id=` URLs → ambiguous; folder_id null, warning
  `"open-id-ambiguous"`. The migration prefers V1's pre-parsed
  `drive_folder_id` column when available rather than guessing.
- Anything that does not contain `drive.google.com` → folder_id null,
  warning `"non-drive-host"`.

### Test cases

| Input URL | Expected folder_id | Expected warning |
|---|---|---|
| _(blank)_ | None | None |
| `https://drive.google.com/drive/folders/1ABCxyz` | `1ABCxyz` | None |
| `https://drive.google.com/drive/folders/1ABCxyz?usp=sharing` | `1ABCxyz` | None |
| `https://drive.google.com/drive/u/0/folders/1ABCxyz` | `1ABCxyz` | None |
| `https://drive.google.com/file/d/1ABCxyz/view` | None | `looks-like-file-not-folder` |
| `https://drive.google.com/open?id=1ABCxyz` | None | `open-id-ambiguous` |
| `https://docs.google.com/document/d/1ABCxyz/edit` | None | `looks-like-file-not-folder` |
| `https://example.com/drive/folders/whatever` | None | `non-drive-host` |
| `1ABCxyz` (bare ID) | None | `non-drive-host` |

## Migration Script Design

A future script lives at `apps/api/scripts/migrate_v1.py` (alongside the
existing `seed_dev.py`, to share the V2 SQLAlchemy session setup).

### CLI flags

- `--v1-db PATH` — path to the V1 SQLite database (required).
- `--v1-projects-dir PATH` — path to the V1 `projects/` directory
  (required when `--include-reports` or `--include-photos`; optional
  otherwise).
- `--organization-name STRING` — V2 organization display name.
  Defaults to `"Sterling Stormwater"`.
- `--dry-run` (default if neither `--dry-run` nor `--apply` is given) —
  no writes; produces the validation report.
- `--apply` — required to actually write. Mutually exclusive with
  `--dry-run`.
- `--reset-imported` — before applying, delete only rows where
  `(organization_id, legacy_source)` matches one of the V1-originating
  sources for this script. Refuses to run against a demo organization.
- `--include-reports` — also run M5 (reports / session snapshots).
  Off by default.
- `--include-photos` — also run M6 (photos / evidence files).
  Off by default. Requires `--include-reports`.
- `--allow-demo-org` — explicit override allowing the migration target
  to be a demo-named organization.
- `--verbose` — debug-level logging of every row processed.

- `--client-aliases PATH` - optional M1.6 dry-run input for a private,
  reviewed CSV of deterministic site-to-client aliases. The script reads
  this file only and never writes back to it. Real mapping files must not
  be committed.

### Safety rules

- Default behavior is dry-run. The script must refuse to write without
  `--apply`.
- `--reset-imported` deletes **only** rows whose `legacy_source` is in
  the V1-source set for the current run. It never truncates tables and
  never touches seed_dev rows.
- There is no destructive full reset flag. If a full wipe is needed,
  use Alembic / db drop manually outside this script.
- Every skipped row is logged with the reason and the V1 ID.
- Every created row carries `legacy_source` and `legacy_id` whenever
  the target table has those columns.
- Row counts are printed before and after each phase.
- Re-running the script with the same inputs is a no-op apart from
  upsert refreshes — this is enforced by the dedupe-on-legacy-id rule
  and by upsert semantics.

## Import Order

The script processes phases in this order. Each phase depends on the
previous one's lookup maps.

1. **`organization`** — first because every other row needs `organization_id`.
2. **`clients` from `crm_contacts.account`** — must exist before sites,
   jobs, and contacts can resolve their parent. Also pulls in any
   report-side clients (from V1 `db.py` report tables, if present) and
   deduplicates them by normalized name + email.
3. **`contacts` from `crm_contacts`** — depends on the clients map so
   each contact gets a `client_id`. Comes before sites so a site-scoped
   contact can be re-attached when its company / person is encountered.
4. **`sites` from `crm_sites`** (+ report-side sites) — depends on the
   clients map. Orphan sites get a synthetic "Unknown" client to
   preserve `client_id` NOT NULL.
5. **`jobs` from `crm_jobs`** — depends on the sites map. Orphan jobs
   get a synthetic "Unassigned" site under the "Unknown" client.
6. **`bmp_systems` from `crm_sites.systems` CSV** — depends on the
   sites map. Skipped if `systems` is blank.
7. **`activity_log` from `crm_communications`** — optional, off by
   default; depends on whichever entity types (`client`, `site`, `job`)
   resolved successfully.
8. **`reports` metadata from `crm_report_artifacts` + `session.json`** —
   depends on the sites + jobs map and the `crm_jobs.report_id` lookup.
9. **`evidence_files` for generated reports** — depends on `reports`
   primary keys for the foreign-key `generated_docx_file_id` /
   `generated_pdf_file_id` round-trip.
10. **Photos / project evidence_files** — last, because they are the
    largest volume and the most expendable on a first dry-run pass.

Reason this ordering is strict: every step writes the lookup map the
next step depends on. Reordering risks orphan resolution silently
attaching to the wrong synthetic parent.

## Conflict Handling

| Conflict | Default action | Log severity | Manual review needed? |
|---|---|---|---|
| Duplicate clients (same normalized name, different `SSC-####`) | Merge into a single V2 `clients` row; both V1 IDs recorded — primary `legacy_id` is the first seen, alternate in `notes` as `"Also v1_monday:SSC-####"`. | warning | yes |
| Duplicate sites (same normalized name + city + client) | Treat as same site; second V1 row updates the first; both legacy IDs recorded as on clients. | warning | yes |
| Site with missing `client_id` | Attach to synthetic `"Unknown client"` (legacy_id `synthetic:client:unknown`). | warning | yes |
| Job with missing `site_id` | Attach to synthetic `"Unassigned site"` under the unknown client. | warning | yes |
| Job with missing `client_id` but valid `site_id` | Use `site.client_id`; no warning. | info | no |
| Job with `client_id` that disagrees with `site.client_id` | Use `site.client_id`; record V1 client mismatch in `notes`. | warning | yes |
| Unparseable date | Field becomes `None`, raw value logged. | warning | no |
| Invalid Drive URL | URL preserved, folder_id `None`, parser warning logged. | warning | no |
| Unknown status value | Status defaults per Status Mapping table. | warning | yes (so the mapping table can be updated). |
| Duplicate `(legacy_source, legacy_id)` within a run | Hard error — the run aborts. This means V1 data has structural inconsistency. | error | yes |
| Re-run hits an existing row with same `legacy_id` | Upsert (update fields, clear `archived_at`). | info | no |
| Missing `projects/{uuid}/session.json` for a referenced project | Skip the report row, log it. | warning | yes |
| Photo referenced in `session.json` missing from disk | Skip the `evidence_files` row, log it. | warning | yes |
| Free-text job owner that doesn't match a V2 user | `assigned_to = None`, raw owner copied into `jobs.notes`. | info | no |

## Validation / Dry-Run Output

A dry run produces a single multi-section report (stdout, plus a copy
written to `reports/migration/v1-to-v2-dry-run-<timestamp>.md` under the
worktree). Sections:

- **Source row counts** — per V1 table (`crm_contacts`, `crm_sites`,
  `crm_jobs`, `crm_leads`, `crm_communications`, `crm_report_artifacts`).
- **Target existing counts** — per V2 table, scoped to the target
  organization, before any work.
- **Planned creates** — per V2 table.
- **Planned updates** — per V2 table (rows whose `legacy_id` already
  exists and whose field values differ).
- **Skipped rows** — per V1 table, with reasons (blank required field,
  unresolved parent, etc.).
- **Conflicts** — duplicate names, owner mismatches, status fall-throughs.
- **Missing FK rows** — orphan sites / jobs and the synthetic parent
  they would attach to.
- **Unparseable dates** — raw value + row key.
- **Invalid Drive URLs** — raw value + row key + parser warning.
- **Orphan jobs** — jobs that would land under the synthetic
  unassigned-site bucket.
- **Report / photo readiness** — count of `projects/{uuid}/` directories,
  number resolvable to a job, number with missing photos on disk.
- **Final go/no-go summary** — an explicit `OK` or `NEEDS REVIEW` line
  based on whether any `error`-severity conflict was logged.

## Test Plan

Tests live under `apps/api/tests/migration/` (new directory). All tests
use a tiny synthetic V1 SQLite fixture committed under
`apps/api/tests/migration/fixtures/`. No real V1 data is checked in.

Required tests:

- **Clients import** — given two `crm_contacts` rows with the same
  `account`, exactly one `clients` row is created.
- **Contacts split** — given a `crm_contacts` row with both `account`
  and `first_name`/`last_name`, both a `clients` and a `contacts` row
  are created and linked.
- **Sites import with client lookup** — `crm_sites.client_id` resolves
  to the correct `v2_client_uuid`.
- **Jobs import with site/client lookup** — `jobs.client_id` is derived
  from `site.client_id` when missing on the V1 row.
- **Orphan job handling** — a `crm_jobs` row with a non-existent
  `site_id` attaches to the synthetic unassigned site; its V1 reference
  is preserved in `notes`.
- **Status mapping** — each table from the Status Vocabulary section is
  exercised (active/inactive/prospect/archived for clients; each job
  status raw → enum); unknown values fall through to the documented
  default with a logged warning.
- **Date parsing** — valid ISO, valid US, blank, unparseable each
  return the expected result and emit the expected log line.
- **Drive URL parser** — every row of the Drive URL test-case table is
  asserted.
- **Idempotent re-run** — running migration → migration → migration
  produces no extra rows; only the first run inserts.
- **`--reset-imported` scope** — a row inserted with a non-V1
  `legacy_source` (e.g. `seed_dev`) survives a `--reset-imported` run.
- **`--dry-run` does not write** — after a dry run on an empty target
  DB, row counts remain zero.
- **Report snapshot import (M5)** — `projects/{uuid}/session.json` →
  `reports.snapshot_json`; missing job link still creates a site-only
  report.

## Manual Review Checklist

Before Bryce runs the real (non-dry) migration, walk through:

- [ ] Status mappings (especially job statuses) — confirm the unknown
      fall-through buckets are acceptable.
- [ ] Leads decision (Option A vs Option B) is locked.
- [ ] `quoted_amount` / `actual_amount` strategy — drop, stash in
      `jobs.notes`, or wait for schema extension.
- [ ] Site contract fields (`contract_start`, `contract_end`, `budget`,
      `service_month`, `submittal_due_date`) — same question.
- [ ] Drive URL handling — confirm that file URLs and bare IDs being
      excluded from `drive_folder_id` is the desired behavior.
- [ ] Systems CSV parsing rules for `bmp_systems`.
- [ ] Orphan jobs policy — synthetic parents vs. hard skip.
- [ ] Report / photo migration timing — explicitly green-lit for M5/M6
      or explicitly deferred.

## Recommended Implementation Phases

Future Codex work is broken into discrete phases. Each ends with a
working, committed slice and a fresh dry-run report.

- **Phase M1 — CRM-only dry-run migration.** `scripts/migrate_v1.py`
  with `--dry-run` only. Implements organization + clients + contacts
  + sites + jobs mapping, status vocabulary, date parser, and a
  validation report. No writes.
- **Phase M2 — CRM apply migration.** Wires `--apply` and
  `--reset-imported`. Adds idempotency tests and the conflict log.
- **Phase M3 — Drive URL parser + folder validation.** Centralizes the
  parser, runs it across sites + jobs, and (optionally) verifies folder
  IDs exist via Drive (out of scope of migration script itself).
- **Phase M4 — BMP systems migration.** Parses `crm_sites.systems` CSV
  into `bmp_systems` rows.
- **Phase M5 — Reports / session snapshots.** Imports
  `projects/{uuid}/session.json` into `reports.snapshot_json`,
  resolves `job_id` / `site_id`, and creates `evidence_files` rows for
  generated DOCX / PDF.
- **Phase M6 — Photos / evidence.** Walks project photo folders, creates
  `evidence_files` rows, preserves caption strings.
- **Phase M7 — Migration QA dashboard / report.** A read-only view of
  the last dry-run / apply report, including unresolved warnings.

## Open Decisions

Decisions intentionally left unresolved here so they can be locked by
Bryce before each phase begins:

- **Leads strategy** — Option A (new `leads` table, recommended) vs.
  Option B (import as `prospect` clients).
- **Money fields** — drop `quoted_amount` / `actual_amount`, stash in
  `jobs.notes`, or extend the schema before M2.
- **Site contract fields** — same question for `contract_start`,
  `contract_end`, `budget`, `service_month`, `submittal_due_date`,
  `last_inspection_date`, `next_service_date`.
- **Photo caption metadata schema** — flatten captions in M6 or extend
  `evidence_files` (or add `report_photo_meta`) first.
- **Owner / assignee mapping** — when a V1 owner string matches an
  existing V2 user by name or email, auto-assign or require explicit
  user-mapping CSV?
- **Report-side clients/sites merge** — fuzzy-merge V1 SQLite report
  client/site tables with `crm_contacts` / `crm_sites` on name, or keep
  them as separate `legacy_source` rows that share a V2 row by
  normalized-name dedupe only?
- **`crm_communications` into `activity_log`** — opt-in by default or
  always-on once available?
- **Observation traceability** — extend `observations` to carry
  `legacy_source` / `legacy_id` before M5 if V1 finding-level data has
  external references; otherwise accept that observation provenance is
  derived from `reports.snapshot_json`.

## Recommended Next Codex Prompt

When it is time to implement, hand Codex a single self-contained prompt
such as:

> Implement `apps/api/scripts/migrate_v1.py` for Phase M1 (CRM-only
> dry-run migration) following
> `docs/architecture/v1-to-v2-migration-blueprint.md` exactly. Cover
> only organization + clients + contacts + sites + jobs. Wire `--v1-db`,
> `--v1-projects-dir`, `--organization-name`, `--dry-run` (default),
> `--apply`, `--reset-imported`, `--verbose`, and `--allow-demo-org`.
> Use the field-mapping tables, status vocabulary, date parser, Drive
> URL parser, conflict-handling rules, and validation/dry-run output
> sections as the implementation contract. Build the lookup maps as
> specified. Do not implement BMP systems, leads, reports, or photos
> yet. Add the tests listed in the Test Plan section, scoped to the
> phases implemented. Refuse to write without `--apply`. Refuse to
> target a demo-named organization unless `--allow-demo-org` is given.
> Do not modify any V1 file, the seed_dev script, or unrelated V2 code.
