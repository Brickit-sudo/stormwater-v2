# V2 Import Templates

These CSVs are fake, commit-safe templates for dry-run validation only. They contain no real clients, sites, jobs, addresses, documents, emails, Drive IDs, or private data.

Use them as headers and examples, then create private working copies under an ignored path such as `docs/import_templates/v2/private/` or `docs/import_templates/v2/filled/`.

For the first tiny real Clients/Sites sample, follow [tiny-real-sample-workflow.md](tiny-real-sample-workflow.md). Start with 3 to 5 clients and 5 to 10 sites, validate only, and do not import anything.

## Files

- `clients_template.csv`: canonical client rows plus alias hints.
- `contacts_template.csv`: contacts linked to a client and optionally a site.
- `sites_template.csv`: canonical sites that must resolve to clients.
- `jobs_template.csv`: jobs that must resolve to sites and matching clients.
- `documents_template.csv`: metadata-only file/Drive links with exactly one parent.
- `emails_template.csv`: local email metadata, either linked or explicitly unlinked for review.

## Required Safety

- Keep real CSV/XLSX files private and ignored.
- Use `example.com` email addresses in examples and tests.
- Do not paste real addresses into committed templates.
- Do not run a real import from these files.
- Run `scripts/validate-v2-import-sample.ps1` for the tiny private Clients/Sites sample.
- Run `apps/api/scripts/validate_import_templates.py` before any future import-center work.
- Keep generated reports under ignored `import_validation_reports/`.
