# V1 M1 Real Dry-Run Review

## 1. Purpose

This M1.5 review summarizes the real V1 CRM dry-run before any V2 apply migration work. The goal is to avoid importing weak or orphaned V1 site records into V2, especially the 544 `crm_sites` rows that currently lack usable client relationships.

This is a sanitized summary. It intentionally omits raw client names, site names, Drive URLs, folder IDs, and row dumps.

## 2. Source Database Reviewed

- Source database: `C:\Users\brolf\Desktop\Stormwater_APP_Clean\stormwater_app\stormwater.db`
- Dry-run command: `apps/api/scripts/migrate_v1.py --dry-run`
- Dry-run output location: temp directory only, not committed
- Dry-run report schema: `m1-dry-run-v2`
- V1 source inspected read-only:
  - `app/services/crm_db.py`
  - `app/services/crm_service.py`
  - `app/services/db.py`
  - `app/services/crm_import.py`
  - V1 SQLite schema and aggregate table counts

## 3. Summary Counts

| Area | Count |
| --- | ---: |
| V1 `crm_contacts` rows | 1 |
| V1 `crm_sites` rows | 544 |
| V1 `crm_jobs` rows | 0 |
| V1 `crm_leads` rows | 0 |
| V1 `crm_report_artifacts` rows | 1 |
| Planned V2 clients | 1 synthetic client |
| Planned V2 contacts | 1 |
| Planned V2 sites | 542 |
| Planned V2 jobs | 0 |
| Dry-run warnings | 1090 |
| Dry-run errors | 0 |
| Go/no-go status | NEEDS REVIEW |

The planned client is synthetic. The single V1 contact row has a `client_id` but no account/client name, no email, no phone, and no `sites_managed` value, so M1 does not recover a real client from `crm_contacts`.

## 4. Why M2 Apply Is Not Ready Yet

M2 apply is not ready.

All 544 source sites are orphaned from a client-resolution perspective. `crm_sites.client_id` exists in the schema, but every real site row has it blank. The current dry-run therefore attaches every site to a synthetic "Unknown client" parent. Because all sites collapse under one synthetic client, duplicate handling also collapses two source site rows before import.

Applying now would create a large, low-trust site inventory that would need cleanup inside V2. That is exactly the migration shape we should avoid.

## 5. Client Relationship Problem

V1 expected site-client linkage through `crm_sites.client_id -> crm_contacts.client_id`.

Real data does not satisfy that model:

| Diagnostic | Count |
| --- | ---: |
| Sites with `client_id` | 0 |
| Sites with resolvable `client_id` | 0 |
| Sites missing `client_id` | 544 |
| Sites with possible client/account text field | 0 |
| Contacts with account/client name | 0 |
| Contacts with `sites_managed` | 0 |
| Planned clients from contacts | 0 |
| Planned synthetic clients | 1 |

The cause is not an M1 parser bug. The V1 site table has the relationship column, but the imported records do not populate it. The V1 import path maps a Monday "Client ID" column into `crm_sites.client_id`; the real site data appears to have been imported without that column populated.

## 6. Site Relationship Findings

The 544 sites came from V1 `crm_sites`.

Useful site-level clues exist, but they are not direct client links:

| Field / clue | Count |
| --- | ---: |
| Drive folder URL present | 544 |
| Parsed Drive folder URL | 544 |
| Address present | 542 |
| City and state present | 543 |
| Systems present | 379 |
| Managed-by present | 293 |
| Notes present | 29 |
| Service month present | 2 |
| Status present | 0 |
| Site contact/email/phone present | 0 |

`managed_by` and site-name prefixes are promising grouping clues, but they are not safe final client resolvers without approval. City/state is too broad to identify clients. Drive folder URLs are strong site identifiers but do not currently include parent folder path or client folder context in SQLite.

## 7. Job/Report Findings

| Area | Finding |
| --- | --- |
| Jobs | `crm_jobs` has 0 rows, so there is no job relationship data to resolve in M1. |
| Report artifacts | 1 artifact exists and is deferred by M1. |
| Artifact linkage | The artifact has a project ID and file path, but no site ID, client ID, job ID, Drive folder ID, or Drive web URL linkage. |
| Legacy report tables | V1 `reports`, `sites`, and `clients` tables are empty in the reviewed database. |

No report/photo migration should be added in this phase.

## 8. Drive URL Findings

