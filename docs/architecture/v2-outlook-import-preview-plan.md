# V2 Outlook OAuth, Import Preview, And Draft Push Plan

## Scope

The Outlook phase is a bounded Work Hub MVP. It lets an operator connect Outlook through Microsoft OAuth, preview a capped set of messages from an explicit request, import selected preview rows into local `email_messages`, and push reviewed local email-style `ai_drafts` into Outlook Drafts.

## Current Behavior

- Outlook entry point: `/work` only.
- Auth/status API endpoints:
  - `GET /v1/outlook/status`
  - `GET /v1/outlook/auth/status?organization_id=`
  - `GET /v1/outlook/auth/start?organization_id=`
  - `GET /v1/outlook/auth/callback?code=&state=`
  - `POST /v1/outlook/auth/disconnect`
- Import API endpoints:
  - `POST /v1/outlook/preview`
  - `POST /v1/outlook/import-selected`
- Draft push API endpoint:
  - `POST /v1/outlook/drafts/from-ai-draft`
- Microsoft OAuth requests only delegated `offline_access`, `User.Read`, and `Mail.ReadWrite`.
- OAuth state is signed and expires quickly. It is stateless for the local MVP; replay protection beyond expiry is deferred.
- Active connection rows live in `outlook_connections`.
- Access and refresh token values are stored server-side only and are never returned by API responses.
- Preview inputs: `organization_id`, optional search query, optional folder ID, optional date range, limit default `25` and capped at `100`.
- Preview uses the stored Outlook connection token when present. A request-supplied access token remains accepted for local development/tests.
- Preview writes no local database rows.
- Import-selected requires an explicit button click, uses the selected preview payload, creates an `email_import_batches` row, and creates local `email_messages` rows only for selected preview messages.
- Deduplication skips existing messages by Outlook `provider_message_id` and `internet_message_id`.
- Attachment payloads are metadata-only; attachments are not downloaded.
- Draft push requires a stored Outlook OAuth connection, an email-style AI draft, To recipients, a subject, and usable body text.
- Draft push creates a message draft with Microsoft Graph `/me/messages`; it does not call `sendMail` or `/send`.
- Draft push saves provider metadata on the local `ai_drafts` row: provider, draft id, web link, status, pushed timestamp, and any provider error.
- Users must review and send the message manually in Outlook.
- Provider readiness is surfaced through `GET /v1/integrations/status`, with optional `organization_id` for Work Hub connection state.
- Imported/local messages can be used by the Smart Hub AI assistant after they become local `email_messages`.

## Microsoft App Registration

Register an app in Microsoft Entra ID:

- Redirect URI: `http://localhost:8000/v1/outlook/auth/callback` for local development.
- Client type: web application.
- Delegated Graph permissions:
  - `offline_access`
  - `User.Read`
  - `Mail.ReadWrite`
- Do not grant or request `Mail.Send`, calendar scopes, OneDrive, SharePoint, or Files scopes for this MVP.
- Create a client secret and put it only in `apps/api/.env`.

## Configuration

Optional API env vars:

```text
MICROSOFT_TENANT_ID=<tenant id>
MICROSOFT_CLIENT_ID=<app client id>
MICROSOFT_CLIENT_SECRET=<app client secret>
MICROSOFT_REDIRECT_URI=http://localhost:8000/v1/outlook/auth/callback
MICROSOFT_GRAPH_BASE_URL=https://graph.microsoft.com/v1.0
TOKEN_ENCRYPTION_KEY=<optional strong local token protection key>
```

These are not required for normal API startup, CRM routes, or tests. Missing values make Outlook auth/import endpoints return a clear configuration error. Status never returns secrets.

## Token Storage

The token storage service is intentionally backend-only:

- With `TOKEN_ENCRYPTION_KEY` and `cryptography` available, token values are stored with Fernet encryption.
- With `TOKEN_ENCRYPTION_KEY` but no `cryptography`, token values use the local keyed protection fallback so the abstraction remains ready for stronger production storage.
- Without `TOKEN_ENCRYPTION_KEY`, local development uses server-side obfuscation. This keeps tokens out of the frontend and localStorage, but it is not production encryption.

Production hardening should use a managed secret store, key rotation, and stricter OAuth state replay protection.

## Explicit Non-Goals

- No background mailbox sync.
- No page-load polling.
- No automatic import.
- No full mailbox import.
- No Gmail.
- No email sending.
- No automatic Outlook draft creation.
- No attachment download.
- No OneDrive or SharePoint scan.
- No Outlook-side AI generation or automatic intelligence run during import.
- No report or photosheet generation.

## Test Strategy

Tests mock Microsoft OAuth and Graph. They validate disconnected status, missing config, auth URL scopes without `Mail.Send`, callback token storage, token secrecy in responses, disconnect token clearing, stored-token preview, refresh-token preview, limit caps, Graph message normalization, batch creation, message creation, provider ID dedupe, internet message ID dedupe, empty import handling, no attachment download, no import-time Graph call, reviewed draft push validation, Graph `/me/messages` draft creation, provider metadata persistence, and no `sendMail` or `/send` calls.

## Future Phases

1. Push revisions to an existing provider draft.
2. Explicit reviewed send flow.
3. Sync sent state back to local CRM timeline.
4. Delta query for controlled sync windows.
5. Microsoft Graph change notifications.
6. Shared mailbox selection.
