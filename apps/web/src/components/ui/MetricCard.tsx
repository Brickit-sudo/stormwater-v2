import type { ReactNode } from "react";

import Card from "./Card";

type MetricCardProps = {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  loading?: boolean;
};

export default function MetricCard({
  label,
  value,
  hint,
  loading = false,
}: MetricCardProps) {
  return (
    <Card className="p-5">
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-text-muted">
        {label}
      </p>
      <div className="mt-3 flex items-baseline gap-2">
        {loading ? (
          <span className="inline-block h-7 w-16 animate-pulse rounded bg-panel-2" />
        ) : (
          <span className="text-3xl font-semibold tracking-tight text-text">
            {value}
          </span>
        )}
      </div>
      {hint ? (
        <p className="mt-2 text-xs text-text-muted">{hint}</p>
      ) : null}
    </Card>
  );
}
