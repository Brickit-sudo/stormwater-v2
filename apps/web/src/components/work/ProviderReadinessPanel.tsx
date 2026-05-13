"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import Badge from "@/components/ui/Badge";
import type { BadgeTone } from "@/components/ui/Badge";
import { getIntegrationsStatus } from "@/lib/api";
import type { IntegrationProviderStatus, IntegrationsStatus, UUID } from "@/lib/types";
import { secondaryButtonClass } from "@/lib/ui";

const providerOrder: Array<keyof IntegrationsStatus> = [
  "outlook",
  "gmail",
  "google_drive",
  "onedrive",
  "ai",
];

function toneForStatus(status: IntegrationProviderStatus): BadgeTone {
  if (status.provider === "outlook" && status.status === "expired") return "warning";
  if (status.provider === "outlook" && status.status === "connected") return "success";
  if (status.provider === "outlook" && status.status === "disconnected") return "warning";
  if (status.provider === "outlook" && status.status === "error") return "danger";
  if (status.configured) return "success";
  if (status.status === "deferred") return "muted";
  return "warning";
}

function statusLabel(status: IntegrationProviderStatus): string {
  if (status.provider === "outlook" && status.status === "connected") return "Connected";
  if (status.provider === "outlook" && status.status === "expired") return "Expired";
  if (status.provider === "outlook" && status.status === "disconnected") return "Disconnected";
  if (status.configured) return "Configured";
  if (status.status === "deferred") return "Configure later";
  return "Configure first";
}

export default function ProviderReadinessPanel({
  organizationId,
}: {
  organizationId: UUID;
}) {
  const [status, setStatus] = useState<IntegrationsStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const providers = useMemo(
    () => (status ? providerOrder.map((key) => status[key]) : []),
    [status],
  );

  const loadStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setStatus(await getIntegrationsStatus(organizationId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load integration status.");
    } finally {
      setLoading(false);
    }
  }, [organizationId]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadStatus();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadStatus]);

  return (
    <section className="rounded-lg border border-border bg-panel p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-base font-semibold text-text">Provider Readiness</h2>
          <p className="mt-1 text-sm text-text-muted">
            Local Work Hub actions stay available while provider sync and picker paths are configured later.
          </p>
        </div>
        <button
          type="button"
          className={secondaryButtonClass}
          onClick={() => void loadStatus()}
          disabled={loading}
        >
          {loading ? "Checking..." : "Refresh"}
        </button>
      </div>

      {error ? (
        <div className="mt-3 rounded-md border border-[color:var(--red)]/40 bg-[color:var(--red-soft)] px-3 py-2 text-sm text-[color:var(--red)]">
          {error}
        </div>
      ) : null}

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        {providers.length > 0
          ? providers.map((provider) => (
              <article
                key={provider.provider}
                className="rounded-lg border border-border-soft bg-panel-2 p-3"
              >
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-sm font-semibold text-text">{provider.label}</h3>
                  <Badge tone={toneForStatus(provider)}>{statusLabel(provider)}</Badge>
                </div>
                <p className="mt-2 min-h-12 text-xs leading-5 text-text-muted">
                  {provider.message}
                </p>
                {provider.model ? (
                  <p className="mt-2 text-xs text-text-secondary">
                    Model: <span className="font-semibold text-text">{provider.model}</span>
                  </p>
                ) : null}
                {provider.missing_fields.length > 0 ? (
                  <p className="mt-2 text-xs text-[color:var(--yellow)]">
                    Missing: {provider.missing_fields.join(", ")}
                  </p>
                ) : null}
                {provider.enabled_capabilities.length > 0 ? (
                  <p className="mt-2 text-xs text-text-secondary">
                    Active: {provider.enabled_capabilities.slice(0, 2).join(", ")}
                  </p>
                ) : null}
              </article>
            ))
          : [0, 1, 2, 3, 4].map((index) => (
              <div
                key={index}
                className="h-36 animate-pulse rounded-lg border border-border-soft bg-panel-2"
              />
            ))}
      </div>
    </section>
  );
}
