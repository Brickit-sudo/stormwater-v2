"use client";

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import AppShell from "@/components/AppShell";
import Badge, { type BadgeTone } from "@/components/ui/Badge";
import SectionHeader from "@/components/ui/SectionHeader";
import {
  archiveProductDecision,
  archiveProductIdea,
  createProductDecision,
  createProductIdea,
  listProductDecisions,
  listProductIdeas,
  updateProductIdea,
} from "@/lib/api";
import { useOrganizationId } from "@/lib/auth";
import type {
  ProductDecision,
  ProductDecisionInput,
  ProductDecisionStatus,
  ProductIdea,
  ProductIdeaCategory,
  ProductIdeaInput,
  ProductIdeaLane,
  ProductIdeaPriority,
  ProductIdeaStatus,
} from "@/lib/types";
import {
  cardClass,
  dangerButtonClass,
  eyebrowClass,
  primaryButtonClass,
  secondaryButtonClass,
} from "@/lib/ui";

type IdeaFormState = {
  title: string;
  description: string;
  category: ProductIdeaCategory;
  lane: ProductIdeaLane;
  status: ProductIdeaStatus;
  priority: ProductIdeaPriority;
  source: string;
  owner: string;
  target_version: string;
  effort: string;
  risk: string;
  boss_demo_relevant: boolean;
};

type DecisionFormState = {
  related_idea_id: string;
  decision_title: string;
  decision_summary: string;
  decision_reason: string;
  alternatives_considered: string;
  status: ProductDecisionStatus;
};

type IdeaFilters = {
  status: "" | ProductIdeaStatus;
  category: "" | ProductIdeaCategory;
  lane: "" | ProductIdeaLane;
  priority: "" | ProductIdeaPriority;
  bossOnly: boolean;
};

const ideaStatuses: ProductIdeaStatus[] = [
  "new",
  "needs_review",
  "planned",
  "in_progress",
  "done",
  "deferred",
  "rejected",
];
const decisionStatuses: ProductDecisionStatus[] = [
  "proposed",
  "decided",
  "superseded",
  "deferred",
];
const priorities: ProductIdeaPriority[] = ["critical", "high", "medium", "low"];
const categories: ProductIdeaCategory[] = [
  "CRM",
  "Files",
  "Reports",
  "Email",
  "Outlook",
  "Gmail",
  "Drive",
  "Map",
  "Scheduling",
  "Billing",
  "AI",
  "Import",
  "Migration",
  "UX",
  "Security",
  "Performance",
  "Microsoft 365",
  "Knowledgebase",
];
const lanes: ProductIdeaLane[] = [
  "V2",
  "Original Streamlit",
  "Migration",
  "Microsoft 365",
  "Docs",
  "Future",
];

const emptyIdeaForm: IdeaFormState = {
  title: "",
  description: "",
  category: "UX",
  lane: "V2",
  status: "new",
  priority: "medium",
  source: "",
  owner: "",
  target_version: "",
  effort: "",
  risk: "",
  boss_demo_relevant: false,
};

const emptyDecisionForm: DecisionFormState = {
  related_idea_id: "",
  decision_title: "",
  decision_summary: "",
  decision_reason: "",
  alternatives_considered: "",
  status: "proposed",
};

const emptyFilters: IdeaFilters = {
  status: "",
  category: "",
  lane: "",
  priority: "",
  bossOnly: false,
};

function optional(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function formatLabel(value: string): string {
  return value.replaceAll("_", " ");
}

function formatDate(value: string | null): string {
  if (!value) {
    return "Not set";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
  }).format(date);
}

function ideaTone(status: ProductIdeaStatus): BadgeTone {
  if (status === "done") return "success";
  if (status === "planned" || status === "in_progress") return "info";
  if (status === "needs_review" || status === "deferred") return "warning";
  if (status === "rejected") return "danger";
  return "muted";
}

function priorityTone(priority: ProductIdeaPriority): BadgeTone {
  if (priority === "critical" || priority === "high") return "danger";
  if (priority === "medium") return "warning";
  return "muted";
}

