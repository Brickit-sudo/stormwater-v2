"use client";

import { useEffect, useState } from "react";

import { listTimeline } from "@/lib/api";
import type { TimelineEntry, TimelineEntryType, UUID } from "@/lib/types";

type TimelinePanelProps = {
  organizationId: UUID;
  clientId?: UUID | null;
  siteId?: UUID | null;
  jobId?: UUID | null;
};

const typeLabels: Record<TimelineEntryType, string> = {
  record: "Record",
  job: "Job",
  reminder: "Reminder",
  file: "File",
  email: "Email",
  email_link: "Email link",
  ai_draft: "AI draft",
  import_batch: "Import",
  outlook_draft: "Outlook draft",
};

const typeClasses: Record<TimelineEntryType, string> = {
  record: "border-border-soft bg-panel text-text-secondary",
  job: "border-[color:var(--green)]/35 bg-[color:var(--green-soft)] text-[color:var(--green)]",
  reminder: "border-[color:var(--yellow)]/35 bg-[color:var(--yellow-soft)] text-[color:var(--yellow)]",
  file: "border-border-soft bg-panel text-text-secondary",
  email: "border-[color:var(--blue)]/35 bg-[color:var(--blue-soft)] text-[color:var(--blue)]",
  email_link: "border-[color:var(--blue)]/35 bg-[color:var(--blue-soft)] text-[color:var(--blue)]",
  ai_draft: "border-[color:var(--blue)]/35 bg-[color:var(--blue-soft)] text-[color:var(--blue)]",
  import_batch: "border-border-soft bg-panel text-text-secondary",
  outlook_draft: "border-[color:var(--green)]/35 bg-[color:var(--green-soft)] text-[color:var(--green)]",
};

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function formatToken(value: string): string {
  return value.replaceAll("_", " ");
}

function targetCount(clientId?: string | null, siteId?: string | null, jobId?: string | null) {
  return Number(Boolean(clientId)) + Number(Boolean(siteId)) + Number(Boolean(jobId));
}

function TimelineEntryRow({ entry }: { entry: TimelineEntry }) {
  const title = entry.href ? (
    <a
      href={entry.href}
      target={entry.href.startsWith("http") ? "_blank" : undefined}
      rel={entry.href.startsWith("http") ? "noreferrer" : undefined}
      className="text-text underline decoration-border-soft underline-offset-4 hover:text-[color:var(--green)]"
    >
      {entry.title}
    </a>
  ) : (
    <span>{entry.title}</span>
  );

  return (
    <li className="relative pl-5">
      <span className="absolute left-0 top-2 h-2.5 w-2.5 rounded-full border border-[color:var(--green)] bg-panel" />
      <div className="rounded-md border border-border-soft bg-panel px-3 py-3">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`rounded border px-2 py-0.5 text-[11px] font-semibold uppercase ${typeClasses[entry.type]}`}
          >
            {typeLabels[entry.type]}
          </span>
          {entry.status ? (
            <span className="rounded border border-border-soft bg-panel-2 px-2 py-0.5 text-xs text-text-muted">
              {formatToken(entry.status)}
            </span>
          ) : null}
          {entry.priority ? (
            <span className="rounded border border-border-soft bg-panel-2 px-2 py-0.5 text-xs text-text-muted">
              {formatToken(entry.priority)}
            </span>
          ) : null}
        </div>
        <p className="mt-2 break-words text-sm font-medium text-text">{title}</p>
        {entry.description ? (
          <p className="mt-1 break-words text-sm text-text-secondary">
            {entry.description}
          </p>
        ) : null}
        <p className="mt-2 text-xs text-text-muted">
          {formatDateTime(entry.occurred_at)}
        </p>
      </div>
    </li>
  );
}

export default function TimelinePanel({
  organizationId,
  clientId,
  siteId,
  jobId,
}: TimelinePanelProps) {
  const [entries, setEntries] = useState<TimelineEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(() => {
      if (!organizationId || targetCount(clientId, siteId, jobId) !== 1) {
        setEntries([]);
        setLoading(false);
        setError(null);
        return;
      }

      setLoading(true);
      setError(null);

      listTimeline({
        organizationId,
        clientId: clientId ?? undefined,
        siteId: siteId ?? undefined,
        jobId: jobId ?? undefined,
        limit: 50,
      })
        .then((response) => {
          if (!cancelled) {
            setEntries(response.items);
          }
        })
        .catch((caught) => {
          if (!cancelled) {
            setEntries([]);
            setError(caught instanceof Error ? caught.message : "Unable to load timeline.");
          }
        })
        .finally(() => {
          if (!cancelled) {
            setLoading(false);
          }
        });
    }, 0);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [clientId, jobId, organizationId, siteId]);

  return (
    <section className="rounded-lg border border-border-soft bg-panel-2">
      <div className="border-b border-border-soft px-3 py-3">
        <h3 className="text-sm font-semibold text-text">Timeline</h3>
      </div>

      <div className="px-3 py-3">
        {loading ? (
          <div className="space-y-3" aria-label="Loading timeline">
            {[0, 1, 2].map((index) => (
              <div
                key={index}
                className="h-20 animate-pulse rounded-md border border-border-soft bg-panel"
              />
            ))}
          </div>
        ) : error ? (
          <p className="rounded-md border border-[color:var(--red)]/40 bg-[color:var(--red-soft)] px-3 py-2 text-sm text-[color:var(--red)]">
            {error}
          </p>
        ) : entries.length > 0 ? (
          <ol className="space-y-3 border-l border-border-soft">
            {entries.map((entry) => (
              <TimelineEntryRow key={entry.id} entry={entry} />
            ))}
          </ol>
        ) : (
          <p className="text-sm text-text-muted">No timeline activity yet.</p>
        )}
      </div>
    </section>
  );
}
