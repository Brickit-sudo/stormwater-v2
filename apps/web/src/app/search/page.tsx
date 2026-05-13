"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import AppShell from "@/components/AppShell";
import Badge, { type BadgeTone } from "@/components/ui/Badge";
import SectionHeader from "@/components/ui/SectionHeader";
import { demoOrganizationId, globalSearch } from "@/lib/api";
import type { SearchGroup, SearchResponse, SearchResult, SearchType } from "@/lib/types";
import { cardClass, eyebrowClass, primaryButtonClass, secondaryButtonClass } from "@/lib/ui";

const searchTypes: Array<{ type: SearchType; label: string }> = [
  { type: "clients", label: "Clients" },
  { type: "sites", label: "Sites" },
  { type: "jobs", label: "Jobs" },
  { type: "files", label: "Files" },
  { type: "emails", label: "Emails" },
  { type: "ai_drafts", label: "AI Drafts" },
  { type: "reminders", label: "Reminders" },
];

const allTypeValues = searchTypes.map((item) => item.type);

function SetupMessage() {
  return (
    <AppShell>
      <div className="rounded-lg border border-[color:var(--yellow)]/40 bg-[color:var(--yellow-soft)] p-5 text-sm text-[color:var(--yellow)]">
        Set NEXT_PUBLIC_DEMO_ORG_ID in apps/web/.env.local to use Search.
      </div>
    </AppShell>
  );
}

function parseTypesParam(value: string | null): SearchType[] {
  if (!value) {
    return allTypeValues;
  }

  const requested = value
    .split(",")
    .map((item) => item.trim())
    .filter((item): item is SearchType => allTypeValues.includes(item as SearchType));

  return requested.length > 0 ? requested : allTypeValues;
}

function formatDate(value: string | null): string | null {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function formatStatus(value: string | null): string | null {
  return value ? value.replaceAll("_", " ") : null;
}

function toneForType(type: string): BadgeTone {
  if (type === "reminders") {
    return "warning";
  }
  if (type === "emails" || type === "ai_drafts") {
    return "info";
  }
  if (type === "files") {
    return "success";
  }
  return "muted";
}

export default function SearchPage() {
  const organizationId = demoOrganizationId;
  const [query, setQuery] = useState("");
  const [selectedTypes, setSelectedTypes] = useState<SearchType[]>(allTypeValues);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [lastQuery, setLastQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const visibleGroups = useMemo(
    () => response?.groups.filter((group) => group.count > 0) ?? [],
    [response],
  );

  const runSearch = useCallback(
    async (nextQuery: string, nextTypes: SearchType[]) => {
      const trimmed = nextQuery.trim();
      if (!organizationId || trimmed.length < 2) {
        setResponse(null);
        setLastQuery(trimmed);
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const result = await globalSearch({
          organizationId,
          q: trimmed,
          types: nextTypes.length === allTypeValues.length ? undefined : nextTypes,
          limit: 10,
        });
        setResponse(result);
        setLastQuery(trimmed);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "Unable to search records.");
      } finally {
        setLoading(false);
      }
    },
    [organizationId],
  );

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams(window.location.search);
      const initialQuery = params.get("q") ?? "";
      const initialTypes = parseTypesParam(params.get("types"));
      setQuery(initialQuery);
      setSelectedTypes(initialTypes);
      if (initialQuery.trim().length >= 2) {
        void runSearch(initialQuery, initialTypes);
      }
    }, 0);

    return () => window.clearTimeout(timer);
  }, [runSearch]);

  if (!organizationId) {
    return <SetupMessage />;
  }

  function updateBrowserQuery(nextQuery: string, nextTypes: SearchType[]) {
    const params = new URLSearchParams();
    const trimmed = nextQuery.trim();
    if (trimmed.length >= 2) {
      params.set("q", trimmed);
    }
    if (nextTypes.length !== allTypeValues.length) {
      params.set("types", nextTypes.join(","));
    }
    const suffix = params.toString();
    window.history.pushState(null, "", suffix ? `/search?${suffix}` : "/search");
  }

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    updateBrowserQuery(query, selectedTypes);
    void runSearch(query, selectedTypes);
  }

  function toggleType(type: SearchType) {
    setSelectedTypes((current) => {
      if (current.includes(type)) {
        return current.length === 1
          ? current
          : current.filter((candidate) => candidate !== type);
      }
      return allTypeValues.filter((candidate) => candidate === type || current.includes(candidate));
    });
  }

  function selectAllTypes() {
    setSelectedTypes(allTypeValues);
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <SectionHeader
          title="Search"
          description="Search local CRM records without provider mailbox or Drive calls."
        />

        <form className={cardClass} onSubmit={submitSearch}>
          <div className="space-y-4 p-4">
            <label className="block">
              <span className="text-sm font-medium text-text-secondary">
                Search term
              </span>
              <div className="mt-2 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto]">
                <input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Client, site, job, file, email, draft, or reminder"
                  className="form-input"
                  minLength={2}
                />
                <button
                  type="submit"
                  className={primaryButtonClass}
                  disabled={loading || query.trim().length < 2}
                >
                  {loading ? "Searching..." : "Search"}
                </button>
              </div>
            </label>

            <div>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className={eyebrowClass}>Types</p>
                <button
                  type="button"
                  className={secondaryButtonClass}
                  onClick={selectAllTypes}
                  disabled={selectedTypes.length === allTypeValues.length}
                >
                  All Types
                </button>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {searchTypes.map((item) => {
                  const selected = selectedTypes.includes(item.type);
                  return (
                    <label
                      key={item.type}
                      className={[
                        "inline-flex h-9 cursor-pointer items-center rounded-md border px-3 text-sm font-semibold transition",
                        selected
                          ? "border-[color:var(--green)]/50 bg-green-soft text-green"
                          : "border-border bg-panel-2 text-text-secondary hover:bg-panel",
                      ].join(" ")}
                    >
                      <input
                        type="checkbox"
                        className="sr-only"
                        checked={selected}
                        onChange={() => toggleType(item.type)}
                      />
                      {item.label}
                    </label>
                  );
                })}
              </div>
            </div>
          </div>
        </form>

        {error ? (
          <div className="rounded-md border border-[color:var(--red)]/40 bg-[color:var(--red-soft)] px-4 py-3 text-sm text-[color:var(--red)]">
            {error}
          </div>
        ) : null}

        <SearchSummary
          loading={loading}
          response={response}
          lastQuery={lastQuery}
        />

        {loading ? (
          <LoadingGroups />
        ) : visibleGroups.length > 0 ? (
          <div className="space-y-5">
            {visibleGroups.map((group) => (
              <ResultGroup key={group.type} group={group} />
            ))}
          </div>
        ) : response && response.total_count === 0 ? (
          <EmptySearch query={response.query} />
        ) : (
          <StartSearch />
        )}
      </div>
    </AppShell>
  );
}

