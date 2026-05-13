"use client";

import type { ReactNode } from "react";

import { secondaryButtonClass } from "@/lib/ui";

type WorkListProps<T> = {
  title: string;
  countLabel: string;
  rows: T[];
  getRowId: (row: T) => string;
  selectedId: string | null;
  onSelect: (row: T) => void;
  renderTitle: (row: T) => ReactNode;
  renderMeta?: (row: T) => ReactNode;
  renderAside?: (row: T) => ReactNode;
  loading?: boolean;
  emptyTitle: string;
  emptyDescription?: string;
  page?: {
    offset: number;
    limit: number;
    total: number;
    onPrevious: () => void;
    onNext: () => void;
  };
};

export default function WorkList<T>({
  title,
  countLabel,
  rows,
  getRowId,
  selectedId,
  onSelect,
  renderTitle,
  renderMeta,
  renderAside,
  loading = false,
  emptyTitle,
  emptyDescription,
  page,
}: WorkListProps<T>) {
  return (
    <section className="min-w-0 rounded-lg border border-border bg-panel">
      <div className="flex items-center justify-between gap-3 border-b border-border-soft px-4 py-3">
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-text">{title}</h2>
          <p className="mt-1 text-xs text-text-muted">{countLabel}</p>
        </div>
        {page ? (
          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              className={secondaryButtonClass}
              onClick={page.onPrevious}
              disabled={loading || page.offset === 0}
            >
              Previous
            </button>
            <button
              type="button"
              className={secondaryButtonClass}
              onClick={page.onNext}
              disabled={loading || page.offset + page.limit >= page.total}
            >
              Next
            </button>
          </div>
        ) : null}
      </div>

      {loading ? (
        <div className="space-y-2 p-3">
          {[0, 1, 2, 3].map((index) => (
            <div
              key={index}
              className="h-16 animate-pulse rounded-md border border-border-soft bg-panel-2"
            />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <div className="px-4 py-10 text-center">
          <p className="text-sm font-semibold text-text">{emptyTitle}</p>
          {emptyDescription ? (
            <p className="mx-auto mt-2 max-w-sm text-sm text-text-muted">
              {emptyDescription}
            </p>
          ) : null}
        </div>
      ) : (
        <div className="divide-y divide-border-soft">
          {rows.map((row) => {
            const id = getRowId(row);
            const selected = id === selectedId;
            return (
              <button
                key={id}
                type="button"
                className={[
                  "grid w-full grid-cols-[minmax(0,1fr)_auto] gap-3 px-4 py-3 text-left transition",
                  selected
                    ? "bg-green-soft shadow-[inset_3px_0_0_var(--green)]"
                    : "hover:bg-panel-2",
                ].join(" ")}
                onClick={() => onSelect(row)}
              >
                <span className="min-w-0">
                  <span className="block truncate text-sm font-semibold text-text">
                    {renderTitle(row)}
                  </span>
                  {renderMeta ? (
                    <span className="mt-1 block text-xs text-text-muted">
                      {renderMeta(row)}
                    </span>
                  ) : null}
                </span>
                {renderAside ? (
                  <span className="shrink-0 text-right text-xs text-text-muted">
                    {renderAside(row)}
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}
