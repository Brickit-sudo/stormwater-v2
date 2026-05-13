"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import Badge from "@/components/ui/Badge";
import { getEmailImportBatch, listEmailImportBatches } from "@/lib/api";
import type { EmailImportBatch, EmailImportBatchStatus, UUID } from "@/lib/types";

import WorkList from "./WorkList";
import WorkPreview from "./WorkPreview";

type ImportBatchesWorkViewProps = {
  organizationId: UUID;
};

const batchLimit = 25;
const statusOptions: Array<"" | EmailImportBatchStatus> = [
  "",
  "seed",
  "previewed",
  "imported",
  "failed",
];

function formatDate(value: string | null): string {
  if (!value) return "Not set";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function statusTone(status: EmailImportBatchStatus): "success" | "warning" | "danger" | "muted" | "info" {
  if (status === "imported" || status === "seed") return "success";
  if (status === "previewed") return "info";
  if (status === "failed") return "danger";
  return "muted";
}

export default function ImportBatchesWorkView({
  organizationId,
}: ImportBatchesWorkViewProps) {
  const [batches, setBatches] = useState<EmailImportBatch[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedBatch, setSelectedBatch] = useState<EmailImportBatch | null>(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [statusFilter, setStatusFilter] = useState<"" | EmailImportBatchStatus>("");
  const [providerFilter, setProviderFilter] = useState("");
  const [loadingList, setLoadingList] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const countLabel = useMemo(
    () => `${total} local batch${total === 1 ? "" : "es"}`,
    [total],
  );

  const loadBatches = useCallback(async () => {
    setLoadingList(true);
    setError(null);
    try {
      const response = await listEmailImportBatches({
        organizationId,
        status: statusFilter || undefined,
        provider: providerFilter.trim() || undefined,
        limit: batchLimit,
        offset,
      });
      setBatches(response.items);
      setTotal(response.total);
      if (response.items.length === 0) {
        setSelectedBatch(null);
      }
      setSelectedId((current) =>
        current && response.items.some((batch) => batch.id === current)
          ? current
          : response.items[0]?.id ?? null,
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load import batches.");
    } finally {
      setLoadingList(false);
    }
  }, [offset, organizationId, providerFilter, statusFilter]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadBatches();
    }, 150);
    return () => window.clearTimeout(timer);
  }, [loadBatches]);

  useEffect(() => {
    if (!selectedId) {
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(() => {
      setLoadingPreview(true);
      getEmailImportBatch(selectedId, organizationId)
        .then((batch) => {
          if (!cancelled) setSelectedBatch(batch);
        })
        .catch((caught) => {
          if (!cancelled) {
            setError(caught instanceof Error ? caught.message : "Unable to load batch preview.");
          }
        })
        .finally(() => {
          if (!cancelled) setLoadingPreview(false);
        });
    }, 0);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [organizationId, selectedId]);

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_440px]">
      <div className="min-w-0 space-y-3">
        <section className="rounded-lg border border-border bg-panel p-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="block">
              <span className="text-sm font-medium text-text-secondary">
                Status
              </span>
              <select
                value={statusFilter}
                onChange={(event) => {
                  setStatusFilter(event.target.value as "" | EmailImportBatchStatus);
                  setOffset(0);
                }}
                className="form-input mt-2"
              >
                {statusOptions.map((status) => (
                  <option key={status || "all"} value={status}>
                    {status ? status : "All active"}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-sm font-medium text-text-secondary">
                Provider
              </span>
              <input
                value={providerFilter}
                onChange={(event) => {
                  setProviderFilter(event.target.value);
                  setOffset(0);
                }}
                className="form-input mt-2"
                placeholder="outlook"
              />
            </label>
          </div>
        </section>

        {error ? (
          <div className="rounded-md border border-[color:var(--red)]/40 bg-[color:var(--red-soft)] px-4 py-3 text-sm text-[color:var(--red)]">
            {error}
          </div>
        ) : null}

        <WorkList
          title="Import Batches"
          countLabel={countLabel}
          rows={batches}
          getRowId={(batch) => batch.id}
          selectedId={selectedId}
          onSelect={(batch) => setSelectedId(batch.id)}
          renderTitle={(batch) => `${batch.provider} - ${batch.import_mode}`}
          renderMeta={(batch) => formatDate(batch.created_at)}
          renderAside={(batch) => (
            <Badge tone={statusTone(batch.status)}>{batch.status}</Badge>
          )}
          loading={loadingList}
          emptyTitle="No import batches found"
          emptyDescription="Local seed and future import preview batches will appear here."
          page={{
            offset,
            limit: batchLimit,
            total,
            onPrevious: () => setOffset(Math.max(0, offset - batchLimit)),
            onNext: () => setOffset(offset + batchLimit),
          }}
        />
      </div>

      <WorkPreview
        title={selectedBatch ? `${selectedBatch.provider} import batch` : "Select a batch"}
        subtitle="Outlook import not connected yet."
      >
        {loadingPreview ? (
          <div className="h-32 animate-pulse rounded-md border border-border-soft bg-panel-2" />
        ) : selectedBatch ? (
          <div className="space-y-5">
            <div className="rounded-lg border border-[color:var(--yellow)]/40 bg-[color:var(--yellow-soft)] p-3 text-sm text-[color:var(--yellow)]">
              Outlook import is not connected yet. This view stores local batch metadata only.
            </div>
            <div className="grid gap-3 text-sm sm:grid-cols-2">
              <Meta label="Status" value={selectedBatch.status} />
              <Meta label="Created" value={formatDate(selectedBatch.created_at)} />
              <Meta label="Previewed" value={String(selectedBatch.preview_count)} />
              <Meta label="Imported" value={String(selectedBatch.imported_count)} />
              <Meta label="Skipped" value={String(selectedBatch.skipped_count)} />
              <Meta label="Duplicates" value={String(selectedBatch.duplicate_count)} />
              <Meta label="Errors" value={String(selectedBatch.error_count)} />
              <Meta label="Completed" value={formatDate(selectedBatch.completed_at)} />
            </div>
            <section>
              <h3 className="text-sm font-semibold text-text">Search Query</h3>
              <p className="mt-2 break-words text-sm text-text-secondary">
                {selectedBatch.search_query ?? "No search query stored."}
              </p>
            </section>
            <JsonBlock title="Request" value={selectedBatch.request_json} />
            <JsonBlock title="Result Summary" value={selectedBatch.result_summary_json} />
          </div>
        ) : (
          <p className="text-sm text-text-muted">
            Choose a local import batch to inspect its counts and metadata.
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

function JsonBlock({
  title,
  value,
}: {
  title: string;
  value: Record<string, unknown> | null;
}) {
  return (
    <section>
      <h3 className="text-sm font-semibold text-text">{title}</h3>
      <pre className="mt-2 overflow-x-auto rounded-md border border-border-soft bg-panel-2 p-3 text-xs leading-5 text-text-secondary">
        {value ? JSON.stringify(value, null, 2) : "No JSON stored."}
      </pre>
    </section>
  );
}
