"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import AppShell from "@/components/AppShell";
import StatusBadge from "@/components/crm/StatusBadge";
import Card from "@/components/ui/Card";
import SectionHeader from "@/components/ui/SectionHeader";
import {
  demoOrganizationId,
  listClients,
  listMapSites,
} from "@/lib/api";
import type { Client, MapSite } from "@/lib/types";
import { secondaryButtonClass } from "@/lib/ui";

const SiteMap = dynamic(() => import("@/components/map/SiteMap"), {
  ssr: false,
  loading: () => <MapSkeleton />,
});

const siteStatusOptions = ["active", "on_hold", "inactive"];

function MapSkeleton() {
  return (
    <div className="flex h-[620px] min-h-[420px] w-full animate-pulse items-center justify-center rounded-lg border border-border bg-panel-2 text-sm text-text-muted">
      Loading site map...
    </div>
  );
}

function SetupMessage() {
  return (
    <AppShell>
      <Card className="p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[color:var(--yellow)]">
          Setup required
        </p>
        <p className="mt-2 text-sm text-text-secondary">
          Set NEXT_PUBLIC_DEMO_ORG_ID in apps/web/.env.local to use the site map.
        </p>
      </Card>
    </AppShell>
  );
}

function formatLocation(site: MapSite): string {
  return [site.city, site.state].filter(Boolean).join(", ") || "Location not set";
}

function siteHref(site: MapSite): string {
  const params = new URLSearchParams({
    client_id: site.client_id,
    site_id: site.id,
  });
  return `/crm/sites?${params.toString()}`;
}

function SitePreview({ site }: { site: MapSite | null }) {
  if (!site) {
    return (
      <Card as="aside" className="p-5">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
          Selected site
        </p>
        <p className="mt-3 text-sm text-text-secondary">
          Select a marker to preview site details.
        </p>
      </Card>
    );
  }

  return (
    <Card as="aside" className="p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between xl:flex-col xl:items-stretch">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
            Selected site
          </p>
          <h2 className="mt-2 text-lg font-semibold text-text">{site.name}</h2>
          <p className="mt-1 text-sm text-text-muted">
            {site.client_name ?? "Client not loaded"}
          </p>
        </div>
        <Link className={secondaryButtonClass} href={siteHref(site)}>
          Open Sites
        </Link>
      </div>

      <dl className="mt-5 grid gap-3 text-sm">
        <div className="rounded-lg border border-border-soft bg-panel-2 p-3">
          <dt className="text-xs font-semibold uppercase tracking-[0.12em] text-text-muted">
            Status
          </dt>
          <dd className="mt-2">
            <StatusBadge status={site.status} />
          </dd>
        </div>
        <div className="rounded-lg border border-border-soft bg-panel-2 p-3">
          <dt className="text-xs font-semibold uppercase tracking-[0.12em] text-text-muted">
            Location
          </dt>
          <dd className="mt-2 text-text-secondary">{formatLocation(site)}</dd>
        </div>
        <div className="rounded-lg border border-border-soft bg-panel-2 p-3">
          <dt className="text-xs font-semibold uppercase tracking-[0.12em] text-text-muted">
            Address
          </dt>
          <dd className="mt-2 text-text-secondary">{site.address ?? "Not set"}</dd>
        </div>
      </dl>
    </Card>
  );
}

export default function MapPage() {
  const organizationId = demoOrganizationId;
  const [sites, setSites] = useState<MapSite[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [selectedSiteId, setSelectedSiteId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [clientFilter, setClientFilter] = useState("");
  const [mappedTotal, setMappedTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedSite = useMemo(
    () => sites.find((site) => site.id === selectedSiteId) ?? null,
    [selectedSiteId, sites],
  );

  const loadMap = useCallback(async () => {
    if (!organizationId) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const [siteResponse, clientResponse] = await Promise.all([
        listMapSites({
          organizationId,
          status: statusFilter || undefined,
          clientId: clientFilter || undefined,
          limit: 1000,
        }),
        listClients({ organizationId, limit: 500 }),
      ]);
      setSites(siteResponse.items);
      setClients(clientResponse.items);
      setMappedTotal(siteResponse.total);
      setSelectedSiteId((current) => {
        if (current && siteResponse.items.some((site) => site.id === current)) {
          return current;
        }
        return siteResponse.items[0]?.id ?? null;
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load site map.");
    } finally {
      setLoading(false);
    }
  }, [clientFilter, organizationId, statusFilter]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadMap();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [loadMap]);

  if (!organizationId) {
    return <SetupMessage />;
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <SectionHeader
          title="Site Map"
          description="Mapped CRM sites with lightweight location data only."
          actions={
            <button
              type="button"
              className={secondaryButtonClass}
              onClick={() => void loadMap()}
              disabled={loading}
            >
              {loading ? "Refreshing..." : "Refresh Map"}
            </button>
          }
        />

        <Card className="p-4">
          <div className="grid gap-3 lg:grid-cols-[220px_260px_1fr] lg:items-end">
            <label className="block">
              <span className="text-sm font-medium text-text-secondary">
                Status
              </span>
              <select
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value)}
                className="form-input mt-2"
              >
                <option value="">All statuses</option>
                {siteStatusOptions.map((status) => (
                  <option key={status} value={status}>
                    {status.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-sm font-medium text-text-secondary">
                Client
              </span>
              <select
                value={clientFilter}
                onChange={(event) => setClientFilter(event.target.value)}
                className="form-input mt-2"
              >
                <option value="">All clients</option>
                {clients.map((client) => (
                  <option key={client.id} value={client.id}>
                    {client.name}
                  </option>
                ))}
              </select>
            </label>
            <div className="rounded-lg border border-border-soft bg-panel-2 px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
                Mapped sites
              </p>
              <p className="mt-1 text-2xl font-semibold text-text">
                {loading ? "..." : sites.length}
              </p>
              <p className="text-xs text-text-muted">
                {mappedTotal === sites.length
                  ? "Current filter result"
                  : `Showing ${sites.length} of ${mappedTotal}`}
              </p>
            </div>
          </div>
        </Card>

        {error ? (
          <Card className="border-[color:var(--red)]/40 p-4 text-sm text-[color:var(--red)]">
            {error}
          </Card>
        ) : null}

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
          <Card className="min-w-0 overflow-hidden p-3">
            {loading && sites.length === 0 ? (
              <MapSkeleton />
            ) : sites.length > 0 ? (
              <SiteMap
                sites={sites}
                selectedSiteId={selectedSiteId}
                onSelectSite={(site) => setSelectedSiteId(site.id)}
              />
            ) : (
              <div className="flex min-h-[420px] items-center justify-center rounded-lg border border-border-soft bg-panel-2 px-6 text-center">
                <div>
                  <p className="text-base font-semibold text-text">
                    No mapped sites found
                  </p>
                  <p className="mt-2 max-w-md text-sm text-text-secondary">
                    The map endpoint only returns non-archived sites with latitude and longitude.
                  </p>
                </div>
              </div>
            )}
          </Card>

          <SitePreview site={selectedSite} />
        </div>
      </div>
    </AppShell>
  );
}
