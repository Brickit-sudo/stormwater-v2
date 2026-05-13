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

## 9. How to read validator results

Start with the console summary:

- `Ready: YES` means the tiny sample passed validation. It still has not been imported.
- `Ready: NO` means one or more stop conditions must be fixed before continuing.
- `Total rows` is the combined client and site row count.
- `Valid rows` and `Invalid rows` show whether specific rows need cleanup.
- `Duplicate rows` points to repeated external IDs.
- `Unresolved references` points to sites that reference missing clients.
- `Reports` gives the ignored JSON and Markdown report paths.

Open the Markdown report for exact row numbers and field-level messages.

## 10. Stop conditions

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

## 11. What files must never be committed

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

## 12. Next step after clean validation

After a clean tiny validation:

1. Keep the private CSVs local and ignored.
2. Save or share only the high-level validation summary, not private row contents.
3. Do not import anything yet.
4. Use the clean result to design the next reviewed import step, such as a read-only Import Center preview.

