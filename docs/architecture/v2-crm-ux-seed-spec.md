# Stormwater V2 CRM UX + Seed Data Spec

## Purpose

This spec exists to support two concurrent workstreams:

1. **Frontend implementation (Codex).** Give Codex a clear, opinionated UX
   target for the first Clients / Sites / Jobs pages in `apps/web` so it can
   ship a clean, consistent first pass without inventing product decisions.
2. **Future V1 → V2 migration.** Lock in the CRM field labels, status
   vocabulary, and seed shape now so that when we migrate V1 Monday-style
   records (SSC / SSW / SSO / SWL) into V2 we don't lose important CRM
   context or paint ourselves into a corner.

Anything not directly serving those two goals is out of scope here. This is
a product + implementation spec, not an architecture document.

## Product Principle

- **CRM is the source of truth.** Clients, Sites, and Jobs are the
  authoritative records that everything else hangs off of.
- **The core workflow is `Clients → Sites → Jobs`.** Users start at a
  client, drill into a site, and act on a job. Every CRM screen should
  reinforce this hierarchy.
- **Reports, photos, and files are downstream.** They are artifacts of
  jobs. They should never be the entry point in the CRM UI and should
  never be created without a parent job (and therefore a parent site and
  client).
- **Drive is a side-car, not the system of record.** A Drive folder URL
  decorates a site; it does not define it.

## Clients Page UX

### Purpose
Browse, search, create, and edit client (customer / property owner)
records. This is the top of the CRM funnel.

### Table columns
- Name
- Status (badge)
- Primary contact name
- Primary contact email
- Phone
- # Sites
- # Active jobs
- Updated at

### Search / filter behavior
- Single search box: substring match on name, primary contact name,
  primary contact email, and phone.
- Status filter: multi-select chips (`active`, `inactive`, `prospect`,
  `archived`). Default = `active` only.
- Sort: by name (default), updated at, # active jobs.
- Server-side pagination (page size ~25). No infinite scroll for v1.

### Selected detail panel fields
When a row is selected, a right-side detail panel shows:
- Name
- Status
- Primary contact name / email / phone
- Billing address (single string, optional)
- Notes (multiline, optional)
- Created at / Updated at
- Linked sites (count + first 5, click-through)
- Linked active jobs (count + first 5, click-through)

### Create / edit form fields
- Name (required)
- Status (default `active`)
- Primary contact name
- Primary contact email
- Phone
- Billing address
- Notes
- (Hidden / internal) `legacy_id`, `legacy_source` — never shown on
  create form; shown read-only on edit if present.

### Linked records
- Sites belonging to this client (click → Sites page filtered by this
  client).
- Jobs belonging to this client via its sites (click → Jobs page filtered
  by this client).

### Buttons / actions that SHOULD exist
- New client
- Edit client
- Archive client (soft delete → status `archived`)
- Unarchive client (only when status = `archived`)
- "View sites" → Sites page filtered to this client
- "View jobs" → Jobs page filtered to this client

### Buttons / actions that should NOT exist yet
- Merge clients
- Bulk import
- Bulk archive
- Email this client
- Generate report (reports belong on Job)
- Upload file (files belong on Job / Site)
- Anything Drive-related at the client level

### Empty / loading / error states
- **Empty:** "No clients yet. Create your first client to get started."
- **Loading:** Skeleton rows (5).
- **Error:** "Couldn't load clients. Check your API connection and try
  again."

## Sites Page UX

### Purpose
Browse, search, create, and edit site (physical property / facility)
records. Sites are always owned by exactly one client.

### Table columns
- Site name
- Client (name, click-through)
- Address (city, state)
- Status (badge)
- # Active jobs
- Last job date
- Drive (icon link, only if `drive_folder_url` present)
- Updated at

### Search / filter behavior
- Single search box: substring match on site name, address, client name.
- Client filter: dropdown of clients (single-select).
- Status filter: multi-select (`active`, `inactive`, `on_hold`,
  `archived`). Default = `active` + `on_hold`.
