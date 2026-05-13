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
- Google Drive and OneDrive are marked deferred for picker/OAuth paths.
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

## Explicit Non-Goals

- No full Outlook sync.
- No automatic Outlook import.
- No Gmail sync.
- No mailbox polling.
- No import-all mailbox operation.
- No email sending.
- No Outlook draft creation.
- No attachment download.
- No Drive, OneDrive, or SharePoint folder scanning.
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
- Heavy work happens only after explicit user actions.
- Deterministic link extraction runs against the selected local email and does not call external providers.

## Future Recommended Build

After Outlook OAuth is stable, build Push approved AI drafts to Outlook Drafts. Keep it review-first and do not send email automatically.
