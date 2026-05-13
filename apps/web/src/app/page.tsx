"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import AppShell from "@/components/AppShell";
import Badge, { type BadgeTone } from "@/components/ui/Badge";
import Card from "@/components/ui/Card";
import MetricCard from "@/components/ui/MetricCard";
import {
  demoOrganizationId,
  getIntegrationsStatus,
  listClients,
  listJobs,
  listReminders,
  listSites,
} from "@/lib/api";
import type {
  IntegrationProviderStatus,
  IntegrationsStatus,
  Job,
  Reminder,
} from "@/lib/types";
import { cardClass, eyebrowClass } from "@/lib/ui";

type DashboardCounts = {
  clients: number | null;
  sites: number | null;
  jobs: number | null;
  openReminders: number | null;
};

type ReminderSummary = {
  today: number | null;
  overdue: number | null;
  nextOpen: Reminder[];
};

type JobSummary = {
  inProgress: number | null;
  scheduled: number | null;
  nextScheduled: Job[];
};

type DashboardData = {
  counts: DashboardCounts;
  reminders: ReminderSummary;
  jobs: JobSummary;
  integrations: IntegrationsStatus | null;
};

type NavCard = {
  href: string;
  title: string;
  description: string;
  label: string;
};

const initialDashboardData: DashboardData = {
  counts: {
    clients: null,
    sites: null,
    jobs: null,
    openReminders: null,
  },
  reminders: {
    today: null,
    overdue: null,
    nextOpen: [],
  },
  jobs: {
    inProgress: null,
    scheduled: null,
    nextScheduled: [],
  },
  integrations: null,
};

const quickLinks: NavCard[] = [
  {
    href: "/search",
    title: "Search",
    description: "Find local CRM records across accounts, work, files, emails, drafts, and reminders.",
    label: "Find",
  },
  {
    href: "/roadmap",
    title: "Roadmap",
    description: "Capture internal product ideas, boss feedback, deferred work, and decisions.",
    label: "Plan",
  },
  {
    href: "/crm/clients",
    title: "Clients",
    description: "Accounts, contacts, and stored client file links.",
    label: "CRM",
  },
  {
    href: "/crm/sites",
    title: "Sites",
    description: "Locations, addresses, statuses, and mapped records.",
    label: "CRM",
  },
  {
    href: "/crm/jobs",
    title: "Jobs",
    description: "Scheduled work orders tied back to client and site records.",
    label: "Ops",
  },
  {
    href: "/schedule",
    title: "Schedule",
    description: "Open follow-ups, due dates, and reminder closeout.",
    label: "Ops",
  },
  {
    href: "/map",
    title: "Map",
    description: "Lazy-loaded site map for reviewed location records.",
    label: "Field",
  },
  {
    href: "/work",
    title: "Work Hub",
    description: "Email imports, AI drafts, files, and provider readiness.",
    label: "Office",
  },
];

const officeWorkflow: NavCard[] = [
  {
    href: "/work",
    title: "Import emails in Work Hub",
    description: "Preview Outlook messages before local CRM import.",
    label: "1",
  },
  {
    href: "/schedule",
    title: "Review reminders",
    description: "Work overdue and today's follow-ups from the schedule.",
    label: "2",
  },
  {
    href: "/map",
    title: "Review site map",
    description: "Check mapped locations before dispatch or planning.",
    label: "3",
  },
  {
    href: "/work",
    title: "Manage files",
    description: "Keep reviewed Drive and file metadata with CRM records.",
    label: "4",
  },
];

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
          Set{" "}
          <code className="rounded bg-panel-2 px-1.5 py-0.5 text-text">
            NEXT_PUBLIC_DEMO_ORG_ID
          </code>{" "}
          in{" "}
          <code className="rounded bg-panel-2 px-1.5 py-0.5 text-text">
            apps/web/.env.local
          </code>{" "}
          and restart the dev server. The CRM workspace will load once the
          organization is wired up.
        </p>
      </Card>
    </AppShell>
  );
}

