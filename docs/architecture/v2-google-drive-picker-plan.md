# V2 Google Drive Picker Foundation

## Purpose

This phase adds manual Google Drive Picker selection to the V2 file metadata workflow.
It lets a user choose a Drive file and save the returned metadata as an `evidence_files`
row linked to exactly one Client, Site, or Job.

## Scope

Included:

- Config/status reporting for Google Drive Picker readiness.
- A lazily loaded browser Picker button in the CRM Drive/File panel.
- A lazily loaded browser Picker button in Work Hub Files after a target record is selected.
- Metadata-only saves through the existing `POST /v1/files` endpoint.
- Open-file links when Google returns a URL.
- Metadata preview in Work Hub Files.

Not included:

- Drive folder crawling.
- Background Drive sync.
- Downloading file contents.
- Uploading files.
- OCR.
- AI file analysis.
- Report generation from files.
- Folder creation.
- Broad Drive access.

## Configuration

API readiness uses optional local env vars:

```text
GOOGLE_CLIENT_ID=
GOOGLE_API_KEY=
```

`GOOGLE_DRIVE_PICKER_ENABLED` is derived from those values in application
settings; it is not a separate required env var.

Frontend Picker UI uses browser-safe public env vars:

```text
NEXT_PUBLIC_GOOGLE_CLIENT_ID=
NEXT_PUBLIC_GOOGLE_API_KEY=
NEXT_PUBLIC_GOOGLE_APP_ID=
```

Leave these blank to run the app normally. The UI then shows a configure state and
the existing Add File Link workflow remains available.

Real keys should be restricted in Google Cloud by HTTP referrer and API usage.
No private client secret is used or exposed in the frontend.

## Picker Behavior

The Picker code is not loaded globally. It is split into the file picker component
and only injects Google scripts after the user clicks Select from Google Drive.

When configured, the browser flow:

1. Loads `https://apis.google.com/js/api.js` and `https://accounts.google.com/gsi/client`.
2. Requests a user token with the narrow scope `https://www.googleapis.com/auth/drive.file`.
3. Opens Google Picker.
4. Reads the selected file metadata from the Picker callback.
5. Calls the existing V2 API to save metadata.

No backend Google Drive API call is made in this phase.

## Saved Metadata

Picker selections create `evidence_files` rows with:

- `source = "google_drive"`
- `file_name` from the Picker file name
- `mime_type` from the Picker MIME type when available
- `drive_file_id` from the Picker file id
- `public_url` from the Picker URL when available
- exactly one of `client_id`, `site_id`, or `job_id`

Icon and thumbnail URLs may be returned by the browser component, but they are
not persisted because the current metadata model does not have stable fields for
them.

## Product Rule

Picker/manual selection comes before sync. A user chooses the file and chooses
the CRM parent. Future Drive sync must build on this reviewed metadata pattern
instead of crawling folders first.

## Deferred Work

Future phases can add:

- Google OAuth connection records and token storage.
- Per-user or per-organization Drive connection strategy.
- Folder picker and folder metadata validation.
- Bounded sync for explicitly connected folders.
- File content download, OCR, and AI analysis after explicit product approval.

Those future actions should stay absent from the UI until they are implemented.
