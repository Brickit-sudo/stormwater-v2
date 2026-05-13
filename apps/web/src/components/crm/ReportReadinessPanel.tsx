"use client";

import { useEffect, useMemo, useState } from "react";

import Badge, { type BadgeTone } from "@/components/ui/Badge";
import { getJobReportReadiness } from "@/lib/api";
import type {
  ReportReadiness,
  ReportReadinessCheck,
  ReportReadinessGroup,
  ReportReadinessOverallStatus,
  UUID,
} from "@/lib/types";

type ReportReadinessPanelProps = {
  organizationId: UUID;
  jobId: UUID | null;
};

const groupOrder: ReportReadinessGroup[] = [
  "Required",
  "Supporting Evidence",
  "Open Issues",
  "Draft / Communication Context",
];

const overallLabels: Record<ReportReadinessOverallStatus, string> = {
  ready: "Ready",
  needs_attention: "Needs Attention",
  blocked: "Blocked",
};

const overallTones: Record<ReportReadinessOverallStatus, BadgeTone> = {
  ready: "success",
  needs_attention: "warning",
  blocked: "danger",
};

function readinessLabel(check: ReportReadinessCheck): string {
  if (check.status === "pass") return "Ready";
  if (check.status === "fail" && check.severity === "high") return "Blocked";
  return "Needs Attention";
}

function readinessTone(check: ReportReadinessCheck): BadgeTone {
  if (check.status === "pass") return "success";
  if (check.status === "fail" && check.severity === "high") return "danger";
  return "warning";
}

function Dot({ check }: { check: ReportReadinessCheck }) {
  const className =
    check.status === "pass"
      ? "bg-green shadow-[0_0_10px_var(--green-glow)]"
      : check.status === "fail" && check.severity === "high"
        ? "bg-[color:var(--red)]"
        : "bg-[color:var(--yellow)]";

  return <span className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${className}`} />;
}

function CheckRow({ check }: { check: ReportReadinessCheck }) {
  return (
    <li className="flex gap-3 py-2.5">
      <Dot check={check} />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="break-words text-sm font-semibold text-text">{check.label}</p>
          <Badge tone={readinessTone(check)}>{readinessLabel(check)}</Badge>
          {check.related_count !== null ? (
            <span className="text-xs text-text-muted">{check.related_count}</span>
          ) : null}
        </div>
        <p className="mt-1 text-sm leading-5 text-text-secondary">{check.message}</p>
        {check.suggested_next_step ? (
          <p className="mt-1 text-xs leading-5 text-text-muted">
            <span className="font-semibold text-text-secondary">Suggested next step:</span>{" "}
            {check.suggested_next_step}
          </p>
        ) : null}
      </div>
    </li>
  );
}

export default function ReportReadinessPanel({
  organizationId,
  jobId,
}: ReportReadinessPanelProps) {
  const [readiness, setReadiness] = useState<ReportReadiness | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(() => {
      if (!organizationId || !jobId) {
        setReadiness(null);
        setLoading(false);
        setError(null);
        return;
      }

      setLoading(true);
      setError(null);

      getJobReportReadiness(jobId, organizationId)
        .then((response) => {
          if (!cancelled) {
            setReadiness(response);
          }
        })
        .catch((caught) => {
          if (!cancelled) {
            setReadiness(null);
            setError(
              caught instanceof Error
                ? caught.message
                : "Unable to load report readiness.",
            );
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
  }, [jobId, organizationId]);

  const groupedChecks = useMemo(() => {
    const byGroup = new Map<ReportReadinessGroup, ReportReadinessCheck[]>();
    for (const group of groupOrder) {
      byGroup.set(group, []);
    }
    for (const check of readiness?.checks ?? []) {
      byGroup.get(check.group)?.push(check);
    }
    return groupOrder
      .map((group) => ({ group, checks: byGroup.get(group) ?? [] }))
      .filter((entry) => entry.checks.length > 0);
  }, [readiness]);

  if (!jobId) {
    return null;
  }

  return (
    <section className="rounded-lg border border-border-soft bg-panel-2">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-border-soft px-3 py-3">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-text">Report Readiness</h3>
          {readiness ? (
            <p className="mt-1 text-xs leading-5 text-text-muted">{readiness.summary}</p>
          ) : null}
        </div>
        {readiness ? (
          <div className="flex shrink-0 items-center gap-2">
            {readiness.score !== null ? (
              <span className="rounded-full border border-border-soft bg-panel px-2.5 py-1 text-xs font-semibold text-text-secondary">
                {readiness.score}%
              </span>
            ) : null}
            <Badge tone={overallTones[readiness.overall_status]}>
              {overallLabels[readiness.overall_status]}
            </Badge>
          </div>
        ) : null}
      </div>

      <div className="px-3 py-3">
        {loading ? (
          <div className="space-y-2" aria-label="Loading report readiness">
            {[0, 1, 2].map((index) => (
              <div
                key={index}
                className="h-14 animate-pulse rounded-md border border-border-soft bg-panel"
              />
            ))}
          </div>
        ) : error ? (
          <p className="rounded-md border border-[color:var(--red)]/40 bg-[color:var(--red-soft)] px-3 py-2 text-sm text-[color:var(--red)]">
            {error}
          </p>
        ) : readiness ? (
          <div className="space-y-4">
            {readiness.warnings.length > 0 ? (
              <div className="rounded-md border border-border-soft bg-panel px-3 py-2">
                <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
                  View missing items
                </p>
                <p className="mt-1 text-sm text-text-secondary">
                  {readiness.warnings.length} item
                  {readiness.warnings.length === 1 ? "" : "s"} need attention.
                </p>
              </div>
            ) : null}

            {groupedChecks.map(({ group, checks }) => (
              <div key={group}>
                <h4 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted">
                  {group}
                </h4>
                <ul className="mt-1 divide-y divide-border-soft">
                  {checks.map((check) => (
                    <CheckRow key={check.key} check={check} />
                  ))}
                </ul>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-text-muted">No readiness data available.</p>
        )}
      </div>
    </section>
  );
}
