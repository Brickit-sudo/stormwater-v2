"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import Badge from "@/components/ui/Badge";
import {
  archiveAiDraft,
  createAiDraft,
  generateClientSummaryDraft,
  generateMaintenanceRecommendationDraft,
  generateReportSectionDraft,
  getAiStatus,
  getAiDraft,
  listAiDrafts,
  listClients,
  listEmailMessages,
  listJobs,
  listSites,
  updateAiDraft,
} from "@/lib/api";
import type {
  AiDraft,
  AiDraftCreateInput,
  AiDraftStatus,
  AiStatus,
  Client,
  EmailMessage,
  Job,
  ReportSectionDraftResponse,
  Site,
  UUID,
} from "@/lib/types";
import {
  dangerButtonClass,
  primaryButtonClass,
  secondaryButtonClass,
} from "@/lib/ui";

import WorkList from "./WorkList";
import WorkPreview from "./WorkPreview";

type AiDraftsWorkViewProps = {
  organizationId: UUID;
};

type TargetType = "none" | "client" | "site" | "job";
type FormMode = "create" | "edit" | null;
type HelperType = "report_section" | "maintenance_recommendation" | "client_summary";

type DraftFormState = {
  target_type: TargetType;
  target_id: string;
  email_message_id: string;
  draft_type: string;
  title: string;
  prompt_context: string;
  draft_text: string;
};

type HelperFormState = {
  helper_type: HelperType;
  target_type: TargetType;
  target_id: string;
  email_message_id: string;
  context: string;
  section_heading: string;
  system_type: string;
};

const draftLimit = 25;
const statusOptions: Array<"" | AiDraftStatus> = ["", "draft", "reviewed", "used"];

const emptyForm: DraftFormState = {
  target_type: "none",
  target_id: "",
  email_message_id: "",
  draft_type: "email_reply",
  title: "",
  prompt_context: "",
  draft_text: "",
};

const emptyHelperForm: HelperFormState = {
  helper_type: "report_section",
  target_type: "none",
  target_id: "",
  email_message_id: "",
  context: "",
  section_heading: "Inspection Findings",
  system_type: "",
};

