"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";

import AppShell from "@/components/AppShell";
import Badge from "@/components/ui/Badge";
import SectionHeader from "@/components/ui/SectionHeader";
import {
  archiveRecordNote,
  createRecordNote,
  listBmpSystems,
  listClients,
  listDocumentChunks,
  listDocumentExtractedFields,
  listDocumentLinkSuggestions,
  listDocuments,
  listJobs,
  listKnowledgeItems,
  listObservations,
  listRecordLinks,
  listRecordNotes,
  listSites,
  updateDocumentExtractedField,
  updateDocumentLinkSuggestion,
} from "@/lib/api";
import { useOrganizationId } from "@/lib/auth";
import type {
  BmpSystem,
  Client,
  DocumentExtractedField,
  DocumentLinkSuggestion,
  DocumentRecord,
  DocumentTextChunk,
  Job,
  KnowledgeItem,
  Observation,
  RecordLink,
  RecordNote,
  Site,
} from "@/lib/types";
import {
  dangerButtonClass,
  primaryButtonClass,
  secondaryButtonClass,
} from "@/lib/ui";

type NoteFormState = {
  title: string;
  body: string;
};

const emptyNoteForm: NoteFormState = {
  title: "",
  body: "",
};

function setupMessage() {
  return (
    <AppShell>
      <div className="rounded-lg border border-[color:var(--yellow)]/40 bg-[color:var(--yellow-soft)] p-5 text-sm text-[color:var(--yellow)]">
        Set NEXT_PUBLIC_DEMO_ORG_ID in apps/web/.env.local to use Intelligence.
      </div>
    </AppShell>
  );
}

function formatType(value: string | null | undefined): string {
  if (!value) return "Not set";
  return value.replaceAll("_", " ");
}

function confidenceLabel(value: number | null): string {
  if (value === null) return "No score";
  return `${Math.round(value * 100)}%`;
}

function statusTone(status: string | null | undefined) {
  if (!status) return "muted" as const;
  if (["approved", "reviewed", "complete", "completed"].includes(status)) {
    return "success" as const;
  }
  if (["needs_review", "reviewing", "pending", "queued"].includes(status)) {
    return "warning" as const;
  }
  if (["failed", "rejected"].includes(status)) {
    return "danger" as const;
  }
  return "muted" as const;
}

