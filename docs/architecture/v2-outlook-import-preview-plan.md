# V2 Outlook Import Preview Plan

## Scope

The Outlook import phase is a bounded Work Hub MVP. It lets an operator check Microsoft Graph configuration, preview a capped set of Outlook messages from an explicit request, and import selected preview rows into local `email_messages`.

## Current Behavior

- Outlook entry point: `/work` only.
- API endpoints:
  - `GET /v1/outlook/status`
  - `POST /v1/outlook/preview`
  - `POST /v1/outlook/import-selected`
- Preview inputs: `organization_id`, optional search query, optional folder ID, optional date range, limit default `25` and capped at `100`, and a request-supplied MVP access token.
- Preview writes no local database rows.
- Import-selected creates an `email_import_batches` row and local `email_messages` rows only for selected preview messages.
- Deduplication skips existing messages by Outlook `provider_message_id` and `internet_message_id`.
- Attachment payloads are metadata-only; attachments are not downloaded.

## Configuration

Optional API env vars:

```text
MICROSOFT_TENANT_ID=<tenant id>
MICROSOFT_CLIENT_ID=<app client id>
MICROSOFT_CLIENT_SECRET=<app client secret>
MICROSOFT_REDIRECT_URI=http://localhost:8000/v1/outlook/oauth/callback
MICROSOFT_GRAPH_BASE_URL=https://graph.microsoft.com/v1.0
```

These are not required for normal API startup, CRM routes, or tests. Missing values make Outlook preview/import endpoints return a clear configuration error. Status never returns secrets.

## Explicit Non-Goals

- No background mailbox sync.
- No page-load polling.
- No automatic import.
- No Gmail.
- No email sending.
- No Outlook draft creation.
- No attachment download.
- No OneDrive or SharePoint scan.
- No AI generation.
- No report or photosheet generation.

## Test Strategy

Tests mock Microsoft Graph. They validate status reporting, missing configuration errors, required request fields, limit caps, Graph message normalization, batch creation, message creation, provider ID dedupe, internet message ID dedupe, empty import handling, no attachment download, and no import-time Graph call.

## Future Phases

1. OAuth UI and token storage.
2. Delta query for controlled sync windows.
3. Microsoft Graph change notifications.
4. Push approved local AI drafts to Outlook drafts.