- Sort: by name (default), last job date, updated at.
- Server-side pagination (page size ~25).

### Selected detail panel fields
- Site name
- Client (name link)
- Address (full)
- Status
- Service notes
- Drive folder link (button: "Open in Drive") — only if URL present
- Created at / Updated at
- Linked jobs (count + first 5)

### Create / edit form fields
- Site name (required)
- Client (required, searchable picker — by client name, not UUID)
- Address line 1
- Address line 2
- City
- State
- Postal code
- Status (default `active`)
- Service notes (multiline)
- Drive folder URL (optional, free text — backend parses out
  `drive_folder_id` if it looks valid)
- (Hidden / internal) `drive_folder_id`, `legacy_id`, `legacy_source`

### Linked records
- Parent client (link).
- Jobs at this site (link → Jobs page filtered by this site).

### Buttons / actions that SHOULD exist
- New site (prefilled with current client if launched from a client
  detail panel)
- Edit site
- Archive / unarchive site
- "New job at this site"
- "View jobs" → Jobs page filtered to this site
- "Open in Drive" (only when URL present)

### Buttons / actions that should NOT exist yet
- Move site to different client
- Bulk Drive sync / scan
- Upload files
- Photosheet / report generation at the site level
- Mapping / geocoding preview
- Anything multi-tenant / sharing related

### Empty / loading / error states
- **Empty:** "No sites yet. Add a site to one of your clients."
- **Loading:** Skeleton rows.
- **Error:** "Couldn't load sites. Try again."
- **Empty (filtered to one client):** "This client has no sites yet."

## Jobs Page UX

### Purpose
Browse, search, create, and edit jobs (a unit of stormwater work at a
site — inspection, maintenance, repair, etc.). This is where most
day-to-day field activity is tracked.

### Table columns
- Job title / short summary
- Site (name, click-through)
- Client (name, derived from site)
- Service type
- Status (badge)
- Scheduled date
- Assigned to (name, optional, may be blank in v1)
- Updated at

### Search / filter behavior
- Single search box: substring match on job title, site name, client
  name.
- Status filter: multi-select (`draft`, `scheduled`, `in_progress`,
  `in_review`, `completed`, `archived`). Default = everything except
  `archived`.
- Client filter: optional.
- Site filter: optional, dependent on client filter when both are set.
- Service type filter: multi-select.
- Date range: scheduled date.
- Sort: scheduled date (default), updated at, status.

### Selected detail panel fields
- Job title
- Status
- Service type
- Site (name link), Client (derived name link)
- Scheduled date
- Assigned to (name, optional)
- Notes / description
- Created at / Updated at
- Drive folder link inherited from site (read-only)
- (Future) Linked artifacts: reports, photosheets, files — out of scope
  this pass, leave a placeholder section that says "Reports & files
  coming soon" rather than a broken button.

### Create / edit form fields
- Job title (required)
- Site (required, searchable picker by site name; client is derived)
- Service type (required, dropdown — see Status Vocabulary section for
  service types)
- Status (default `draft`)
- Scheduled date
- Assigned to (free text or user picker, optional in v1)
- Notes / description (multiline)
- (Hidden / internal) `legacy_id`, `legacy_source`

### Linked records
- Parent site (link).
- Parent client (link, derived).

### Buttons / actions that SHOULD exist
- New job
- Edit job
- Change status (quick action menu)
- Archive / unarchive job
- "Open site" / "Open client"

### Buttons / actions that should NOT exist yet
- Generate report / photosheet
- Upload field photos
- Send to dispatch / scheduling
- Invoice / billing actions
- Time tracking
- Map view / route planning
- Anything related to V1's old reporting flow

### Empty / loading / error states
- **Empty:** "No jobs yet. Create a job from a site."
- **Loading:** Skeleton rows.
- **Error:** "Couldn't load jobs. Try again."
- **Empty (filtered to one site):** "This site has no jobs yet."