function Panel({
  title,
  children,
  action,
}: {
  title: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="rounded-lg border border-border bg-panel p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-text">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}

function EmptyLine({ children }: { children: ReactNode }) {
  return <p className="text-sm text-text-muted">{children}</p>;
}

function SiteSummary({
  site,
  client,
  jobs,
  bmpCount,
  observationCount,
  documentCount,
}: {
  site: Site | null;
  client: Client | null;
  jobs: Job[];
  bmpCount: number;
  observationCount: number;
  documentCount: number;
}) {
  return (
    <section className="rounded-lg border border-border bg-panel p-4">
      <div className="grid gap-4 lg:grid-cols-[1.2fr_1fr_1fr]">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
            Selected Site
          </p>
          <h2 className="mt-2 truncate text-xl font-semibold text-text">
            {site?.name ?? "No site selected"}
          </h2>
          <p className="mt-1 text-sm text-text-secondary">
            {client?.name ?? "Client not loaded"}
          </p>
          <p className="mt-1 text-sm text-text-muted">
            {[site?.address, site?.city, site?.state].filter(Boolean).join(", ") ||
              "Address not set"}
          </p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
            Source Boundary
          </p>
          <p className="mt-2 text-sm text-text-secondary">
            Monday remains a source system. V2 stores reviewed relationships,
            notes, documents, and approved structure.
          </p>
        </div>
        <div className="grid grid-cols-3 gap-2 text-center">
          <div className="rounded-md border border-border-soft bg-panel-2 p-3">
            <p className="text-2xl font-semibold text-text">{bmpCount}</p>
            <p className="text-xs text-text-muted">BMPs</p>
          </div>
          <div className="rounded-md border border-border-soft bg-panel-2 p-3">
            <p className="text-2xl font-semibold text-text">{observationCount}</p>
            <p className="text-xs text-text-muted">Findings</p>
          </div>
          <div className="rounded-md border border-border-soft bg-panel-2 p-3">
            <p className="text-2xl font-semibold text-text">{documentCount}</p>
            <p className="text-xs text-text-muted">Docs</p>
          </div>
          <div className="col-span-3 rounded-md border border-border-soft bg-panel-2 p-3 text-left">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
              Active Work
            </p>
            <p className="mt-1 text-sm text-text-secondary">
              {jobs.length > 0
                ? jobs.map((job) => job.name).join(", ")
                : "No jobs in the current local slice."}
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

function BmpPanel({ bmps }: { bmps: BmpSystem[] }) {
  return (
    <Panel title="BMP Systems">
      {bmps.length === 0 ? (
        <EmptyLine>No BMP systems are linked to this site yet.</EmptyLine>
      ) : (
        <div className="space-y-3">
          {bmps.map((bmp) => (
            <article key={bmp.id} className="rounded-md border border-border-soft bg-panel-2 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-medium text-text">{bmp.name ?? bmp.system_code ?? "BMP system"}</p>
                <Badge>{formatType(bmp.system_type)}</Badge>
              </div>
              <p className="mt-2 text-sm text-text-secondary">
                {bmp.location_description ?? "Location not set"}
              </p>
              {bmp.notes ? <p className="mt-1 text-sm text-text-muted">{bmp.notes}</p> : null}
            </article>
          ))}
        </div>
      )}
    </Panel>
  );
}

function ObservationsPanel({
  observations,
  systemNameById,
  jobNameById,
}: {
  observations: Observation[];
  systemNameById: Map<string, string>;
  jobNameById: Map<string, string>;
}) {
  return (
    <Panel title="Observations / Findings">
      {observations.length === 0 ? (
        <EmptyLine>No observations are linked to this site yet.</EmptyLine>
      ) : (
        <div className="space-y-3">
          {observations.map((observation) => (
            <article key={observation.id} className="rounded-md border border-border-soft bg-panel-2 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={observation.maintenance_needed ? "warning" : "success"}>
                  {observation.maintenance_needed ? "maintenance" : "reviewed"}
                </Badge>
                <Badge>{observation.severity ?? "severity not set"}</Badge>
                <span className="text-xs text-text-muted">
                  {observation.system_id
                    ? systemNameById.get(observation.system_id) ?? "BMP system"
                    : "Site-level"}
                </span>
              </div>
              <p className="mt-2 text-sm font-medium text-text">
                {observation.finding ?? "Finding not set"}
              </p>
              <p className="mt-1 text-sm text-text-secondary">
                {observation.recommendation ?? "Recommendation not set"}
              </p>
              <p className="mt-2 text-xs text-text-muted">
                {jobNameById.get(observation.job_id) ?? "Linked job"}
              </p>
            </article>
          ))}
        </div>
      )}
    </Panel>
  );
}

function NotesPanel({
  notes,
  form,
  saving,
  onFormChange,
  onSubmit,
  onArchive,
}: {
  notes: RecordNote[];
  form: NoteFormState;
  saving: boolean;
  onFormChange: (next: NoteFormState) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onArchive: (noteId: string) => void;
}) {
  return (
    <Panel title="Record Notes">
      <form onSubmit={onSubmit} className="mb-4 grid gap-2">
        <input
          value={form.title}
          onChange={(event) => onFormChange({ ...form, title: event.target.value })}
          placeholder="Note title"
          className="h-9 rounded-md border border-border bg-panel-2 px-3 text-sm text-text outline-none transition placeholder:text-text-muted focus:border-[color:var(--green)] focus:ring-2 focus:ring-green/40"
        />
        <textarea
          value={form.body}
          onChange={(event) => onFormChange({ ...form, body: event.target.value })}
          placeholder="Note body"
          rows={3}
          className="rounded-md border border-border bg-panel-2 px-3 py-2 text-sm text-text outline-none transition placeholder:text-text-muted focus:border-[color:var(--green)] focus:ring-2 focus:ring-green/40"
        />
        <div>
          <button
            type="submit"
            disabled={saving || !form.title.trim() || !form.body.trim()}
            className={primaryButtonClass}
          >
            {saving ? "Saving" : "Add note"}
          </button>
        </div>
      </form>
      {notes.length === 0 ? (
        <EmptyLine>No site notes yet.</EmptyLine>
      ) : (
        <div className="space-y-3">
          {notes.map((note) => (
            <article key={note.id} className="rounded-md border border-border-soft bg-panel-2 p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-medium text-text">{note.title}</p>
                  <p className="mt-1 text-sm text-text-secondary">{note.body}</p>
                </div>
                <button
                  type="button"
                  onClick={() => onArchive(note.id)}
                  className={dangerButtonClass}
                >
                  Archive
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </Panel>
  );
}

function KnowledgePanel({ items }: { items: KnowledgeItem[] }) {
  return (
    <Panel title="Knowledge Items">
      {items.length === 0 ? (
        <EmptyLine>No knowledge items are linked to this site yet.</EmptyLine>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <article key={item.id} className="rounded-md border border-border-soft bg-panel-2 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-medium text-text">{item.title}</p>
                <Badge tone="info">{formatType(item.knowledge_type)}</Badge>
              </div>
              <p className="mt-2 text-sm text-text-secondary">{item.content}</p>
              {item.tags_json?.length ? (
                <p className="mt-2 text-xs text-text-muted">{item.tags_json.join(" / ")}</p>
              ) : null}
            </article>
          ))}
        </div>
      )}
    </Panel>
  );
}

function DocumentsPanel({
  documents,
  selectedDocumentId,
  onSelectDocument,
}: {
  documents: DocumentRecord[];
  selectedDocumentId: string | null;
  onSelectDocument: (documentId: string) => void;
}) {
  return (
    <Panel title="Document Intake Queue">
      {documents.length === 0 ? (
        <EmptyLine>No document intake records are linked to this site yet.</EmptyLine>
      ) : (
        <div className="space-y-2">
          {documents.map((document) => {
            const active = document.id === selectedDocumentId;
            return (
              <button
                key={document.id}
                type="button"
                onClick={() => onSelectDocument(document.id)}
                className={[
                  "w-full rounded-md border p-3 text-left transition",
                  active
                    ? "border-[color:var(--green)] bg-green-soft/20"
                    : "border-border-soft bg-panel-2 hover:border-border-strong",
                ].join(" ")}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-text">{document.file_name}</span>
                  <Badge tone={statusTone(document.status)}>{formatType(document.status)}</Badge>
                  <Badge tone={statusTone(document.extraction_status)}>
                    {formatType(document.extraction_status)}
                  </Badge>
                </div>
                <p className="mt-1 text-sm text-text-muted">{formatType(document.document_type)}</p>
              </button>
            );
          })}
        </div>
      )}
    </Panel>
  );
}

function DocumentDetailPanel({
  loading,
  chunks,
  fields,
  suggestions,
  onFieldStatus,
  onSuggestionStatus,
}: {
  loading: boolean;
  chunks: DocumentTextChunk[];
  fields: DocumentExtractedField[];
  suggestions: DocumentLinkSuggestion[];
  onFieldStatus: (fieldId: string, reviewStatus: string) => void;
  onSuggestionStatus: (suggestionId: string, reviewStatus: string) => void;
}) {
  return (
    <Panel title="Document Review Detail">
      {loading ? <EmptyLine>Loading document detail...</EmptyLine> : null}
      {!loading && chunks.length === 0 && fields.length === 0 && suggestions.length === 0 ? (
        <EmptyLine>Select a document with extracted review data.</EmptyLine>
      ) : null}
      {chunks.length > 0 ? (
        <div className="mb-4 space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
            Text Chunks
          </p>
          {chunks.map((chunk) => (
            <div key={chunk.id} className="rounded-md border border-border-soft bg-panel-2 p-3">
              <p className="text-sm font-medium text-text">
                {chunk.heading ?? `Chunk ${chunk.chunk_index + 1}`}
              </p>
              <p className="mt-1 text-sm text-text-secondary">{chunk.text}</p>
            </div>
          ))}
        </div>
      ) : null}
      {fields.length > 0 ? (
        <div className="mb-4 space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
            Extracted Candidates
          </p>
          {fields.map((field) => (
            <div key={field.id} className="rounded-md border border-border-soft bg-panel-2 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-text">{formatType(field.field_name)}</span>
                <Badge tone={statusTone(field.review_status)}>{formatType(field.review_status)}</Badge>
                <span className="text-xs text-text-muted">{confidenceLabel(field.confidence)}</span>
              </div>
              <p className="mt-1 text-sm text-text-secondary">{field.field_value}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  className={secondaryButtonClass}
                  onClick={() => onFieldStatus(field.id, "approved")}
                >
                  Approve
                </button>
                <button
                  type="button"
                  className={dangerButtonClass}
                  onClick={() => onFieldStatus(field.id, "rejected")}
                >
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : null}
      {suggestions.length > 0 ? (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-muted">
            Link Suggestions
          </p>
          {suggestions.map((suggestion) => (
            <div key={suggestion.id} className="rounded-md border border-border-soft bg-panel-2 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-text">
                  {suggestion.target_label ?? formatType(suggestion.target_type)}
                </span>
                <Badge tone={statusTone(suggestion.review_status)}>
                  {formatType(suggestion.review_status)}
                </Badge>
                <span className="text-xs text-text-muted">
                  {confidenceLabel(suggestion.confidence)}
                </span>
              </div>
              <p className="mt-1 text-sm text-text-secondary">
                {suggestion.reason ?? "No reason captured"}
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  className={secondaryButtonClass}
                  onClick={() => onSuggestionStatus(suggestion.id, "approved")}
                >
                  Approve
                </button>
                <button
                  type="button"
                  className={dangerButtonClass}
                  onClick={() => onSuggestionStatus(suggestion.id, "rejected")}
                >
                  Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : null}
    </Panel>
  );
}

function RecordLinksPanel({ links }: { links: RecordLink[] }) {
  return (
    <Panel title="Relationship Context">
      {links.length === 0 ? (
        <EmptyLine>No universal links point at this site yet.</EmptyLine>
      ) : (
        <div className="space-y-3">
          {links.map((link) => (
            <article key={link.id} className="rounded-md border border-border-soft bg-panel-2 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge>{formatType(link.source_type)}</Badge>
                <span className="text-sm text-text-secondary">to</span>
                <Badge>{formatType(link.target_type)}</Badge>
                <Badge tone="info">{formatType(link.relationship_type)}</Badge>
              </div>
              <p className="mt-2 text-sm text-text-secondary">
                {link.link_reason ?? "No reason captured"}
              </p>
            </article>
          ))}
        </div>
      )}
    </Panel>
  );
}

export default function IntelligencePage() {
  const organizationId = useOrganizationId();
  const [clients, setClients] = useState<Client[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedSiteId, setSelectedSiteId] = useState<string>("");
  const [bmps, setBmps] = useState<BmpSystem[]>([]);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [notes, setNotes] = useState<RecordNote[]>([]);
  const [knowledgeItems, setKnowledgeItems] = useState<KnowledgeItem[]>([]);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [recordLinks, setRecordLinks] = useState<RecordLink[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [chunks, setChunks] = useState<DocumentTextChunk[]>([]);
  const [fields, setFields] = useState<DocumentExtractedField[]>([]);
  const [suggestions, setSuggestions] = useState<DocumentLinkSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [documentLoading, setDocumentLoading] = useState(false);
  const [savingNote, setSavingNote] = useState(false);
  const [noteForm, setNoteForm] = useState<NoteFormState>(emptyNoteForm);
  const [error, setError] = useState<string | null>(null);

  const clientById = useMemo(
    () => new Map(clients.map((client) => [client.id, client])),
    [clients],
  );
  const jobNameById = useMemo(
    () => new Map(jobs.map((job) => [job.id, job.name])),
    [jobs],
  );
  const systemNameById = useMemo(
    () => new Map(bmps.map((bmp) => [bmp.id, bmp.name ?? bmp.system_code ?? bmp.system_type])),
    [bmps],
  );
  const selectedSite = useMemo(
    () => sites.find((site) => site.id === selectedSiteId) ?? null,
    [selectedSiteId, sites],
  );
  const selectedClient = selectedSite ? clientById.get(selectedSite.client_id) ?? null : null;
  const selectedSiteJobs = useMemo(
    () => jobs.filter((job) => job.site_id === selectedSiteId),
    [jobs, selectedSiteId],
  );

  const loadFoundation = useCallback(async () => {
    if (!organizationId) return;
    setLoading(true);
    setError(null);
    try {
      const [clientResponse, siteResponse, jobResponse] = await Promise.all([
        listClients({ organizationId, limit: 500 }),
        listSites({ organizationId, limit: 500 }),
        listJobs({ organizationId, limit: 500 }),
      ]);
      setClients(clientResponse.items);
      setSites(siteResponse.items);
      setJobs(jobResponse.items);
      setSelectedSiteId((current) => {
        if (current && siteResponse.items.some((site) => site.id === current)) {
          return current;
        }
        return siteResponse.items[0]?.id ?? "";
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load Intelligence.");
    } finally {
      setLoading(false);
    }
  }, [organizationId]);

  const loadSiteIntelligence = useCallback(async () => {
    if (!organizationId || !selectedSiteId) return;
    setLoading(true);
    setError(null);
    try {
      const [
        bmpResponse,
        observationResponse,
        noteResponse,
        knowledgeResponse,
        documentResponse,
        linkResponse,
      ] = await Promise.all([
        listBmpSystems({ organizationId, siteId: selectedSiteId, limit: 100 }),
        listObservations({ organizationId, siteId: selectedSiteId, limit: 100 }),
        listRecordNotes({
          organizationId,
          parentType: "site",
          parentId: selectedSiteId,
          limit: 100,
        }),
        listKnowledgeItems({ organizationId, siteId: selectedSiteId, limit: 100 }),
        listDocuments({ organizationId, siteId: selectedSiteId, limit: 100 }),
        listRecordLinks({
          organizationId,
          targetType: "site",
          targetId: selectedSiteId,
          limit: 100,
        }),
      ]);
      setBmps(bmpResponse.items);
      setObservations(observationResponse.items);
      setNotes(noteResponse.items);
      setKnowledgeItems(knowledgeResponse.items);
      setDocuments(documentResponse.items);
      setRecordLinks(linkResponse.items);
      setSelectedDocumentId((current) => {
        if (current && documentResponse.items.some((document) => document.id === current)) {
          return current;
        }
        return documentResponse.items[0]?.id ?? null;
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load site intelligence.");
    } finally {
      setLoading(false);
    }
  }, [organizationId, selectedSiteId]);

  const loadDocumentDetail = useCallback(async () => {
    if (!organizationId || !selectedDocumentId) {
      setChunks([]);
      setFields([]);
      setSuggestions([]);
      return;
    }
    setDocumentLoading(true);
    setError(null);
    try {
      const [chunkResponse, fieldResponse, suggestionResponse] = await Promise.all([
        listDocumentChunks(selectedDocumentId, organizationId),
        listDocumentExtractedFields(selectedDocumentId, organizationId),
        listDocumentLinkSuggestions(selectedDocumentId, organizationId),
      ]);
      setChunks(chunkResponse.items);
      setFields(fieldResponse.items);
      setSuggestions(suggestionResponse.items);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load document detail.");
    } finally {
      setDocumentLoading(false);
    }
  }, [organizationId, selectedDocumentId]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadFoundation();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadFoundation]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadSiteIntelligence();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadSiteIntelligence]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadDocumentDetail();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [loadDocumentDetail]);

  async function submitNote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!organizationId || !selectedSiteId) return;
    setSavingNote(true);
    setError(null);
    try {
      const created = await createRecordNote(organizationId, {
        parent_type: "site",
        parent_id: selectedSiteId,
        title: noteForm.title.trim(),
        body: noteForm.body.trim(),
        note_type: "general",
        visibility: "internal",
      });
      setNotes((current) => [created, ...current]);
      setNoteForm(emptyNoteForm);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save note.");
    } finally {
      setSavingNote(false);
    }
  }

  async function archiveNote(noteId: string) {
    if (!organizationId) return;
    setError(null);
    try {
      await archiveRecordNote(noteId, organizationId);
      setNotes((current) => current.filter((note) => note.id !== noteId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to archive note.");
    }
  }

  async function setFieldStatus(fieldId: string, reviewStatus: string) {
    if (!organizationId || !selectedDocumentId) return;
    try {
      const updated = await updateDocumentExtractedField(
        selectedDocumentId,
        fieldId,
        organizationId,
        { review_status: reviewStatus },
      );
      setFields((current) => current.map((field) => (field.id === fieldId ? updated : field)));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to update field.");
    }
  }

  async function setSuggestionStatus(suggestionId: string, reviewStatus: string) {
    if (!organizationId || !selectedDocumentId) return;
    try {
      const updated = await updateDocumentLinkSuggestion(
        selectedDocumentId,
        suggestionId,
        organizationId,
        { review_status: reviewStatus },
      );
      setSuggestions((current) =>
        current.map((suggestion) => (suggestion.id === suggestionId ? updated : suggestion)),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to update suggestion.");
    }
  }

  if (!organizationId) {
    return setupMessage();
  }

  return (
    <AppShell>
      <div className="mx-auto flex max-w-[1480px] flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8 xl:px-10">
        <SectionHeader
          title="Site Intelligence"
          description="Reviewed local structure for stormwater assets, findings, notes, documents, and source relationships."
          actions={
            <select
              value={selectedSiteId}
              onChange={(event) => setSelectedSiteId(event.target.value)}
              className="h-9 min-w-64 rounded-md border border-border bg-panel px-3 text-sm text-text outline-none transition focus:border-[color:var(--green)] focus:ring-2 focus:ring-green/40"
            >
              {sites.map((site) => (
                <option key={site.id} value={site.id}>
                  {site.name}
                </option>
              ))}
            </select>
          }
        />

        {error ? (
          <div className="rounded-lg border border-[color:var(--red)]/40 bg-[color:var(--red-soft)] p-4 text-sm text-[color:var(--red)]">
            {error}
          </div>
        ) : null}

        {loading && sites.length === 0 ? (
          <div className="rounded-lg border border-border bg-panel p-4 text-sm text-text-muted">
            Loading Intelligence...
          </div>
        ) : null}

        <SiteSummary
          site={selectedSite}
          client={selectedClient}
          jobs={selectedSiteJobs}
          bmpCount={bmps.length}
          observationCount={observations.length}
          documentCount={documents.length}
        />

        <div className="grid gap-5 xl:grid-cols-[1fr_1fr]">
          <BmpPanel bmps={bmps} />
          <ObservationsPanel
            observations={observations}
            systemNameById={systemNameById}
            jobNameById={jobNameById}
          />
        </div>

        <div className="grid gap-5 xl:grid-cols-[1fr_1fr]">
          <NotesPanel
            notes={notes}
            form={noteForm}
            saving={savingNote}
            onFormChange={setNoteForm}
            onSubmit={submitNote}
            onArchive={(noteId) => void archiveNote(noteId)}
          />
          <KnowledgePanel items={knowledgeItems} />
        </div>

        <div className="grid gap-5 xl:grid-cols-[0.85fr_1.15fr]">
          <DocumentsPanel
            documents={documents}
            selectedDocumentId={selectedDocumentId}
            onSelectDocument={setSelectedDocumentId}
          />
          <DocumentDetailPanel
            loading={documentLoading}
            chunks={chunks}
            fields={fields}
            suggestions={suggestions}
            onFieldStatus={(fieldId, reviewStatus) => void setFieldStatus(fieldId, reviewStatus)}
            onSuggestionStatus={(suggestionId, reviewStatus) =>
              void setSuggestionStatus(suggestionId, reviewStatus)
            }
          />
        </div>

        <RecordLinksPanel links={recordLinks} />
      </div>
    </AppShell>
  );
}