function optional(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function statusTone(status: AiDraftStatus): "success" | "warning" | "muted" | "info" {
  if (status === "reviewed") return "warning";
  if (status === "used") return "success";
  if (status === "draft") return "info";
  return "muted";
}

function formatDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export default function AiDraftsWorkView({ organizationId }: AiDraftsWorkViewProps) {
  const [drafts, setDrafts] = useState<AiDraft[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedDraft, setSelectedDraft] = useState<AiDraft | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [emails, setEmails] = useState<EmailMessage[]>([]);
  const [aiStatus, setAiStatus] = useState<AiStatus | null>(null);
  const [statusFilter, setStatusFilter] = useState<"" | AiDraftStatus>("");
  const [formMode, setFormMode] = useState<FormMode>(null);
  const [form, setForm] = useState<DraftFormState>(emptyForm);
  const [helperForm, setHelperForm] = useState<HelperFormState>(emptyHelperForm);
  const [loadingList, setLoadingList] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [generating, setGenerating] = useState(false);
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
  const emailSubjectById = useMemo(
    () => new Map(emails.map((email) => [email.id, email.subject])),
    [emails],
  );

  const targetOptions = useMemo(() => {
    if (form.target_type === "client") {
      return clients.map((client) => ({ id: client.id, label: client.name }));
    }
    if (form.target_type === "site") {
      return sites.map((site) => ({
        id: site.id,
        label: clientNameById.get(site.client_id)
          ? `${site.name} - ${clientNameById.get(site.client_id)}`
          : site.name,
      }));
    }
    if (form.target_type === "job") {
      return jobs.map((job) => ({
        id: job.id,
        label: siteNameById.get(job.site_id)
          ? `${job.name} - ${siteNameById.get(job.site_id)}`
          : job.name,
      }));
    }
    return [];
  }, [clientNameById, clients, form.target_type, jobs, siteNameById, sites]);

  const helperTargetOptions = useMemo(() => {
    if (helperForm.target_type === "client") {
      return clients.map((client) => ({ id: client.id, label: client.name }));
    }
    if (helperForm.target_type === "site") {
      return sites.map((site) => ({
        id: site.id,
        label: clientNameById.get(site.client_id)
          ? `${site.name} - ${clientNameById.get(site.client_id)}`
          : site.name,
      }));
    }
    if (helperForm.target_type === "job") {
      return jobs.map((job) => ({
        id: job.id,
        label: siteNameById.get(job.site_id)
          ? `${job.name} - ${siteNameById.get(job.site_id)}`
          : job.name,
      }));
    }
    return [];
  }, [clientNameById, clients, helperForm.target_type, jobs, siteNameById, sites]);

  const linkedLabel = useCallback(
    (draft: AiDraft): string => {
      if (draft.job_id) return jobNameById.get(draft.job_id) ?? "Linked job";
      if (draft.site_id) return siteNameById.get(draft.site_id) ?? "Linked site";
      if (draft.client_id) return clientNameById.get(draft.client_id) ?? "Linked client";
      return "No CRM link";
    },
    [clientNameById, jobNameById, siteNameById],
  );

  const firstTargetId = useCallback(
    (type: TargetType): string => {
      if (type === "client") return clients[0]?.id ?? "";
      if (type === "site") return sites[0]?.id ?? "";
      if (type === "job") return jobs[0]?.id ?? "";
      return "";
    },
    [clients, jobs, sites],
  );

  const loadReferences = useCallback(async () => {
    try {
      const [clientResponse, siteResponse, jobResponse, emailResponse] =
        await Promise.all([
          listClients({ organizationId, limit: 500 }),
          listSites({ organizationId, limit: 500 }),
          listJobs({ organizationId, limit: 500 }),
          listEmailMessages({ organizationId, limit: 100 }),
        ]);
      setClients(clientResponse.items);
      setSites(siteResponse.items);
      setJobs(jobResponse.items);
      setEmails(emailResponse.items);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load draft references.");
    }
  }, [organizationId]);

  const loadDrafts = useCallback(async () => {
    setLoadingList(true);
    setError(null);
    try {
      const response = await listAiDrafts({
        organizationId,
        status: statusFilter || undefined,
        limit: draftLimit,
        offset,
      });
      setDrafts(response.items);
      setTotal(response.total);
      if (response.items.length === 0) {
        setSelectedDraft(null);
      }
      setSelectedId((current) =>
        current && response.items.some((draft) => draft.id === current)
          ? current
          : response.items[0]?.id ?? null,
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load AI drafts.");
    } finally {
      setLoadingList(false);
    }
  }, [offset, organizationId, statusFilter]);

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
      void loadDrafts();
    }, 150);
    return () => window.clearTimeout(timer);
  }, [loadDrafts]);

  useEffect(() => {
    if (!selectedId || formMode === "create") {
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(() => {
      setLoadingPreview(true);
      getAiDraft(selectedId, organizationId)
        .then((draft) => {
          if (cancelled) return;
          setSelectedDraft(draft);
        })
        .catch((caught) => {
          if (!cancelled) {
            setError(caught instanceof Error ? caught.message : "Unable to load draft preview.");
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
  }, [formMode, organizationId, selectedId]);

  function formFromDraft(draft: AiDraft): DraftFormState {
    const target_type: TargetType = draft.job_id
      ? "job"
      : draft.site_id
        ? "site"
        : draft.client_id
          ? "client"
          : "none";
    return {
      target_type,
      target_id: draft.job_id ?? draft.site_id ?? draft.client_id ?? "",
      email_message_id: draft.email_message_id ?? "",
      draft_type: draft.draft_type,
      title: draft.title,
      prompt_context: draft.prompt_context ?? "",
      draft_text: draft.draft_text,
    };
  }

  function startCreate() {
    const target_type: TargetType = jobs.length > 0 ? "job" : sites.length > 0 ? "site" : clients.length > 0 ? "client" : "none";
    setForm({
      ...emptyForm,
      target_type,
      target_id: firstTargetId(target_type),
    });
    setFormMode("create");
    setSelectedDraft(null);
    setError(null);
  }

  function startEdit() {
    if (!selectedDraft) {
      return;
    }
    setForm(formFromDraft(selectedDraft));
    setFormMode("edit");
    setError(null);
  }

  function cancelForm() {
    setFormMode(null);
    setForm(emptyForm);
    setError(null);
  }

  function updateTargetType(type: TargetType) {
    setForm({
      ...form,
      target_type: type,
      target_id: firstTargetId(type),
    });
  }

  function updateHelperTargetType(type: TargetType) {
    setHelperForm({
      ...helperForm,
      target_type: type,
      target_id: firstTargetId(type),
    });
  }

  function helperTargetPayload() {
    if (helperForm.target_type === "none") {
      return {};
    }
    if (!helperForm.target_id) {
      return null;
    }
    if (helperForm.target_type === "client") {
      return { client_id: helperForm.target_id };
    }
    if (helperForm.target_type === "site") {
      return { site_id: helperForm.target_id };
    }
    return { job_id: helperForm.target_id };
  }

  function payloadFromForm(): AiDraftCreateInput {
    return {
      client_id: form.target_type === "client" ? form.target_id : null,
      site_id: form.target_type === "site" ? form.target_id : null,
      job_id: form.target_type === "job" ? form.target_id : null,
      email_message_id: optional(form.email_message_id),
      draft_type: form.draft_type.trim() || "email_reply",
      title: form.title.trim(),
      prompt_context: optional(form.prompt_context),
      draft_text: form.draft_text.trim(),
    };
  }

  async function saveDraft() {
    const payload = payloadFromForm();
    if (!payload.title) {
      setError("Draft title is required.");
      return;
    }
    if (!payload.draft_text) {
      setError("Draft text is required.");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const saved =
        formMode === "edit" && selectedDraft
          ? await updateAiDraft(selectedDraft.id, organizationId, payload)
          : await createAiDraft(organizationId, payload);
      setFormMode(null);
      setSelectedId(saved.id);
      setSelectedDraft(saved);
      await loadDrafts();
      await loadReferences();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save draft.");
    } finally {
      setSaving(false);
    }
  }

  async function generateHelperDraft() {
    if (!aiStatus?.enabled) {
      setError("Configure OPENAI_API_KEY before generating AI drafts.");
      return;
    }
    const target = helperTargetPayload();
    if (target === null) {
      setError("Choose a linked record or switch CRM Link to No CRM link.");
      return;
    }
    if (!optional(helperForm.context) && !optional(helperForm.email_message_id)) {
      setError("Add context or choose a related email before generating a draft.");
      return;
    }

    setGenerating(true);
    setError(null);
    setNotice(null);
    try {
      const base = {
        organization_id: organizationId,
        ...target,
        email_message_id: optional(helperForm.email_message_id),
        user_context: optional(helperForm.context),
        save_draft: true,
      };
      let response: ReportSectionDraftResponse;
      if (helperForm.helper_type === "maintenance_recommendation") {
        response = await generateMaintenanceRecommendationDraft({
          ...base,
          system_type: optional(helperForm.system_type),
        });
      } else if (helperForm.helper_type === "client_summary") {
        response = await generateClientSummaryDraft({
          ...base,
          audience: "client",
        });
      } else {
        response = await generateReportSectionDraft({
          ...base,
          section_heading: helperForm.section_heading.trim() || "Inspection Findings",
        });
      }

      if (!response.available) {
        setNotice(response.message);
        return;
      }
      if (response.saved_draft) {
        setSelectedId(response.saved_draft.id);
        setNotice(`Saved ${response.saved_draft.title} to AI Drafts.`);
      } else {
        setNotice(response.message);
      }
      await loadDrafts();
      await loadReferences();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to generate draft.");
    } finally {
      setGenerating(false);
    }
  }

  async function setDraftStatus(status: AiDraftStatus) {
    if (!selectedDraft) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const updated = await updateAiDraft(selectedDraft.id, organizationId, { status });
      setSelectedDraft(updated);
      await loadDrafts();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to update draft status.");
    } finally {
      setSaving(false);
    }
  }

  async function archiveSelectedDraft() {
    if (!selectedDraft) {
      return;
    }
    const confirmed = window.confirm(`Archive ${selectedDraft.title}?`);
    if (!confirmed) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await archiveAiDraft(selectedDraft.id, organizationId);
      setSelectedDraft(null);
      setSelectedId(null);
      await loadDrafts();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to archive draft.");
    } finally {
      setSaving(false);
    }
  }

  const previewTitle =
    formMode === "create"
      ? "New AI Draft"
      : formMode === "edit"
        ? "Edit AI Draft"
        : selectedDraft?.title ?? "Select a draft";

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_480px]">
      <div className="min-w-0 space-y-3">
        <section className="rounded-lg border border-border bg-panel p-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <label className="block md:w-56">
              <span className="text-sm font-medium text-text-secondary">
                Status
              </span>
              <select
                value={statusFilter}
                onChange={(event) => {
                  setStatusFilter(event.target.value as "" | AiDraftStatus);
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
            <button
              type="button"
              className={primaryButtonClass}
              onClick={startCreate}
              disabled={saving}
            >
              New Draft
            </button>
          </div>
        </section>

        <ReportDraftHelper
          form={helperForm}
          setForm={setHelperForm}
          targetOptions={helperTargetOptions}
          emails={emails}
          aiEnabled={Boolean(aiStatus?.enabled)}
          generating={generating}
          onTargetTypeChange={updateHelperTargetType}
          onGenerate={() => void generateHelperDraft()}
        />

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
          title="AI Drafts"
          countLabel={`${total} manual drafts`}
          rows={drafts}
          getRowId={(draft) => draft.id}
          selectedId={selectedId}
          onSelect={(draft) => {
            setSelectedId(draft.id);
            setFormMode(null);
          }}
          renderTitle={(draft) => draft.title}
          renderMeta={(draft) => `${draft.draft_type} - ${linkedLabel(draft)}`}
          renderAside={(draft) => (
            <Badge tone={statusTone(draft.status)}>{draft.status}</Badge>
          )}
          loading={loadingList}
          emptyTitle="No AI drafts found"
          emptyDescription="Create a manual draft and link it to local CRM or email records."
          page={{
            offset,
            limit: draftLimit,
            total,
            onPrevious: () => setOffset(Math.max(0, offset - draftLimit)),
            onNext: () => setOffset(offset + draftLimit),
          }}
        />
      </div>

      <WorkPreview
        title={previewTitle}
        subtitle={
          formMode
            ? "Manual storage only; no AI generation runs here"
            : selectedDraft
              ? `${selectedDraft.draft_type} - ${linkedLabel(selectedDraft)}`
              : "Draft preview"
        }
        actions={
          !formMode && selectedDraft ? (
            <>
              <button
                type="button"
                className={secondaryButtonClass}
                onClick={startEdit}
                disabled={saving}
              >
                Edit Draft
              </button>
              {selectedDraft.status !== "reviewed" ? (
                <button
                  type="button"
                  className={secondaryButtonClass}
                  onClick={() => void setDraftStatus("reviewed")}
                  disabled={saving}
                >
                  Mark Reviewed
                </button>
              ) : null}
              {selectedDraft.status !== "used" ? (
                <button
                  type="button"
                  className={secondaryButtonClass}
                  onClick={() => void setDraftStatus("used")}
                  disabled={saving}
                >
                  Mark Used
                </button>
              ) : null}
              <button
                type="button"
                className={dangerButtonClass}
                onClick={() => void archiveSelectedDraft()}
                disabled={saving}
              >
                Archive Draft
              </button>
            </>
          ) : null
        }
      >
        {formMode ? (
          <DraftForm
            form={form}
            setForm={setForm}
            targetOptions={targetOptions}
            emails={emails}
            saving={saving}
            onTargetTypeChange={updateTargetType}
            onCancel={cancelForm}
            onSave={saveDraft}
          />
        ) : loadingPreview ? (
          <div className="h-40 animate-pulse rounded-md border border-border-soft bg-panel-2" />
        ) : selectedDraft ? (
          <div className="space-y-5">
            <div className="grid gap-3 text-sm sm:grid-cols-2">
              <Meta label="Status" value={selectedDraft.status} />
              <Meta label="Created" value={formatDate(selectedDraft.created_at)} />
              <Meta label="CRM Link" value={linkedLabel(selectedDraft)} />
              <Meta
                label="Email"
                value={
                  selectedDraft.email_message_id
                    ? emailSubjectById.get(selectedDraft.email_message_id) ?? "Linked email"
                    : "No email link"
                }
              />
            </div>
            {selectedDraft.prompt_context ? (
              <section>
                <h3 className="text-sm font-semibold text-text">Prompt Context</h3>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-text-secondary">
                  {selectedDraft.prompt_context}
                </p>
              </section>
            ) : null}
            <section>
              <h3 className="text-sm font-semibold text-text">Draft Text</h3>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-text-secondary">
                {selectedDraft.draft_text}
              </p>
            </section>
          </div>
        ) : (
          <p className="text-sm text-text-muted">
            Choose a draft or create a manual draft tied to local CRM and email records.
          </p>
        )}
      </WorkPreview>
    </div>
  );
}

function DraftForm({
  form,
  setForm,
  targetOptions,
  emails,
  saving,
  onTargetTypeChange,
  onCancel,
  onSave,
}: {
  form: DraftFormState;
  setForm: (form: DraftFormState) => void;
  targetOptions: Array<{ id: string; label: string }>;
  emails: EmailMessage[];
  saving: boolean;
  onTargetTypeChange: (type: TargetType) => void;
  onCancel: () => void;
  onSave: () => void;
}) {
  function update(field: keyof DraftFormState, value: string) {
    if (field === "target_type") {
      onTargetTypeChange(value as TargetType);
      return;
    }
    setForm({ ...form, [field]: value });
  }

  return (
    <form
      className="space-y-4"
      onSubmit={(event) => {
        event.preventDefault();
        onSave();
      }}
    >
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField label="Draft Type">
          <input
            value={form.draft_type}
            onChange={(event) => update("draft_type", event.target.value)}
            className="form-input"
          />
        </FormField>
        <FormField label="Related Email">
          <select
            value={form.email_message_id}
            onChange={(event) => update("email_message_id", event.target.value)}
            className="form-input"
          >
            <option value="">No email link</option>
            {emails.map((email) => (
              <option key={email.id} value={email.id}>
                {email.subject}
              </option>
            ))}
          </select>
        </FormField>
      </div>

      <FormField label="Title">
        <input
          value={form.title}
          onChange={(event) => update("title", event.target.value)}
          className="form-input"
          required
          maxLength={255}
        />
      </FormField>

      <div className="grid gap-3 sm:grid-cols-[140px_minmax(0,1fr)]">
        <FormField label="CRM Link">
          <select
            value={form.target_type}
            onChange={(event) => update("target_type", event.target.value)}
            className="form-input"
          >
            <option value="none">No CRM link</option>
            <option value="client">Client</option>
            <option value="site">Site</option>
            <option value="job">Job</option>
          </select>
        </FormField>
        <FormField label="Linked Record">
          <select
            value={form.target_id}
            onChange={(event) => update("target_id", event.target.value)}
            className="form-input"
            disabled={form.target_type === "none"}
          >
            <option value="">Select a record</option>
            {targetOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </FormField>
      </div>

      <FormField label="Prompt Context">
        <textarea
          value={form.prompt_context}
          onChange={(event) => update("prompt_context", event.target.value)}
          className="form-textarea"
          rows={4}
        />
      </FormField>

      <FormField label="Draft Text">
        <textarea
          value={form.draft_text}
          onChange={(event) => update("draft_text", event.target.value)}
          className="form-textarea"
          rows={8}
          required
        />
      </FormField>

      <div className="flex justify-end gap-2 pt-2">
        <button
          type="button"
          className={secondaryButtonClass}
          onClick={onCancel}
          disabled={saving}
        >
          Cancel
        </button>
        <button type="submit" className={primaryButtonClass} disabled={saving}>
          {saving ? "Saving..." : "Save Draft"}
        </button>
      </div>
    </form>
  );
}

function ReportDraftHelper({
  form,
  setForm,
  targetOptions,
  emails,
  aiEnabled,
  generating,
  onTargetTypeChange,
  onGenerate,
}: {
  form: HelperFormState;
  setForm: (form: HelperFormState) => void;
  targetOptions: Array<{ id: string; label: string }>;
  emails: EmailMessage[];
  aiEnabled: boolean;
  generating: boolean;
  onTargetTypeChange: (type: TargetType) => void;
  onGenerate: () => void;
}) {
  function update(field: keyof HelperFormState, value: string) {
    if (field === "target_type") {
      onTargetTypeChange(value as TargetType);
      return;
    }
    if (field === "helper_type") {
      setForm({ ...form, helper_type: value as HelperType });
      return;
    }
    setForm({ ...form, [field]: value });
  }

  return (
    <section className="rounded-lg border border-border bg-panel p-4">
      <div className="flex flex-col gap-3">
        <div>
          <h2 className="text-base font-semibold text-text">Report Draft Helper</h2>
          <p className="mt-1 text-sm text-text-muted">
            Provider-backed drafts are saved locally for review and do not generate final reports.
          </p>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <FormField label="Helper">
            <select
              value={form.helper_type}
              onChange={(event) => update("helper_type", event.target.value)}
              className="form-input"
              disabled={generating}
            >
              <option value="report_section">Report section</option>
              <option value="maintenance_recommendation">Maintenance recommendation</option>
              <option value="client_summary">Client-facing summary</option>
            </select>
          </FormField>
          <FormField label="Related Email">
            <select
              value={form.email_message_id}
              onChange={(event) => update("email_message_id", event.target.value)}
              className="form-input"
              disabled={generating}
            >
              <option value="">No email link</option>
              {emails.map((email) => (
                <option key={email.id} value={email.id}>
                  {email.subject}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="Section Heading">
            <input
              value={form.section_heading}
              onChange={(event) => update("section_heading", event.target.value)}
              className="form-input"
              disabled={generating || form.helper_type !== "report_section"}
            />
          </FormField>
        </div>

        <div className="grid gap-3 md:grid-cols-[140px_minmax(0,1fr)_180px]">
          <FormField label="CRM Link">
            <select
              value={form.target_type}
              onChange={(event) => update("target_type", event.target.value)}
              className="form-input"
              disabled={generating}
            >
              <option value="none">No CRM link</option>
              <option value="client">Client</option>
              <option value="site">Site</option>
              <option value="job">Job</option>
            </select>
          </FormField>
          <FormField label="Linked Record">
            <select
              value={form.target_id}
              onChange={(event) => update("target_id", event.target.value)}
              className="form-input"
              disabled={generating || form.target_type === "none"}
            >
              <option value="">Select a record</option>
              {targetOptions.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </FormField>
          <FormField label="System Type">
            <input
              value={form.system_type}
              onChange={(event) => update("system_type", event.target.value)}
              className="form-input"
              disabled={generating || form.helper_type !== "maintenance_recommendation"}
              placeholder="Catch basin"
            />
          </FormField>
        </div>

        <FormField label="Context">
          <textarea
            value={form.context}
            onChange={(event) => update("context", event.target.value)}
            className="form-textarea"
            rows={4}
            disabled={generating}
            placeholder="Paste field notes, findings, or client-facing context"
          />
        </FormField>

        <div className="flex justify-end">
          <button
            type="button"
            className={primaryButtonClass}
            onClick={onGenerate}
            disabled={generating || !aiEnabled}
            title={aiEnabled ? "Generate and save local draft" : "Configure first"}
          >
            {aiEnabled ? (generating ? "Generating..." : "Generate Draft") : "Configure first"}
          </button>
        </div>
      </div>
    </section>
  );
}

function FormField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-text-secondary">{label}</span>
      <div className="mt-2">{children}</div>
    </label>
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
