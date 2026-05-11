import type { ReactNode } from "react";

export type BadgeTone = "success" | "warning" | "danger" | "info" | "muted";

type BadgeProps = {
  tone?: BadgeTone;
  children: ReactNode;
  className?: string;
};

const toneStyles: Record<BadgeTone, string> = {
  success:
    "bg-[color:var(--green-soft)] text-green ring-[color:var(--green)]/30",
  warning:
    "bg-[color:var(--yellow-soft)] text-[color:var(--yellow)] ring-[color:var(--yellow)]/30",
  danger:
    "bg-[color:var(--red-soft)] text-[color:var(--red)] ring-[color:var(--red)]/30",
  info: "bg-[color:var(--blue-soft)] text-[color:var(--blue)] ring-[color:var(--blue)]/30",
  muted: "bg-panel-2 text-text-secondary ring-border",
};

export default function Badge({
  tone = "muted",
  children,
  className,
}: BadgeProps) {
  return (
    <span
      className={[
        "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset capitalize",
        toneStyles[tone],
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </span>
  );
}
