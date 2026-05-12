"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import AppShell from "@/components/AppShell";
import StatusBadge from "@/components/crm/StatusBadge";
import Badge, { type BadgeTone } from "@/components/ui/Badge";
import SectionHeader from "@/components/ui/SectionHeader";
import {
  archiveReminder,
  completeReminder,
  createReminder,
  demoOrganizationId,
  listClients,
  listJobs,
  listReminders,
  listSites,
  updateReminder,
} from "@/lib/api";
import type {
  Client,
  Job,
  Reminder,
  ReminderCreate,
  ReminderPriority,
  ReminderStatus,
  Site,
} from "@/lib/types";
import {
  cardClass,
  dangerButtonClass,
  eyebrowClass,
  primaryButtonClass,
  secondaryButtonClass,
} from "@/lib/ui";

type TargetType = "client" | "site" | "job";
type FormMode = "create" | "edit" | null;

type ReminderFormState = {
  target_type: TargetType;
  target_id: string;
  title: string;
  description: string;
  priority: ReminderPriority;
  due_at: string;
  reminder_at: string;
};

type ReminderGroup = {
  key: string;
  title: string;
  description: string;
  items: Reminder[];
};

const priorityOptions: ReminderPriority[] = ["high", "medium", "low"];
const statusOptions: ReminderStatus[] = ["open", "snoozed", "completed"];

const emptyForm: ReminderFormState = {
  target_type: "job",
  target_id: "",
  title: "",
  description: "",
  priority: "medium",
  due_at: "",
  reminder_at: "",
};

const priorityTone: Record<ReminderPriority, BadgeTone> = {
  high: "danger",
  medium: "warning",
  low: "muted",
};

