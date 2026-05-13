"use client";

import type { ReactNode } from "react";

type WorkPreviewProps = {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
};

export default function WorkPreview({
  title,
  subtitle,
  actions,
  children,
}: WorkPreviewProps) {
  return (
    <aside className="min-w-0 rounded-lg border border-border bg-panel">
      <div className="border-b border-border-soft px-4 py-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="break-words text-base font-semibold text-text">
              {title}
            </h2>
            {subtitle ? (
              <p className="mt-1 break-words text-xs text-text-muted">
                {subtitle}
              </p>
            ) : null}
          </div>
          {actions ? <div className="flex shrink-0 flex-wrap justify-end gap-2">{actions}</div> : null}
        </div>
      </div>
      <div className="p-4">{children}</div>
    </aside>
  );
}