function getTodayBounds() {
  const start = new Date();
  start.setHours(0, 0, 0, 0);

  const overdueEnd = new Date(start.getTime() - 1);
  const todayEnd = new Date(start);
  todayEnd.setDate(todayEnd.getDate() + 1);
  todayEnd.setMilliseconds(todayEnd.getMilliseconds() - 1);

  return {
    startIso: start.toISOString(),
    overdueEndIso: overdueEnd.toISOString(),
    todayEndIso: todayEnd.toISOString(),
  };
}

function formatShortDate(value: string | null): string {
  if (!value) {
    return "Unscheduled";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
  }).format(date);
}

function formatStatus(value: string): string {
  return value.replaceAll("_", " ");
}

function providerTone(status: IntegrationProviderStatus | undefined): BadgeTone {
  if (!status) {
    return "muted";
  }
  if (status.provider === "outlook" && status.status === "connected") {
    return "success";
  }
  if (status.provider === "outlook" && status.status === "expired") {
    return "warning";
  }
  if (status.provider === "outlook" && status.status === "disconnected") {
    return "warning";
  }
  if (status.provider === "outlook" && status.status === "error") {
    return "danger";
  }
  if (status.configured) {
    return "success";
  }
  if (status.status === "deferred") {
    return "muted";
  }
  return "warning";
}

function outlookLabel(status: IntegrationProviderStatus | undefined): string {
  if (!status) {
    return "Checking";
  }
  if (status.status === "connected") {
    return "Connected";
  }
  if (status.status === "expired") {
    return "Expired";
  }
  if (status.status === "disconnected") {
    return status.configured ? "Configured" : "Disconnected";
  }
  if (status.configured) {
    return "Configured";
  }
  return "Needs config";
}

function aiLabel(status: IntegrationProviderStatus | undefined): string {
  if (!status) {
    return "Checking";
  }
  return status.configured ? "Configured" : "Local fallback";
}

function LoadingRows({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, index) => (
        <div
          key={index}
          className="h-16 animate-pulse rounded-lg border border-border-soft bg-panel-2"
        />
      ))}
    </div>
  );
}

function SummaryValue({
  label,
  value,
  badge,
  tone = "muted",
  loading,
}: {
  label: string;
  value: number | null;
  badge: string;
  tone?: BadgeTone;
  loading: boolean;
}) {
  return (
    <div className="rounded-lg border border-border-soft bg-panel-2 p-3">
      <p className={eyebrowClass}>{label}</p>
      {loading ? (
        <span className="mt-3 block h-7 w-12 animate-pulse rounded bg-panel" />
      ) : (
        <div className="mt-2 flex items-baseline gap-2">
          <span className="text-2xl font-semibold text-text">
            {value ?? 0}
          </span>
          <Badge tone={tone}>{badge}</Badge>
        </div>
      )}
    </div>
  );
}

function EmptyLine({ children }: { children: ReactNode }) {
  return (
    <p className="rounded-lg border border-border-soft bg-panel-2 px-4 py-3 text-sm text-text-muted">
      {children}
    </p>
  );
}

function HomeHero() {
  return (
    <section className="rounded-lg border border-border bg-panel p-5 shadow-[0_1px_0_rgba(255,255,255,0.02)_inset,0_18px_46px_-30px_rgba(69,224,79,0.45)] sm:p-6">
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-end">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-text sm:text-3xl">
            CRM Command Dashboard
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-text-secondary">
            Sterling Stormwater V2 brings clients, sites, jobs, reminders, map
            review, files, and Work Hub readiness into one fast local view.
          </p>
        </div>
        <div className="rounded-lg border border-border-soft bg-panel-2 p-4">
          <p className={eyebrowClass}>Operational path</p>
          <p className="mt-2 text-sm font-semibold text-text">
            Clients - Sites - Jobs - Schedule - Work Hub
          </p>
          <p className="mt-1 text-xs leading-5 text-text-muted">
            Dashboard data comes from bounded local API reads.
          </p>
        </div>
      </div>
    </section>
  );
}

