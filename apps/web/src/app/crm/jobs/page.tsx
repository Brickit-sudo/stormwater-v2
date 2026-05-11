"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import AppShell from "@/components/AppShell";
import DetailPanel, { DetailField } from "@/components/crm/DetailPanel";
import EmptyState from "@/components/crm/EmptyState";
import EntityTable, { type EntityColumn } from "@/components/crm/EntityTable";
import StatusBadge from "@/components/crm/StatusBadge";
import {
  archiveJob,
  createJob,
  demoOrganizationId,
  listClients,
  listJobs,
  listSites,
  updateJob,
} from "@/lib/api";
import type { Client, Job, JobFormInput, Site } from "@/lib/types";

type FormMode = "view" | "create" | "edit" | "status";

type JobFormState = {
  client_id: string;
  site_id: string;
  name: string;
  service_type: string;
  status: string;
  scheduled_date: string;
  due_date: string;
  scope: string;
  notes: string;
  drive_folder_url: string;
};

const buttonClass =
  "inline-flex h-9 items-center justify-center rounded-md bg-[#1a7f37] px-3 text-sm font-semibold text-white transition hover:bg-[#176d31] disabled:cursor-not-allowed disabled:bg-[#a9b7a9]";
const secondaryButtonClass =
  "inline-flex h-9 items-center justify-center rounded-md border border-[#cfd8cc] bg-white px-3 text-sm font-semibold text-[#263126] transition hover:bg-[#f6f8f4] disabled:cursor-not-allowed disabled:text-[#98a398]";
const dangerButtonClass =
  "inline-flex h-9 items-center justify-center rounded-md border border-[#e2bcbc] bg-white px-3 text-sm font-semibold text-[#963333] transition hover:bg-[#fff6f6] disabled:cursor-not-allowed disabled:text-[#b99b9b]";

const jobStatusOptions = [
  "draft",
  "scheduled",
  "in_progress",
  "completed",
  "cancelled",
];

const columns: EntityColumn<Job>[] = [
  {
    key: "name",
    header: "Name",
    className: "w-[28%]",
    render: (job) => <span className="font-medium">{job.name}</span>,
  },
  {
    key: "service_type",
    header: "Service Type",
    className: "w-[20%]",
    render: (job) => job.service_type || "Not set",
  },
  {
    key: "status",
    header: "Status",
    className: "w-[16%]",
    render: (job) => <StatusBadge status={job.status} />,
  },
  {
    key: "scheduled_date",
    header: "Scheduled Date",
    className: "w-[18%]",
    render: (job) => formatDate(job.scheduled_date),
  },
  {
    key: "due_date",
    header: "Due Date",
    className: "w-[18%]",
    render: (job) => formatDate(job.due_date),
  },
];

