# V2 Work Hub Email Intelligence Foundation

## Scope

This phase adds a local, providerless Work Hub at `/work`.

It gives Sterling a fast place to review file links, local email records, manual AI draft storage, and local email import batch metadata before Outlook import is connected.

## What Exists Now

- `/work` route with Files, Emails, AI Drafts, and Import Batches views.
- Local email tables: `email_import_batches`, `email_messages`, `email_record_links`, and `ai_drafts`.
- API routes under `/v1` for email messages, record links, AI drafts, and import batches.
- Seeded stormwater examples: 1 local Outlook-style import batch, 5 local email message records, 3 manual AI drafts, and 3 email-to-record links.
- Email preview pane loads the selected email record by id.
- Email list is paginated and filtered through the API.
- Drafts are manual storage only and can be created, edited, reviewed, used, and archived.

## Explicit Non-Goals

This phase does not add Outlook OAuth, Microsoft Graph calls, Gmail, email sending, Outlook draft creation, mailbox scanning, background sync, polling, attachment downloads, Drive folder scanning, AI generation, or report/photosheet generation.

No visible Work Hub control should imply any of those capabilities.

## Speed Boundaries

- Work Hub data loads only on `/work`.
- CRM pages do not import Work Hub components or fetch email records.
- No Work Hub data is loaded in `layout.tsx`, `AppShell`, `Sidebar`, or `Topbar`.
- The email list uses `limit` and `offset`.
- The selected email preview calls `GET /v1/email-messages/{id}`.
- Files view reuses existing `evidence_files` metadata.

## Future Outlook Import Preview

The next phase should add an Outlook import preview, still without importing an entire mailbox by default.

Recommended shape:

- Add Microsoft account connection and token storage only after auth/org scoping is ready.
- Use Microsoft Graph to preview a bounded folder/search/date range.
- Store preview counts in `email_import_batches`.
- Import only selected messages or a bounded result set.
- Dedupe by `provider_message_id`.
- Keep attachment metadata separate from attachment downloads.
- Do not send email or create Outlook drafts from this flow.