function decisionTone(status: ProductDecisionStatus): BadgeTone {
  if (status === "decided") return "success";
  if (status === "superseded") return "danger";
  if (status === "deferred") return "warning";
  return "muted";
}

function formFromIdea(idea: ProductIdea): IdeaFormState {
  return {
    title: idea.title,
    description: idea.description ?? "",
    category: idea.category as ProductIdeaCategory,
    lane: idea.lane as ProductIdeaLane,
    status: idea.status,
    priority: idea.priority,
    source: idea.source ?? "",
    owner: idea.owner ?? "",
    target_version: idea.target_version ?? "",
    effort: idea.effort ?? "",
    risk: idea.risk ?? "",
    boss_demo_relevant: idea.boss_demo_relevant,
  };
}

function ideaPayload(form: IdeaFormState): ProductIdeaInput {
  return {
    title: form.title.trim(),
    description: optional(form.description),
    category: form.category,
    lane: form.lane,
    status: form.status,
    priority: form.priority,
    source: optional(form.source),
    owner: optional(form.owner),
    target_version: optional(form.target_version),
    effort: optional(form.effort),
    risk: optional(form.risk),
    boss_demo_relevant: form.boss_demo_relevant,
  };
}

function decisionPayload(form: DecisionFormState): ProductDecisionInput {
  return {
    related_idea_id: optional(form.related_idea_id),
    decision_title: form.decision_title.trim(),
    decision_summary: optional(form.decision_summary),
    decision_reason: optional(form.decision_reason),
    alternatives_considered: optional(form.alternatives_considered),
    status: form.status,
  };
}

function SetupMessage() {
  return (
    <AppShell>
      <div className="rounded-lg border border-[color:var(--yellow)]/40 bg-[color:var(--yellow-soft)] p-5 text-sm text-[color:var(--yellow)]">
        Set NEXT_PUBLIC_DEMO_ORG_ID in apps/web/.env.local to use Roadmap.
      </div>
    </AppShell>
  );
}

