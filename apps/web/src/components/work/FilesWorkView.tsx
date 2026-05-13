"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";

import type { GoogleDrivePickedFile } from "@/components/files/GoogleDrivePickerButton";
import Badge from "@/components/ui/Badge";
import { createFileLink, listClients, listFiles, listJobs, listSites } from "@/lib/api";
import type { Client, EvidenceFile, Job, Site, UUID } from "@/lib/types";
import { linkChipClass, secondaryButtonClass } from "@/lib/ui";

import WorkList from "./WorkList";
import WorkPreview from "./WorkPreview";

type FilesWorkViewProps = {
  organizationId: UUID;
};

type TargetKind = "client" | "site" | "job";

type TargetOption = {
  id: UUID;
  label: string;
};

const GoogleDrivePickerButton = dynamic(
  () => import("@/components/files/GoogleDrivePickerButton"),
  { ssr: false },
);

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

function sourceLabel(source: string | null): string {
  if (source === "google_drive") return "Google Drive";
  if (source === "drive_link") return "Drive link";
  if (source === "upload_placeholder") return "Upload placeholder";
  if (source === "report_export") return "Report export";
  if (source === "photo") return "Photo";
  if (source === "other") return "Other";
  return "File link";
}

function optionLabel(name: string, code: string | null | undefined): string {
  return code ? `${name} (${code})` : name;
}

export default function FilesWorkView({ organizationId }: FilesWorkViewProps) {
  const [files, setFiles] = useState<EvidenceFile[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [targetKind, setTargetKind] = useState<TargetKind>("job");
  const [targetId, setTargetId] = useState<UUID>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pickerError, setPickerError] = useState<string | null>(null);
  const [savingPicked, setSavingPicked] = useState(false);

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

  const targetOptions = useMemo<TargetOption[]>(() => {
    if (targetKind === "client") {
      return clients.map((client) => ({
        id: client.id,
        label: optionLabel(client.name, client.client_code),
      }));
    }
    if (targetKind === "site") {
      return sites.map((site) => ({
        id: site.id,
        label: optionLabel(site.name, site.site_code),
      }));
    }
    return jobs.map((job) => ({
      id: job.id,
      label: optionLabel(job.name, job.job_code),
    }));
  }, [clients, jobs, sites, targetKind]);

  const activeTargetId = useMemo(() => {
    if (targetOptions.some((option) => option.id === targetId)) {
      return targetId;
    }
    return targetOptions[0]?.id ?? "";
  }, [targetId, targetOptions]);

  const selectedTargetLabel = useMemo(
    () => targetOptions.find((option) => option.id === activeTargetId)?.label ?? "",
    [activeTargetId, targetOptions],
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

  async function savePickedDriveFile(file: GoogleDrivePickedFile) {
    if (!activeTargetId) {
      const message = "Choose a Client, Site, or Job before selecting a Drive file.";
      setPickerError(message);
      throw new Error(message);
    }

    setSavingPicked(true);
    setPickerError(null);
    try {
      const saved = await createFileLink(organizationId, {
        file_name: file.name,
        source: "google_drive",
        public_url: file.url,
        drive_file_id: file.drive_file_id,
        mime_type: file.mime_type,
        client_id: targetKind === "client" ? activeTargetId : null,
        site_id: targetKind === "site" ? activeTargetId : null,
        job_id: targetKind === "job" ? activeTargetId : null,
      });
      await loadFiles();
      setSelectedId(saved.id);
    } catch (caught) {
      const message =
        caught instanceof Error
          ? caught.message
          : "Couldn't save the selected Drive file metadata.";
      setPickerError(message);
      throw new Error(message);
    } finally {
      setSavingPicked(false);
    }
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_440px]">
      <div className="min-w-0 space-y-3">
        <section className="rounded-lg border border-border bg-panel p-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h2 className="text-sm font-semibold text-text">Attach Drive file</h2>
              <p className="mt-1 text-xs leading-5 text-text-muted">
                Pick a target record first. Selection stores file metadata only.
              </p>
            </div>
            <button
              type="button"
              className={secondaryButtonClass}
              onClick={() => void loadFiles()}
              disabled={loading}
            >
              {loading ? "Refreshing..." : "Refresh Files"}
            </button>
          </div>

          <div className="mt-4 grid gap-3 lg:grid-cols-[150px_minmax(0,1fr)_auto] lg:items-start">
            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted">
                Target type
              </span>
              <select
                value={targetKind}
                onChange={(event) => {
                  setTargetKind(event.target.value as TargetKind);
                  setPickerError(null);
                }}
                className="form-input mt-2"
              >
                <option value="job">Job</option>
                <option value="site">Site</option>
                <option value="client">Client</option>
              </select>
            </label>

            <label className="block">
              <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted">
                Target record
              </span>
              <select
                value={activeTargetId}
                onChange={(event) => {
                  setTargetId(event.target.value);
                  setPickerError(null);
                }}
                className="form-input mt-2"
                disabled={targetOptions.length === 0}
              >
                {targetOptions.length > 0 ? (
                  targetOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))
                ) : (
                  <option value="">No records loaded</option>
                )}
              </select>
            </label>

            <GoogleDrivePickerButton
              label={savingPicked ? "Saving..." : "Select from Google Drive"}
              onPicked={savePickedDriveFile}
              disabled={loading || savingPicked || !activeTargetId}
              className="lg:text-right"
            />
          </div>

          {selectedTargetLabel ? (
            <p className="mt-3 text-xs text-text-muted">
              New selections attach to {selectedTargetLabel}.
            </p>
          ) : null}

          {pickerError ? (
            <div className="mt-3 rounded-md border border-[color:var(--red)]/40 bg-[color:var(--red-soft)] px-3 py-2 text-sm text-[color:var(--red)]">
              {pickerError}
            </div>
          ) : null}
        </section>

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
          emptyDescription="Evidence file metadata will appear here after a CRM panel link or reviewed Drive Picker selection is saved."
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
              <Meta label="File name" value={selectedFile.file_name} />
              <Meta label="Source" value={sourceLabel(selectedFile.source)} />
              <Meta label="Linked parent" value={linkedLabel(selectedFile)} />
              <Meta label="MIME type" value={selectedFile.mime_type ?? "Not set"} />
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
