import type { ReactNode } from "react";

import { cardClass } from "@/lib/ui";

import EmptyState from "./EmptyState";

export type EntityColumn<T> = {
  key: string;
  header: string;
  className?: string;
  render: (row: T) => ReactNode;
};

type EntityTableProps<T> = {
  rows: T[];
  columns: EntityColumn<T>[];
  getRowId: (row: T) => string;
  selectedRowId?: string | null;
  onRowClick: (row: T) => void;
  loading?: boolean;
  emptyTitle: string;
  emptyDescription?: string;
};

export default function EntityTable<T>({
  rows,
  columns,
  getRowId,
  selectedRowId,
  onRowClick,
  loading = false,
  emptyTitle,
  emptyDescription,
}: EntityTableProps<T>) {
  if (loading) {
    return (
      <div className={`${cardClass} overflow-hidden`}>
        <div className="border-b border-border-soft bg-panel-2 px-4 py-3">
          <div className="h-3.5 w-44 animate-pulse rounded bg-border" />
        </div>
        <div className="divide-y divide-border-soft">
          {Array.from({ length: 6 }).map((_, index) => (
            <div
              key={index}
              className="grid grid-cols-5 gap-4 px-4 py-4"
              aria-hidden="true"
            >
              {Array.from({ length: 5 }).map((__, cellIndex) => (
                <div
                  key={cellIndex}
                  className="h-3.5 animate-pulse rounded bg-panel-2"
                />
              ))}
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (rows.length === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }

  return (
    <div className={`${cardClass} overflow-hidden`}>
      <div className="overflow-x-auto">
        <table className="min-w-full table-fixed">
          <thead>
            <tr className="border-b border-border-soft bg-panel-2/60">
              {columns.map((column) => (
                <th
                  key={column.key}
                  scope="col"
                  className={[
                    "px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted",
                    column.className,
                  ]
                    .filter(Boolean)
                    .join(" ")}
                >
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border-soft">
            {rows.map((row) => {
              const rowId = getRowId(row);
              const selected = rowId === selectedRowId;

              return (
                <tr
                  key={rowId}
                  onClick={() => onRowClick(row)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onRowClick(row);
                    }
                  }}
                  tabIndex={0}
                  aria-selected={selected}
                  className={[
                    "group cursor-pointer transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-green",
                    selected
                      ? "bg-[color:var(--green-soft)] shadow-[inset_2px_0_0_var(--green)]"
                      : "hover:bg-panel-2",
                  ].join(" ")}
                >
                  {columns.map((column) => (
                    <td
                      key={column.key}
                      className={[
                        "truncate px-4 py-3 text-sm",
                        selected ? "text-text" : "text-text-secondary",
                        column.className,
                      ]
                        .filter(Boolean)
                        .join(" ")}
                    >
                      {column.render(row)}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
