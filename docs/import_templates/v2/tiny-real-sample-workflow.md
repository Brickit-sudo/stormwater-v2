# Tiny Real Clients/Sites Sample Workflow

## 1. Purpose

Use this workflow to validate a tiny private Clients/Sites sample before any V2 import work exists.

The sample is for confidence-building only: a few real clients, a few real sites, and enough relationship data to prove that every site has one clear client.

## 2. What this does

- Creates private local CSV copies from the safe committed templates.
- Checks required columns and required fields.
- Checks duplicate client and site external IDs.
- Checks that every site references a client from the same tiny sample.
- Writes validation reports under `import_validation_reports/`.
- Gives a clear READY or NOT READY result.

## 3. What this does NOT do

- It does not import data.
- It does not write to the database.
- It does not run Alembic migrations.
- It does not run the V1 migration apply path.
- It does not call Outlook, Gmail, Google Drive, or OpenAI.
- It does not crawl Drive folders or mailboxes.
- It does not create reports, jobs, documents, photosheets, or DOCX output.

## 4. Folder setup

Create private sample files under this ignored folder:

```text
docs/import_templates/v2/private/
```

Expected private files:

```text
docs/import_templates/v2/private/clients_tiny_sample.csv
docs/import_templates/v2/private/sites_tiny_sample.csv
```

The `private/` folder is gitignored. Real client names, site names, addresses, emails, and Drive links must stay there and must never be committed.

## 5. How to copy safe templates

From the repo root:

```powershell
cd C:\Users\brolf\Desktop\Stormwater_APP_Clean\stormwater-v2
New-Item -ItemType Directory -Force docs\import_templates\v2\private | Out-Null
Copy-Item docs\import_templates\v2\clients_template.csv docs\import_templates\v2\private\clients_tiny_sample.csv
Copy-Item docs\import_templates\v2\sites_template.csv docs\import_templates\v2\private\sites_tiny_sample.csv
```

After copying, delete the fake demo rows from the private copies and replace them with the tiny real sample.

## 6. How to create a tiny real sample

Keep it tiny:

- 3 to 5 real clients maximum.
- 5 to 10 real sites maximum.
- No jobs yet.
- No documents yet.
- No full exports yet.

Use stable IDs from the source system whenever possible. If a source system has a client ID, account ID, site ID, store ID, folder ID, or other durable source identifier, put that value in the matching external ID column.

Every site row must have `client_external_id`, and that value must exactly match one row in `clients_tiny_sample.csv`.

Use `drive_folder_url` only when the exact client or site folder is already known. Leave it blank when uncertain.

## 7. Required fields

Client rows require:

- `source_system`
- `client_external_id`
- `canonical_name`
- `status`

Site rows require:

- `source_system`
- `site_external_id`
- `client_external_id`
- `canonical_name`
- `status`

Also include these fields when available:

- `legacy_source`
- `legacy_id`
- `alias_values`
- `drive_folder_url`
- notes explaining uncertainty

For statuses, use the values already shown in the templates. For the tiny sample, `active`, `inactive`, `prospect`, `on_hold`, and `archived` cover the current client/site cases.

## 8. How to run validator

Preferred command from the repo root:

```powershell
cd C:\Users\brolf\Desktop\Stormwater_APP_Clean\stormwater-v2
.\scripts\validate-v2-import-sample.ps1
```

Explicit paths:

```powershell
.\scripts\validate-v2-import-sample.ps1 `
  -ClientsPath "docs\import_templates\v2\private\clients_tiny_sample.csv" `
  -SitesPath "docs\import_templates\v2\private\sites_tiny_sample.csv"
```

Reports are written to:

```text
import_validation_reports/
```

That folder is gitignored because reports may contain private row clues.

## 9. How to prepare Monday samples

The Monday prep helper is validation prep only. It reads the private Monday exports, writes ignored sample CSVs, and writes an ignored aggregate mapping report. It does not import rows, write the database, run migrations, or call providers.

Tiny sample:

```powershell
cd C:\Users\brolf\Desktop\Stormwater_APP_Clean\stormwater-v2\apps\api
python scripts\prepare_monday_tiny_sample.py
```