## Field Labels

These tables drive both the frontend labels and the migration mapping
later. UI labels are the user-facing strings — never show raw column
names.

### Clients

| V2 field | UI label | Notes | V1 migration note |
|---|---|---|---|
| id | — | UUID, never shown in UI | new V2 ID |
| organization_id | — | scoping field, never shown | derived from migration target org |
| name | Name | required | from V1 client name |
| status | Status | enum, badge | map V1 messy statuses (see Status Vocabulary) |
| primary_contact_name | Primary contact | optional | from V1 contact fields |
| primary_contact_email | Email | optional | from V1 contact email |
| phone | Phone | optional | from V1 phone fields, normalize |
| billing_address | Billing address | single string for v1 | best-effort from V1 address fields |
| notes | Notes | multiline | from V1 notes / description |
| legacy_id | Legacy ID | internal, shown read-only on edit | V1 Monday-style ID (e.g. SSC-####) |
| legacy_source | Legacy source | internal | `v1_monday` or similar |
| created_at | Created | read-only | preserve original V1 created if available |
| updated_at | Updated | read-only | preserve original V1 updated if available |

### Sites

| V2 field | UI label | Notes | V1 migration note |
|---|---|---|---|
| id | — | UUID, never shown | new V2 ID |
| organization_id | — | never shown | inherited |
| client_id | Client | UI shows client *name*, never raw UUID | resolve via V1 client mapping |
| name | Site name | required | from V1 site name |
| address_line1 | Address line 1 | optional | split out from V1 address blob |
| address_line2 | Address line 2 | optional | split out from V1 address blob |
| city | City | optional | from V1 address |
| state | State | optional | from V1 address |
| postal_code | Postal code | optional | from V1 address |
| status | Status | enum, badge | map V1 messy statuses |
| service_notes | Service notes | multiline | from V1 site notes |
| drive_folder_url | Drive folder | shown as link button | from V1 `gdrive_url` |
| drive_folder_id | — | hidden / internal | parsed from `drive_folder_url` |
| legacy_id | Legacy ID | internal, read-only on edit | V1 Monday-style ID (e.g. SSW-####) |
| legacy_source | Legacy source | internal | `v1_monday` |
| created_at | Created | read-only | preserve V1 if available |
| updated_at | Updated | read-only | preserve V1 if available |

### Jobs

| V2 field | UI label | Notes | V1 migration note |
|---|---|---|---|
| id | — | UUID, never shown | new V2 ID |
| organization_id | — | never shown | inherited |
| site_id | Site | UI shows site *name*; client is derived | resolve via V1 site mapping |
| title | Job title | required | from V1 job name / short description |
| service_type | Service type | enum dropdown | map from V1 service / job type field |
| status | Status | enum, badge | map V1 mixed statuses |
| scheduled_date | Scheduled date | optional | from V1 scheduled / due date |
| assigned_to | Assigned to | free text in v1 (user picker later) | from V1 assignee, may be blank |
| description | Notes | multiline | from V1 job notes / description |
| legacy_id | Legacy ID | internal, read-only on edit | V1 Monday-style ID (e.g. SSO-####, SWL-####) |
| legacy_source | Legacy source | internal | `v1_monday` |
| created_at | Created | read-only | preserve V1 if available |
| updated_at | Updated | read-only | preserve V1 if available |

**General UI rules:**
- Never show raw UUIDs in the UI. Always resolve `client_id` / `site_id`
  to names.
- `legacy_id` is internal but may be shown read-only on an edit screen
  inside an "Advanced / metadata" collapsible.
- `drive_folder_url` is shown as a single "Open in Drive" link button.
- `drive_folder_id` is never shown to users.

## Status Vocabulary

### Client statuses

| Value | Label | Meaning | Migration notes |
|---|---|---|---|
| active | Active | Current customer, in service | default for migrated V1 clients that have any recent activity |
| inactive | Inactive | No recent work, not archived | for V1 clients with no jobs in last N months |
| prospect | Prospect | Not yet a paying customer | only for V1 leads if we promote any |
| archived | Archived | Soft-deleted, hidden by default | from explicit V1 archived / dead-deal flags |

### Site statuses

| Value | Label | Meaning | Migration notes |
|---|---|---|---|
| active | Active | In service | default for V1 sites with current contracts |
| inactive | Inactive | No active jobs but not archived | for V1 sites whose client went inactive |
| on_hold | On hold | Temporarily paused (weather, dispute, etc.) | rare in V1; map explicitly when found |
| archived | Archived | Soft-deleted, hidden by default | from V1 explicit archived flag |

### Job statuses

| Value | Label | Meaning | Migration notes |
|---|---|---|---|
| draft | Draft | Created but not yet scheduled | for V1 records with no schedule data |
| scheduled | Scheduled | On the calendar | from V1 "Scheduled" / pending-dispatch states |
| in_progress | In progress | Field work happening | from V1 "In Progress" / on-site states |
| in_review | In review | Awaiting office review / report finalization | from V1 "Needs Review" / report-pending |
| completed | Completed | Closed-out, report delivered | from V1 "Done" / "Complete" / "Billed" |
| archived | Archived | Soft-deleted, hidden by default | from V1 explicit archived flag |

### Service types (Jobs)

For v1 of the frontend, use a fixed dropdown. Add more later as the data
demands:

- Inspection
- Maintenance
- Repair
- Construction
- Snow / Ice mitigation
- Emergency response
- Other

### V1 status mapping risk

V1 statuses are messy — historically populated via Monday-style boards
with overlapping and freeform values ("Done!", "DONE", "complete", "billed",
"dead", "no contact", etc.). Migration must include an explicit mapping
table from V1 raw values to V2 enum values. Anything that doesn't match
should be flagged and bucketed conservatively (default to `inactive` for
clients/sites, `draft` or `archived` for jobs depending on age).

## Seed Data

Seed data should be realistic enough to exercise filters, search,
pagination boundaries, and linked-record rendering. Maine / Northeast
biased, with one multi-state portfolio example.

### Organization seed

| id | name |
|---|---|
| `00000000-0000-0000-0000-000000000001` | Sterling Stormwater (Demo) |

This is the org pointed to by `NEXT_PUBLIC_DEMO_ORG_ID` during local
development.

### Clients seed

| name | status | primary_contact_name | primary_contact_email | phone | billing_address | notes |
|---|---|---|---|---|---|---|
| Casco Bay Property Group | active | Erin Whittier | erin@cascobaypg.com | 207-555-0142 | 14 Commercial St, Portland ME 04101 | Multi-site portfolio in Greater Portland. |
| Kennebec Industrial Park | active | Dan Roy | droy@kennebecind.com | 207-555-0188 | 100 Industrial Way, Augusta ME 04330 | Heavy industrial, MS4 sensitive. |
| Northeast Retail Holdings | active | Pat Kuo | pkuo@nerh.com | 617-555-0211 | 50 Boylston St, Boston MA 02116 | Multi-state retail portfolio (ME, NH, MA). |

### Sites seed

| name | client | address | status | service_notes | drive_folder_url |
|---|---|---|---|---|---|
| Casco Bay PG — Commercial St HQ | Casco Bay Property Group | 14 Commercial St, Portland ME | active | Two underground detention vaults, annual inspection. | `https://drive.google.com/drive/folders/1ABCxyzExampleFolder001` |
| Casco Bay PG — Marginal Way Lot | Casco Bay Property Group | 220 Marginal Way, Portland ME | on_hold | Owner dispute pending; paused Q2. | _(blank)_ |
| Casco Bay PG — Riverside Office | Casco Bay Property Group | 9 Riverside Industrial Pkwy, Portland ME | active | Bioretention basin + perimeter swales. | `https://drive.google.com/drive/folders/1ABCxyzExampleFolder002` |
| Kennebec IP — Plant 3 | Kennebec Industrial Park | 102 Industrial Way, Augusta ME | active | Oil/water separator + outfall, MS4 reporting. | `https://drive.google.com/drive/folders/1ABCxyzExampleFolder003` |
| NERH — Salem Crossing Plaza | Northeast Retail Holdings | 410 Highland Ave, Salem NH | active | Catch basins + porous parking strip. | _(blank)_ |

### Jobs seed

| title | site | service_type | status | scheduled_date | assigned_to | description |
|---|---|---|---|---|---|---|
| Annual inspection — Commercial St vaults | Casco Bay PG — Commercial St HQ | Inspection | completed | 2026-03-12 | M. Côté | Annual underground detention vault inspection, both vaults. |
| Spring clean-out — Riverside swales | Casco Bay PG — Riverside Office | Maintenance | in_review | 2026-04-22 | J. Boucher | Sediment removal in perimeter swales, report pending. |
| Outfall repair — Plant 3 | Kennebec IP — Plant 3 | Repair | in_progress | 2026-05-08 | Crew B | Concrete spalling at outfall headwall, mobilizing crew. |
| MS4 annual inspection — Plant 3 | Kennebec IP — Plant 3 | Inspection | scheduled | 2026-06-03 | _(unassigned)_ | Required MS4 annual inspection + report. |
| Catch basin sweep — Salem Crossing | NERH — Salem Crossing Plaza | Maintenance | scheduled | 2026-05-20 | Crew A | Quarterly catch basin clean-out, 14 structures. |
| Storm damage assessment — Marginal Way | Casco Bay PG — Marginal Way Lot | Emergency response | draft | _(none)_ | _(unassigned)_ | Post-storm assessment pending owner approval. |
| Re-inspection — Commercial St vault #2 | Casco Bay PG — Commercial St HQ | Inspection | draft | _(none)_ | _(unassigned)_ | Follow-up after sediment threshold flagged in March. |
| Snow / ice mitigation site walk | NERH — Salem Crossing Plaza | Snow / Ice mitigation | archived | 2025-12-15 | M. Côté | Closed-out site walk from prior winter season. |

**Coverage notes:**
- Casco Bay Property Group has 3 sites (multi-site client requirement).
- Casco Bay PG — Commercial St HQ has 2 jobs and Kennebec IP — Plant 3
  has 2 jobs (multi-job site requirement).
- Statuses span all enum values across the three entities.
- Drive URLs: 3 populated, 2 blank.
- Service types cover Inspection, Maintenance, Repair, Emergency
  response, Snow / Ice mitigation.
- Northeast Retail Holdings demonstrates a multi-state portfolio client
  (ME + NH + MA in `billing_address`, with NH site seeded).

## Migration Readiness Notes

- **V1 IDs are Monday-style.** Clients are `SSC-####`, sites are
  `SSW-####`, jobs are `SSO-####` (operations) and `SWL-####` (work
  log / similar). V2 uses UUIDs; the V1 IDs come in via `legacy_source`
  + `legacy_id` and are preserved for traceability and idempotent
  re-runs of the migration.
- **Drive linking.** V1 `gdrive_url` maps to V2 `drive_folder_url`. The
  migration (or the backend on save) should also attempt to parse
  `drive_folder_id` out of the URL. Both should round-trip; UI only
  exposes the URL.
- **Contacts + clients are messy.** V1 has duplicate clients, free-text
  contact blobs, and contacts that should arguably be clients. The
  migration plan must include a dedupe pass keyed on normalized name +
  email + phone, with a human-review queue for ambiguous matches.
  Frontend does not need a contacts model in this first pass.
- **Jobs with missing parents.** V1 jobs may have missing or invalid
  `client_id` / `site_id`. Migration must handle these deterministically:
  prefer auto-attaching to a parent if a confident match exists, else
  attach to a synthetic "Unassigned" site under a synthetic "Unknown
  client" record so that nothing is silently dropped. Flag these for
  cleanup.
- **V1 leads have no V2 home yet.** Don't build a Leads page now. When
  needed, leads should probably enter as `prospect`-status clients with
  no sites/jobs — but that decision is deferred.
- **Reports and photos migrate later.** They live on jobs. We cannot
  migrate them until the CRM records (and especially the
  `legacy_id → V2 id` mapping for jobs) exist.
- **Idempotency.** Every migrated record carries `legacy_source` +
  `legacy_id`. Re-running the migration should upsert on that key, not
  duplicate.

## Manual QA Checklist

Codex / whoever lands the first frontend pass should be able to walk
through this list end-to-end against a freshly seeded demo org:

- [ ] Missing `NEXT_PUBLIC_DEMO_ORG_ID` shows a clean setup message
      (not a stack trace).
- [ ] API unreachable shows a clean error state on every list page
      (not a stack trace, not an infinite spinner).
- [ ] Clients page lists seeded clients.
- [ ] Can create a new client.
- [ ] Can edit an existing client.
- [ ] Can archive a client; archived clients are hidden by default.
- [ ] Can unarchive a client.
- [ ] Selecting a client shows linked sites and active jobs.
- [ ] Sites page lists seeded sites.
- [ ] Sites page client filter works.
- [ ] Can create a site linked to an existing client (client picker
      shows names, not UUIDs).
- [ ] Can edit a site.
- [ ] Can archive / unarchive a site.
- [ ] "Open in Drive" appears only when a Drive URL is set and opens in
      a new tab.
- [ ] Can create a job from a site (site is prefilled, client is
      derived).
- [ ] Jobs page lists seeded jobs.
- [ ] Jobs page status filter works.
- [ ] Can edit a job.
- [ ] Can change a job's status via the quick action menu.
- [ ] Can archive / unarchive a job.
- [ ] No "fake" buttons are visible (no Reports, Photos, Files,
      Invoice, Map, etc. buttons that don't do anything yet).
- [ ] No raw UUIDs are shown where a name should be shown (anywhere
      a `client_id` or `site_id` surfaces in the UI, it's resolved to a
      name).
- [ ] Loading states use skeletons, not blank screens.
- [ ] Empty states show the copy from the UX Copy section, not generic
      "no results" text.

## UX Copy

Short, plain copy blocks the frontend should use verbatim where it makes
sense:

- **No clients yet:** "No clients yet. Create your first client to get
  started."
- **No sites yet:** "No sites yet. Add a site to one of your clients."
- **No jobs yet:** "No jobs yet. Create a job from a site."
- **Missing demo organization ID:** "Local dev is missing
  `NEXT_PUBLIC_DEMO_ORG_ID`. Set it in `apps/web/.env.local` to load CRM
  data."
- **API not reachable:** "Can't reach the API. Make sure the backend is
  running, then try again."
- **No linked sites:** "This client doesn't have any sites yet."
- **No linked jobs:** "No jobs here yet."
- **Save success:** "Saved."
- **Save failed:** "Couldn't save your changes. Try again, or check the
  highlighted fields."
- **Archive confirmation:** "Archive this {client | site | job}? It
  will be hidden from the default view. You can restore it later."

## Recommended Next Codex Prompt

After the first frontend CRM pass, suggested next prompt:

> Wire the Clients, Sites, and Jobs pages in `apps/web` to the existing
> FastAPI endpoints using `NEXT_PUBLIC_DEMO_ORG_ID` as the org scope.
> Follow `docs/architecture/v2-crm-ux-seed-spec.md` exactly for table
> columns, field labels, status vocabulary, allowed/forbidden buttons,
> empty/error/loading states, and UX copy. Do not introduce reports,
> photos, files, dispatch, or any feature not listed in that spec. Use
> the seed data described there for local development. Confirm every
> item in the Manual QA Checklist passes before declaring done.
