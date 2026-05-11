"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { label: "Clients", href: "/crm/clients" },
  { label: "Sites", href: "/crm/sites" },
  { label: "Jobs", href: "/crm/jobs" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="border-b border-[#dbe1d8] bg-white lg:border-b-0 lg:border-r">
      <div className="flex h-full flex-col px-4 py-4">
        <Link
          href="/crm/clients"
          className="flex h-11 items-center rounded-md px-2 text-base font-semibold text-[#172017]"
        >
          Stormwater CRM
        </Link>

        <nav className="mt-5">
          <p className="px-2 text-xs font-semibold uppercase tracking-[0.12em] text-[#667466]">
            CRM
          </p>
          <div className="mt-2 space-y-1">
            {navItems.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={[
                    "flex h-10 items-center rounded-md px-3 text-sm font-medium transition",
                    active
                      ? "bg-[#e7f4e9] text-[#176d31]"
                      : "text-[#465446] hover:bg-[#f2f5f0] hover:text-[#172017]",
                  ].join(" ")}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        </nav>
      </div>
    </aside>
  );
}
