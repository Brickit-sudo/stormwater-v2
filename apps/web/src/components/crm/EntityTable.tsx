import type { ReactNode } from "react";

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
      <div className="overflow-hidden rounded-md border border-[#dbe1d8] bg-white">
        <div className="border-b border-[#e3e8e0] bg-[#f8faf7] px-4 py-3">
          <div className="h-4 w-44 animate-pulse rounded bg-[#dfe6dc]" />
        </div>
        <div className="divide-y divide-[#edf0eb]">
          {Array.from({ length: 6 }).map((_, index) => (
            <div
              key={index}
              className="grid grid-cols-5 gap-4 px-4 py-4"
              aria-hidden="true"
            >
              {Array.from({ length: 5 }).map((__, cellIndex) => (
                <div
                  key={cellIndex}
                  className="h-4 animate-pulse rounded bg-[#edf1ea]"
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
    <div className="overflow-hidden rounded-md border border-[#dbe1d8] bg-white">
      <div className="overflow-x-auto">
        <table className="min-w-full table-fixed divide-y divide-[#e3e8e0]">
          <thead className="bg-[#f8faf7]">
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  scope="col"
                  className={[
                    "px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.08em] text-[#667466]",
                    column.className,
                  ].join(" ")}
                >
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[#edf0eb]">
            {rows.map((row) => {
              const rowId = getRowId(row);
              const selected = rowId === selectedRowId;

              return (
                <tr
                  key={rowId}
                  onClick={() => onRowClick(row)}
                  className={[
                    "cursor-pointer transition hover:bg-[#f8faf7]",
                    selected ? "bg-[#eef8ef]" : "bg-white",
                  ].join(" ")}
                >
                  {columns.map((column) => (
                    <td
                      key={column.key}
                      className={[
                        "truncate px-4 py-3 text-sm text-[#263126]",
                        column.className,
                      ].join(" ")}
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
