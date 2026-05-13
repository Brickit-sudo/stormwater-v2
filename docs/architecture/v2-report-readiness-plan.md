# V2 Job Report Readiness Checklist

## Purpose

The Job Report Readiness Checklist helps a user select a V2 job and quickly see whether the local CRM record is ready for report work. It is guidance only, not compliance certification.

This phase is intentionally read-only. It does not generate reports, photosheets, PDFs, DOCX files, final report text, or client deliverables.

## Boundaries

- No DOCX or PDF generation.
- No final report claims.
- No report builder, photosheet builder, DOCX layout, or V1 Streamlit changes.
- No Outlook, Gmail, Google Drive, or OpenAI provider calls.
- No Drive folder scans, file picker, sync, or background jobs.
- No AI final report generation.
- No mutation actions from the readiness panel.

## Local Checks

The backend endpoint `GET /v1/jobs/{job_id}/report-readiness` reads bounded local V2 database records only.

Required checks:

- Client linked.
- Site linked.
- Service type present.
- Usable job status.
- Scheduled date or due date present where applicable.

Supporting checks:

- Scope or notes.
- Linked evidence/file metadata.
- Stored Drive folder URL or linked file records.
- Job reminders and blockers.
- Relevant AI drafts.
- Local linked email context.
- Local timeline activity from existing CRM tables.

## Status Logic

`Ready` means required checks pass, no high-severity blockers exist, no high-priority overdue open job reminders exist, and supporting evidence is present enough to start report work.

`Needs Attention` means no hard blocker exists, but warnings remain. Missing optional email context, missing AI draft context, missing scope/notes, sparse timeline activity, missing evidence, or missing Drive folder context can all warn without blocking.

`Blocked` means report work would be unsafe or unusable because the job is archived, cancelled, missing a usable client/site link, or has a high-priority overdue open job reminder.

## Future Bridge

This checklist prepares the CRM for future report engine extraction by making missing local inputs visible before any generation path exists. Later work can use these readiness signals to decide when a job snapshot is complete enough to pass into a dedicated report engine.
