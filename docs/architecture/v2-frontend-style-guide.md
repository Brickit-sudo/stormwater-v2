# V2 Frontend Style Guide

## Visual Target

The Sterling Green Hub screenshots are the reference direction: a premium dark field-service dashboard with near-black depth, deep green and blue-teal panels, bright Sterling green accents, readable tables, and calm operational density.

## Design Principle

V2 should feel like a stormwater operations command center, not a generic admin template. Keep workflows simple like a spreadsheet, but style the surfaces like a professional SaaS product for field-service teams.

## Color Tokens

The source of truth is `apps/web/src/app/globals.css`.

| Token | Use |
| --- | --- |
| `--bg` | App background |
| `--bg-elevated` | Elevated page background |
| `--panel` | Primary cards, tables, panels |
| `--panel-2` | Secondary panels and input surfaces |
| `--panel-soft` | Disabled and subtle selected surfaces |
| `--border` | Standard borders |
| `--border-soft` | Internal dividers |
| `--text` | Primary text |
| `--text-secondary` | Body and metadata text |
| `--text-muted` | Labels, hints, empty states |
| `--green` | Primary action and active state |
| `--green-soft` | Active row and nav tint |
| `--yellow`, `--red`, `--blue` | Warning, danger, and info badges |

Use green only for primary actions, active navigation, selected rows, and success states.

## Typography

- Page titles: `text-2xl font-semibold tracking-tight`.
- Panel titles: `text-base font-semibold`.
- Body text: `text-sm text-text-secondary`.
- Labels: uppercase, small, muted, with generous tracking.
- Buttons and inputs: deliberate `text-sm`, never browser-default sizing.

## Sidebar

- Sidebar is fixed on desktop and uses the darkest surface.
- Brand appears at the top with the subtitle `Field Service Admin`.
- Navigation is limited to Clients, Sites, Jobs, Schedule, and Map.
- Active navigation uses `--green-soft`, green text, and a small green status dot.
- Do not add notification, profile, settings, or placeholder nav controls.

## Topbar

- Keep the topbar slim and informational.
- It may show the current section title and short subtitle.
- Do not add fake action buttons, fake profile menus, notification icons, or API-connected indicators.

## Cards And Panels

- Use `Card`, `DetailPanel`, or shared classes from `apps/web/src/lib/ui.ts`.
- Cards and panels use dark surfaces, 8px radius, subtle borders, and restrained shadow.
- Avoid stacking decorative cards inside cards. Use sub-panels only for real grouped metadata, forms, or repeated records.

## Tables

- Tables live in dark bordered panels.
- Headers are muted uppercase labels.
- Rows use comfortable spacing, hover state, and selected green left accent.
- Rows may be clickable only when selection is real.
- Empty and loading states must match the dark table surface.

## Detail Panels

- Detail panels sit to the right of CRM tables on wide screens.
- Selected record names are prominent in the panel header.
- Metadata should be grouped in compact dark sub-panels.
- Contextual actions belong in the header and must be real.
- Archive actions are visually secondary and use danger styling.

## Status Badges

Use `StatusBadge` for CRM statuses.

| Entity | Status | Tone |
| --- | --- | --- |
| Clients | active | success |
| Clients | inactive, archived | muted |
| Clients | prospect | info |
| Sites | active | success |
| Sites | inactive, archived | muted |
| Sites | on_hold | warning |
| Jobs | draft, archived | muted |
| Jobs | scheduled | info |
| Jobs | in_progress | success |
| Jobs | in_review | warning |
| Jobs | completed | success |
| Jobs | cancelled | danger |
| Reminders | open | info |
| Reminders | snoozed | warning |
| Reminders | completed | success |
| Reminders | archived | muted |

Unknown statuses fall back to muted.

## Forms And Inputs

- Use `.form-input` and `.form-textarea`.
- Inputs are dark, bordered, readable, and focus with the Sterling green ring.
- Selects show user-facing labels, not raw UUIDs.
- Validation errors use red soft backgrounds and concise copy.

## No Fake Buttons

Every visible normal-user action must do real work. Do not render placeholder controls for Export CSV, New Service Job, Emergency Service, API connected, notifications, profile, maps, Drive upload, Drive sync, folder scan, Outlook sync, Gmail sync, calendar sync, reports, photosheets, invoices, or quotes.

Future pages should follow this design system before adding new primitives.

## Site Map

- Keep the map on `/map`; do not render it on the dashboard or normal CRM pages.
- Load map code through a route-only dynamic import.
- Use the lightweight `/v1/sites/map` payload instead of full site records.
- Real visible actions are limited to Refresh Map, status/client filtering, marker selection, and opening the Sites page.
- Do not add geocoding, routing, dispatch, scheduling, sync, AI analysis, report, or photosheet controls until those workflows are actually implemented.
