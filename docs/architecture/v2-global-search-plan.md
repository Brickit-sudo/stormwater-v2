# V2 Global Search Foundation

## Goal

Global Search gives the V2 app one fast local lookup surface across CRM records that already exist in the V2 database:

- Clients
- Sites
- Jobs
- Evidence file metadata
- Imported or seeded email message records
- AI draft records
- Reminders

This phase is a foundation only. It is deliberately local-only and does not call Outlook, Gmail, Google Drive, OneDrive, SharePoint, OpenAI, or any provider API.

## Backend Contract

`GET /v1/search` requires:

- `organization_id`
- `q` with at least two characters

Optional params:

- `types`: comma list of `clients`, `sites`, `jobs`, `files`, `emails`, `ai_drafts`, `reminders`
- `limit`: per-type result cap, default `10`, max `25`

The response includes the normalized query, grouped results, and `total_count` for returned rows. Counts are bounded returned counts, not unbounded full match counts.

## Search Fields

- Clients: name, primary contact name, email, phone, notes
- Sites: name, address, city, state, notes, stored Drive folder URL
- Jobs: name, service type, status, scope, notes
- Files: file name, caption, public URL, source
- Emails: subject, sender, snippet, and a capped prefix of local `body_text`
- AI Drafts: title, draft type, and a capped prefix of local draft text
- Reminders: title, description, status, priority

Every query is organization-scoped and excludes archived rows.

## Frontend Contract

The `/search` page reads `NEXT_PUBLIC_DEMO_ORG_ID`, waits for an explicit form submit, and displays grouped results. It does not run live provider searches and does not fetch on every keystroke.

Result links use only real supported routes:

- Clients: `/crm/clients`
- Sites: `/crm/sites?site_id=<id>`
- Jobs: `/crm/jobs`
- Files, emails, and AI drafts: `/work`
- Reminders: `/schedule`

Where a selected-record deep link is not supported, Search routes to the safe workspace only.

## Deferred

Future phases can add:

- Provider-backed Outlook/Gmail/Drive search after explicit user action
- Full-text indexing for larger local data sets
- A command palette
- Record-specific deep links for Clients, Jobs, Work Hub records, and Reminders
- Background indexing only if scale requires it

Until those are implemented, Global Search remains a bounded local SQL fan-out.
