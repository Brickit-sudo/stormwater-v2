import type { ReactNode } from "react";

type DetailPanelProps = {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
};

type DetailFieldProps = {
  label: string;
  value: ReactNode;
};

export function DetailField({ label, value }: DetailFieldProps) {
  const hasValue =
    value !== null && value !== undefined && value !== "" && value !== false;

  return (
    <div className="rounded-md border border-border-soft bg-panel-2/70 p-3">
      <dt className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted">
        {label}
      </dt>
      <dd className="mt-1.5 min-h-6 break-words text-sm text-text">
        {hasValue ? value : <span className="text-text-muted">Not set</span>}
      </dd>
    </div>
  );
}

export default function DetailPanel({
  title,
  subtitle,
  actions,
  children,
}: DetailPanelProps) {
  return (
    <aside className="flex min-h-[520px] min-w-0 flex-col rounded-lg border border-border bg-panel shadow-[0_1px_0_rgba(255,255,255,0.02)_inset,0_18px_38px_-26px_rgba(0,0,0,0.7)]">
      <div className="border-b border-border-soft bg-panel-2/35 px-5 py-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold text-text">
              {title}
            </h2>
            {subtitle ? (
              <p className="mt-1 truncate text-sm text-text-secondary">
                {subtitle}
              </p>
            ) : null}
          </div>
          {actions ? (
            <div className="flex shrink-0 flex-wrap items-center justify-end gap-2">
              {actions}
            </div>
          ) : null}
        </div>
      </div>
      <div className="min-w-0 flex-1 overflow-auto p-5">{children}</div>
    </aside>
  );
}
