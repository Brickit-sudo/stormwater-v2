# V2 CRM Timeline Foundation

## Scope

The CRM timeline is a read-only activity view for one selected Client, Site, or Job. It is built from local database records only and is intended to give operators quick context without starting provider syncs or changing CRM data.

## Current Behavior

- `GET /v1/timeline` accepts `organization_id` plus exactly one of `client_id`, `site_id`, or `job_id`.
- `limit` defaults to 50 and is capped at 200.
- The endpoint verifies organization scope for the selected record.
- Source queries are bounded and run only after a record is selected.
- Results are normalized into a single newest-first list.

## Included Sources

- Jobs related to a selected Client or Site.
- Reminders linked directly or through related Jobs/Sites.
- Evidence files linked directly or through related Jobs/Sites.
- Local email messages linked to the selected record.
- Email record links and their local message metadata.
- AI drafts linked to the record or to a related local email.
- Outlook draft push metadata stored on AI drafts.
- Email import batches related through local email messages.
- Selected record created/updated events when there is other timeline activity.

## Guardrails

- No Outlook, Gmail, Google Drive, or OpenAI provider calls.
- No background sync.
- No mutation actions from the timeline.
- No report generation.
- No fake timeline actions or placeholder buttons.

## Future Direction

- Add first-class `activity_log` events for status changes and audit history.
- Add richer filters by source type and date range.
- Add timeline entries for explicit status transitions once those events are recorded.
- Add compact cross-record rollups for reporting readiness.
