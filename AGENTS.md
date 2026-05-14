# AGENTS.md

This file provides guidance to Codex when working in the Stormwater V2 repository.

## Repository Scope

This nested repo is the authoritative repo for Stormwater V2 work. The parent
`Stormwater_APP_Clean` directory may also be a Git repo; do not assume commits
made there apply here. Run Git commands from this repo root unless intentionally
checking the parent workspace.

Stormwater V2 is the clean rewrite around the CRM as the source of truth:

Clients -> Sites -> Jobs / Visits -> BMP Systems -> Observations -> Photos /
Files -> Reports / Quotes / Invoices.

## Running The App

From the V2 repo root:

```powershell
# One-command local demo
.\scripts\start-v2-demo.ps1 -Seed

# Fresh deterministic seed reset
.\scripts\start-v2-demo.ps1 -ResetSeed

# Check or stop the demo
.\scripts\status-v2-demo.ps1
.\scripts\stop-v2-demo.ps1
```

API commands:

```powershell
cd apps\api
.\.venv\Scripts\python -m uvicorn app.main:app --reload
.\.venv\Scripts\python -m compileall app scripts tests
.\.venv\Scripts\python -m pytest -q
.\.venv\Scripts\python -m alembic heads
```

Web commands:

```powershell
cd apps\web
npm run dev
npm run lint
npm run build
```

`apps\web\AGENTS.md` contains additional Next.js guidance and applies inside
that subtree.

## Repository Safety Rules

- Keep changes small, focused, and easy to review.
- Preserve existing stormwater report formatting, terminology, and professional tone.
- Preserve CRM import/export behavior unless the task explicitly asks to change it.
- Do not edit `.env`, local database files, generated exports, generated import
  reports, image caches, or large binary files unless Bryce explicitly asks.
- Do not store private auth material, private client data, or private service
  configuration in repo files.
- Do not add brokerage, trading, or live-trading API integrations.
- Always run relevant tests after code changes. If no targeted automated test
  exists for the touched area, say that clearly.
- For UI changes, inspect the actual page in a browser when possible.
- For database changes, check migrations, backwards compatibility, and
  seed/import assumptions.
- For export, report, or photo handling changes, check generated artifact logic
  and layout assumptions.
- Be extra careful with Windows paths, PowerShell quoting, and UTF-8 encoding.

## V2 Product Boundaries

- Work Hub is local-first unless a task explicitly changes that boundary.
- Outlook integration keeps provider auth material server-side only; the
  frontend must not read it.
- Outlook draft support creates reviewed drafts only. Do not add a send button
  or request broader mail permissions without explicit direction.
- Google Drive Picker and file links are metadata-only in the current V2 scope.
  Do not add folder crawling, downloads, uploads, OCR, AI file analysis, report
  generation, or broad sync behavior unless explicitly requested.
- Search should remain bounded to local V2 CRM records unless the task explicitly
  asks for external provider search.
