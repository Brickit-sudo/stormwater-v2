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
  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-[0.08em] text-[#6d7a6d]">
        {label}
      </dt>
      <dd className="mt-1 min-h-6 break-words text-sm text-[#1f291f]">
        {value || <span className="text-[#8a958a]">Not set</span>}
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
    <aside className="flex min-h-[520px] min-w-0 flex-col rounded-md border border-[#dbe1d8] bg-white">
      <div className="border-b border-[#e3e8e0] px-5 py-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold text-[#172017]">
              {title}
            </h2>
            {subtitle ? (
              <p className="mt-1 truncate text-sm text-[#667466]">{subtitle}</p>
            ) : null}
          </div>
          {actions ? <div className="flex shrink-0 gap-2">{actions}</div> : null}
        </div>
      </div>
      <div className="min-w-0 flex-1 overflow-auto p-5">{children}</div>
    </aside>
  );
}