function ReminderPanel({
  summary,
  loading,
}: {
  summary: ReminderSummary;
  loading: boolean;
}) {
  return (
    <Card as="section" className="p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className={eyebrowClass}>Reminder summary</p>
          <h2 className="mt-2 text-lg font-semibold text-text">
            Today and overdue
          </h2>
        </div>
        <Link
          href="/schedule"
          className="text-sm font-semibold text-green transition hover:text-green-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
        >
          Open Schedule
        </Link>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <SummaryValue
          label="Overdue"
          value={summary.overdue}
          badge={(summary.overdue ?? 0) > 0 ? "Needs review" : "Clear"}
          tone={(summary.overdue ?? 0) > 0 ? "danger" : "muted"}
          loading={loading}
        />
        <SummaryValue
          label="Today"
          value={summary.today}
          badge={(summary.today ?? 0) > 0 ? "Due" : "Clear"}
          tone={(summary.today ?? 0) > 0 ? "warning" : "muted"}
          loading={loading}
        />
      </div>

      <div className="mt-5 space-y-3">
        <h3 className="text-sm font-semibold text-text">Next open follow-ups</h3>
        {loading ? (
          <LoadingRows />
        ) : summary.nextOpen.length > 0 ? (
          <div className="space-y-3">
            {summary.nextOpen.map((reminder) => (
              <div
                key={reminder.id}
                className="rounded-lg border border-border-soft bg-panel-2 p-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-text">
                    {reminder.title}
                  </p>
                  <Badge tone={reminder.priority === "high" ? "danger" : "muted"}>
                    {reminder.priority}
                  </Badge>
                </div>
                <p className="mt-2 text-xs text-text-muted">
                  Due {formatShortDate(reminder.due_at)}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <EmptyLine>No open reminders are due in the current queue.</EmptyLine>
        )}
      </div>
    </Card>
  );
}

function JobsPanel({
  summary,
  loading,
}: {
  summary: JobSummary;
  loading: boolean;
}) {
  return (
    <Card as="section" className="p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className={eyebrowClass}>Job summary</p>
          <h2 className="mt-2 text-lg font-semibold text-text">
            Active and upcoming work
          </h2>
        </div>
        <Link
          href="/crm/jobs"
          className="text-sm font-semibold text-green transition hover:text-green-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
        >
          Open Jobs
        </Link>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <SummaryValue
          label="In progress"
          value={summary.inProgress}
          badge={(summary.inProgress ?? 0) > 0 ? "Active" : "None"}
          tone={(summary.inProgress ?? 0) > 0 ? "info" : "muted"}
          loading={loading}
        />
        <SummaryValue
          label="Scheduled"
          value={summary.scheduled}
          badge={(summary.scheduled ?? 0) > 0 ? "Upcoming" : "None"}
          tone={(summary.scheduled ?? 0) > 0 ? "success" : "muted"}
          loading={loading}
        />
      </div>

      <div className="mt-5 space-y-3">
        <h3 className="text-sm font-semibold text-text">Next scheduled jobs</h3>
        {loading ? (
          <LoadingRows />
        ) : summary.nextScheduled.length > 0 ? (
          <div className="space-y-3">
            {summary.nextScheduled.map((job) => (
              <div
                key={job.id}
                className="rounded-lg border border-border-soft bg-panel-2 p-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-text">{job.name}</p>
                  <Badge tone="info">{formatStatus(job.status)}</Badge>
                </div>
                <p className="mt-2 text-xs text-text-muted">
                  Due {formatShortDate(job.due_date)} -{" "}
                  {job.service_type ?? "Service type not set"}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <EmptyLine>No scheduled jobs are in the current queue.</EmptyLine>
        )}
      </div>
    </Card>
  );
}

function WorkHubStatusCard({
  integrations,
  loading,
}: {
  integrations: IntegrationsStatus | null;
  loading: boolean;
}) {
  const outlook = integrations?.outlook;
  const ai = integrations?.ai;

  return (
    <Card as="section" className="p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className={eyebrowClass}>Work Hub status</p>
          <h2 className="mt-2 text-lg font-semibold text-text">
            Provider readiness
          </h2>
        </div>
        <Link
          href="/work"
          className="text-sm font-semibold text-green transition hover:text-green-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
        >
          Open Work Hub
        </Link>
      </div>

      <div className="mt-5 grid gap-3 md:grid-cols-2">
        <ProviderTile
          title="Outlook"
          badge={outlookLabel(outlook)}
          tone={providerTone(outlook)}
          message={
            outlook?.message
            ?? (loading ? "Checking readiness..." : "Outlook status unavailable.")
          }
          detail={
            outlook?.enabled_capabilities.length
              ? `Active: ${outlook.enabled_capabilities.slice(0, 2).join(", ")}`
              : outlook?.missing_fields.length
                ? `Missing: ${outlook.missing_fields.join(", ")}`
                : null
          }
          loading={loading}
        />
        <ProviderTile
          title="AI"
          badge={aiLabel(ai)}
          tone={providerTone(ai)}
          message={
            ai?.message
            ?? (loading ? "Checking readiness..." : "AI status unavailable.")
          }
          detail={ai?.model ? `Model: ${ai.model}` : null}
          loading={loading}
        />
      </div>
    </Card>
  );
}

function ProviderTile({
  title,
  badge,
  tone,
  message,
  detail,
  loading,
}: {
  title: string;
  badge: string;
  tone: BadgeTone;
  message: string;
  detail: string | null;
  loading: boolean;
}) {
  return (
    <article className="rounded-lg border border-border-soft bg-panel-2 p-4">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-sm font-semibold text-text">{title}</h3>
        <Badge tone={tone}>{badge}</Badge>
      </div>
      {loading ? (
        <div className="mt-4 space-y-2">
          <div className="h-3 w-full animate-pulse rounded bg-panel" />
          <div className="h-3 w-3/4 animate-pulse rounded bg-panel" />
        </div>
      ) : (
        <>
          <p className="mt-3 min-h-10 text-xs leading-5 text-text-muted">
            {message}
          </p>
          {detail ? (
            <p className="mt-3 text-xs font-medium text-text-secondary">
              {detail}
            </p>
          ) : null}
        </>
      )}
    </article>
  );
}

function QuickLinks() {
  return (
    <section>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className={eyebrowClass}>Quick navigation</p>
          <h2 className="mt-2 text-lg font-semibold text-text">
            Operational workspaces
          </h2>
        </div>
      </div>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {quickLinks.map((link) => (
          <DashboardLinkCard key={link.href} link={link} />
        ))}
      </div>
    </section>
  );
}

function OfficeWorkflowCard() {
  return (
    <Card as="section" className="p-5">
      <p className={eyebrowClass}>Office workflow</p>
      <h2 className="mt-2 text-lg font-semibold text-text">
        Review-first daily loop
      </h2>
      <div className="mt-5 space-y-3">
        {officeWorkflow.map((link) => (
          <Link
            key={`${link.label}-${link.title}`}
            href={link.href}
            className="group grid gap-3 rounded-lg border border-border-soft bg-panel-2 p-3 transition hover:border-[color:var(--green)]/40 hover:bg-panel focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green focus-visible:ring-offset-2 focus-visible:ring-offset-bg sm:grid-cols-[34px_minmax(0,1fr)]"
          >
            <span className="flex h-8 w-8 items-center justify-center rounded-md border border-border bg-panel text-xs font-semibold text-green">
              {link.label}
            </span>
            <span className="min-w-0">
              <span className="block text-sm font-semibold text-text">
                {link.title}
              </span>
              <span className="mt-1 block text-xs leading-5 text-text-muted">
                {link.description}
              </span>
            </span>
          </Link>
        ))}
      </div>
    </Card>
  );
}

function DashboardLinkCard({ link }: { link: NavCard }) {
  return (
    <Link
      href={link.href}
      className={[
        cardClass,
        "group block p-4 transition hover:border-[color:var(--green)]/40 hover:bg-panel-2 hover:shadow-[0_0_0_1px_rgba(69,224,79,0.18),0_18px_38px_-26px_rgba(69,224,79,0.5)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green focus-visible:ring-offset-2 focus-visible:ring-offset-bg",
      ].join(" ")}
    >
      <div className="flex items-start justify-between gap-3">
        <p className={eyebrowClass}>{link.label}</p>
        <span
          aria-hidden="true"
          className="text-sm font-semibold text-green opacity-0 transition group-hover:opacity-100"
        >
          -&gt;
        </span>
      </div>
      <h3 className="mt-3 text-base font-semibold text-text">{link.title}</h3>
      <p className="mt-2 text-sm leading-6 text-text-secondary">
        {link.description}
      </p>
    </Link>
  );
}

export default function Home() {
  const organizationId = demoOrganizationId;
  const [data, setData] = useState<DashboardData>(initialDashboardData);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    if (!organizationId) {
      setLoading(false);
      return;
    }

    const { startIso, overdueEndIso, todayEndIso } = getTodayBounds();

    setLoading(true);
    setError(null);
    try {
      const [
        clients,
        sites,
        jobs,
        openReminders,
        overdueReminders,
        todayReminders,
        inProgressJobs,
        scheduledJobs,
        integrations,
      ] = await Promise.all([
        listClients({ organizationId, limit: 1 }),
        listSites({ organizationId, limit: 1 }),
        listJobs({ organizationId, limit: 1 }),
        listReminders({ organizationId, status: "open", limit: 3 }),
        listReminders({
          organizationId,
          status: "open",
          dueBefore: overdueEndIso,
          limit: 1,
        }),
        listReminders({
          organizationId,
          status: "open",
          dueAfter: startIso,
          dueBefore: todayEndIso,
          limit: 1,
        }),
        listJobs({ organizationId, status: "in_progress", limit: 1 }),
        listJobs({ organizationId, status: "scheduled", limit: 3 }),
        getIntegrationsStatus(organizationId),
      ]);

      setData({
        counts: {
          clients: clients.total,
          sites: sites.total,
          jobs: jobs.total,
          openReminders: openReminders.total,
        },
        reminders: {
          today: todayReminders.total,
          overdue: overdueReminders.total,
          nextOpen: openReminders.items,
        },
        jobs: {
          inProgress: inProgressJobs.total,
          scheduled: scheduledJobs.total,
          nextScheduled: scheduledJobs.items,
        },
        integrations,
      });
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to load dashboard metrics.",
      );
    } finally {
      setLoading(false);
    }
  }, [organizationId]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadDashboard();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [loadDashboard]);

  const kpiCards = useMemo(
    () => [
      {
        label: "Clients",
        value: data.counts.clients,
        hint: "Accounts in the CRM",
      },
      {
        label: "Sites",
        value: data.counts.sites,
        hint: "Locations linked to clients",
      },
      {
        label: "Jobs",
        value: data.counts.jobs,
        hint: "All non-archived work orders",
      },
      {
        label: "Open reminders",
        value: data.counts.openReminders,
        hint: "Follow-ups still open",
      },
    ],
    [
      data.counts.clients,
      data.counts.jobs,
      data.counts.openReminders,
      data.counts.sites,
    ],
  );

  if (!organizationId) {
    return <SetupBanner />;
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <HomeHero />

        {error ? (
          <Card className="border-[color:var(--red)]/40 p-4 text-sm text-[color:var(--red)]">
            {error}
          </Card>
        ) : null}

        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {kpiCards.map((card) => (
            <MetricCard
              key={card.label}
              label={card.label}
              value={card.value ?? 0}
              hint={card.hint}
              loading={loading}
            />
          ))}
        </section>

        <div className="grid gap-4 xl:grid-cols-2">
          <ReminderPanel summary={data.reminders} loading={loading} />
          <JobsPanel summary={data.jobs} loading={loading} />
        </div>

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
          <WorkHubStatusCard integrations={data.integrations} loading={loading} />
          <OfficeWorkflowCard />
        </div>

        <QuickLinks />
      </div>
    </AppShell>
  );
}
