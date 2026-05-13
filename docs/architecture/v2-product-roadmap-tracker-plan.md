# V2 Product Roadmap Tracker Plan

The V2 roadmap tracker is an internal product-memory surface for ideas,
deferred work, boss feedback, and product decisions. It is not client-facing and
is not a replacement for full project management yet.

## Purpose

- Keep ideas inside V2 instead of scattered across prompts and memory.
- Capture product decisions with rationale and alternatives.
- Mark boss-demo-relevant ideas separately from later backlog work.
- Preserve "do not build yet" items without losing them.

## Data Model

`product_ideas` stores idea/backlog records scoped by `organization_id`:

- title, description
- category, lane, status, priority
- source, owner, target_version, effort, risk
- boss_demo_relevant
- created_at, updated_at, archived_at

`product_decisions` stores decision log records scoped by `organization_id`:

- optional related_idea_id
- decision_title, decision_summary, decision_reason
- alternatives_considered
- status, decided_at
- created_at, updated_at, archived_at

Both tables use soft archive. Normal list routes exclude archived rows.

## API

Ideas:

- `GET /v1/product-ideas`
- `POST /v1/product-ideas`
- `GET /v1/product-ideas/{id}`
- `PATCH /v1/product-ideas/{id}`
- `DELETE /v1/product-ideas/{id}`

Decisions:

- `GET /v1/product-decisions`
- `POST /v1/product-decisions`
- `PATCH /v1/product-decisions/{id}`
- `DELETE /v1/product-decisions/{id}`

Idea filters include `status`, `priority`, `category`, `lane`, and
`boss_demo_relevant`.

## Frontend

The internal `/roadmap` page includes:

- idea list with filters
- create/edit/archive idea actions
- boss-demo-relevant filter and count
- "Do Not Build Yet" section for deferred/rejected ideas
- decision list
- create/archive decision actions

All visible buttons call real local API routes. There is no drag-and-drop board,
fake automation, provider sync, or client-facing sharing in this phase.

## Seed Data

`scripts/seed_dev.py` seeds internal roadmap examples for the deterministic demo
organization, including current V2 capabilities, future integration ideas,
report ideas, import concerns, pricing/billing ideas, and core product
decisions.

## Guardrails

- Do not store secrets, tokens, passwords, API keys, or OAuth credentials in
  roadmap notes.
- Do not store private client details unless auth, access control, and staging
  protection are in place.
- Boss feedback can be captured here, but sensitive business details should be
  summarized carefully.
- Migration/import concerns should stay planning-only until the import
  contract, validators, and reviewed samples are ready.