function optional(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function dateTimeToLocalInput(value: string | null): string {
  if (!value) {
    return "";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "";
  }

  const pad = (input: number) => String(input).padStart(2, "0");
  return [
    date.getFullYear(),
    "-",
    pad(date.getMonth() + 1),
    "-",
    pad(date.getDate()),
    "T",
    pad(date.getHours()),
    ":",
    pad(date.getMinutes()),
  ].join("");
}

function localInputToIso(value: string): string | null {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date.toISOString();
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return "Not set";
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

function isToday(value: string | null): boolean {
  if (!value) {
    return false;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return false;
  }
  const now = new Date();
  return (
    date.getFullYear() === now.getFullYear()
    && date.getMonth() === now.getMonth()
    && date.getDate() === now.getDate()
  );
}

function isOverdue(value: string | null): boolean {
  if (!value) {
    return false;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return false;
  }
  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);
  return date < todayStart;
}

function inferTarget(reminder: Reminder): { type: TargetType; id: string } {
  if (reminder.job_id) {
    return { type: "job", id: reminder.job_id };
  }
  if (reminder.site_id) {
    return { type: "site", id: reminder.site_id };
  }
  return { type: "client", id: reminder.client_id ?? "" };
}

function formFromReminder(reminder: Reminder): ReminderFormState {
  const target = inferTarget(reminder);
  return {
    target_type: target.type,
    target_id: target.id,
    title: reminder.title,
    description: reminder.description ?? "",
    priority: reminder.priority,
    due_at: dateTimeToLocalInput(reminder.due_at),
    reminder_at: dateTimeToLocalInput(reminder.reminder_at),
  };
}

function SetupMessage() {
  return (
    <AppShell>
      <div className="rounded-lg border border-[color:var(--yellow)]/40 bg-[color:var(--yellow-soft)] p-5 text-sm text-[color:var(--yellow)]">
        Set NEXT_PUBLIC_DEMO_ORG_ID in apps/web/.env.local to use Schedule.
      </div>
    </AppShell>
  );
}

export default function SchedulePage() {
  const organizationId = demoOrganizationId;
  const [reminders, setReminders] = useState<Reminder[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [statusFilter, setStatusFilter] = useState<"" | ReminderStatus>("");
  const [priorityFilter, setPriorityFilter] = useState<"" | ReminderPriority>("");
  const [loadingReminders, setLoadingReminders] = useState(false);
  const [loadingReferences, setLoadingReferences] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formMode, setFormMode] = useState<FormMode>(null);
  const [editingReminderId, setEditingReminderId] = useState<string | null>(null);
  const [form, setForm] = useState<ReminderFormState>(emptyForm);

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
    if (form.target_type === "client") {
      return clients.map((client) => ({ id: client.id, label: client.name }));
    }
    if (form.target_type === "site") {
      return sites.map((site) => ({
        id: site.id,
        label: clientNameById.get(site.client_id)
          ? `${site.name} · ${clientNameById.get(site.client_id)}`
          : site.name,
      }));
    }
    return jobs.map((job) => ({
      id: job.id,
      label: siteNameById.get(job.site_id)
        ? `${job.name} · ${siteNameById.get(job.site_id)}`
        : job.name,
    }));
  }, [clients, clientNameById, form.target_type, jobs, siteNameById, sites]);

  const grouped = useMemo<ReminderGroup[]>(() => {
    const overdue: Reminder[] = [];
    const today: Reminder[] = [];
    const upcoming: Reminder[] = [];
    const completed: Reminder[] = [];

    reminders.forEach((reminder) => {
      if (reminder.status === "completed") {
        completed.push(reminder);
      } else if (isOverdue(reminder.due_at)) {
        overdue.push(reminder);
      } else if (isToday(reminder.due_at)) {
        today.push(reminder);
      } else {
        upcoming.push(reminder);
      }
    });

    return [
      {
        key: "overdue",
        title: "Overdue",
        description: "Due before today and still open or snoozed.",
        items: overdue,
      },
      {
        key: "today",
        title: "Today",
        description: "Due on today’s schedule.",
        items: today,
      },
      {
        key: "upcoming",
        title: "Upcoming",
        description: "Future reminders and unscheduled follow-ups.",
        items: upcoming,
      },
      {
        key: "completed",
        title: "Completed",
        description: "Done reminders kept visible for review.",
        items: completed,
      },
    ];
  }, [reminders]);

  const hasAnyTarget = clients.length > 0 || sites.length > 0 || jobs.length > 0;

  const loadReferences = useCallback(async () => {
    if (!organizationId) {
      return;
    }

    setLoadingReferences(true);
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
      setError(
        caught instanceof Error ? caught.message : "Unable to load linked records.",
      );
    } finally {
      setLoadingReferences(false);
    }
  }, [organizationId]);

  const loadReminders = useCallback(async () => {
    if (!organizationId) {
      return;
    }

    setLoadingReminders(true);
    setError(null);
    try {
      const response = await listReminders({
        organizationId,
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
        limit: 500,
      });
      setReminders(response.items);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to load reminders.",
      );
    } finally {
      setLoadingReminders(false);
    }
  }, [organizationId, priorityFilter, statusFilter]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadReferences();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [loadReferences]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadReminders();
    }, 150);

    return () => window.clearTimeout(timer);
  }, [loadReminders]);

  if (!organizationId) {
    return <SetupMessage />;
  }

  function resolveTargetType(targetType: TargetType = "job"): TargetType {
    return targetType === "job" && jobs.length > 0
      ? "job"
      : targetType === "site" && sites.length > 0
        ? "site"
        : targetType === "client" && clients.length > 0
          ? "client"
          : jobs.length > 0
            ? "job"
            : sites.length > 0
              ? "site"
              : "client";
  }

  function firstTargetId(targetType: TargetType): string {
    return targetType === "job"
      ? jobs[0]?.id ?? ""
      : targetType === "site"
        ? sites[0]?.id ?? ""
        : clients[0]?.id ?? "";
  }

  function firstTargetState(targetType: TargetType = "job"): ReminderFormState {
    const fallbackType = resolveTargetType(targetType);

    return {
      ...emptyForm,
      target_type: fallbackType,
      target_id: firstTargetId(fallbackType),
    };
  }

  function startCreate() {
    setFormMode("create");
    setEditingReminderId(null);
    setForm(firstTargetState());
    setError(null);
  }

  function startEdit(reminder: Reminder) {
    setFormMode("edit");
    setEditingReminderId(reminder.id);
    setForm(formFromReminder(reminder));
    setError(null);
  }

  function cancelForm() {
    setFormMode(null);
    setEditingReminderId(null);
    setForm(emptyForm);
    setError(null);
  }

  function updateTargetType(targetType: TargetType) {
    const fallbackType = resolveTargetType(targetType);
    setForm({
      ...form,
      target_type: fallbackType,
      target_id: firstTargetId(fallbackType),
    });
  }

  function payloadFromForm(): ReminderCreate {
    const payload: ReminderCreate = {
      title: form.title.trim(),
      description: optional(form.description),
      priority: form.priority,
      due_at: localInputToIso(form.due_at),
      reminder_at: localInputToIso(form.reminder_at),
      client_id: form.target_type === "client" ? form.target_id : null,
      site_id: form.target_type === "site" ? form.target_id : null,
      job_id: form.target_type === "job" ? form.target_id : null,
    };
    if (formMode !== "edit") {
      payload.status = "open";
    }
    return payload;
  }

  async function saveReminder() {
    const payload = payloadFromForm();
    if (!payload.title) {
      setError("Reminder title is required.");
      return;
    }
    if (!form.target_id) {
      setError("Choose a client, site, or job to link this reminder.");
      return;
    }

    setSaving(true);
    setError(null);
    try {
      if (formMode === "edit" && editingReminderId) {
        await updateReminder(editingReminderId, organizationId, payload);
      } else {
        await createReminder(organizationId, payload);
      }
      cancelForm();
      await loadReminders();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save reminder.");
    } finally {
      setSaving(false);
    }
  }

  async function markComplete(reminder: Reminder) {
    setSaving(true);
    setError(null);
    try {
      await completeReminder(reminder.id, organizationId);
      await loadReminders();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to complete reminder.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function archiveSelectedReminder(reminder: Reminder) {
    const confirmed = window.confirm(`Archive ${reminder.title}?`);
    if (!confirmed) {
      return;
    }

    setSaving(true);
    setError(null);
    try {
      await archiveReminder(reminder.id, organizationId);
      await loadReminders();
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to archive reminder.",
      );
    } finally {
      setSaving(false);
    }
  }

  function linkedLabel(reminder: Reminder): string {
    if (reminder.job_id) {
      return jobNameById.get(reminder.job_id) ?? "Linked job";
    }
    if (reminder.site_id) {
      return siteNameById.get(reminder.site_id) ?? "Linked site";
    }
    if (reminder.client_id) {
      return clientNameById.get(reminder.client_id) ?? "Linked client";
    }
    return "Linked record";
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <SectionHeader
          title="Schedule"
          description="Local reminders for client, site, and job follow-ups."
          actions={
            <button
              type="button"
              className={primaryButtonClass}
              onClick={startCreate}
              disabled={saving || loadingReferences || !hasAnyTarget}
            >
              New Reminder
            </button>
          }
        />

        {error ? (
          <div className="rounded-md border border-[color:var(--red)]/40 bg-[color:var(--red-soft)] px-4 py-3 text-sm text-[color:var(--red)]">
            {error}
          </div>
        ) : null}

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {grouped.map((group) => (
            <SummaryTile key={group.key} label={group.title} value={group.items.length} />
          ))}
        </div>

        <section className={cardClass}>
          <div className="grid gap-4 p-4 sm:grid-cols-[220px_220px_minmax(0,1fr)]">
            <label className="block">
              <span className="text-sm font-medium text-text-secondary">
                Status filter
              </span>
              <select
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value as "" | ReminderStatus)}
                className="form-input mt-2"
              >
                <option value="">All active statuses</option>
                {statusOptions.map((status) => (
                  <option key={status} value={status}>
                    {status.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-sm font-medium text-text-secondary">
                Priority filter
              </span>
              <select
                value={priorityFilter}
                onChange={(event) => setPriorityFilter(event.target.value as "" | ReminderPriority)}
                className="form-input mt-2"
              >
                <option value="">All priorities</option>
                {priorityOptions.map((priority) => (
                  <option key={priority} value={priority}>
                    {priority}
                  </option>
                ))}
              </select>
            </label>
            <div className="flex items-end text-sm text-text-muted">
              {loadingReminders ? "Loading reminders..." : `${reminders.length} reminders shown`}
            </div>
          </div>
        </section>

        {formMode ? (
          <section className={cardClass}>
            <div className="border-b border-border-soft px-4 py-3">
              <h2 className="text-base font-semibold text-text">
                {formMode === "edit" ? "Edit Reminder" : "New Reminder"}
              </h2>
            </div>
            <ReminderForm
              form={form}
              setForm={setForm}
              targetOptions={targetOptions}
              saving={saving}
              onTargetTypeChange={updateTargetType}
              onCancel={cancelForm}
              onSave={saveReminder}
            />
          </section>
        ) : null}

        <div className="space-y-6">
          {grouped.map((group) => (
            <ReminderGroupSection
              key={group.key}
              group={group}
              linkedLabel={linkedLabel}
              saving={saving}
              onEdit={startEdit}
              onComplete={markComplete}
              onArchive={archiveSelectedReminder}
            />
          ))}
        </div>
      </div>
    </AppShell>
  );
}

function SummaryTile({ label, value }: { label: string; value: number }) {
  return (
    <div className={cardClass}>
      <div className="p-4">
        <p className={eyebrowClass}>{label}</p>
        <p className="mt-2 text-2xl font-semibold text-text">{value}</p>
      </div>
    </div>
  );
}

function ReminderGroupSection({
  group,
  linkedLabel,
  saving,
  onEdit,
  onComplete,
  onArchive,
}: {
  group: ReminderGroup;
  linkedLabel: (reminder: Reminder) => string;
  saving: boolean;
  onEdit: (reminder: Reminder) => void;
  onComplete: (reminder: Reminder) => void;
  onArchive: (reminder: Reminder) => void;
}) {
  return (
    <section>
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-text">{group.title}</h2>
          <p className="mt-1 text-sm text-text-muted">{group.description}</p>
        </div>
        <Badge tone={group.items.length > 0 ? "info" : "muted"}>
          {group.items.length}
        </Badge>
      </div>

      {group.items.length > 0 ? (
        <div className="mt-3 grid gap-3">
          {group.items.map((reminder) => (
            <ReminderCard
              key={reminder.id}
              reminder={reminder}
              linkedLabel={linkedLabel(reminder)}
              saving={saving}
              onEdit={() => onEdit(reminder)}
              onComplete={() => onComplete(reminder)}
              onArchive={() => onArchive(reminder)}
            />
          ))}
        </div>
      ) : (
        <p className="mt-3 rounded-lg border border-border-soft bg-panel-2 px-4 py-3 text-sm text-text-muted">
          No reminders in this group.
        </p>
      )}
    </section>
  );
}

function ReminderCard({
  reminder,
  linkedLabel,
  saving,
  onEdit,
  onComplete,
  onArchive,
}: {
  reminder: Reminder;
  linkedLabel: string;
  saving: boolean;
  onEdit: () => void;
  onComplete: () => void;
  onArchive: () => void;
}) {
  return (
    <article className={cardClass}>
      <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_auto]">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="min-w-0 text-base font-semibold text-text">
              {reminder.title}
            </h3>
            <Badge tone={priorityTone[reminder.priority]}>
              {reminder.priority}
            </Badge>
            <StatusBadge status={reminder.status} />
          </div>
          <p className="mt-2 text-sm text-text-secondary">{linkedLabel}</p>
          {reminder.description ? (
            <p className="mt-3 text-sm leading-6 text-text-secondary">
              {reminder.description}
            </p>
          ) : null}
          <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
            <ReminderMeta label="Due" value={formatDateTime(reminder.due_at)} />
            <ReminderMeta
              label="Reminder"
              value={formatDateTime(reminder.reminder_at)}
            />
            <ReminderMeta
              label="Completed"
              value={formatDateTime(reminder.completed_at)}
            />
          </dl>
        </div>
        <div className="flex flex-wrap items-start justify-end gap-2">
          <button
            type="button"
            className={secondaryButtonClass}
            onClick={onEdit}
            disabled={saving || reminder.status === "archived"}
          >
            Edit Reminder
          </button>
          {reminder.status !== "completed" && reminder.status !== "archived" ? (
            <button
              type="button"
              className={secondaryButtonClass}
              onClick={onComplete}
              disabled={saving}
            >
              Mark Complete
            </button>
          ) : null}
          {reminder.status !== "archived" ? (
            <button
              type="button"
              className={dangerButtonClass}
              onClick={onArchive}
              disabled={saving}
            >
              Archive
            </button>
          ) : null}
        </div>
      </div>
    </article>
  );
}

function ReminderMeta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className={eyebrowClass}>{label}</dt>
      <dd className="mt-1 text-text">{value}</dd>
    </div>
  );
}

