"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import Card from "@/components/ui/Card";
import MetricCard from "@/components/ui/MetricCard";
import SectionHeader from "@/components/ui/SectionHeader";
import { demoOrganizationId, listClients, listJobs, listSites } from "@/lib/api";

const navLinks = [
  {
    href: "/crm/clients",
    title: "Clients",
    description:
      "Accounts and their primary contacts. Start here when onboarding a new customer.",
    eyebrow: "Step 1",
  },
  {
    href: "/crm/sites",
    title: "Sites",
    description:
      "Physical locations linked to clients. Manage addresses and Drive folders.",
    eyebrow: "Step 2",
  },
  {
    href: "/crm/jobs",
    title: "Jobs",
    description:
      "Scheduled work against a client and site. Track status from draft to completion.",
    eyebrow: "Step 3",
  },
];

type Counts = {
  clients: number | null;
  sites: number | null;
  jobs: number | null;
  inProgress: number | null;
};

const initialCounts: Counts = {
  clients: null,
  sites: null,
  jobs: null,
  inProgress: null,
};

function SetupBanner() {
  return (
    <AppShell>
      <Card className="p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[color:var(--yellow)]">
          Setup required
        </p>
        <h1 className="mt-2 text-2xl font-semibold text-text">
          Connect the demo organization
        </h1>
        <p className="mt-3 max-w-prose text-sm text-text-secondary">
          Set <code className="rounded bg-panel-2 px-1.5 py-0.5 text-text">NEXT_PUBLIC_DEMO_ORG_ID</code>{" "}
          in <code className="rounded bg-panel-2 px-1.5 py-0.5 text-text">apps/web/.env.local</code>{" "}
          and restart the dev server. The CRM workspace will load once the
          organization is wired up.
        </p>
      </Card>
    </AppShell>
  );
}

export default function Home() {
  const organizationId = demoOrganizationId;
  const [counts, setCounts] = useState<Counts>(initialCounts);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(() => {
      if (!organizationId) {
        setLoading(false);
        return;
      }

      setLoading(true);
      setError(null);

      Promise.all([
        listClients({ organizationId, limit: 1 }),
        listSites({ organizationId, limit: 1 }),
        listJobs({ organizationId, limit: 1 }),
        listJobs({ organizationId, limit: 1, status: "in_progress" }),
      ])
        .then(([clients, sites, jobs, inProgress]) => {
          if (cancelled) return;
          setCounts({
            clients: clients.total,
            sites: sites.total,
            jobs: jobs.total,
            inProgress: inProgress.total,
          });
        })
        .catch((caught) => {
          if (cancelled) return;
          setError(
            caught instanceof Error
              ? caught.message
              : "Unable to load workspace metrics.",
          );
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, 0);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [organizationId]);

  if (!organizationId) {
    return <SetupBanner />;
  }

  return (
    <AppShell>
      <div className="space-y-8">
        <SectionHeader
          title="Stormwater operations"
          description="Sterling Stormwater V2 - clients, sites, and jobs at a glance."
        />

        {error ? (
          <Card className="border-[color:var(--red)]/40 p-4 text-sm text-[color:var(--red)]">
            {error}
          </Card>
        ) : null}

        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Clients"
            value={counts.clients ?? 0}
            hint="Accounts in the workspace"
            loading={loading}
          />
          <MetricCard
            label="Sites"
            value={counts.sites ?? 0}
            hint="Locations linked to clients"
            loading={loading}
          />
          <MetricCard
            label="Jobs"
            value={counts.jobs ?? 0}
            hint="All scheduled work orders"
            loading={loading}
          />
          <MetricCard
            label="In progress"
            value={counts.inProgress ?? 0}
            hint="Jobs currently being worked"
            loading={loading}
          />
        </section>

        <section>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-text-muted">
            Workspace
          </p>
          <h2 className="mt-2 text-lg font-semibold text-text">
            CRM Command Center
          </h2>
          <p className="mt-1 max-w-prose text-sm text-text-secondary">
            Move through the Clients {"->"} Sites {"->"} Jobs workflow to keep records
            linked end to end.
          </p>

          <div className="mt-5 grid gap-4 lg:grid-cols-3">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="group rounded-lg border border-border bg-panel p-5 transition hover:border-[color:var(--green)]/40 hover:bg-panel-2 hover:shadow-[0_0_0_1px_rgba(69,224,79,0.18),0_18px_38px_-26px_rgba(69,224,79,0.5)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
              >
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted">
                  {link.eyebrow}
                </p>
                <div className="mt-2 flex items-center justify-between gap-3">
                  <span className="text-lg font-semibold text-text">
                    {link.title}
                  </span>
                  <span
                    aria-hidden="true"
                    className="text-green opacity-0 transition group-hover:opacity-100"
                  >
                    {"->"}
                  </span>
                </div>
                <p className="mt-3 text-sm leading-6 text-text-secondary">
                  {link.description}
                </p>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </AppShell>
  );
}