function optional(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function formatDate(value: string | null): string {
  if (!value) {
    return "Not set";
  }

  const [year, month, day] = value.split("-");
  if (!year || !month || !day) {
    return value;
  }

  return `${month}/${day}/${year}`;
}

function emptyForm(defaultClientId = "", defaultSiteId = ""): JobFormState {
  return {
    client_id: defaultClientId,
    site_id: defaultSiteId,
    name: "",
    service_type: "",
    status: "draft",
    scheduled_date: "",
    due_date: "",
    scope: "",
    notes: "",
    drive_folder_url: "",
  };
}

function formFromJob(job: Job): JobFormState {
  return {
    client_id: job.client_id,
    site_id: job.site_id,
    name: job.name,
    service_type: job.service_type ?? "",
    status: job.status,
    scheduled_date: job.scheduled_date ?? "",
    due_date: job.due_date ?? "",
    scope: job.scope ?? "",
    notes: job.notes ?? "",
    drive_folder_url: job.drive_folder_url ?? "",
  };
}

function payloadFromForm(form: JobFormState): JobFormInput {
  return {
    client_id: form.client_id,
    site_id: form.site_id,
    name: form.name.trim(),
    service_type: optional(form.service_type),
    status: form.status.trim() || "draft",
    scheduled_date: optional(form.scheduled_date),
    due_date: optional(form.due_date),
    scope: optional(form.scope),
    notes: optional(form.notes),
    drive_folder_url: optional(form.drive_folder_url),
  };
}

function SetupMessage() {
  return (
    <AppShell>
      <div className="rounded-md border border-[#e4d28d] bg-[#fff9e8] p-5 text-sm text-[#604a13]">
        Set NEXT_PUBLIC_DEMO_ORG_ID in apps/web/.env.local to use the CRM.
      </div>
    </AppShell>
  );
}

export default function JobsPage() {
  const organizationId = demoOrganizationId;
  const [jobs, setJobs] = useState<Job[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<FormMode>("view");
  const [form, setForm] = useState<JobFormState>(emptyForm());
  const [statusDraft, setStatusDraft] = useState("draft");

  const clientNameById = useMemo(
    () => new Map(clients.map((client) => [client.id, client.name])),
    [clients],
  );

  const siteNameById = useMemo(
    () => new Map(sites.map((site) => [site.id, site.name])),
    [sites],
  );

  const selectedJob = useMemo(
    () => jobs.find((job) => job.id === selectedJobId) ?? null,
    [jobs, selectedJobId],
  );

  const loadReferences = useCallback(async () => {
    if (!organizationId) {
      return;
    }

    try {
      const [clientResponse, siteResponse] = await Promise.all([
        listClients({ organizationId, limit: 500 }),
        listSites({ organizationId, limit: 500 }),
      ]);
      setClients(clientResponse.items);
      setSites(siteResponse.items);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to load dropdown data.",
      );
    }
  }, [organizationId]);

  const loadJobs = useCallback(async () => {
    if (!organizationId) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await listJobs({
        organizationId,
        search,
        status: statusFilter || undefined,
        limit: 100,
      });
      setJobs(response.items);
      setSelectedJobId((current) => {
        if (current && response.items.some((job) => job.id === current)) {
          return current;
        }
        return response.items[0]?.id ?? null;
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load jobs.");
    } finally {
      setLoading(false);
    }
  }, [organizationId, search, statusFilter]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadReferences();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [loadReferences]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const params = new URLSearchParams(window.location.search);
      if (params.get("new") === "1") {
        const clientId = params.get("client_id") ?? "";
        const siteId = params.get("site_id") ?? "";
        setMode("create");
        setForm(emptyForm(clientId, siteId));
      }
    }, 0);

    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadJobs();
    }, 250);

    return () => window.clearTimeout(timer);
  }, [loadJobs]);

  if (!organizationId) {
    return <SetupMessage />;
  }

  function startCreate() {
    const defaultSite = sites[0];
    setMode("create");
    setForm(emptyForm(defaultSite?.client_id ?? clients[0]?.id ?? "", defaultSite?.id ?? ""));
    setError(null);
  }

  function startEdit() {
    if (!selectedJob) {
      return;
    }
    setMode("edit");
    setForm(formFromJob(selectedJob));
    setError(null);
  }

  function startStatusUpdate() {
    if (!selectedJob) {
      return;
    }
    setStatusDraft(selectedJob.status);
    setMode("status");
    setError(null);
  }

  async function saveJob() {
    const payload = payloadFromForm(form);
    if (!payload.client_id || !payload.site_id) {
      setError("Client and site are required.");
      return;
    }
    if (!payload.name) {
      setError("Job name is required.");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const saved =
        mode === "create"
          ? await createJob(organizationId, payload)
          : selectedJob
            ? await updateJob(selectedJob.id, organizationId, payload)
            : null;

      await loadJobs();
      if (saved) {
        setSelectedJobId(saved.id);
      }
      setMode("view");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save job.");
    } finally {
      setSaving(false);
    }
  }

  async function saveStatus() {
    if (!selectedJob) {
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const saved = await updateJob(selectedJob.id, organizationId, {
        status: statusDraft,
      });
      await loadJobs();
      setSelectedJobId(saved.id);
      setMode("view");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to update status.");
    } finally {
      setSaving(false);
    }
  }

  async function archiveSelectedJob() {
    if (!selectedJob) {
      return;
    }

    const confirmed = window.confirm(`Archive ${selectedJob.name}?`);
    if (!confirmed) {
      return;
    }

    setSaving(true);
    setError(null);

    try {
      await archiveJob(selectedJob.id, organizationId);
      setMode("view");
      await loadJobs();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to archive job.");
    } finally {
      setSaving(false);
    }
  }

  const panelActions =
    mode === "view" && selectedJob ? (
      <>
        <button
          type="button"
          className={secondaryButtonClass}
          onClick={startStatusUpdate}
          disabled={saving}
        >
          Update Status
        </button>
        <button
          type="button"
          className={secondaryButtonClass}
          onClick={startEdit}
          disabled={saving}
        >
          Edit Job
        </button>
        <button
          type="button"
          className={dangerButtonClass}
          onClick={archiveSelectedJob}
          disabled={saving}
        >
          Archive Job
        </button>
      </>
    ) : null;

  return (
    <AppShell>
      <div className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-[#172017]">Jobs</h1>
            <p className="mt-1 text-sm text-[#667466]">
              Schedule and track work against real client and site records.
            </p>
          </div>
          <button
            type="button"
            className={buttonClass}
            onClick={startCreate}
            disabled={sites.length === 0}
          >
            New Job
          </button>
        </div>

        {error ? (
          <div className="rounded-md border border-[#e7b9b9] bg-[#fff6f6] px-4 py-3 text-sm text-[#8a2f2f]">
            {error}
          </div>
        ) : null}

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
          <section className="min-w-0 space-y-3">
            <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_220px]">
              <label className="block">
                <span className="text-sm font-medium text-[#3d4a3d]">
                  Search jobs
                </span>
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search by name, code, or service type"
                  className="mt-2 h-10 w-full rounded-md border border-[#cfd8cc] bg-white px-3 text-sm outline-none transition placeholder:text-[#9aa59a] focus:border-[#1a7f37] focus:ring-2 focus:ring-[#d8eedc]"
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-[#3d4a3d]">
                  Status filter
                </span>
                <select
                  value={statusFilter}
                  onChange={(event) => setStatusFilter(event.target.value)}
                  className="mt-2 h-10 w-full rounded-md border border-[#cfd8cc] bg-white px-3 text-sm outline-none transition focus:border-[#1a7f37] focus:ring-2 focus:ring-[#d8eedc]"
                >
                  <option value="">All statuses</option>
                  {jobStatusOptions.map((status) => (
                    <option key={status} value={status}>
                      {status.replaceAll("_", " ")}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <EntityTable
              rows={jobs}
              columns={columns}
              getRowId={(job) => job.id}
              selectedRowId={selectedJobId}
              onRowClick={(job) => {
                setSelectedJobId(job.id);
                setMode("view");
              }}
              loading={loading}
              emptyTitle="No jobs found"
              emptyDescription="Create jobs only after a client and site are available."
            />
          </section>

          <DetailPanel
            title={
              mode === "create"
                ? "New Job"
                : selectedJob?.name ?? "Select a job"
            }
            subtitle={
              selectedJob
                ? siteNameById.get(selectedJob.site_id) ?? "Site not loaded"
                : undefined
            }
            actions={panelActions}
          >
            {mode === "create" || mode === "edit" ? (
              <JobForm
                clients={clients}
                sites={sites}
                form={form}
                setForm={setForm}
                saving={saving}
                onCancel={() => setMode("view")}
                onSave={saveJob}
              />
            ) : mode === "status" && selectedJob ? (
              <StatusForm
                status={statusDraft}
                setStatus={setStatusDraft}
                saving={saving}
                onCancel={() => setMode("view")}
                onSave={saveStatus}
              />
            ) : selectedJob ? (
              <div className="space-y-6">
                <dl className="grid gap-4 sm:grid-cols-2">
                  <DetailField label="Status" value={<StatusBadge status={selectedJob.status} />} />
                  <DetailField
                    label="Client"
                    value={clientNameById.get(selectedJob.client_id)}
                  />
                  <DetailField
                    label="Site"
                    value={siteNameById.get(selectedJob.site_id)}
                  />
                  <DetailField label="Service Type" value={selectedJob.service_type} />
                  <DetailField
                    label="Scheduled Date"
                    value={formatDate(selectedJob.scheduled_date)}
                  />
                  <DetailField
                    label="Due Date"
                    value={formatDate(selectedJob.due_date)}
                  />
                  <DetailField label="Scope" value={selectedJob.scope} />
                  <DetailField label="Drive URL" value={selectedJob.drive_folder_url} />
                  <DetailField label="Notes" value={selectedJob.notes} />
                </dl>
              </div>
            ) : (
              <EmptyState
                title="No job selected"
                description="Choose a row to see work details and status."
              />
            )}
          </DetailPanel>
        </div>
      </div>
    </AppShell>
  );
}

function JobForm({
  clients,
  sites,
  form,
  setForm,
  saving,
  onCancel,
  onSave,
}: {
  clients: Client[];
  sites: Site[];
  form: JobFormState;
  setForm: (form: JobFormState) => void;
  saving: boolean;
  onCancel: () => void;
  onSave: () => void;
}) {
  const availableSites = sites.filter(
    (site) => !form.client_id || site.client_id === form.client_id,
  );

  function update(field: keyof JobFormState, value: string) {
    if (field === "client_id") {
      const siteStillMatches = sites.some(
        (site) => site.id === form.site_id && site.client_id === value,
      );
      setForm({ ...form, client_id: value, site_id: siteStillMatches ? form.site_id : "" });
      return;
    }

    if (field === "site_id") {
      const site = sites.find((candidate) => candidate.id === value);
      setForm({
        ...form,
        site_id: value,
        client_id: site?.client_id ?? form.client_id,
      });
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
      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Client">
          <select
            value={form.client_id}
            onChange={(event) => update("client_id", event.target.value)}
            className="form-input"
            required
          >
            <option value="">Select a client</option>
            {clients.map((client) => (
              <option key={client.id} value={client.id}>
                {client.name}
              </option>
            ))}
          </select>
        </FormField>

        <FormField label="Site">
          <select
            value={form.site_id}
            onChange={(event) => update("site_id", event.target.value)}
            className="form-input"
            required
          >
            <option value="">Select a site</option>
            {availableSites.map((site) => (
              <option key={site.id} value={site.id}>
                {site.name}
              </option>
            ))}
          </select>
        </FormField>
      </div>

      <FormField label="Name">
        <input
          value={form.name}
          onChange={(event) => update("name", event.target.value)}
          className="form-input"
          required
        />
      </FormField>

      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Service Type">
          <input
            value={form.service_type}
            onChange={(event) => update("service_type", event.target.value)}
            className="form-input"
          />
        </FormField>

        <FormField label="Status">
          <select
            value={form.status}
            onChange={(event) => update("status", event.target.value)}
            className="form-input"
          >
            {jobStatusOptions.map((status) => (
              <option key={status} value={status}>
                {status.replaceAll("_", " ")}
              </option>
            ))}
          </select>
        </FormField>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Scheduled Date">
          <input
            value={form.scheduled_date}
            onChange={(event) => update("scheduled_date", event.target.value)}
            className="form-input"
            type="date"
          />
        </FormField>

        <FormField label="Due Date">
          <input
            value={form.due_date}
            onChange={(event) => update("due_date", event.target.value)}
            className="form-input"
            type="date"
          />
        </FormField>
      </div>

      <FormField label="Scope">
        <textarea
          value={form.scope}
          onChange={(event) => update("scope", event.target.value)}
          className="form-textarea"
          rows={4}
        />
      </FormField>

      <FormField label="Drive Folder URL">
        <input
          value={form.drive_folder_url}
          onChange={(event) => update("drive_folder_url", event.target.value)}
          className="form-input"
          placeholder="Optional stored link"
        />
      </FormField>

      <FormField label="Notes">
        <textarea
          value={form.notes}
          onChange={(event) => update("notes", event.target.value)}
          className="form-textarea"
          rows={4}
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
        <button type="submit" className={buttonClass} disabled={saving}>
          {saving ? "Saving..." : "Save Job"}
        </button>
      </div>
    </form>
  );
}

function StatusForm({
  status,
  setStatus,
  saving,
  onCancel,
  onSave,
}: {
  status: string;
  setStatus: (status: string) => void;
  saving: boolean;
  onCancel: () => void;
  onSave: () => void;
}) {
  return (
    <form
      className="space-y-4"
      onSubmit={(event) => {
        event.preventDefault();
        onSave();
      }}
    >
      <FormField label="Status">
        <select
          value={status}
          onChange={(event) => setStatus(event.target.value)}
          className="form-input"
        >
          {jobStatusOptions.map((option) => (
            <option key={option} value={option}>
              {option.replaceAll("_", " ")}
            </option>
          ))}
        </select>
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
        <button type="submit" className={buttonClass} disabled={saving}>
          {saving ? "Saving..." : "Save Status"}
        </button>
      </div>
    </form>
  );
}

function FormField({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-[#3d4a3d]">{label}</span>
      <div className="mt-2">{children}</div>
    </label>
  );
}