function ReminderForm({
  form,
  setForm,
  targetOptions,
  saving,
  onTargetTypeChange,
  onCancel,
  onSave,
}: {
  form: ReminderFormState;
  setForm: (form: ReminderFormState) => void;
  targetOptions: Array<{ id: string; label: string }>;
  saving: boolean;
  onTargetTypeChange: (targetType: TargetType) => void;
  onCancel: () => void;
  onSave: () => void;
}) {
  function update(field: keyof ReminderFormState, value: string) {
    if (field === "target_type") {
      onTargetTypeChange(value as TargetType);
      return;
    }
    if (field === "priority") {
      setForm({ ...form, priority: value as ReminderPriority });
      return;
    }
    setForm({ ...form, [field]: value });
  }

  return (
    <form
      className="space-y-4 p-4"
      onSubmit={(event) => {
        event.preventDefault();
        onSave();
      }}
    >
      <div className="grid gap-4 md:grid-cols-[180px_minmax(0,1fr)]">
        <FormField label="Target Type">
          <select
            value={form.target_type}
            onChange={(event) => update("target_type", event.target.value)}
            className="form-input"
          >
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
            required
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

      <FormField label="Title">
        <input
          value={form.title}
          onChange={(event) => update("title", event.target.value)}
          className="form-input"
          required
        />
      </FormField>

      <div className="grid gap-4 md:grid-cols-3">
        <FormField label="Priority">
          <select
            value={form.priority}
            onChange={(event) => update("priority", event.target.value)}
            className="form-input"
          >
            {priorityOptions.map((priority) => (
              <option key={priority} value={priority}>
                {priority}
              </option>
            ))}
          </select>
        </FormField>
        <FormField label="Due Date/Time">
          <input
            type="datetime-local"
            value={form.due_at}
            onChange={(event) => update("due_at", event.target.value)}
            className="form-input"
          />
        </FormField>
        <FormField label="Reminder Date/Time">
          <input
            type="datetime-local"
            value={form.reminder_at}
            onChange={(event) => update("reminder_at", event.target.value)}
            className="form-input"
          />
        </FormField>
      </div>

      <FormField label="Description">
        <textarea
          value={form.description}
          onChange={(event) => update("description", event.target.value)}
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
        <button type="submit" className={primaryButtonClass} disabled={saving}>
          {saving ? "Saving..." : "Save Reminder"}
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
      <span className="text-sm font-medium text-text-secondary">{label}</span>
      <div className="mt-2">{children}</div>
    </label>
  );
}
