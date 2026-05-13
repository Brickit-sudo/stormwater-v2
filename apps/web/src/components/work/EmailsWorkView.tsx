"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import Badge from "@/components/ui/Badge";
import {
  archiveEmailMessage,
  createFileLink,
  createEmailRecordLink,
  createReminder,
  draftEmailReply,
  extractEmailActionItems,
  extractFileLinks,
  getAiStatus,
  getEmailMessage,
  listClients,
  listEmailMessages,
  listJobs,
  listSites,
  suggestRecordLinks,
  summarizeEmail,
} from "@/lib/api";
import type {
  ActionItemSuggestion,
  AiStatus,
  Client,
  EmailMessage,
  EmailMessageStatus,
  EmailSummaryResult,
  FileLinkCandidate,
  Job,
  RecordLinkSuggestion,
  Site,
  UUID,
} from "@/lib/types";
import {
  dangerButtonClass,
  linkChipClass,
  primaryButtonClass,
  secondaryButtonClass,
} from "@/lib/ui";

import WorkList from "./WorkList";
import WorkPreview from "./WorkPreview";

type EmailsWorkViewProps = {
  organizationId: UUID;
};

type TargetType = "client" | "site" | "job";

const emailLimit = 25;
const statusOptions: Array<"" | EmailMessageStatus> = ["", "unlinked", "linked"];
const actionPriority = (value: string): "low" | "medium" | "high" => {
  if (value === "low" || value === "high") {
    return value;
  }
  return "medium";
};

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
  const [aiStatus, setAiStatus] = useState<AiStatus | null>(null);
  const [summary, setSummary] = useState<EmailSummaryResult | null>(null);
  const [actionItems, setActionItems] = useState<ActionItemSuggestion[]>([]);
  const [detectedLinks, setDetectedLinks] = useState<FileLinkCandidate[]>([]);
  const [recordSuggestions, setRecordSuggestions] = useState<RecordLinkSuggestion[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<"" | EmailMessageStatus>("");
  const [providerFilter, setProviderFilter] = useState("");
  const [targetType, setTargetType] = useState<TargetType>("job");
  const [targetId, setTargetId] = useState("");
  const [loadingList, setLoadingList] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [intelligenceLoading, setIntelligenceLoading] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

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

  const currentTargetPayload = useCallback(() => {
    if (selectedMessage?.job_id) return { job_id: selectedMessage.job_id };
    if (selectedMessage?.site_id) return { site_id: selectedMessage.site_id };
    if (selectedMessage?.client_id) return { client_id: selectedMessage.client_id };
    if (!targetId) return null;
    if (targetType === "client") return { client_id: targetId };
    if (targetType === "site") return { site_id: targetId };
    return { job_id: targetId };
  }, [selectedMessage, targetId, targetType]);

  const canUseAiDrafting = Boolean(aiStatus?.enabled);

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
        setSummary(null);
        setActionItems([]);
        setDetectedLinks([]);
        setRecordSuggestions([]);
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
    let cancelled = false;
    const timer = window.setTimeout(() => {
      getAiStatus()
        .then((status) => {
          if (!cancelled) setAiStatus(status);
        })
        .catch(() => {
          if (!cancelled) setAiStatus(null);
        });
    }, 0);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, []);

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
          setSummary(null);
          setActionItems([]);
          setDetectedLinks([]);
          setRecordSuggestions([]);
          setNotice(null);
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
            setTargetId("");
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

  useEffect(() => {
    if (!selectedMessage) {
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(() => {
      setIntelligenceLoading("links");
      extractFileLinks({
        organization_id: organizationId,
        email_message_id: selectedMessage.id,
      })
        .then((response) => {
          if (!cancelled) setDetectedLinks(response.links);
        })
        .catch(() => {
          if (!cancelled) setDetectedLinks([]);
        })
        .finally(() => {
          if (!cancelled) setIntelligenceLoading((current) => (current === "links" ? null : current));
        });
    }, 0);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [organizationId, selectedMessage]);

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
      setSummary(null);
      setActionItems([]);
      setDetectedLinks([]);
      setRecordSuggestions([]);
      await loadMessages();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to archive email.");
    } finally {
      setSaving(false);
    }
  }

  async function runSummary() {
    if (!selectedMessage) return;
    setIntelligenceLoading("summary");
    setError(null);
    setNotice(null);
    try {
      const response = await summarizeEmail({
        organization_id: organizationId,
        email_message_id: selectedMessage.id,
        save_draft: true,
      });
      setSummary(response.result);
      setNotice(response.saved_draft ? `Saved ${response.saved_draft.title} to AI Drafts.` : response.message);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to summarize email.");
    } finally {
      setIntelligenceLoading(null);
    }
  }

  async function runActionExtraction() {
    if (!selectedMessage) return;
    setIntelligenceLoading("actions");
    setError(null);
    setNotice(null);
    try {
      const response = await extractEmailActionItems({
        organization_id: organizationId,
        email_message_id: selectedMessage.id,
        save_draft: true,
      });
      setActionItems(response.items);
      setNotice(response.saved_draft ? `Saved ${response.saved_draft.title} to AI Drafts.` : response.message);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to extract action items.");
    } finally {
      setIntelligenceLoading(null);
    }
  }

  async function runRecordSuggestions() {
    if (!selectedMessage) return;
    setIntelligenceLoading("records");
    setError(null);
    setNotice(null);
    try {
      const response = await suggestRecordLinks({
        organization_id: organizationId,
        email_message_id: selectedMessage.id,
      });
      setRecordSuggestions(response.suggestions);
      setNotice(response.message);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to suggest CRM links.");
    } finally {
      setIntelligenceLoading(null);
    }
  }

  async function runDraftReply() {
    if (!selectedMessage || !canUseAiDrafting) return;
    setIntelligenceLoading("reply");
    setError(null);
    setNotice(null);
    try {
      const response = await draftEmailReply({
        organization_id: organizationId,
        email_message_id: selectedMessage.id,
        tone: "professional",
        save_draft: true,
      });
      if (!response.available) {
        setNotice(response.message);
        return;
      }
      setNotice(response.saved_draft ? `Saved ${response.saved_draft.title} to AI Drafts.` : response.message);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to draft reply.");
    } finally {
      setIntelligenceLoading(null);
    }
  }

  async function createReminderFromAction(item: ActionItemSuggestion) {
    if (!selectedMessage) return;
    const target = currentTargetPayload();
    if (!target) {
      setError("Choose a linked record before creating a reminder from this email.");
      return;
    }

    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await createReminder(organizationId, {
        ...target,
        title: item.title,
        description: `${item.reason}${item.due_hint ? ` Due hint: ${item.due_hint}.` : ""}`,
        priority: actionPriority(item.priority),
        status: "open",
        source_type: "email_action_item",
        source_id: selectedMessage.id,
      });
      setNotice("Reminder created from the selected action item.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to create reminder.");
    } finally {
      setSaving(false);
    }
  }

  async function saveLinkCandidate(candidate: FileLinkCandidate) {
    const target = currentTargetPayload();
    if (!target) {
      setError("Choose a linked record before saving an email link as a file.");
      return;
    }

    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await createFileLink(organizationId, {
        ...target,
        file_name: candidate.label,
        public_url: candidate.url,
        source: candidate.link_type === "generic_url" ? "other" : "drive_link",
        caption: selectedMessage
          ? `Detected from email "${selectedMessage.subject}" as ${candidate.link_type}.`
          : `Detected from email as ${candidate.link_type}.`,
      });
      setNotice("File link saved as evidence metadata. No file was downloaded.");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save file link.");
    } finally {
      setSaving(false);
    }
  }

  async function applyRecordSuggestion(suggestion: RecordLinkSuggestion) {
    if (!selectedMessage) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await createEmailRecordLink(organizationId, {
        email_message_id: selectedMessage.id,
        client_id: suggestion.target_type === "client" ? suggestion.target_id : null,
        site_id: suggestion.target_type === "site" ? suggestion.target_id : null,
        job_id: suggestion.target_type === "job" ? suggestion.target_id : null,
        link_reason: suggestion.reason,
        confidence: suggestion.confidence,
      });
      const refreshed = await getEmailMessage(selectedMessage.id, organizationId);
      setSelectedMessage(refreshed);
      await loadMessages();
      setNotice(`Linked email to ${suggestion.target_name}.`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to apply suggested link.");
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
        {notice ? (
          <div className="rounded-md border border-[color:var(--green)]/35 bg-green-soft px-4 py-3 text-sm text-green">
            {notice}
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

            <section className="rounded-lg border border-border-soft bg-panel-2 p-3">
              <div className="flex flex-col gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-text">Intelligence Actions</h3>
                  <p className="mt-1 text-xs text-text-muted">
                    Review-first local analysis; provider-backed drafting is gated by AI configuration.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    className={secondaryButtonClass}
                    onClick={() => void runSummary()}
                    disabled={Boolean(intelligenceLoading)}
                  >
                    {intelligenceLoading === "summary" ? "Summarizing..." : "Summarize"}
                  </button>
                  <button
                    type="button"
                    className={secondaryButtonClass}
                    onClick={() => void runActionExtraction()}
                    disabled={Boolean(intelligenceLoading)}
                  >
                    {intelligenceLoading === "actions" ? "Extracting..." : "Extract Actions"}
                  </button>
                  <button
                    type="button"
                    className={secondaryButtonClass}
                    onClick={() => void runRecordSuggestions()}
                    disabled={Boolean(intelligenceLoading)}
                  >
                    {intelligenceLoading === "records" ? "Checking..." : "Suggest CRM Links"}
                  </button>
                  <button
                    type="button"
                    className={secondaryButtonClass}
                    onClick={() => void runDraftReply()}
                    disabled={Boolean(intelligenceLoading) || !canUseAiDrafting}
                    title={canUseAiDrafting ? "Save a review-first reply draft" : "Configure first"}
                  >
                    {canUseAiDrafting
                      ? intelligenceLoading === "reply"
                        ? "Drafting..."
                        : "Draft Reply"
                      : "Configure first"}
                  </button>
                </div>
              </div>
            </section>

            <SummaryBlock summary={summary} />
            <DetectedLinksBlock
              links={detectedLinks}
              loading={intelligenceLoading === "links"}
              canSave={Boolean(currentTargetPayload()) && !saving}
              onSave={(candidate) => void saveLinkCandidate(candidate)}
            />
            <ActionItemsBlock
              items={actionItems}
              canCreate={Boolean(currentTargetPayload()) && !saving}
              onCreate={(item) => void createReminderFromAction(item)}
            />
            <RecordSuggestionsBlock
              suggestions={recordSuggestions}
              saving={saving}
              onApply={(suggestion) => void applyRecordSuggestion(suggestion)}
            />

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

function SummaryBlock({ summary }: { summary: EmailSummaryResult | null }) {
  if (!summary) {
    return (
      <section>
        <h3 className="text-sm font-semibold text-text">Summary</h3>
        <p className="mt-2 rounded-md border border-border-soft bg-panel-2 px-3 py-2 text-sm text-text-muted">
          Run Summarize to create a review-first local draft summary.
        </p>
      </section>
    );
  }

  return (
    <section>
      <h3 className="text-sm font-semibold text-text">Summary</h3>
      <div className="mt-2 space-y-3 rounded-lg border border-border-soft bg-panel-2 p-3 text-sm">
        <p className="leading-6 text-text-secondary">{summary.summary}</p>
        {summary.key_points.length > 0 ? (
          <ul className="space-y-1 text-text-muted">
            {summary.key_points.map((point, index) => (
              <li key={index}>- {point}</li>
            ))}
          </ul>
        ) : null}
        <p className="text-text-secondary">
          <span className="font-semibold text-text">Next step:</span>{" "}
          {summary.recommended_next_step}
        </p>
      </div>
    </section>
  );
}

function DetectedLinksBlock({
  links,
  loading,
  canSave,
  onSave,
}: {
  links: FileLinkCandidate[];
  loading: boolean;
  canSave: boolean;
  onSave: (candidate: FileLinkCandidate) => void;
}) {
  return (
    <section>
      <h3 className="text-sm font-semibold text-text">Detected Links</h3>
      {loading ? (
        <div className="mt-2 h-16 animate-pulse rounded-md border border-border-soft bg-panel-2" />
      ) : links.length > 0 ? (
        <ul className="mt-2 divide-y divide-border-soft rounded-lg border border-border-soft bg-panel-2">
          {links.map((link) => (
            <li key={link.url} className="space-y-2 px-3 py-2 text-sm">
              <div className="flex items-start justify-between gap-3">
                <span className="min-w-0">
                  <span className="block font-semibold text-text">{link.label}</span>
                  <span className="mt-1 block break-all text-xs text-text-muted">
                    {link.url}
                  </span>
                </span>
                <Badge tone={link.link_type === "generic_url" ? "muted" : "info"}>
                  {link.link_type.replace("_", " ")}
                </Badge>
              </div>
              <div className="flex justify-end gap-2">
                <a
                  href={link.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className={linkChipClass}
                >
                  Open Link
                </a>
                <button
                  type="button"
                  className={secondaryButtonClass}
                  onClick={() => onSave(link)}
                  disabled={!canSave}
                  title={canSave ? "Save metadata only" : "Choose a linked record first"}
                >
                  Save as File Link
                </button>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 rounded-md border border-border-soft bg-panel-2 px-3 py-2 text-sm text-text-muted">
          No Drive, OneDrive, SharePoint, or web links detected in the local email body.
        </p>
      )}
    </section>
  );
}

function ActionItemsBlock({
  items,
  canCreate,
  onCreate,
}: {
  items: ActionItemSuggestion[];
  canCreate: boolean;
  onCreate: (item: ActionItemSuggestion) => void;
}) {
  return (
    <section>
      <h3 className="text-sm font-semibold text-text">Action Item Suggestions</h3>
      {items.length > 0 ? (
        <ul className="mt-2 divide-y divide-border-soft rounded-lg border border-border-soft bg-panel-2">
          {items.map((item, index) => (
            <li key={`${item.title}-${index}`} className="space-y-2 px-3 py-2 text-sm">
              <div className="flex items-start justify-between gap-3">
                <span>
                  <span className="block font-semibold text-text">{item.title}</span>
                  <span className="mt-1 block text-xs text-text-muted">
                    {item.reason}
                    {item.due_hint ? ` Due hint: ${item.due_hint}.` : ""}
                  </span>
                </span>
                <Badge tone={item.priority === "high" ? "warning" : "muted"}>
                  {item.priority}
                </Badge>
              </div>
              <div className="flex justify-end">
                <button
                  type="button"
                  className={secondaryButtonClass}
                  onClick={() => onCreate(item)}
                  disabled={!canCreate}
                  title={canCreate ? "Create local reminder" : "Choose a linked record first"}
                >
                  Create Reminder
                </button>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 rounded-md border border-border-soft bg-panel-2 px-3 py-2 text-sm text-text-muted">
          Run Extract Actions to review possible reminder candidates.
        </p>
      )}
    </section>
  );
}

function RecordSuggestionsBlock({
  suggestions,
  saving,
  onApply,
}: {
  suggestions: RecordLinkSuggestion[];
  saving: boolean;
  onApply: (suggestion: RecordLinkSuggestion) => void;
}) {
  return (
    <section>
      <h3 className="text-sm font-semibold text-text">Suggested CRM Links</h3>
      {suggestions.length > 0 ? (
        <ul className="mt-2 divide-y divide-border-soft rounded-lg border border-border-soft bg-panel-2">
          {suggestions.map((suggestion) => (
            <li key={`${suggestion.target_type}-${suggestion.target_id}`} className="space-y-2 px-3 py-2 text-sm">
              <div className="flex items-start justify-between gap-3">
                <span>
                  <span className="block font-semibold text-text">
                    {suggestion.target_name}
                  </span>
                  <span className="mt-1 block text-xs text-text-muted">
                    {suggestion.reason}
                  </span>
                </span>
                <Badge tone="info">{suggestion.target_type}</Badge>
              </div>
              <div className="flex justify-end">
                <button
                  type="button"
                  className={secondaryButtonClass}
                  onClick={() => onApply(suggestion)}
                  disabled={saving}
                >
                  Use Suggestion
                </button>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 rounded-md border border-border-soft bg-panel-2 px-3 py-2 text-sm text-text-muted">
          Run Suggest CRM Links to check exact local client, site, and job matches.
        </p>
      )}
    </section>
  );
}
