# V2 Smart Hub AI Intelligence Foundation

## Scope

This phase makes local Work Hub email and file records useful immediately while keeping external integrations bounded and review-first.

The implementation is local-first:

- Provider readiness is exposed at `GET /v1/integrations/status`.
- AI readiness is exposed at `GET /v1/ai/status`.
- Email intelligence actions operate on local `email_messages`.
- File link candidates are extracted from local email text and saved only after user review.
- Suggested reminders are created only after user review.
- AI outputs can be saved as `ai_drafts`.

## What Is Real Now

- `/work` shows provider readiness cards for Outlook, Gmail, Google Drive, OneDrive, and AI.
- Outlook status reflects Microsoft Graph env readiness and Work Hub connection state. Outlook OAuth stores server-side token data, and preview/import-selected remains bounded, explicit, and config-gated.
- Gmail is marked deferred. Future sync should use push notifications, not polling.
- Google Drive reports Picker readiness from optional config. Picker selection
  is manual and metadata-only; full Drive sync/OAuth connection records remain
  deferred. OneDrive is still deferred for picker/OAuth paths.
- AI provider calls are config-gated behind `OPENAI_API_KEY`.
- Deterministic helpers work without API keys:
  - URL extraction from email/body text.
  - Google Drive, OneDrive, SharePoint, and generic URL classification.
  - keyword-based action item candidates.
  - exact-match Client/Site/Job suggestions.
- Email preview can:
  - summarize selected email.
  - extract action suggestions.
  - suggest local CRM links.
  - save detected links as `evidence_files` metadata.
  - create local reminders from selected action suggestions.
  - draft replies only when AI is configured.
- AI Drafts view can generate review-first report section, maintenance recommendation, and client-facing summary drafts when AI is configured.
- AI Drafts view can push reviewed email-style drafts to Outlook Drafts when Outlook is connected with Microsoft Graph `Mail.ReadWrite`. This creates a draft message only, stores provider draft metadata locally, and leaves review/send in Outlook. `Mail.Send` is not requested.

## Explicit Non-Goals

- No full Outlook sync.
- No automatic Outlook import.
- No Gmail sync.
- No mailbox polling.
- No import-all mailbox operation.
- No email sending.
- No automatic Outlook draft creation.
- No attachment download.
- No Drive, OneDrive, or SharePoint folder scanning.
- No file download, upload, OCR, or AI file analysis.
- No final report generation.
- No automatic CRM linking.
- No automatic reminder creation.

## API Surface

- `GET /v1/integrations/status`
- `GET /v1/ai/status`
- `POST /v1/ai/email-summary`
- `POST /v1/ai/email-action-items`
- `POST /v1/ai/extract-file-links`
- `POST /v1/ai/suggest-record-links`
- `POST /v1/ai/draft-reply`
- `POST /v1/ai/report-section-draft`
- `POST /v1/ai/maintenance-recommendation-draft`
- `POST /v1/ai/client-summary-draft`
- `POST /v1/outlook/drafts/from-ai-draft`

All POST routes require `organization_id`. Email routes may use `email_message_id`; report helpers can use manual `user_context`.

## Configuration

Optional API env vars:

```text
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
AI_FEATURES_ENABLED=
```

Leaving `OPENAI_API_KEY` blank disables provider-backed drafting. Deterministic extraction and suggestions still work.

Tests mock provider behavior and never require real OpenAI, Microsoft, or Google credentials.

## Speed Boundaries

- No email, AI, or provider data loads from CRM pages.
- Work Hub loads provider status, Outlook connection state, and local email intelligence only under `/work`.
- Google Picker scripts load only after a user clicks a picker button in a file-specific view.
- Heavy work happens only after explicit user actions.
- Deterministic link extraction runs against the selected local email and does not call external providers.
- Outlook draft creation happens only after an explicit Create Outlook Draft click and never calls `sendMail`.

## Future Recommended Build

Outlook-specific follow-ups are push revisions to an existing draft, explicit reviewed send, and sent-state sync.

After Outlook Draft Push is stable, build CRM Timeline Foundation so imported email, AI draft, Outlook draft, reminder, file, and job events can be scanned from one place.