function SearchSummary({
  loading,
  response,
  lastQuery,
}: {
  loading: boolean;
  response: SearchResponse | null;
  lastQuery: string;
}) {
  if (loading) {
    return (
      <div className="rounded-lg border border-border-soft bg-panel-2 px-4 py-3 text-sm text-text-muted">
        Searching local records...
      </div>
    );
  }

  if (!response) {
    return lastQuery.length === 1 ? (
      <div className="rounded-lg border border-border-soft bg-panel-2 px-4 py-3 text-sm text-text-muted">
        Enter at least two characters.
      </div>
    ) : null;
  }

  return (
    <div className="rounded-lg border border-border-soft bg-panel-2 px-4 py-3 text-sm text-text-secondary">
      {response.total_count} results for{" "}
      <span className="font-semibold text-text">{response.query}</span>
    </div>
  );
}

function LoadingGroups() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 3 }).map((_, index) => (
        <div
          key={index}
          className="h-28 animate-pulse rounded-lg border border-border-soft bg-panel-2"
        />
      ))}
    </div>
  );
}

function StartSearch() {
  return (
    <div className="rounded-lg border border-border-soft bg-panel-2 px-4 py-6 text-sm text-text-muted">
      Enter a search term to find local records.
    </div>
  );
}

function EmptySearch({ query }: { query: string }) {
  return (
    <div className="rounded-lg border border-border-soft bg-panel-2 px-4 py-6 text-sm text-text-muted">
      No local records matched {query}.
    </div>
  );
}

function ResultGroup({ group }: { group: SearchGroup }) {
  return (
    <section>
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className={eyebrowClass}>{group.label}</p>
          <h2 className="mt-1 text-base font-semibold text-text">
            {group.count} matches
          </h2>
        </div>
        <Badge tone={toneForType(group.type)}>{group.type.replaceAll("_", " ")}</Badge>
      </div>

      <div className="mt-3 grid gap-3">
        {group.results.map((result) => (
          <ResultCard key={`${result.type}-${result.id}`} result={result} />
        ))}
      </div>
    </section>
  );
}

function ResultCard({ result }: { result: SearchResult }) {
  const timestamp = formatDate(result.occurred_at ?? result.updated_at);
  const status = formatStatus(result.status);
  const body = (
    <article className="rounded-lg border border-border bg-panel p-4 transition hover:border-[color:var(--green)]/40 hover:bg-panel-2">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h3 className="text-base font-semibold text-text">{result.title}</h3>
          {result.subtitle ? (
            <p className="mt-1 text-sm text-text-secondary">{result.subtitle}</p>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {status ? <Badge tone="muted">{status}</Badge> : null}
          {timestamp ? (
            <span className="text-xs text-text-muted">{timestamp}</span>
          ) : null}
        </div>
      </div>
      {result.description ? (
        <p className="mt-3 text-sm leading-6 text-text-secondary">
          {result.description}
        </p>
      ) : null}
      <div className="mt-3 flex flex-wrap gap-2">
        {result.matched_fields.map((field) => (
          <span
            key={field}
            className="rounded-full border border-border-soft bg-panel-2 px-2 py-1 text-[11px] font-medium text-text-muted"
          >
            {field.replaceAll("_", " ")}
          </span>
        ))}
      </div>
    </article>
  );

  return result.href ? (
    <Link
      href={result.href}
      className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
    >
      {body}
    </Link>
  ) : (
    body
  );
}
