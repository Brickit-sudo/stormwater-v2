"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import Badge from "@/components/ui/Badge";
import {
  archiveEmailMessage,
  createEmailRecordLink,
  getEmailMessage,
  listClients,
  listEmailMessages,
  listJobs,
  listSites,
} from "@/lib/api";
import type {
  Client,
  EmailMessage,
  EmailMessageStatus,
  Job,
  Site,
  UUID,
} from "@/lib/types";
import {
  dangerButtonClass,
  linkChipClass,
  primaryButtonClass,
} from "@/lib/ui";

import WorkList from "./WorkList";
import WorkPreview from "./WorkPreview";

type EmailsWorkViewProps = {
  organizationId: UUID;
};

type TargetType = "client" | "site" | "job";

const emailLimit = 25;
const statusOptions: Array<"" | EmailMessageStatus> = ["", "unlinked", "linked"];

function formatDate(value: string | null): string {
  if (!value) {
    return "No received date";
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

function jsonText(item: Record<string, unknown>, keys: string[]): string {
  for (const key of keys) {
    const value = item[key];
    if (typeof value === "string" && value.trim()) {
      return value;
    }
    if (typeof value === "number") {
      return String(value);
    }
  }
  return JSON.stringify(item);
}

function jsonUrl(item: Record<string, unknown>): string | null {
  const value = item.url ?? item.href ?? item.webUrl;
  return typeof value === "string" && value.trim() ? value : null;
}

export default function EmailsWorkView({ organizationId }: EmailsWorkViewProps) {
  const [messages, setMessages] = useState<EmailMessage[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedMessage, setSelectedMessage] = useState<EmailMessage | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"" | EmailMessageStatus>("");
  const [providerFilter, setProviderFilter] = useState("");
  const [targetType, setTargetType] = useState<TargetType>("job");
  const [targetId, setTargetId] = useState("");
  const [loadingList, setLoadingList] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const clientNameById = useMemo(
    () => new Map(clients.map((client) => [client.id, client.name])),
    [clients],
  );
  const siteNameById = useMemo(
    () => new Map(sites.map((site) => [site.id, site.name])),
    [sites],
  );
  const jobNameById = useMemo(
    () => new Map(jobs.map((job) => [job.id, job.name])),
    [jobs],
  );

  const targetOptions = useMemo(() => {
    if (targetType === "client") {
      return clients.map((client) => ({ id: client.id, label: client.name }));
    }
    if (targetType === "site") {
      return sites.map((site) => ({
        id: site.id,
        label: clientNameById.get(site.client_id)
          ? `${site.name} - ${clientNameById.get(site.client_id)}`
          : site.name,
      }));
    }
    return jobs.map((job) => ({
      id: job.id,
      label: siteNameById.get(job.site_id)
        ? `${job.name} - ${siteNameById.get(job.site_id)}`
        : job.name,
    }));
  }, [clientNameById, clients, jobs, siteNameById, sites, targetType]);

  const linkedLabel = useCallback(
    (message: EmailMessage): string => {
      if (message.job_id) return jobNameById.get(message.job_id) ?? "Linked job";
      if (message.site_id) return siteNameById.get(message.site_id) ?? "Linked site";
      if (message.client_id) return clientNameById.get(message.client_id) ?? "Linked client";
      return "Unlinked";
    },
    [clientNameById, jobNameById, siteNameById],
  );

  const firstTargetId = useCallback(
    (type: TargetType): string => {
      if (type === "client") return clients[0]?.id ?? "";
      if (type === "site") return sites[0]?.id ?? "";
      return jobs[0]?.id ?? "";
    },
    [clients, jobs, sites],
  );

  const loadReferences = useCallback(async () => {
    try {
      const [clientResponse, siteResponse, jobResponse] = await Promise.all([
        listClients({ organizationId, limit: 500 }),
        listSites({ organizationId, limit: 500 }),
        listJobs({ organizationId, limit: 500 }),
      ]);
      setClients(clientResponse.items);
      setSites(siteResponse.items);
      setJobs(jobResponse.items);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load linked records.");
    }
  }, [organizationId]);

  const loadMessages = useCallback(async () => {
    setLoadingList(true);
    setError(null);
    try {
      const response = await listEmailMessages({
        organizationId,
        search: search.trim() || undefined,
        status: statusFilter || undefined,
        provider: providerFilter.trim() || undefined,
        limit: emailLimit,
        offset,
      });
      setMessages(response.items);
      setTotal(response.total);
      if (response.items.length === 0) {
        setSelectedMessage(null);
      }
      setSelectedId((current) =>
        current && response.items.some((message) => message.id === current)
          ? current
          : response.items[0]?.id ?? null,
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load email records.");
    } finally {
      setLoadingList(false);
    }
  }, [offset, organizationId, providerFilter, search, statusFilter]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadReferences();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadReferences]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadMessages();
    }, 250);
    return () => window.clearTimeout(timer);
  }, [loadMessages]);

  useEffect(() => {
    if (!selectedId) {
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(() => {
      setLoadingPreview(true);
      getEmailMessage(selectedId, organizationId)
        .then((message) => {
          if (cancelled) return;
          setSelectedMessage(message);
          if (message.job_id) {
            setTargetType("job");
            setTargetId(message.job_id);
          } else if (message.site_id) {
            setTargetType("site");
            setTargetId(message.site_id);
          } else if (message.client_id) {
            setTargetType("client");
            setTargetId(message.client_id);
          } else {
            setTargetType("job");
            setTargetId(firstTargetId("job"));
          }
        })
        .catch((caught) => {
          if (!cancelled) {
            setError(caught instanceof Error ? caught.message : "Unable to load email preview.");
          }
        })
        .finally(() => {
          if (!cancelled) setLoadingPreview(false);
        });
    }, 0);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [firstTargetId, organizationId, selectedId]);

  function updateTargetType(type: TargetType) {
    setTargetType(type);
    setTargetId(firstTargetId(type));
  }

  async function linkSelectedEmail() {
    if (!selectedMessage || !targetId) {
      setError("Choose an email and a client, site, or job to link.");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await createEmailRecordLink(organizationId, {
        email_message_id: selectedMessage.id,
        client_id: targetType === "client" ? targetId : null,
        site_id: targetType === "site" ? targetId : null,
        job_id: targetType === "job" ? targetId : null,
        link_reason: "manual",
        confidence: 1,
      });
      const refreshed = await getEmailMessage(selectedMessage.id, organizationId);
      setSelectedMessage(refreshed);
      await loadMessages();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to link email.");
    } finally {
      setSaving(false);
    }
  }

  async function archiveSelectedEmail() {
    if (!selectedMessage) {
      return;
    }
    const confirmed = window.confirm(`Archive ${selectedMessage.subject}?`);
    if (!confirmed) {
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await archiveEmailMessage(selectedMessage.id, organizationId);
      setSelectedMessage(null);
      setSelectedId(null);
      await loadMessages();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to archive email.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_480px]">
      <div className="min-w-0 space-y-3">
        <section className="rounded-lg border border-border bg-panel p-4">
          <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_180px_160px]">
            <label className="block">
              <span className="text-sm font-medium text-text-secondary">
                Search local emails
              </span>
              <input
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value);
                  setOffset(0);
                }}
                className="form-input mt-2"
                placeholder="Subject, sender, snippet, or body"
              />
            </label>
            <label className="block">
              <span className="text-sm font-medium text-text-secondary">
                Status
              </span>
              <select
                value={statusFilter}
                onChange={(event) => {
                  setStatusFilter(event.target.value as "" | EmailMessageStatus);
                  setOffset(0);
                }}
                className="form-input mt-2"
              >
                {statusOptions.map((status) => (
                  <option key={status || "all"} value={status}>
                    {status ? status : "All active"}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-sm font-medium text-text-secondary">
                Provider
              </span>
              <input
                value={providerFilter}
                onChange={(event) => {
                  setProviderFilter(event.target.value);
                  setOffset(0);
                }}
                className="form-input mt-2"
                placeholder="outlook"
              />
            </label>
          </div>
        </section>

        {error ? (
          <div className="rounded-md border border-[color:var(--red)]/40 bg-[color:var(--red-soft)] px-4 py-3 text-sm text-[color:var(--red)]">
            {error}
          </div>
        ) : null}

        <WorkList
          title="Emails"
          countLabel={`${total} local records`}
          rows={messages}
          getRowId={(message) => message.id}
          selectedId={selectedId}
          onSelect={(message) => setSelectedId(message.id)}
          renderTitle={(message) => message.subject}
          renderMeta={(message) => `${message.sender} - ${linkedLabel(message)}`}
          renderAside={(message) => (
            <span className="space-y-1">
              <Badge tone={message.status === "linked" ? "success" : "muted"}>
                {message.status}
              </Badge>
              <span className="block">{formatDate(message.received_at)}</span>
            </span>
          )}
          loading={loadingList}
          emptyTitle="No email records found"
          emptyDescription="Seeded and future imported local email records will appear here."
          page={{
            offset,
            limit: emailLimit,
            total,
            onPrevious: () => setOffset(Math.max(0, offset - emailLimit)),
            onNext: () => setOffset(offset + emailLimit),
          }}
        />
      </div>

      <WorkPreview
        title={selectedMessage?.subject ?? "Select an email"}
        subtitle={
          selectedMessage
            ? `${selectedMessage.sender} - ${formatDate(selectedMessage.received_at)}`
            : "Preview loads only the selected email"
        }
        actions={
          selectedMessage ? (
            <button
              type="button"
              className={dangerButtonClass}
              onClick={() => void archiveSelectedEmail()}
              disabled={saving}
            >
              Archive Email
            </button>
          ) : null
        }
      >
        {loadingPreview ? (
          <div className="h-32 animate-pulse rounded-md border border-border-soft bg-panel-2" />
        ) : selectedMessage ? (
          <div className="space-y-5">
            <div className="grid gap-3 text-sm sm:grid-cols-2">
              <Meta label="Status" value={selectedMessage.status} />
              <Meta label="Linked" value={linkedLabel(selectedMessage)} />
              <Meta label="Provider" value={selectedMessage.provider} />
              <Meta label="Received" value={formatDate(selectedMessage.received_at)} />
            </div>

            <section className="rounded-lg border border-border-soft bg-panel-2 p-3">
              <div className="grid gap-3 md:grid-cols-[120px_minmax(0,1fr)]">
                <label className="block">
                  <span className="text-sm font-medium text-text-secondary">
                    Link type
                  </span>
                  <select
                    value={targetType}
                    onChange={(event) => updateTargetType(event.target.value as TargetType)}
                    className="form-input mt-2"
                    disabled={saving}
                  >
                    <option value="client">Client</option>
                    <option value="site">Site</option>
                    <option value="job">Job</option>
                  </select>
                </label>
                <label className="block">
                  <span className="text-sm font-medium text-text-secondary">
                    Linked record
                  </span>
                  <select
                    value={targetId}
                    onChange={(event) => setTargetId(event.target.value)}
                    className="form-input mt-2"
                    disabled={saving}
                  >
                    <option value="">Select a record</option>
                    {targetOptions.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="mt-3 flex justify-end">
                <button
                  type="button"
                  className={primaryButtonClass}
                  onClick={() => void linkSelectedEmail()}
                  disabled={saving || !targetId}
                >
                  Link Email
                </button>
              </div>
            </section>

            {selectedMessage.snippet ? (
              <p className="rounded-md border border-border-soft bg-panel-2 p-3 text-sm leading-6 text-text-secondary">
                {selectedMessage.snippet}
              </p>
            ) : null}

            <section>
              <h3 className="text-sm font-semibold text-text">Body</h3>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-text-secondary">
                {selectedMessage.body_text || "No plain-text body stored."}
              </p>
            </section>

            <JsonList
              title="Extracted links"
              items={selectedMessage.links_json}
              empty="No links stored on this email."
              linkMode
            />
            <JsonList
              title="Attachment metadata"
              items={selectedMessage.attachments_json}
              empty="No attachment metadata stored."
            />
          </div>
        ) : (
          <p className="text-sm text-text-muted">
            Choose a local email record to preview the message and link it to CRM work.
          </p>
        )}
      </WorkPreview>
    </div>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border-soft bg-panel-2 p-3">
      <dt className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-muted">
        {label}
      </dt>
      <dd className="mt-1 break-words text-sm text-text">{value}</dd>
    </div>
  );
}

function JsonList({
  title,
  items,
  empty,
  linkMode = false,
}: {
  title: string;
  items: Array<Record<string, unknown>>;
  empty: string;
  linkMode?: boolean;
}) {
  return (
    <section>
      <h3 className="text-sm font-semibold text-text">{title}</h3>
      {items.length > 0 ? (
        <ul className="mt-2 divide-y divide-border-soft rounded-lg border border-border-soft bg-panel-2">
          {items.map((item, index) => {
            const url = linkMode ? jsonUrl(item) : null;
            return (
              <li key={index} className="flex items-start justify-between gap-3 px-3 py-2 text-sm">
                <span className="min-w-0 break-words text-text-secondary">
                  {jsonText(item, ["label", "name", "fileName", "url"])}
                </span>
                {url ? (
                  <a
                    href={url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className={linkChipClass}
                  >
                    Open Link
                  </a>
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="mt-2 rounded-md border border-border-soft bg-panel-2 px-3 py-2 text-sm text-text-muted">
          {empty}
        </p>
      )}
    </section>
  );
}
