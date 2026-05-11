import Badge, { type BadgeTone } from "@/components/ui/Badge";

type StatusBadgeProps = {
  status: string | null | undefined;
};

const statusTone: Record<string, BadgeTone> = {
  // Clients
  active: "success",
  inactive: "muted",
  prospect: "info",

  // Sites (active/inactive already mapped above)
  on_hold: "warning",

  // Jobs
  draft: "muted",
  scheduled: "info",
  in_progress: "success",
  in_review: "warning",
  completed: "success",
  cancelled: "danger",

  // Shared lifecycle
  archived: "muted",
  unknown: "muted",
};

export default function StatusBadge({ status }: StatusBadgeProps) {
  const normalized = (status?.trim() || "unknown").toLowerCase();
  const tone = statusTone[normalized] ?? "muted";

  return <Badge tone={tone}>{normalized.replaceAll("_", " ")}</Badge>;
}
