"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type NavItem = {
  label: string;
  href: string;
  description: string;
};

const navItems: NavItem[] = [
  { label: "Clients", href: "/crm/clients", description: "Accounts" },
  { label: "Sites", href: "/crm/sites", description: "Locations" },
  { label: "Jobs", href: "/crm/jobs", description: "Work orders" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="border-b border-border bg-sidebar lg:sticky lg:top-0 lg:h-screen lg:border-b-0 lg:border-r">
      <div className="flex h-full flex-col px-4 py-5">
        <Link
          href="/"
          className="group flex items-center gap-3 rounded-lg px-2 py-2 transition hover:bg-panel focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green focus-visible:ring-offset-2 focus-visible:ring-offset-sidebar"
        >
          <span
            aria-hidden="true"
            className="flex h-9 w-9 items-center justify-center rounded-md bg-green-soft text-green ring-1 ring-inset ring-[color:var(--green)]/40 shadow-[0_0_18px_-6px_var(--green-glow)]"
          >
            <span className="text-base font-bold">S</span>
          </span>
          <span className="flex flex-col leading-tight">
            <span className="text-sm font-semibold text-text">
              Sterling Stormwater
            </span>
            <span className="text-[11px] uppercase tracking-[0.14em] text-text-muted">
              Field Service Admin
            </span>
          </span>
        </Link>

        <nav className="mt-8" aria-label="CRM navigation">
          <p className="px-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-text-muted">
            CRM
          </p>
          <div className="mt-3 space-y-1">
            {navItems.map((item) => {
              const active =
                pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={[
                    "group relative flex h-10 items-center gap-3 rounded-lg px-3 text-sm font-medium transition",
                    active
                      ? "bg-green-soft text-green shadow-[inset_0_0_0_1px_rgba(69,224,79,0.25)]"
                      : "text-text-secondary hover:bg-panel hover:text-text",
                  ].join(" ")}
                >
                  <span
                    aria-hidden="true"
                    className={[
                      "h-1.5 w-1.5 rounded-full transition",
                      active
                        ? "bg-green shadow-[0_0_10px_2px_var(--green-glow)]"
                        : "bg-border group-hover:bg-text-muted",
                    ].join(" ")}
                  />
                  <span className="flex-1">{item.label}</span>
                  <span
                    className={[
                      "text-[10px] uppercase tracking-[0.14em]",
                      active ? "text-green" : "text-text-muted",
                    ].join(" ")}
                  >
                    {item.description}
                  </span>
                </Link>
              );
            })}
          </div>
        </nav>

        <div className="mt-auto pt-6">
          <div className="rounded-lg border border-border-soft bg-panel/85 p-3">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted">
              Environment
            </p>
            <p className="mt-1 text-sm font-semibold text-text">
              V2 Bootstrap
            </p>
            <p className="mt-1 text-xs text-text-muted">
              Local dev workspace
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
