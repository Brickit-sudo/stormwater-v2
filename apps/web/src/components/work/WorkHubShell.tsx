"use client";

import { useState } from "react";

import SectionHeader from "@/components/ui/SectionHeader";
import type { UUID } from "@/lib/types";

import AiDraftsWorkView from "./AiDraftsWorkView";
import EmailsWorkView from "./EmailsWorkView";
import FilesWorkView from "./FilesWorkView";
import ImportBatchesWorkView from "./ImportBatchesWorkView";
import OutlookImportWorkView from "./OutlookImportWorkView";
import WorkNav from "./WorkNav";

export type WorkView = "files" | "emails" | "outlook" | "drafts" | "batches";

type WorkHubShellProps = {
  organizationId: UUID;
};

export default function WorkHubShell({ organizationId }: WorkHubShellProps) {
  const [activeView, setActiveView] = useState<WorkView>("emails");

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Work Hub"
        description="Local files, email records, manual AI drafts, and import history for stormwater operations."
      />

      <div className="grid gap-4 xl:grid-cols-[220px_minmax(0,1fr)]">
        <div className="xl:sticky xl:top-20 xl:self-start">
          <WorkNav activeView={activeView} onChange={setActiveView} />
        </div>
        <div className="min-w-0">
          {activeView === "files" ? (
            <FilesWorkView organizationId={organizationId} />
          ) : null}
          {activeView === "emails" ? (
            <EmailsWorkView organizationId={organizationId} />
          ) : null}
          {activeView === "outlook" ? (
            <OutlookImportWorkView organizationId={organizationId} />
          ) : null}
          {activeView === "drafts" ? (
            <AiDraftsWorkView organizationId={organizationId} />
          ) : null}
          {activeView === "batches" ? (
            <ImportBatchesWorkView organizationId={organizationId} />
          ) : null}
        </div>
      </div>
    </div>
  );
}
