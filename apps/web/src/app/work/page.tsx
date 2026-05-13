"use client";

import AppShell from "@/components/AppShell";
import WorkHubShell from "@/components/work/WorkHubShell";
import { demoOrganizationId } from "@/lib/api";

function SetupMessage() {
  return (
    <AppShell>
      <div className="rounded-lg border border-[color:var(--yellow)]/40 bg-[color:var(--yellow-soft)] p-5 text-sm text-[color:var(--yellow)]">
        Set NEXT_PUBLIC_DEMO_ORG_ID in apps/web/.env.local to use Work Hub.
      </div>
    </AppShell>
  );
}

export default function WorkPage() {
  const organizationId = demoOrganizationId;

  if (!organizationId) {
    return <SetupMessage />;
  }

  return (
    <AppShell>
      <WorkHubShell organizationId={organizationId} />
    </AppShell>
  );
}