export default function RoadmapPage() {
  const organizationId = useOrganizationId();
  const [ideas, setIdeas] = useState<ProductIdea[]>([]);
  const [decisions, setDecisions] = useState<ProductDecision[]>([]);
  const [filters, setFilters] = useState<IdeaFilters>(emptyFilters);
  const [ideaForm, setIdeaForm] = useState<IdeaFormState>(emptyIdeaForm);
  const [decisionForm, setDecisionForm] = useState<DecisionFormState>(emptyDecisionForm);
  const [editingIdeaId, setEditingIdeaId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ideaById = useMemo(
    () => new Map(ideas.map((idea) => [idea.id, idea])),
    [ideas],
  );

  const filteredIdeas = useMemo(
    () =>
      ideas.filter((idea) => {
        if (filters.status && idea.status !== filters.status) return false;
        if (filters.category && idea.category !== filters.category) return false;
        if (filters.lane && idea.lane !== filters.lane) return false;
        if (filters.priority && idea.priority !== filters.priority) return false;
        if (filters.bossOnly && !idea.boss_demo_relevant) return false;
        return true;
      }),
    [filters, ideas],
  );

  const doNotBuildIdeas = useMemo(
    () =>
      ideas.filter(
        (idea) => idea.status === "deferred" || idea.status === "rejected",
      ),
    [ideas],
  );

  const bossDemoCount = useMemo(
    () => ideas.filter((idea) => idea.boss_demo_relevant).length,
    [ideas],
  );

  const loadRoadmap = useCallback(async () => {
    if (!organizationId) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [ideaPage, decisionPage] = await Promise.all([
        listProductIdeas({ organizationId, limit: 250 }),
        listProductDecisions({ organizationId, limit: 100 }),
      ]);
      setIdeas(ideaPage.items);
      setDecisions(decisionPage.items);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to load roadmap.",
      );
    } finally {
      setLoading(false);
    }
  }, [organizationId]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadRoadmap();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [loadRoadmap]);

  async function submitIdea(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!organizationId) return;
    setSaving(true);
    setError(null);
    try {
      if (editingIdeaId) {
        await updateProductIdea(editingIdeaId, organizationId, ideaPayload(ideaForm));
      } else {
        await createProductIdea(organizationId, ideaPayload(ideaForm));
      }
      setIdeaForm(emptyIdeaForm);
      setEditingIdeaId(null);
      await loadRoadmap();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save idea.");
    } finally {
      setSaving(false);
    }
  }

  async function submitDecision(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!organizationId) return;
    setSaving(true);
    setError(null);
    try {
      await createProductDecision(organizationId, decisionPayload(decisionForm));
      setDecisionForm(emptyDecisionForm);
      await loadRoadmap();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save decision.");
    } finally {
      setSaving(false);
    }
  }

  async function archiveIdea(ideaId: string) {
    if (!organizationId) return;
    setSaving(true);
    setError(null);
    try {
      await archiveProductIdea(ideaId, organizationId);
      if (editingIdeaId === ideaId) {
        setEditingIdeaId(null);
        setIdeaForm(emptyIdeaForm);
      }
      await loadRoadmap();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to archive idea.");
    } finally {
      setSaving(false);
    }
  }

  async function archiveDecision(decisionId: string) {
    if (!organizationId) return;
    setSaving(true);
    setError(null);
    try {
      await archiveProductDecision(decisionId, organizationId);
      await loadRoadmap();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to archive decision.");
    } finally {
      setSaving(false);
    }
  }

  function startEditIdea(idea: ProductIdea) {
    setEditingIdeaId(idea.id);
    setIdeaForm(formFromIdea(idea));
  }

  function cancelEdit() {
    setEditingIdeaId(null);
    setIdeaForm(emptyIdeaForm);
  }

  if (!organizationId) {
    return <SetupMessage />;
  }

  return (
    <AppShell>
      <div className="space-y-6">
        <SectionHeader
          title="Product Roadmap"
          description="Internal ideas, deferred work, boss feedback, and product decisions."
          actions={
            <button
              type="button"
              onClick={() => void loadRoadmap()}
              className={secondaryButtonClass}
              disabled={loading}
            >
              Refresh
            </button>
          }
        />

        {error ? (
          <div className="rounded-lg border border-[color:var(--red)]/40 bg-[color:var(--red-soft)] p-4 text-sm text-[color:var(--red)]">
            {error}
          </div>
        ) : null}

        <section className="grid gap-4 md:grid-cols-3">
          <Metric label="Ideas" value={ideas.length} />
          <Metric label="Boss-demo relevant" value={bossDemoCount} />
          <Metric label="Decisions" value={decisions.length} />
        </section>

        <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
          <div className="space-y-4">
            <div className={cardClass}>
              <div className="border-b border-border-soft p-4">
                <p className={eyebrowClass}>Filters</p>
                <div className="mt-3 grid gap-3 md:grid-cols-5">
                  <SelectFilter
                    label="Status"
                    value={filters.status}
                    options={ideaStatuses}
                    onChange={(value) =>
                      setFilters((current) => ({
                        ...current,
                        status: value as "" | ProductIdeaStatus,
                      }))
                    }
                  />
                  <SelectFilter
                    label="Category"
                    value={filters.category}
                    options={categories}
                    onChange={(value) =>
                      setFilters((current) => ({
                        ...current,
                        category: value as "" | ProductIdeaCategory,
                      }))
                    }
                  />
                  <SelectFilter
                    label="Lane"
                    value={filters.lane}
                    options={lanes}
                    onChange={(value) =>
                      setFilters((current) => ({
                        ...current,
                        lane: value as "" | ProductIdeaLane,
                      }))
                    }
                  />
                  <SelectFilter
                    label="Priority"
                    value={filters.priority}
                    options={priorities}
                    onChange={(value) =>
                      setFilters((current) => ({
                        ...current,
                        priority: value as "" | ProductIdeaPriority,
                      }))
                    }
                  />
                  <label className="flex h-10 items-center gap-2 rounded-md border border-border bg-panel-2 px-3 text-sm text-text-secondary">
                    <input
                      type="checkbox"
                      checked={filters.bossOnly}
                      onChange={(event) =>
                        setFilters((current) => ({
                          ...current,
                          bossOnly: event.target.checked,
                        }))
                      }
                      className="h-4 w-4 accent-[color:var(--green)]"
                    />
                    Boss demo
                  </label>
                </div>
              </div>

              <div className="divide-y divide-border-soft">
                {loading ? (
                  <p className="p-4 text-sm text-text-muted">Loading roadmap...</p>
                ) : filteredIdeas.length > 0 ? (
                  filteredIdeas.map((idea) => (
                    <IdeaRow
                      key={idea.id}
                      idea={idea}
                      onEdit={startEditIdea}
                      onArchive={(ideaId) => void archiveIdea(ideaId)}
                      disabled={saving}
                    />
                  ))
                ) : (
                  <p className="p-4 text-sm text-text-muted">No ideas match the current filters.</p>
                )}
              </div>
            </div>

            <div className={cardClass}>
              <div className="border-b border-border-soft p-4">
                <p className={eyebrowClass}>Do Not Build Yet</p>
                <h2 className="mt-2 text-lg font-semibold text-text">
                  Deferred and rejected ideas
                </h2>
              </div>
              <div className="divide-y divide-border-soft">
                {doNotBuildIdeas.length > 0 ? (
                  doNotBuildIdeas.map((idea) => (
                    <IdeaRow
                      key={idea.id}
                      idea={idea}
                      onEdit={startEditIdea}
                      onArchive={(ideaId) => void archiveIdea(ideaId)}
                      disabled={saving}
                      compact
                    />
                  ))
                ) : (
                  <p className="p-4 text-sm text-text-muted">No deferred or rejected ideas.</p>
                )}
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <IdeaForm
              form={ideaForm}
              editing={Boolean(editingIdeaId)}
              saving={saving}
              onSubmit={(event) => void submitIdea(event)}
              onCancel={cancelEdit}
              onChange={setIdeaForm}
            />

            <DecisionForm
              form={decisionForm}
              ideas={ideas}
              saving={saving}
              onSubmit={(event) => void submitDecision(event)}
              onChange={setDecisionForm}
            />
          </div>
        </section>

        <section className={cardClass}>
          <div className="border-b border-border-soft p-4">
            <p className={eyebrowClass}>Decisions</p>
            <h2 className="mt-2 text-lg font-semibold text-text">
              Product decision log
            </h2>
          </div>
          <div className="divide-y divide-border-soft">
            {decisions.length > 0 ? (
              decisions.map((decision) => (
                <DecisionRow
                  key={decision.id}
                  decision={decision}
                  relatedIdea={decision.related_idea_id ? ideaById.get(decision.related_idea_id) : null}
                  onArchive={(decisionId) => void archiveDecision(decisionId)}
                  disabled={saving}
                />
              ))
            ) : (
              <p className="p-4 text-sm text-text-muted">No decisions logged yet.</p>
            )}
          </div>
        </section>
      </div>
    </AppShell>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className={`${cardClass} p-4`}>
      <p className={eyebrowClass}>{label}</p>
      <p className="mt-2 text-2xl font-semibold text-text">{value}</p>
    </div>
  );
}

