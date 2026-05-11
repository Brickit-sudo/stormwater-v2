type StatusBadgeProps = {
  status: string | null | undefined;
};

const statusStyles: Record<string, string> = {
  active: "bg-[#e7f4e9] text-[#176d31] ring-[#b8e0bf]",
  inactive: "bg-[#f1f2ef] text-[#596459] ring-[#d9ded6]",
  draft: "bg-[#edf1f7] text-[#3d5878] ring-[#cbd8e8]",
  scheduled: "bg-[#fff5dd] text-[#785a16] ring-[#ead59c]",
  in_progress: "bg-[#e6f4f5] text-[#186a70] ring-[#b8dcdf]",
  completed: "bg-[#e7f4e9] text-[#176d31] ring-[#b8e0bf]",
  archived: "bg-[#f4e7e7] text-[#8a3535] ring-[#e4bbbb]",
};

export default function StatusBadge({ status }: StatusBadgeProps) {
  const normalized = status?.trim() || "unknown";
  const style =
    statusStyles[normalized.toLowerCase()] ??
    "bg-[#f1f2ef] text-[#596459] ring-[#d9ded6]";

  return (
    <span
      className={[
        "inline-flex items-center rounded-full px-2 py-1 text-xs font-semibold capitalize ring-1 ring-inset",
        style,
      ].join(" ")}
    >
      {normalized.replaceAll("_", " ")}
    </span>
  );
}
