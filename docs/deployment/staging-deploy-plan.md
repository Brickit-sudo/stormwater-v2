# V2 Staging Deploy Plan

This document describes the path from local demo to 24/7 hosted staging. It does not authorize real production data, real imports, or production use before auth and access control exist.

## Local Demo vs 24/7 Hosting

The local demo runs on Bryce's computer:

- Postgres runs in Docker Desktop.
- FastAPI and Next.js run in dev mode.
- URLs are local by default.
- The computer must stay on.
- It is for seed/demo data only.

24/7 hosted staging runs on internet-accessible infrastructure:

- Frontend and backend run as services.
- Postgres is persistent and backed up.
- HTTPS is managed.
- Env vars and secrets are managed outside git.
- OAuth callback URLs use the staging domain.
- Access is gated before real client data appears.

## Recommended Hosting Options

### 1. Vercel Frontend + Render/Railway/Fly Backend + Managed Postgres

Recommended immediate path.

This keeps the Next.js frontend on a platform built for Next while the FastAPI backend and Postgres live on services that support long-running API processes and database backups. It is the clearest bridge from today's app shape to hosted staging without forcing a VPS too early.

Good fit when:

- The frontend should deploy from git with preview URLs.
- The backend needs a stable HTTPS API URL.
- Postgres backups should be managed.
- Bryce wants less server administration.

### 2. Single VPS With Docker Compose

Good later option when everything should run on one server. This would use Docker Compose for Postgres, API, and web behind a reverse proxy such as Caddy, Traefik, or Nginx.

Good fit when:

- One monthly server bill is preferred.
- Someone is comfortable patching the server.
- Backups, firewall, monitoring, and deploy scripts are owned by the team.

This repo does not currently include API/web Dockerfiles, so Compose is documented as a later step rather than added to the local demo launcher.

### 3. All-In-One Render/Railway

Good for a fast staging proof where frontend, backend, and Postgres are all managed in one place.

Good fit when:

- Simplicity matters more than platform specialization.
- The staging database can be created and backed up on the same provider.
- The team accepts provider-specific service limits.

## Recommended Immediate Staging Path

Use option 1:

- Frontend: Vercel
- Backend: Render, Railway, or Fly
- Database: managed Postgres from the backend provider or a dedicated managed Postgres provider

Reason: it matches the current Next/FastAPI split, gives stable HTTPS URLs, avoids hand-managed server operations, and keeps the database in managed infrastructure with backups.

## Environment Variables

Backend service:

```text
APP_NAME=Stormwater V2 API
ENVIRONMENT=staging
DATABASE_URL=<managed postgres url>
CORS_ORIGINS=https://<staging-web-domain>
MICROSOFT_TENANT_ID=<tenant id>
MICROSOFT_CLIENT_ID=<app client id>
MICROSOFT_CLIENT_SECRET=<app client secret>
MICROSOFT_REDIRECT_URI=https://<staging-api-domain>/v1/outlook/auth/callback
MICROSOFT_GRAPH_BASE_URL=https://graph.microsoft.com/v1.0
TOKEN_ENCRYPTION_KEY=<strong secret>
OPENAI_API_KEY=<optional, only when AI provider calls are approved>
OPENAI_MODEL=gpt-4.1-mini
AI_FEATURES_ENABLED=<true/false>
GOOGLE_CLIENT_ID=<optional picker client id>
GOOGLE_API_KEY=<optional picker api key>
```

Frontend service:

```text
NEXT_PUBLIC_API_BASE_URL=https://<staging-api-domain>
NEXT_PUBLIC_DEMO_ORG_ID=<temporary demo org id only until auth replaces it>
NEXT_PUBLIC_GOOGLE_CLIENT_ID=<optional browser-safe picker client id>
NEXT_PUBLIC_GOOGLE_API_KEY=<optional restricted browser key>
NEXT_PUBLIC_GOOGLE_APP_ID=<optional Google app id>
```

Do not commit env files. Secrets belong in the hosting provider's secret manager.

## Database Requirements

Before staging contains anything important:

- Use managed Postgres or a server with persistent storage.
- Run Alembic migrations as a deploy step.
- Enable automatic backups.
- Confirm restore steps before relying on staging.
- Keep a manual backup before any risky migration or import rehearsal.

Local Docker Postgres is fine for demos, but not for 24/7 staging.

## HTTPS and Domains

Staging needs HTTPS for the web app and API.

Set:

- `NEXT_PUBLIC_API_BASE_URL` to the HTTPS API URL.
- `CORS_ORIGINS` to the HTTPS web URL.
- Microsoft OAuth redirect URI to the HTTPS API callback URL.
- Google OAuth/Picker origins and callback settings to the staging web/API domains when those flows are enabled.

Provider callback URLs must exactly match the values registered with Microsoft/Google.

## Auth and Real Data Gate

No real client data should go online until V2 has:

- Login/authentication.
- Organization membership and role checks.
- Server-side organization scoping based on the logged-in user.
- Protected API routes instead of demo `organization_id` trust.
- Session/token security reviewed for the chosen hosting model.

The current `NEXT_PUBLIC_DEMO_ORG_ID` bridge is acceptable for local seed demos and internal fake-data staging only. It is not access control.

## Import Readiness Gate

The import contract, templates, and validator are readiness tools:

- Contract: `docs/architecture/v2-database-import-contract.md`
- Templates: `docs/import_templates/v2/`
- Validator: `apps/api/scripts/validate_import_templates.py`

Before real import work:

- Keep real source files in ignored private paths.
- Validate private copies locally.
- Resolve duplicate, invalid, and unmatched rows.
- Do not run a V1 apply migration.
- Do not call Outlook, Gmail, Drive, or OpenAI during validation.
- Do not write real CRM rows until an reviewed import center/apply workflow exists.

## Deployment Checklist

- Pick hosting option and staging domain names.
- Create managed Postgres.
- Configure backend env vars in the host.
- Configure frontend env vars in the host.
- Run `alembic upgrade head` against staging.
- Seed fake/demo staging data only.
- Deploy backend and verify `/health`.
- Deploy frontend and verify it reaches the staging API.
- Configure HTTPS.
- Configure CORS.
- Configure Microsoft/Google callback URLs only when testing those providers.
- Confirm logs do not print secrets.
- Confirm backups and restore notes exist.
- Add auth before real client data.

## Rollback and Backup Expectations

Minimum rollback plan:

- Keep the previous deploy available through the hosting provider.
- Record the commit deployed to staging.
- Take a database backup before migrations that change data.
- Know how to restore the latest backup into a new database.
- Keep env var changes documented outside git in a secure internal location.

Rollback should be boring: redeploy the previous commit, point to a known-good database backup if needed, and verify `/health` plus the main CRM routes.