function SelectFilter({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className="sr-only">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="form-input"
      >
        <option value="">{label}</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {formatLabel(option)}
          </option>
        ))}
      </select>
    </label>
  );
}

function IdeaRow({
  idea,
  onEdit,
  onArchive,
  disabled,
  compact = false,
}: {
  idea: ProductIdea;
  onEdit: (idea: ProductIdea) => void;
  onArchive: (ideaId: string) => void;
  disabled: boolean;
  compact?: boolean;
}) {
  return (
    <article className={compact ? "p-4" : "p-4 sm:p-5"}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base font-semibold text-text">{idea.title}</h3>
            {idea.boss_demo_relevant ? <Badge tone="success">Boss demo</Badge> : null}
          </div>
          {idea.description ? (
            <p className="mt-2 text-sm leading-6 text-text-secondary">
              {idea.description}
            </p>
          ) : null}
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <button
            type="button"
            onClick={() => onEdit(idea)}
            className={secondaryButtonClass}
            disabled={disabled}
          >
            Edit
          </button>
          <button
            type="button"
            onClick={() => onArchive(idea.id)}
            className={dangerButtonClass}
            disabled={disabled}
          >
            Archive
          </button>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <Badge tone={ideaTone(idea.status)}>{formatLabel(idea.status)}</Badge>
        <Badge tone={priorityTone(idea.priority)}>{idea.priority}</Badge>
        <Badge tone="muted">{idea.category}</Badge>
        <Badge tone="muted">{idea.lane}</Badge>
        {idea.target_version ? <Badge tone="info">{idea.target_version}</Badge> : null}
      </div>
      {!compact ? (
        <dl className="mt-4 grid gap-3 text-xs text-text-muted sm:grid-cols-3">
          <Meta label="Source" value={idea.source} />
          <Meta label="Owner" value={idea.owner} />
          <Meta label="Updated" value={formatDate(idea.updated_at)} />
        </dl>
      ) : null}
    </article>
  );
}

