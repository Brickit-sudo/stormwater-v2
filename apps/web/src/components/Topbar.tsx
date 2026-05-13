"use client";

import { useState, type FormEvent } from "react";

import { usePathname, useRouter } from "next/navigation";

const titles: Record<string, { title: string; subtitle: string }> = {
  "/search": {
    title: "Search",
    subtitle: "Local CRM records",
  },
  "/roadmap": {
    title: "Roadmap",
    subtitle: "Internal product ideas and decisions",
  },
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
  "/work": {
    title: "Work Hub",
    subtitle: "Files, email records, drafts, and local import history",
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
  const router = useRouter();
  const section = resolveSection(pathname);
  const [searchValue, setSearchValue] = useState("");

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = searchValue.trim();
    if (trimmed.length < 2) {
      router.push("/search");
      return;
    }
    router.push(`/search?q=${encodeURIComponent(trimmed)}`);
  }

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
        <div className="flex items-center gap-3">
          <form className="hidden md:block" onSubmit={submitSearch}>
            <label className="sr-only" htmlFor="topbar-search">
              Search local records
            </label>
            <input
              id="topbar-search"
              value={searchValue}
              onChange={(event) => setSearchValue(event.target.value)}
              placeholder="Search local records"
              className="h-9 w-64 rounded-md border border-border bg-panel-2 px-3 text-sm text-text outline-none transition placeholder:text-text-muted focus:border-[color:var(--green)] focus:ring-2 focus:ring-green/40"
            />
          </form>
          <span className="inline-flex items-center rounded-full border border-border-soft bg-panel px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted">
            V2 Bootstrap
          </span>
        </div>
      </div>
    </header>
  );
}
