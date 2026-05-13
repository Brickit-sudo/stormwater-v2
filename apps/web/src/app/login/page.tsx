"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { primaryButtonClass } from "@/lib/ui";

function getNextPath(): string {
  if (typeof window === "undefined") {
    return "/";
  }
  const requested = new URLSearchParams(window.location.search).get("next");
  if (!requested || !requested.startsWith("/") || requested.startsWith("//")) {
    return "/";
  }
  return requested;
}

export default function LoginPage() {
  const router = useRouter();
  const { authEnabled, loading, user, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authEnabled) {
      router.replace("/");
      return;
    }
    if (!loading && user) {
      router.replace(getNextPath());
    }
  }, [authEnabled, loading, router, user]);

  async function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(email.trim(), password);
      router.replace(getNextPath());
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 401) {
        setError("Invalid email or password.");
      } else {
        setError(caught instanceof Error ? caught.message : "Unable to sign in.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (authEnabled && loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-bg px-4 text-text">
        <div className="rounded-lg border border-border bg-panel px-5 py-4 text-sm text-text-secondary">
          Checking secure session...
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-bg px-4 py-8 text-text">
      <section className="w-full max-w-md rounded-lg border border-border bg-panel p-6 shadow-[0_1px_0_rgba(255,255,255,0.02)_inset,0_18px_46px_-30px_rgba(69,224,79,0.45)]">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-md bg-green-soft text-lg font-bold text-green ring-1 ring-inset ring-[color:var(--green)]/40">
            S
          </span>
          <div>
            <h1 className="text-lg font-semibold text-text">
              Sterling Stormwater
            </h1>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
              Staging access
            </p>
          </div>
        </div>

        <form className="mt-6 space-y-4" onSubmit={(event) => void submitLogin(event)}>
          <label className="block">
            <span className="text-sm font-medium text-text-secondary">Email</span>
            <input
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="form-input mt-2"
              type="email"
              autoComplete="email"
              required
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium text-text-secondary">Password</span>
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="form-input mt-2"
              type="password"
              autoComplete="current-password"
              required
            />
          </label>

          {error ? (
            <div className="rounded-md border border-[color:var(--red)]/40 bg-[color:var(--red-soft)] px-3 py-2 text-sm text-[color:var(--red)]">
              {error}
            </div>
          ) : null}

          <button
            type="submit"
            className={`${primaryButtonClass} w-full justify-center`}
            disabled={submitting || loading}
          >
            {submitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