function Meta({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <dt className="font-semibold uppercase tracking-[0.12em]">{label}</dt>
      <dd className="mt-1 text-text-secondary">{value || "Not set"}</dd>
    </div>
  );
}

function IdeaForm({
  form,
  editing,
  saving,
  onSubmit,
  onCancel,
  onChange,
}: {
  form: IdeaFormState;
  editing: boolean;
  saving: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onCancel: () => void;
  onChange: (form: IdeaFormState) => void;
}) {
  return (
    <form onSubmit={onSubmit} className={`${cardClass} p-4`}>
      <p className={eyebrowClass}>{editing ? "Edit idea" : "New idea"}</p>
      <div className="mt-4 space-y-3">
        <input
          value={form.title}
          onChange={(event) => onChange({ ...form, title: event.target.value })}
          placeholder="Title"
          className="form-input"
          required
        />
        <textarea
          value={form.description}
          onChange={(event) => onChange({ ...form, description: event.target.value })}
          placeholder="Description"
          className="form-textarea min-h-24"
        />
        <div className="grid gap-3 sm:grid-cols-2">
          <FormSelect
            value={form.category}
            options={categories}
            onChange={(value) => onChange({ ...form, category: value as ProductIdeaCategory })}
          />
          <FormSelect
            value={form.lane}
            options={lanes}
            onChange={(value) => onChange({ ...form, lane: value as ProductIdeaLane })}
          />
          <FormSelect
            value={form.status}
            options={ideaStatuses}
            onChange={(value) => onChange({ ...form, status: value as ProductIdeaStatus })}
          />
          <FormSelect
            value={form.priority}
            options={priorities}
            onChange={(value) => onChange({ ...form, priority: value as ProductIdeaPriority })}
          />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <input
            value={form.source}
            onChange={(event) => onChange({ ...form, source: event.target.value })}
            placeholder="Source"
            className="form-input"
          />
          <input
            value={form.owner}
            onChange={(event) => onChange({ ...form, owner: event.target.value })}
            placeholder="Owner"
            className="form-input"
          />
          <input
            value={form.target_version}
            onChange={(event) => onChange({ ...form, target_version: event.target.value })}
            placeholder="Target version"
            className="form-input"
          />
          <input
            value={form.effort}
            onChange={(event) => onChange({ ...form, effort: event.target.value })}
            placeholder="Effort"
            className="form-input"
          />
          <input
            value={form.risk}
            onChange={(event) => onChange({ ...form, risk: event.target.value })}
            placeholder="Risk"
            className="form-input"
          />
          <label className="flex h-10 items-center gap-2 rounded-md border border-border bg-panel-2 px-3 text-sm text-text-secondary">
            <input
              type="checkbox"
              checked={form.boss_demo_relevant}
              onChange={(event) =>
                onChange({ ...form, boss_demo_relevant: event.target.checked })
              }
              className="h-4 w-4 accent-[color:var(--green)]"
            />
            Boss demo
          </label>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <button type="submit" className={primaryButtonClass} disabled={saving}>
          {editing ? "Save Idea" : "Create Idea"}
        </button>
        {editing ? (
          <button
            type="button"
            onClick={onCancel}
            className={secondaryButtonClass}
            disabled={saving}
          >
            Cancel
          </button>
        ) : null}
      </div>
    </form>
  );
}

