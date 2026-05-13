"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import Badge from "@/components/ui/Badge";
import {
  getOutlookStatus,
  importSelectedOutlookMessages,
  previewOutlookMessages,
} from "@/lib/api";
import type {
  OutlookImportSelectedResponse,
  OutlookPreviewMessage,
  OutlookStatus,
  UUID,
} from "@/lib/types";
import { primaryButtonClass, secondaryButtonClass } from "@/lib/ui";

type OutlookImportWorkViewProps = {
  organizationId: UUID;
};

type PreviewForm = {
  searchQuery: string;
  dateFrom: string;
  dateTo: string;
  limit: string;
  folderId: string;
  accessToken: string;
};

const defaultForm: PreviewForm = {
  searchQuery: "",
  dateFrom: "",
  dateTo: "",
  limit: "25",
  folderId: "",
  accessToken: "",
};

function optional(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function dateStart(value: string): string | null {
  return value ? `${value}T00:00:00Z` : null;
}

function dateEnd(value: string): string | null {
  return value ? `${value}T23:59:59Z` : null;
}

function parseLimit(value: string): number {
  const numeric = Number.parseInt(value, 10);
  if (Number.isNaN(numeric)) {
    return 25;
  }
  return Math.max(1, numeric);
}

function formatDate(value: string | null): string {
  if (!value) {
    return "No received date";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export default function OutlookImportWorkView({
  organizationId,
}: OutlookImportWorkViewProps) {
  const [status, setStatus] = useState<OutlookStatus | null>(null);
  const [form, setForm] = useState<PreviewForm>(defaultForm);
  const [previewItems, setPreviewItems] = useState<OutlookPreviewMessage[]>([]);
  const [hasPreviewed, setHasPreviewed] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());
  const [importResult, setImportResult] =
    useState<OutlookImportSelectedResponse | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedMessages = useMemo(
    () =>
      previewItems.filter((message) =>
        selectedIds.has(message.provider_message_id),
      ),
    [previewItems, selectedIds],
  );

  const loadStatus = useCallback(async () => {
    setLoadingStatus(true);
    setError(null);
    try {
      setStatus(await getOutlookStatus());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load Outlook status.");
    } finally {
      setLoadingStatus(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadStatus();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadStatus]);

  function updateForm(field: keyof PreviewForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function toggleSelected(messageId: string) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (next.has(messageId)) {
        next.delete(messageId);
      } else {
        next.add(messageId);
      }
      return next;
    });
  }

  async function runPreview() {
    setPreviewing(true);
    setError(null);
    setImportResult(null);
    try {
      const response = await previewOutlookMessages({
        organization_id: organizationId,
        search_query: optional(form.searchQuery),
        folder_id: optional(form.folderId),
        date_from: dateStart(form.dateFrom),
        date_to: dateEnd(form.dateTo),
        limit: parseLimit(form.limit),
        access_token: optional(form.accessToken),
      });
      setPreviewItems(response.items);
      setSelectedIds(new Set());
      setHasPreviewed(true);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to preview Outlook emails.");
    } finally {
      setPreviewing(false);
    }
  }

  async function importSelected() {
    if (selectedMessages.length === 0) {
      setError("Select at least one previewed email to import.");
      return;
    }

    setImporting(true);
    setError(null);
    try {
      const response = await importSelectedOutlookMessages({
        organization_id: organizationId,
        search_query: optional(form.searchQuery),
        folder_id: optional(form.folderId),
        date_from: dateStart(form.dateFrom),
        date_to: dateEnd(form.dateTo),
        limit: parseLimit(form.limit),
        selected_messages: selectedMessages,
      });
      setImportResult(response);
      setSelectedIds(new Set());
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to import selected emails.");
    } finally {
      setImporting(false);
    }
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
      <div className="min-w-0 space-y-4">
        <StatusPanel
          status={status}
          loading={loadingStatus}
        />

        <section className="rounded-lg border border-border bg-panel p-4">
          <div className="grid gap-3 md:grid-cols-2">
            <FormField label="Search Query">
              <input
                value={form.searchQuery}
                onChange={(event) => updateForm("searchQuery", event.target.value)}
                className="form-input"
                placeholder="stormwater OR catch basin"
              />
            </FormField>
            <FormField label="Folder ID">
              <input
                value={form.folderId}
                onChange={(event) => updateForm("folderId", event.target.value)}
                className="form-input"
                placeholder="inbox"
              />
            </FormField>
            <FormField label="Date From">
              <input
                type="date"
                value={form.dateFrom}
                onChange={(event) => updateForm("dateFrom", event.target.value)}
                className="form-input"
              />
            </FormField>
            <FormField label="Date To">
              <input
                type="date"
                value={form.dateTo}
                onChange={(event) => updateForm("dateTo", event.target.value)}
                className="form-input"
              />
            </FormField>
            <FormField label="Limit">
              <input
                type="number"
                min={1}
                max={100}
                value={form.limit}
                onChange={(event) => updateForm("limit", event.target.value)}
                className="form-input"
              />
            </FormField>
            <FormField label="Access Token">
              <input
                type="password"
                value={form.accessToken}
                onChange={(event) => updateForm("accessToken", event.target.value)}
                className="form-input"
                placeholder="Request token for preview MVP"
                autoComplete="off"
              />
            </FormField>
          </div>
          <div className="mt-4 flex flex-wrap justify-end gap-2">
            {hasPreviewed ? (
              <button
                type="button"
                className={secondaryButtonClass}
                onClick={() => void runPreview()}
                disabled={previewing || importing}
              >
                Refresh Preview
              </button>
            ) : null}
            <button
              type="button"
              className={primaryButtonClass}
              onClick={() => void runPreview()}
              disabled={previewing || importing}
            >
              {previewing ? "Previewing..." : "Preview Outlook Emails"}
            </button>
          </div>
        </section>

        {error ? (
          <div className="rounded-md border border-[color:var(--red)]/40 bg-[color:var(--red-soft)] px-4 py-3 text-sm text-[color:var(--red)]">
            {error}
          </div>
        ) : null}

        <section className="rounded-lg border border-border bg-panel">
          <div className="flex items-center justify-between gap-3 border-b border-border-soft px-4 py-3">
            <div className="min-w-0">
              <h2 className="text-base font-semibold text-text">Preview Results</h2>
              <p className="mt-1 text-xs text-text-muted">
                {previewItems.length} messages, {selectedMessages.length} selected
              </p>
            </div>
            {previewItems.length > 0 ? (
              <button
                type="button"
                className={primaryButtonClass}
                onClick={() => void importSelected()}
                disabled={previewing || importing}
              >
                {importing ? "Importing..." : "Import Selected Emails"}
              </button>
            ) : null}
          </div>

          {previewing ? (
            <div className="space-y-2 p-3">
              {[0, 1, 2].map((index) => (
                <div
                  key={index}
                  className="h-20 animate-pulse rounded-md border border-border-soft bg-panel-2"
                />
              ))}
            </div>
          ) : previewItems.length === 0 ? (
            <div className="px-4 py-10 text-center">
              <p className="text-sm font-semibold text-text">No preview loaded</p>
              <p className="mx-auto mt-2 max-w-sm text-sm text-text-muted">
                Use Preview Outlook Emails to fetch a bounded message list.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-border-soft">
              {previewItems.map((message) => {
                const selected = selectedIds.has(message.provider_message_id);
                return (
                  <label
                    key={message.provider_message_id}
                    className={[
                      "grid cursor-pointer grid-cols-[auto_minmax(0,1fr)_auto] gap-3 px-4 py-3 transition",
                      selected ? "bg-green-soft" : "hover:bg-panel-2",
                    ].join(" ")}
                  >
                    <input
                      type="checkbox"
                      className="mt-1 h-4 w-4 accent-[color:var(--green)]"
                      checked={selected}
                      onChange={() => toggleSelected(message.provider_message_id)}
                    />
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-semibold text-text">
                        {message.subject}
                      </span>
                      <span className="mt-1 block truncate text-xs text-text-muted">
                        {message.sender} - {formatDate(message.received_at)}
                      </span>
                      {message.snippet ? (
                        <span className="mt-2 block max-h-10 overflow-hidden text-sm leading-5 text-text-secondary">
                          {message.snippet}
                        </span>
                      ) : null}
                    </span>
                    <span className="shrink-0 text-right">
                      {message.has_attachments ? (
                        <Badge tone="warning">attachment</Badge>
                      ) : (
                        <Badge tone="muted">mail</Badge>
                      )}
                    </span>
                  </label>
                );
              })}
            </div>
          )}
        </section>
      </div>

      <aside className="min-w-0 rounded-lg border border-border bg-panel">
        <div className="border-b border-border-soft px-4 py-3">
          <h2 className="text-base font-semibold text-text">Import Summary</h2>
          <p className="mt-1 text-xs text-text-muted">
            Imported messages become local email records.
          </p>
        </div>
        <div className="space-y-5 p-4">
          {importResult ? (
            <>
              <div className="grid gap-3 text-sm sm:grid-cols-2">
                <Meta label="Imported" value={String(importResult.imported_count)} />
                <Meta label="Skipped" value={String(importResult.skipped_count)} />
                <Meta label="Duplicates" value={String(importResult.duplicate_count)} />
                <Meta label="Errors" value={String(importResult.error_count)} />
              </div>
              <section>
                <h3 className="text-sm font-semibold text-text">Batch</h3>
                <p className="mt-2 break-all text-sm text-text-secondary">
                  {importResult.batch.id}
                </p>
              </section>
              {importResult.imported_messages.length > 0 ? (
                <section>
                  <h3 className="text-sm font-semibold text-text">Imported Emails</h3>
                  <ul className="mt-2 divide-y divide-border-soft rounded-lg border border-border-soft bg-panel-2">
                    {importResult.imported_messages.map((message) => (
                      <li key={message.id} className="px-3 py-2 text-sm">
                        <p className="truncate font-semibold text-text">{message.subject}</p>
                        <p className="mt-1 truncate text-xs text-text-muted">
                          {message.sender}
                        </p>
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}
            </>
          ) : (
            <p className="text-sm text-text-muted">
              Import results will appear after selected preview messages are stored locally.
            </p>
          )}
        </div>
      </aside>
    </div>
  );
}

function StatusPanel({
  status,
  loading,
}: {
  status: OutlookStatus | null;
  loading: boolean;
}) {
  const configured = Boolean(status?.configured);
  const checking = loading || !status;
  return (
    <section className="rounded-lg border border-border bg-panel p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-base font-semibold text-text">Outlook Status</h2>
            {checking ? (
              <Badge tone="muted">checking</Badge>
            ) : (
              <Badge tone={configured ? "success" : "warning"}>
                {configured ? "configured" : "not configured"}
              </Badge>
            )}
          </div>
          {status ? (
            <p className="mt-2 break-words text-sm text-text-secondary">
              {status.message}
            </p>
          ) : null}
        </div>
      </div>
      {status && !status.configured ? (
        <div className="mt-4 rounded-md border border-[color:var(--yellow)]/40 bg-[color:var(--yellow-soft)] p-3 text-sm text-[color:var(--yellow)]">
          Set {status.missing_fields.join(", ")} in <code>apps/api/.env</code> and restart the API.
        </div>
      ) : null}
      {status ? (
        <div className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
          <Meta label="Graph URL" value={status.graph_base_url} />
          <Meta label="Auth Mode" value={status.auth_mode} />
        </div>
      ) : null}
    </section>
  );
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