Medium sample:

```powershell
cd C:\Users\brolf\Desktop\Stormwater_APP_Clean\stormwater-v2\apps\api
python scripts\prepare_monday_tiny_sample.py `
  --client-limit 25 `
  --site-limit 75 `
  --clients-output ..\..\docs\import_templates\v2\private\clients_medium_sample.csv `
  --sites-output ..\..\docs\import_templates\v2\private\sites_medium_sample.csv `
  --report-output ..\..\import_validation_reports\monday-medium-mapping-review.md
```

Review the ignored mapping report for:

- Monday Site Information `Status` values and proposed V2 status mappings.
- Rows defaulted to `active` for validation only.
- Excluded or unresolved site relationship buckets.
- Excluded client candidate buckets.
- Sanitized unresolved site/client tokens.

Do not commit the generated CSVs or reports.

## 10. Medium Sample Mapping Review

The medium sample can pass template validation for the clear Clients/Sites rows while unresolved Monday rows still need manual mapping review. A clean validator result only means the selected clear rows are internally consistent. It does not approve the excluded rows, weak client links, unmapped statuses, duplicates, or defaulted statuses for import.

Generate the private mapping review pack from the same Monday exports:

```powershell
cd C:\Users\brolf\Desktop\Stormwater_APP_Clean\stormwater-v2\apps\api
python scripts\prepare_monday_tiny_sample.py `
  --client-limit 25 `
  --site-limit 75 `
  --clients-output ..\..\docs\import_templates\v2\private\clients_medium_sample.csv `
  --sites-output ..\..\docs\import_templates\v2\private\sites_medium_sample.csv `
  --report-output ..\..\import_validation_reports\monday-medium-mapping-review.md `
  --write-review-pack `
  --review-output-dir ..\..\import_validation_reports\monday_review_pack
```

The review pack is written under:

```text
import_validation_reports/monday_review_pack/
```

Generated files:

- `unresolved_sites_review.csv`
- `client_status_review.csv`
- `duplicate_sites_review.csv`
- `status_defaults_review.csv`
- `README.md`

These files are private and ignored. They may contain real client names, site names, source row numbers, and source IDs. Do not commit them or paste their row contents into issue trackers, commits, or public docs.

Bryce should fill:

- `manual_client_external_id` when a site has a reviewed client mapping that the exports could not prove.
- `manual_status` when a defaulted or unmapped site status needs a reviewed V2 status.
- `suggested_status` when a client has an unmapped Monday status.
- `review_status` with a clear decision such as `approved`, `skip`, `needs_source_fix`, or `needs_followup`.
- `notes` for context that should survive into the next private validation pass.

Do not proceed to import until:

- unresolved site buckets have been reviewed,
- unmapped client statuses have reviewed V2 statuses,
- duplicate Site ID rows have keep/skip/merge decisions,
- status defaults have been accepted or manually corrected,
- generated private review files remain untracked in git.

After Bryce completes the review, generate a larger private validation sample using only reviewed mappings. Do not import yet.

## 11. Review Mapping Workbook

The review workbook is a private Excel convenience layer over the review CSVs. It is for human review only. It does not import data, write the database, run migrations, run V1 migration apply, or call Outlook, Gmail, Google Drive, or OpenAI.

Generate it from the repo root:

```powershell
.\scripts\create-monday-review-workbook.ps1 -Open
```

Equivalent Python command:

```powershell
.\apps\api\.venv\Scripts\python apps\api\scripts\prepare_monday_tiny_sample.py `
  --write-review-workbook `
  --review-pack-dir "import_validation_reports\monday_review_pack" `
  --review-workbook-path "import_validation_reports\monday_review_pack\monday_mapping_review.xlsx"
