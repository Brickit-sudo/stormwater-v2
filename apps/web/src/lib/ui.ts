/**
 * Shared className constants for the Sterling V2 dark CRM.
 *
 * Pages import these instead of redefining inline strings. Keep this file
 * the single source of truth for button/link/badge surface styles so the
 * design system stays consistent.
 */

export const primaryButtonClass =
  "inline-flex h-9 items-center justify-center rounded-md bg-green px-3.5 text-sm font-semibold text-bg shadow-[0_0_0_1px_rgba(69,224,79,0.35),0_8px_24px_-12px_rgba(69,224,79,0.55)] transition hover:bg-green-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green focus-visible:ring-offset-2 focus-visible:ring-offset-bg disabled:cursor-not-allowed disabled:bg-panel-soft disabled:text-text-muted disabled:shadow-none";

export const secondaryButtonClass =
  "inline-flex h-9 items-center justify-center rounded-md border border-border bg-panel px-3.5 text-sm font-semibold text-text transition hover:border-border-strong hover:bg-panel-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green focus-visible:ring-offset-2 focus-visible:ring-offset-bg disabled:cursor-not-allowed disabled:text-text-muted";

export const ghostButtonClass =
  "inline-flex h-9 items-center justify-center rounded-md px-3 text-sm font-medium text-text-secondary transition hover:bg-panel hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green focus-visible:ring-offset-2 focus-visible:ring-offset-bg disabled:cursor-not-allowed disabled:text-text-muted";

export const dangerButtonClass =
  "inline-flex h-9 items-center justify-center rounded-md border border-[color:var(--red)]/40 bg-panel px-3.5 text-sm font-semibold text-[color:var(--red)] transition hover:bg-[color:var(--red-soft)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--red)] focus-visible:ring-offset-2 focus-visible:ring-offset-bg disabled:cursor-not-allowed disabled:text-text-muted";

export const linkChipClass =
  "inline-flex h-8 items-center rounded-md border border-border bg-panel-2 px-3 text-xs font-semibold text-green transition hover:border-border-strong hover:bg-panel focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green focus-visible:ring-offset-2 focus-visible:ring-offset-bg";

export const cardClass =
  "rounded-lg border border-border bg-panel shadow-[0_1px_0_rgba(255,255,255,0.02)_inset,0_12px_32px_-22px_rgba(0,0,0,0.7)]";

export const subCardClass =
  "rounded-lg border border-border-soft bg-panel-2";

export const labelClass = "text-sm font-medium text-text-secondary";

export const eyebrowClass =
  "text-xs font-semibold uppercase tracking-[0.12em] text-text-muted";
