"use client";

import { usePathname } from "next/navigation";

const titles: Record<string, { title: string; subtitle: string }> = {
  "/crm/clients": {
    title: "Clients",
    subtitle: "Accounts and their primary contacts",
  },
  "/crm/sites": {
    title: "Sites",
    subtitle: "Locations tied to client records",
  },
  "/crm/jobs": {
    title: "Jobs",
    subtitle: "Scheduled work against client and site records",
  },
  "/": {
    title: "Command Center",
    subtitle: "Stormwater operations overview",
  },
};

function resolveSection(pathname: string) {
  if (pathname in titles) return titles[pathname];
  const match = Object.keys(titles).find(
    (key) => key !== "/" && pathname.startsWith(`${key}/`),
  );
  return match
    ? titles[match]
    : { title: "Workspace", subtitle: "Sterling Stormwater V2" };
}

export default function Topbar() {
  const pathname = usePathname();
  const section = resolveSection(pathname);

  return (
    <header className="sticky top-0 z-10 border-b border-border bg-bg/85 backdrop-blur-md">
      <div className="mx-auto flex min-h-14 max-w-[1480px] items-center justify-between gap-4 px-4 sm:px-6 lg:px-8 xl:px-10">
        <div className="flex min-w-0 items-center gap-4">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-text">
              {section.title}
            </p>
            <p className="truncate text-xs text-text-muted">
              {section.subtitle}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center rounded-full border border-border-soft bg-panel px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted">
            V2 Bootstrap
          </span>
        </div>
      </div>
    </header>
  );
}