```

The workbook is written to:

```text
import_validation_reports/monday_review_pack/monday_mapping_review.xlsx
```

The workbook is private and ignored. Do not commit it, paste row contents into public systems, or use it as an import source.

Workbook tabs:

- `Overview`: generated time, source review pack path, row counts, approved count, and private-file warning.
- `Unresolved Sites`: sites that need Bryce to decide the correct client link, status, or exclusion decision.
- `Client Status Review`: clients whose Monday status needs a reviewed V2 client status.
- `Duplicate Sites`: duplicate Site ID rows that need one keep/skip-style decision per row.
- `Status Defaults`: selected sample sites whose raw status defaulted to active for validation only.
- `Instructions`: short review checklist.

Bryce should fill:

- `manual_client_external_id` only when the correct client is known.
- `manual_status` only with a reviewed site status: `active`, `inactive`, `on_hold`, or `archived`.
- `suggested_status` only with a reviewed client status: `active`, `inactive`, `prospect`, or `archived`.
- `review_status` with `approved`, `skip`, `needs_source_fix`, or `needs_followup`.
- `keep_or_skip` with `keep`, `skip`, `needs_source_fix`, or `needs_followup` as a review note. Before running the applier, every duplicate row must still resolve to an applier-safe decision.
- `notes` when the decision needs context.

Review steps:

1. Review `Unresolved Sites`.
2. Fill `manual_client_external_id` only when you know the correct client.
3. Set `review_status` to `approved` only when the row is safe.
4. Use `skip` for rows that should not import.
5. Use `needs_source_fix` for bad source data.
6. Use `needs_followup` if Bryce/Tom needs to decide.
7. Review `Client Status Review` and set `suggested_status`.
8. Review `Duplicate Sites` and mark keep/skip decisions.
9. Review `Status Defaults` and approve or set `manual_status`.
10. Save the workbook.
11. Use the Apply Reviewed Workbook helper to export the workbook decisions back to private review CSVs.
12. Do not import from this workbook directly.

After workbook review, run the Apply Reviewed Workbook helper. It updates the private review CSVs, generates the reviewed private sample, and validates it without importing anything.

## 12. Apply Reviewed Workbook

Fill the workbook first, then save it.

From the repo root:

```powershell
cd C:\Users\brolf\Desktop\Stormwater_APP_Clean\stormwater-v2
.\scripts\apply-monday-review-workbook.ps1
```

The helper:

- reads `import_validation_reports/monday_review_pack/monday_mapping_review.xlsx`;
- writes the reviewed tabs back to the private review CSVs in `import_validation_reports/monday_review_pack/`;
- runs the reviewed mapping applier against explicit approved rows only;
- validates `docs/import_templates/v2/private/clients_reviewed_sample.csv` and `docs/import_templates/v2/private/sites_reviewed_sample.csv`;
- prints `READY` or `NOT READY` with paths to the private outputs and validation reports.

No import occurs. The helper does not write the database, run migrations, run the V1 apply path, stage git files, or call Outlook, Gmail, Google Drive, or OpenAI.

Private files remain ignored:

- the workbook,
- review CSVs under `import_validation_reports/monday_review_pack/`,
- reviewed sample CSVs under `docs/import_templates/v2/private/`,
- validation reports under `import_validation_reports/reviewed_sample/`.

If the helper prints `READY`, the next step is a larger reviewed private sample validation. Do not proceed to mass import.

## 13. How to apply Bryce-reviewed mappings

The reviewed mapping applier reads only the private review CSVs and private Monday exports, then writes a new private Clients/Sites validation sample. It still does not import data, write the database, run migrations, run the V1 apply path, or call Outlook, Gmail, Google Drive, or OpenAI.

Accepted `review_status` values:

- `approved`: Bryce reviewed the row and the required manual fields are ready to apply.
- `skip`: intentionally exclude this row from the reviewed sample.
- `needs_source_fix`: exclude this row until Monday/source data is corrected and the review pack is regenerated.
- `needs_followup`: exclude this row until Bryce resolves the open question.
- blank: treated as not approved and skipped.

Blank `review_status` is never treated as approval.

Bryce should fill the review CSVs this way:

- `unresolved_sites_review.csv`: use `review_status=approved` only when the site should be sampled and `manual_client_external_id` is filled with the reviewed V2 client external ID. If the raw site status is blank or unknown, also fill `manual_status`.
- `client_status_review.csv`: use `review_status=approved` only when `suggested_status` is filled with `active`, `inactive`, `prospect`, or `archived`.
- `status_defaults_review.csv`: use `review_status=approved` only when `manual_status` is filled with `active`, `inactive`, `on_hold`, or `archived`.
- `duplicate_sites_review.csv`: fill `keep_or_skip` with `keep`, `skip`, or `needs_source_fix`. Use at most one `keep` per duplicate group. A kept duplicate row must also have an approved row in `unresolved_sites_review.csv`.

Generate the reviewed private sample from the repo root:

```powershell
.\apps\api\.venv\Scripts\python apps\api\scripts\prepare_monday_tiny_sample.py `
  --apply-reviewed-mappings `
  --review-pack-dir "import_validation_reports\monday_review_pack" `
  --output-clients "docs\import_templates\v2\private\clients_reviewed_sample.csv" `
  --output-sites "docs\import_templates\v2\private\sites_reviewed_sample.csv"