All 544 sites have a Drive folder URL and all 544 parse as folder URLs. This is useful for stable site evidence and duplicate protection.

Drive URLs should not be used alone to infer client ownership in M2 because the SQLite rows only contain the site folder URL. They do not contain parent folder path, portfolio folder, or account folder metadata. A future resolver could use Drive parent-path enrichment, but that should be explicit and reviewed before apply.

## 9. Duplicate/Pattern Findings

| Pattern | Count |
| --- | ---: |
| Exact duplicate site-name groups | 2 |
| Rows in exact duplicate site-name groups | 4 |
| Exact duplicate site-name plus address groups | 1 |
| Rows in exact duplicate site-name plus address groups | 2 |
| Migration duplicate warnings | 2 |

Grouping clues:

| Signal | Distinct values | Groups with 2+ rows | Rows in groups with 2+ rows | Largest group sizes |
| --- | ---: | ---: | ---: | --- |
| Site-name prefix | 71 | 20 | 138 | 51, 28, 9, 7, 6 |
| Managed-by | 92 | 39 | 240 | 51, 27, 17, 12, 10 |
| City/state | 170 | 49 | 422 | 74, 65, 30, 28, 22 |
| Site-name prefix plus managed-by | 38 | 15 | 122 | 51, 27, 9, 7, 4 |

These patterns are good for preparing a manual resolver review. They are not sufficient for automatic client creation.

## 10. Recommended Resolver Rules

Use deterministic rules only, in this order:

1. Direct client ID: attach a site to a client only when `crm_sites.client_id` is non-empty and matches a planned/imported `crm_contacts.client_id`.
2. Approved alias mapping: attach a site when an explicit mapping file says a source value and source field map to a target client.
3. Site-name prefix aliases: allow only reviewed `site_name_prefix` mappings. Do not infer new clients from prefixes automatically.
4. Managed-by aliases: allow only reviewed `managed_by` mappings. Treat this as a routing clue, not proof of client ownership.
5. Drive folder aliases: allow only reviewed Drive-derived values, ideally parent folder path or folder ID plus an approved mapping. Do not infer from site folder URL alone.
6. Duplicate policy: dedupe only after client resolution. A duplicate site name under an unresolved synthetic client should block apply, not collapse records.
7. Unknown client policy: keep synthetic parents in dry-run diagnostics only. M2 apply should refuse large unresolved imports unless Bryce explicitly approves a small, bounded exception.

Avoid fuzzy matching as default M2 behavior. Fuzzy scores may be useful as review hints, but they should produce proposed mapping rows for human approval rather than final import relationships.

## 11. Proposed Manual Mapping File Strategy

Add support in a future M1/M1.5 pass for a mapping file like:

`apps/api/migration_maps/client_aliases.example.csv`

Columns:

| Column | Purpose |
| --- | --- |
| `source_value` | Raw source clue to match, such as a site-name prefix or managed-by value. |
| `source_field` | Field namespace, such as `site_name_prefix`, `managed_by`, `drive_parent_folder`, or `client_id`. |
| `target_client_name` | The approved V2 client/account name to create or attach to. |
| `target_client_status` | Approved V2 client status, usually `active`, `inactive`, `prospect`, or `archived`. |
| `notes` | Human explanation, ticket, or review context. |

The real `client_aliases.csv` should not be committed if it contains private client data. Commit only an example template with fake rows.

## 12. Open Decisions for Bryce

- Should V2 import all 544 site rows after client aliases are reviewed, or only an approved active subset first?
- Which source field should be the primary manual resolver: site-name prefix, managed-by, Drive parent folder, or an external client list?
- Should `managed_by` become a V2 contact/person field, an owner field, or only a migration clue?
- Should Drive parent folder paths be exported/crawled before M2 to improve client grouping?
- Should unresolved sites block apply entirely, or is there an explicit maximum unresolved threshold?
- How should duplicate site names be handled once sites are assigned to real clients?

## 13. Go/No-Go Checklist Before M2

- Real client alias mapping reviewed and approved.
- Dry-run shows most sites resolved to real clients, not a synthetic parent.
- Dry-run reports zero large-scale synthetic-client imports.
- Duplicate review happens after client resolution.
- M2 apply refuses unresolved site imports above an explicit threshold.
- No report/photo migration added to M2.
- No V2 Postgres writes occur until apply mode is intentionally implemented and reviewed.
- Full API, web, and core checks pass after resolver changes.

