"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import Badge from "@/components/ui/Badge";
import { listClients, listFiles, listJobs, listSites } from "@/lib/api";
import type { Client, EvidenceFile, Job, Site, UUID } from "@/lib/types";
import { linkChipClass } from "@/lib/ui";

import WorkList from "./WorkList";
import WorkPreview from "./WorkPreview";

type FilesWorkViewProps = {
  organizationId: UUID;
};

function formatBytes(value: number | null): string {
  if (!value || value <= 0) {
    return "Size not set";
  }
  if (value < 1024) {
    return `${value} bytes`;
  }
  if (value < 1024 * 1024) {
    return `${Math.round(value / 1024)} KB`;
  }
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function fileScope(file: EvidenceFile): "client" | "site" | "job" | "none" {
  if (file.job_id) return "job";
  if (file.site_id) return "site";
  if (file.client_id) return "client";
  return "none";
}

export default function FilesWorkView({ organizationId }: FilesWorkViewProps) {
  const [files, setFiles] = useState<EvidenceFile[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clientNameById = useMemo(
    () => new Map(clients.map((client) => [client.id, client.name])),
    [clients],
  );
  const siteNameById = useMemo(
    () => new Map(sites.map((site) => [site.id, site.name])),
    [sites],
  );
  const jobNameById = useMemo(
    () => new Map(jobs.map((job) => [job.id, job.name])),
    [jobs],
  );

  const selectedFile = useMemo(
    () => files.find((file) => file.id === selectedId) ?? null,
    [files, selectedId],
  );

  const linkedLabel = useCallback(
    (file: EvidenceFile): string => {
      if (file.job_id) return jobNameById.get(file.job_id) ?? "Linked job";
      if (file.site_id) return siteNameById.get(file.site_id) ?? "Linked site";
      if (file.client_id) return clientNameById.get(file.client_id) ?? "Linked client";
      return "No linked CRM record";
    },
    [clientNameById, jobNameById, siteNameById],
  );

  const loadFiles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [fileResponse, clientResponse, siteResponse, jobResponse] =
        await Promise.all([
          listFiles({ organizationId, limit: 100 }),
          listClients({ organizationId, limit: 500 }),
          listSites({ organizationId, limit: 500 }),
          listJobs({ organizationId, limit: 500 }),
        ]);
      setFiles(fileResponse.items);
      setClients(clientResponse.items);
      setSites(siteResponse.items);
      setJobs(jobResponse.items);
      setSelectedId((current) =>
        current && fileResponse.items.some((file) => file.id === current)
          ? current
          : fileResponse.items[0]?.id ?? null,
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load files.");
    } finally {
      setLoading(false);
    }
  }, [organizationId]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadFiles();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadFiles]);

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_440px]">
      <div className="min-w-0 space-y-3">
        {error ? (
          <div className="rounded-md border border-[color:var(--red)]/40 bg-[color:var(--red-soft)] px-4 py-3 text-sm text-[color:var(--red)]">
            {error}
          </div>
        ) : null}

        <WorkList
          title="Files"
          countLabel={`${files.length} local file links`}
          rows={files}
          getRowId={(file) => file.id}
          selectedId={selectedId}
          onSelect={(file) => setSelectedId(file.id)}
          renderTitle={(file) => file.file_name}
          renderMeta={(file) => linkedLabel(file)}
          renderAside={(file) => <Badge tone="info">{fileScope(file)}</Badge>}
          loading={loading}
          emptyTitle="No files found"
          emptyDescription="Evidence file links will appear here from the existing Files foundation."
        />
      </div>

      <WorkPreview
        title={selectedFile?.file_name ?? "Select a file"}
        subtitle={selectedFile ? linkedLabel(selectedFile) : "File metadata preview"}
        actions={
          selectedFile?.public_url ? (
            <a
              href={selectedFile.public_url}
              target="_blank"
              rel="noreferrer noopener"
              className={linkChipClass}
            >
              Open File
            </a>
          ) : null
        }
      >
        {selectedFile ? (
          <div className="space-y-5">
            <div className="grid gap-3 text-sm sm:grid-cols-2">
              <Meta label="Source" value={selectedFile.source ?? "File link"} />
              <Meta label="MIME" value={selectedFile.mime_type ?? "Not set"} />
              <Meta label="Size" value={formatBytes(selectedFile.size_bytes)} />
              <Meta label="Created" value={formatDate(selectedFile.created_at)} />
            </div>
            {selectedFile.caption ? (
              <section>
                <h3 className="text-sm font-semibold text-text">Caption</h3>
                <p className="mt-2 text-sm leading-6 text-text-secondary">
                  {selectedFile.caption}
                </p>
              </section>
            ) : null}
            <section>
              <h3 className="text-sm font-semibold text-text">Stored URL</h3>
              <p className="mt-2 break-all text-sm text-text-secondary">
                {selectedFile.public_url ?? "No URL stored for this file link."}
              </p>
            </section>
          </div>
        ) : (
          <p className="text-sm text-text-muted">
            Choose a file link to inspect its stored metadata.
          </p>
        )}
      </WorkPreview>
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border-soft bg-panel-2 p-3">
      <dt className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted">
        {label}
      </dt>
      <dd className="mt-1 break-words text-sm text-text">{value}</dd>
    </div>
  );
}