function FormSelect({
  value,
  options,
  onChange,
}: {
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <select
      value={value}
      onChange={(event) => onChange(event.target.value)}
      className="form-input"
    >
      {options.map((option) => (
        <option key={option} value={option}>
          {formatLabel(option)}
        </option>
      ))}
    </select>
  );
}

function DecisionForm({
  form,
  ideas,
  saving,
  onSubmit,
  onChange,
}: {
  form: DecisionFormState;
  ideas: ProductIdea[];
  saving: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onChange: (form: DecisionFormState) => void;
}) {
  return (
    <form onSubmit={onSubmit} className={`${cardClass} p-4`}>
      <p className={eyebrowClass}>New decision</p>
      <div className="mt-4 space-y-3">
        <input
          value={form.decision_title}
          onChange={(event) => onChange({ ...form, decision_title: event.target.value })}
          placeholder="Decision title"
          className="form-input"
          required
        />
        <select
          value={form.related_idea_id}
          onChange={(event) => onChange({ ...form, related_idea_id: event.target.value })}
          className="form-input"
        >
          <option value="">No related idea</option>
          {ideas.map((idea) => (
            <option key={idea.id} value={idea.id}>
              {idea.title}
            </option>
          ))}
        </select>
        <FormSelect
          value={form.status}
          options={decisionStatuses}
          onChange={(value) =>
            onChange({ ...form, status: value as ProductDecisionStatus })
          }
        />
        <textarea
          value={form.decision_summary}
          onChange={(event) => onChange({ ...form, decision_summary: event.target.value })}
          placeholder="Summary"
          className="form-textarea min-h-20"
        />
        <textarea
          value={form.decision_reason}
          onChange={(event) => onChange({ ...form, decision_reason: event.target.value })}
          placeholder="Reason"
          className="form-textarea min-h-20"
        />
        <textarea
          value={form.alternatives_considered}
          onChange={(event) =>
            onChange({ ...form, alternatives_considered: event.target.value })
          }
          placeholder="Alternatives considered"
          className="form-textarea min-h-20"
        />
      </div>
      <div className="mt-4">
        <button type="submit" className={primaryButtonClass} disabled={saving}>
          Log Decision
        </button>
      </div>
    </form>
  );
}

function DecisionRow({
  decision,
  relatedIdea,
  onArchive,
  disabled,
}: {
  decision: ProductDecision;
  relatedIdea: ProductIdea | null | undefined;
  onArchive: (decisionId: string) => void;
  disabled: boolean;
}) {
  return (
    <article className="p-4 sm:p-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-base font-semibold text-text">
              {decision.decision_title}
            </h3>
            <Badge tone={decisionTone(decision.status)}>
              {formatLabel(decision.status)}
            </Badge>
          </div>
          {decision.decision_summary ? (
            <p className="mt-2 text-sm leading-6 text-text-secondary">
              {decision.decision_summary}
            </p>
          ) : null}
          {relatedIdea ? (
            <p className="mt-2 text-xs font-medium text-text-muted">
              Related: {relatedIdea.title}
            </p>
          ) : null}
        </div>
        <button
          type="button"
          onClick={() => onArchive(decision.id)}
          className={dangerButtonClass}
          disabled={disabled}
        >
          Archive
        </button>
      </div>
      <dl className="mt-4 grid gap-3 text-xs text-text-muted md:grid-cols-3">
        <Meta label="Reason" value={decision.decision_reason} />
        <Meta label="Alternatives" value={decision.alternatives_considered} />
        <Meta label="Decided" value={formatDate(decision.decided_at)} />
      </dl>
    </article>
  );
}
