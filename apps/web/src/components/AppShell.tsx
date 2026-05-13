"use client";

import type { ReactNode } from "react";
import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";

import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import { useAuth } from "@/lib/auth";

type AppShellProps = {
  children: ReactNode;
};

export default function AppShell({ children }: AppShellProps) {
  const { authEnabled, loading, user } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (authEnabled && !loading && !user) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [authEnabled, loading, pathname, router, user]);

  if (authEnabled && (loading || !user)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg px-4 text-text">
        <div className="rounded-lg border border-border bg-panel px-5 py-4 text-sm text-text-secondary shadow-[0_18px_46px_-30px_rgba(69,224,79,0.45)]">
          Checking secure session...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg text-text">
      <div className="grid min-h-screen grid-cols-1 lg:grid-cols-[260px_1fr]">
        <Sidebar />
        <div className="flex min-w-0 flex-col">
          <Topbar />
          <main className="mx-auto min-w-0 w-full max-w-[1480px] flex-1 px-4 py-6 sm:px-6 lg:px-8 xl:px-10">
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
