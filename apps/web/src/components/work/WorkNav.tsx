"use client";

import type { WorkView } from "./WorkHubShell";

const navItems: Array<{ id: WorkView; label: string; description: string }> = [
  { id: "files", label: "Files", description: "Evidence links" },
  { id: "emails", label: "Emails", description: "Local messages" },
  { id: "outlook", label: "Outlook Import", description: "Preview first" },
  { id: "drafts", label: "AI Drafts", description: "Manual drafts" },
  { id: "batches", label: "Import Batches", description: "Local history" },
];

type WorkNavProps = {
  activeView: WorkView;
  onChange: (view: WorkView) => void;
};

export default function WorkNav({ activeView, onChange }: WorkNavProps) {
  return (
    <nav className="space-y-2" aria-label="Work Hub views">
      {navItems.map((item) => {
        const active = item.id === activeView;
        return (
          <button
            key={item.id}
            type="button"
            className={[
              "flex w-full items-center justify-between gap-3 rounded-lg border px-3 py-3 text-left transition",
              active
                ? "border-[color:var(--green)]/35 bg-green-soft text-green"
                : "border-border-soft bg-panel text-text-secondary hover:border-border-strong hover:bg-panel-2 hover:text-text",
            ].join(" ")}
            onClick={() => onChange(item.id)}
          >
            <span className="min-w-0">
              <span className="block text-sm font-semibold">{item.label}</span>
              <span
                className={[
                  "mt-1 block text-xs",
                  active ? "text-green" : "text-text-muted",
                ].join(" ")}
              >
                {item.description}
              </span>
            </span>
            <span
              aria-hidden="true"
              className={[
                "h-2 w-2 rounded-full",
                active ? "bg-green shadow-[0_0_12px_var(--green-glow)]" : "bg-border",
              ].join(" ")}
            />
          </button>
        );
      })}
    </nav>
  );
}