```

Optional caps for a smaller reviewed pass:

```powershell
  --max-clients 25 `
  --max-sites 75
```

The applier automatically validates the generated reviewed sample and writes private reports under:

```text
import_validation_reports/reviewed_sample/
```

Reviewed sample stop conditions:

- Any required review CSV is missing.
- Any required review column is missing.
- An approved unresolved site lacks `manual_client_external_id`.
- An approved unknown/defaulted site status lacks `manual_status`.
- An approved client status lacks `suggested_status`.
- A duplicate row lacks a clear `keep`, `skip`, or `needs_source_fix` decision.
- A duplicate group has more than one `keep`.
- A kept duplicate row lacks a matching approved unresolved-site review row.
- A reviewed site references a client that cannot be written to the output Clients CSV.
- The reviewed output would contain zero clients or zero sites.
- The generated reviewed sample fails template validation.

If the console says `READY`, the reviewed Clients/Sites CSVs are internally valid for continued validation work only. If it says `NOT READY`, fix the review CSVs or source exports and rerun the applier. In both cases, this is still not an import.

Do not commit:

- `docs/import_templates/v2/private/clients_reviewed_sample.csv`
- `docs/import_templates/v2/private/sites_reviewed_sample.csv`
- anything under `import_validation_reports/reviewed_sample/`

## 14. How to read validator results

Start with the console summary:

- `Ready: YES` means the tiny sample passed validation. It still has not been imported.
- `Ready: NO` means one or more stop conditions must be fixed before continuing.
- `Total rows` is the combined client and site row count.
- `Valid rows` and `Invalid rows` show whether specific rows need cleanup.
- `Duplicate rows` points to repeated external IDs.
- `Unresolved references` points to sites that reference missing clients.
- `Reports` gives the ignored JSON and Markdown report paths.

Open the Markdown report for exact row numbers and field-level messages.

## 15. Stop conditions

Stop and fix the private CSVs when any of these appear:

- A required column is missing.
- A required field is blank.
- A client row is missing `source_system` or `client_external_id`.
- A site row is missing `source_system`, `site_external_id`, or `client_external_id`.
- A site row references a `client_external_id` that is not in the client sample.
- A client has a duplicate `client_external_id`.
- A site has a duplicate `site_external_id`.
- A status value is not in the allowed list.
- A URL is not an `http` or `https` URL.
- Any private or generated file appears in `git status --short`.

No orphan Sites. No weak Client mapping. No blind import.

## 16. What files must never be committed

Never commit:

- `docs/import_templates/v2/private/`
- `docs/import_templates/v2/filled/`
- `apps/api/import_data/`
- `import_validation_reports/`
- real CSV or XLSX files
- files named like `*_real_import*.csv`
- files named like `*_real_import*.xlsx`
- files named like `*_private*.csv`
- files named like `*_private*.xlsx`
- `.env`
- `.env.local`
- local `*.db` files

The committed templates are safe. Private copies and reports are not.

## 17. Next step after clean validation

After a clean tiny validation:

1. Keep the private CSVs local and ignored.
2. Save or share only the high-level validation summary, not private row contents.
3. Do not import anything yet.
4. Use the clean result to design the next reviewed import step, such as a read-only Import Center preview.
