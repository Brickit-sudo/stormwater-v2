# V2 Scheduling And Reminders

## What Shipped

V2 now has a local-only reminders foundation for operational follow-up. Reminders can be linked to exactly one Client, Site, or Job, then managed from `/schedule`. Job-linked reminders also appear in a compact panel on the Jobs detail view.

The first UI is a fast list view grouped into Overdue, Today, Upcoming, and Completed. A calendar grid is intentionally deferred until the local reminder workflow is proven.

## Local-Only Scope

Reminders live only in the V2 database. This phase does not implement Outlook, Gmail, Google Calendar, Microsoft Graph, email sending, external calendar event creation, push notifications, or AI follow-up drafting.

The visible actions are real local actions:

- New Reminder
- Edit Reminder on `/schedule`
- Mark Complete
- Archive
- Add Reminder for this Job from the Jobs detail panel
- Filter reminders

## Data Rules

Each reminder belongs to one organization and must link to exactly one target:

- `client_id`
- `site_id`
- `job_id`

Statuses are `open`, `snoozed`, `completed`, and `archived`. Priorities are `low`, `medium`, and `high`.

Normal reminder lists exclude archived records. Completed reminders remain listable and are shown in their own group. Delete is a soft archive that sets `status=archived` and `archived_at`.

## API

The API surface is:

- `GET /v1/reminders`
- `POST /v1/reminders`
- `GET /v1/reminders/{reminder_id}`
- `PATCH /v1/reminders/{reminder_id}`
- `DELETE /v1/reminders/{reminder_id}`

List filters support `organization_id`, `status`, `priority`, `client_id`, `site_id`, `job_id`, `due_before`, `due_after`, `limit`, and `offset`.

## Future Integration Path

The intended path is:

1. Local reminder list and job-linked follow-ups.
2. Local scheduling model refinements if needed.
3. Calendar export or ICS if the team wants a simple handoff first.
4. Outlook/Gmail/Calendar provider schemas and OAuth.
5. Push/sync jobs after conflict behavior is explicit.

External sync is deferred because reminders need to be useful and reviewable locally before V2 creates events or sends messages outside the app.
