"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useState, type ReactNode } from "react";

import Badge from "@/components/ui/Badge";
import {
  archiveFileLink,
  createFileLink,
  listFiles,
} from "@/lib/api";
import type {
  EvidenceFile,
  EvidenceFileCreateInput,
  UUID,
} from "@/lib/types";
import type { GoogleDrivePickedFile } from "@/components/files/GoogleDrivePickerButton";
import {
  linkChipClass,
  primaryButtonClass,
  secondaryButtonClass,
} from "@/lib/ui";

type DriveFilePanelProps = {
  organizationId: UUID;
  clientId?: UUID;
  siteId?: UUID;
  jobId?: UUID;
  driveFolderUrl?: string | null;
  selectedRecordLabel?: string;
};

const GoogleDrivePickerButton = dynamic(
  () => import("@/components/files/GoogleDrivePickerButton"),
  { ssr: false },
);

type AddFormState = {
  file_name: string;
  public_url: string;
  source: "drive_link" | "other";
  mime_type: string;
  caption: string;
};

const emptyForm: AddFormState = {
  file_name: "",
  public_url: "",
  source: "drive_link",
  mime_type: "",
  caption: "",
};

function trimOrNull(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function emptyCopyForScope(props: DriveFilePanelProps): string {
  if (props.clientId) {
    return "No files linked to this client yet.";
  }
  if (props.siteId) {
    return "No files linked to this site yet.";
  }
  if (props.jobId) {
    return "No files linked to this job yet.";
  }
  return "No files linked yet.";
}

function SourceBadge({ source }: { source: string | null }) {
  const label =
    source === "google_drive"
      ? "Google Drive"
      : source === "drive_link"
      ? "Drive link"
      : source === "other"
        ? "Other"
        : "File link";
  return <Badge tone="info">{label}</Badge>;
}

function FormField({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-text-secondary">{label}</span>
      <div className="mt-2">{children}</div>
    </label>
  );
}

function shouldRenderMime(mime: string | null): boolean {
  if (!mime) return false;
  const trimmed = mime.trim().toLowerCase();
  if (!trimmed) return false;
  if (trimmed === "application/octet-stream") return false;
  return true;
}

export default function DriveFilePanel(props: DriveFilePanelProps) {
  const {
    organizationId,
    clientId,
    siteId,
    jobId,
    driveFolderUrl,
  } = props;

  const scopeId = clientId ?? siteId ?? jobId ?? null;

  const [files, setFiles] = useState<EvidenceFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<AddFormState>(emptyForm);
  const [formError, setFormError] = useState<string | null>(null);
  const [pickerSaving, setPickerSaving] = useState(false);
  const [pickerError, setPickerError] = useState<string | null>(null);

  const loadFiles = useCallback(async () => {
    if (!organizationId || !scopeId) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await listFiles({
        organizationId,
        clientId,
        siteId,
        jobId,
        limit: 100,
      });
      setFiles(response.items);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Couldn't load files. Try again.",
      );
    } finally {
      setLoading(false);
    }
  }, [organizationId, scopeId, clientId, siteId, jobId]);

  useEffect(() => {
    if (!scopeId) {
      return;
    }
    const timer = window.setTimeout(() => {
      void loadFiles();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadFiles, scopeId]);

  if (!organizationId || !scopeId) {
    return null;
  }

  function updateForm<K extends keyof AddFormState>(field: K, value: AddFormState[K]) {
    setForm({ ...form, [field]: value });
  }

  function startAdd() {
    setForm(emptyForm);
    setFormError(null);
    setAdding(true);
  }

  function cancelAdd() {
    setAdding(false);
    setFormError(null);
    setForm(emptyForm);
  }

  async function submitAdd() {
    const fileName = form.file_name.trim();
    if (!fileName) {
      setFormError("File name is required.");
      return;
    }

    const input: EvidenceFileCreateInput = {
      file_name: fileName,
      source: form.source,
      public_url: trimOrNull(form.public_url),
      mime_type: trimOrNull(form.mime_type),
      caption: trimOrNull(form.caption),
      client_id: clientId ?? null,
      site_id: siteId ?? null,
      job_id: jobId ?? null,
    };

    setSaving(true);
    setFormError(null);
    try {
      await createFileLink(organizationId, input);
      setAdding(false);
      setForm(emptyForm);
      await loadFiles();
    } catch (caught) {
      setFormError(
        caught instanceof Error
          ? caught.message
          : "Couldn't save your changes. Try again, or check the highlighted fields.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function savePickedDriveFile(file: GoogleDrivePickedFile) {
    const input: EvidenceFileCreateInput = {
      file_name: file.name,
      source: "google_drive",
      public_url: file.url,
      drive_file_id: file.drive_file_id,
      mime_type: file.mime_type,
      client_id: clientId ?? null,
      site_id: siteId ?? null,
      job_id: jobId ?? null,
    };

    setPickerSaving(true);
    setPickerError(null);
    try {
      await createFileLink(organizationId, input);
      await loadFiles();
    } catch (caught) {
      const message =
        caught instanceof Error
          ? caught.message
          : "Couldn't save the selected Drive file metadata.";
      setPickerError(message);
      throw new Error(message);
    } finally {
      setPickerSaving(false);
    }
  }

  async function archiveFile(file: EvidenceFile) {
    const confirmed = window.confirm(
      "Archive this file link? It will be hidden from the default view. This does not delete the actual file in Drive.",
    );
    if (!confirmed) {
      return;
    }
    setError(null);
    try {
      await archiveFileLink(file.id, organizationId);
      await loadFiles();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Couldn't archive the file link.",
      );
    }
  }

  return (
    <section className="space-y-4 rounded-lg border border-border-soft bg-panel-2 p-4">
      <div className="flex flex-col gap-1">
        <h3 className="text-sm font-semibold text-text">Files & Drive</h3>
        <p className="text-xs text-text-muted">
          Store reviewed file metadata for this record. Google Picker selection
          is manual and does not sync, download, or scan Drive folders.
        </p>
      </div>

      <div className="rounded-lg border border-border-soft bg-panel p-3">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted">
              Drive folder
            </p>
            {driveFolderUrl ? (
              <p className="mt-1 truncate text-sm text-text" title={driveFolderUrl}>
                {driveFolderUrl}
              </p>
            ) : (
              <p className="mt-1 text-sm text-text-muted">
                No Drive folder linked yet.
              </p>
            )}
          </div>
          {driveFolderUrl ? (
            <a
              href={driveFolderUrl}
              target="_blank"
              rel="noreferrer noopener"
              className={linkChipClass}
            >
              Open Drive Folder
            </a>
          ) : null}
        </div>
      </div>

      <div className="flex items-center justify-between gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted">
          Linked files
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            className={secondaryButtonClass}
            onClick={() => void loadFiles()}
            disabled={loading || adding}
          >
            Refresh
          </button>
          <GoogleDrivePickerButton
            label={pickerSaving ? "Saving..." : "Select from Google Drive"}
            onPicked={savePickedDriveFile}
            disabled={loading || adding || pickerSaving}
            className="text-right"
          />
          <button
            type="button"
            className={primaryButtonClass}
            onClick={startAdd}
            disabled={adding}
          >
            Add File Link
          </button>
        </div>
      </div>

      {pickerError ? (
        <div className="rounded-md border border-[color:var(--red)]/40 bg-[color:var(--red-soft)] px-3 py-2 text-sm text-[color:var(--red)]">
          {pickerError}
        </div>
      ) : null}

      {error ? (
        <div className="rounded-md border border-[color:var(--red)]/40 bg-[color:var(--red-soft)] px-3 py-2 text-sm text-[color:var(--red)]">
          {error}
        </div>
      ) : null}

      {adding ? (
        <form
          className="space-y-3 rounded-lg border border-border-soft bg-panel p-3"
          onSubmit={(event) => {
            event.preventDefault();
            void submitAdd();
          }}
        >
          <FormField label="File name">
            <input
              value={form.file_name}
              onChange={(event) => updateForm("file_name", event.target.value)}
              className="form-input"
              required
              maxLength={255}
              placeholder="e.g. Site Plan v3.pdf"
            />
          </FormField>
          <FormField label="File URL">
            <input
              value={form.public_url}
              onChange={(event) => updateForm("public_url", event.target.value)}
              className="form-input"
              placeholder="https://drive.google.com/..."
            />
          </FormField>
          <div className="grid gap-3 sm:grid-cols-2">
            <FormField label="Source">
              <select
                value={form.source}
                onChange={(event) =>
                  updateForm("source", event.target.value as AddFormState["source"])
                }
                className="form-input"
              >
                <option value="drive_link">Drive link</option>
                <option value="other">Other</option>
              </select>
            </FormField>
            <FormField label="MIME type (optional)">
              <input
                value={form.mime_type}
                onChange={(event) => updateForm("mime_type", event.target.value)}
                className="form-input"
                placeholder="application/pdf"
              />
            </FormField>
          </div>
          <FormField label="Caption (optional)">
            <input
              value={form.caption}
              onChange={(event) => updateForm("caption", event.target.value)}
              className="form-input"
            />
          </FormField>

          {formError ? (
            <div className="rounded-md border border-[color:var(--red)]/40 bg-[color:var(--red-soft)] px-3 py-2 text-sm text-[color:var(--red)]">
              {formError}
            </div>
          ) : null}

          <div className="flex justify-end gap-2">
            <button
              type="button"
              className={secondaryButtonClass}
              onClick={cancelAdd}
              disabled={saving}
            >
              Cancel
            </button>
            <button type="submit" className={primaryButtonClass} disabled={saving}>
              {saving ? "Saving..." : "Save File Link"}
            </button>
          </div>
        </form>
      ) : null}

      {loading ? (
        <div className="space-y-2">
          {[0, 1, 2].map((index) => (
            <div
              key={index}
              className="h-12 animate-pulse rounded-md border border-border-soft bg-panel"
            />
          ))}
        </div>
      ) : files.length === 0 ? (
        <p className="rounded-lg border border-dashed border-border-strong bg-panel px-3 py-4 text-center text-sm text-text-muted">
          {emptyCopyForScope(props)}
        </p>
      ) : (
        <ul className="divide-y divide-border-soft rounded-lg border border-border-soft bg-panel">
          {files.map((file) => (
            <li key={file.id} className="px-3 py-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="break-words text-sm font-semibold text-text">
                      {file.file_name}
                    </span>
                    <SourceBadge source={file.source} />
                  </div>
                  {file.caption ? (
                    <p className="text-xs text-text-secondary">{file.caption}</p>
                  ) : null}
                  <div className="flex flex-wrap gap-3 text-xs text-text-muted">
                    {shouldRenderMime(file.mime_type) ? (
                      <span>{file.mime_type}</span>
                    ) : null}
                    {file.size_bytes && file.size_bytes > 0 ? (
                      <span>{file.size_bytes} bytes</span>
                    ) : null}
                  </div>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-2">
                  {file.public_url ? (
                    <a
                      href={file.public_url}
                      target="_blank"
                      rel="noreferrer noopener"
                      className={linkChipClass}
                    >
                      Open
                    </a>
                  ) : null}
                  <button
                    type="button"
                    className="text-xs font-medium text-[color:var(--red)] hover:underline"
                    onClick={() => void archiveFile(file)}
                  >
                    Archive
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
