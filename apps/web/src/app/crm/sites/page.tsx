"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import AppShell from "@/components/AppShell";
import DetailPanel, { DetailField } from "@/components/crm/DetailPanel";
import EmptyState from "@/components/crm/EmptyState";
import EntityTable, { type EntityColumn } from "@/components/crm/EntityTable";
import StatusBadge from "@/components/crm/StatusBadge";
import {
  archiveSite,
  createSite,
  demoOrganizationId,
  getSiteJobs,
  listClients,
  listSites,
  updateSite,
} from "@/lib/api";
import type { Client, Job, Site, SiteFormInput } from "@/lib/types";

type FormMode = "view" | "create" | "edit";

type SiteFormState = {
  client_id: string;
  name: string;
  status: string;
  address: string;
  city: string;
  state: string;
  zip: string;
  notes: string;
  drive_folder_url: string;
};

const buttonClass =
  "inline-flex h-9 items-center justify-center rounded-md bg-[#1a7f37] px-3 text-sm font-semibold text-white transition hover:bg-[#176d31] disabled:cursor-not-allowed disabled:bg-[#a9b7a9]";
const secondaryButtonClass =
  "inline-flex h-9 items-center justify-center rounded-md border border-[#cfd8cc] bg-white px-3 text-sm font-semibold text-[#263126] transition hover:bg-[#f6f8f4] disabled:cursor-not-allowed disabled:text-[#98a398]";
const dangerButtonClass =
  "inline-flex h-9 items-center justify-center rounded-md border border-[#e2bcbc] bg-white px-3 text-sm font-semibold text-[#963333] transition hover:bg-[#fff6f6] disabled:cursor-not-allowed disabled:text-[#b99b9b]";

const siteStatusOptions = ["active", "inactive", "on_hold"];

const columns: EntityColumn<Site>[] = [
  {
    key: "name",
    header: "Name",
    className: "w-[28%]",
    render: (site) => <span className="font-medium">{site.name}</span>,
  },
  {
    key: "status",
    header: "Status",
    className: "w-[14%]",
    render: (site) => <StatusBadge status={site.status} />,
  },
  {
    key: "address",
    header: "Address",
    className: "w-[26%]",
    render: (site) => site.address || "Not set",
  },
  {
    key: "city",
    header: "City",
    className: "w-[18%]",
    render: (site) => site.city || "Not set",
  },
  {
    key: "state",
    header: "State",
    className: "w-[14%]",
    render: (site) => site.state || "Not set",
  },
];

function optional(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function formFromSite(site: Site): SiteFormState {
  return {
    client_id: site.client_id,
    name: site.name,
    status: site.status,
    address: site.address ?? "",
    city: site.city ?? "",
    state: site.state ?? "",
    zip: site.zip ?? "",
    notes: site.notes ?? "",
    drive_folder_url: site.drive_folder_url ?? "",
  };
}

function emptyForm(defaultClientId = ""): SiteFormState {
  return {
    client_id: defaultClientId,
    name: "",
    status: "active",
    address: "",
    city: "",
    state: "",
    zip: "",
    notes: "",
    drive_folder_url: "",
  };
}

function payloadFromForm(form: SiteFormState): SiteFormInput {
  return {
    client_id: form.client_id,
    name: form.name.trim(),
    status: form.status.trim() || "active",
    address: optional(form.address),
    city: optional(form.city),
    state: optional(form.state),
    zip: optional(form.zip),
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

export default function SitesPage() {
  const organizationId = demoOrganizationId;
  const [sites, setSites] = useState<Site[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [selectedSiteId, setSelectedSiteId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [clientFilter, setClientFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<FormMode>("view");
  const [form, setForm] = useState<SiteFormState>(emptyForm());
  const [linkedJobs, setLinkedJobs] = useState<Job[]>([]);
  const [linkedLoading, setLinkedLoading] = useState(false);

  const clientNameById = useMemo(
    () => new Map(clients.map((client) => [client.id, client.name])),
    [clients],
  );

  const selectedSite = useMemo(
    () => sites.find((site) => site.id === selectedSiteId) ?? null,
    [sites, selectedSiteId],
  );

  const loadClients = useCallback(async () => {
    if (!organizationId) {
      return;
    }

    try {
      const response = await listClients({ organizationId, limit: 500 });
      setClients(response.items);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load clients.");
    }
  }, [organizationId]);

  const loadSites = useCallback(async () => {
    if (!organizationId) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await listSites({
        organizationId,
        search,
        clientId: clientFilter || undefined,
        limit: 100,
      });
      setSites(response.items);
      setSelectedSiteId((current) => {
        if (current && response.items.some((site) => site.id === current)) {
          return current;
        }
        return response.items[0]?.id ?? null;
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load sites.");
    } finally {
      setLoading(false);
    }
  }, [clientFilter, organizationId, search]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadClients();
    }, 0);

    return () => window.clearTimeout(timer);
  }, [loadClients]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadSites();
    }, 250);

    return () => window.clearTimeout(timer);
  }, [loadSites]);

  useEffect(() => {
    if (!organizationId || !selectedSiteId) {
      const timer = window.setTimeout(() => {
        setLinkedJobs([]);
      }, 0);
      return () => window.clearTimeout(timer);
    }

    let cancelled = false;
    const timer = window.setTimeout(() => {
      setLinkedLoading(true);

      getSiteJobs(selectedSiteId, { organizationId, limit: 5 })
        .then((response) => {
          if (!cancelled) {
            setLinkedJobs(response.items);
          }
        })
        .catch((caught) => {
          if (!cancelled) {
            setError(
              caught instanceof Error ? caught.message : "Unable to load linked jobs.",
            );
          }
        })
        .finally(() => {
          if (!cancelled) {
            setLinkedLoading(false);
          }
        });
    }, 0);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [organizationId, selectedSiteId]);

  if (!organizationId) {
    return <SetupMessage />;
  }

  function startCreate() {
    const defaultClientId = clientFilter || clients[0]?.id || "";
    setMode("create");
    setForm(emptyForm(defaultClientId));
    setError(null);
  }

  function startEdit() {
    if (!selectedSite) {
      return;
    }
    setMode("edit");
    setForm(formFromSite(selectedSite));
    setError(null);
  }

  async function saveSite() {
    const payload = payloadFromForm(form);
    if (!payload.client_id) {
      setError("Client is required.");
      return;
    }
    if (!payload.name) {
      setError("Site name is required.");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const saved =
        mode === "create"
          ? await createSite(organizationId, payload)
          : selectedSite
            ? await updateSite(selectedSite.id, organizationId, payload)
            : null;

      await loadSites();
      if (saved) {
        setSelectedSiteId(saved.id);
      }
      setMode("view");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save site.");
    } finally {
      setSaving(false);
    }
  }

  async function archiveSelectedSite() {
    if (!selectedSite) {
      return;
    }

    const confirmed = window.confirm(`Archive ${selectedSite.name}?`);
    if (!confirmed) {
      return;
    }

    setSaving(true);
    setError(null);

    try {
      await archiveSite(selectedSite.id, organizationId);
      setMode("view");
      await loadSites();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to archive site.");
    } finally {
      setSaving(false);
    }
  }

  const panelActions =
    mode === "view" && selectedSite ? (
      <>
        <Link
          className={secondaryButtonClass}
          href={`/crm/jobs?client_id=${selectedSite.client_id}&site_id=${selectedSite.id}&new=1`}
        >
          New Job
        </Link>
        <button
          type="button"
          className={secondaryButtonClass}
          onClick={startEdit}
          disabled={saving}
        >
          Edit Site
        </button>
        <button
          type="button"
          className={dangerButtonClass}
          onClick={archiveSelectedSite}
          disabled={saving}
        >
          Archive Site
        </button>
      </>
    ) : null;

  return (
    <AppShell>
      <div className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-[#172017]">Sites</h1>
            <p className="mt-1 text-sm text-[#667466]">
              Keep locations tied to clients before work is scheduled.
            </p>
          </div>
          <button
            type="button"
            className={buttonClass}
            onClick={startCreate}
            disabled={clients.length === 0}
          >
            New Site
          </button>
        </div>

        {error ? (
          <div className="rounded-md border border-[#e7b9b9] bg-[#fff6f6] px-4 py-3 text-sm text-[#8a2f2f]">
            {error}
          </div>
        ) : null}

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
          <section className="min-w-0 space-y-3">
            <div className="grid gap-3 sm:grid-cols-[minmax(0,1fr)_240px]">
              <label className="block">
                <span className="text-sm font-medium text-[#3d4a3d]">
                  Search sites
                </span>
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search by name, code, address, city, or state"
                  className="mt-2 h-10 w-full rounded-md border border-[#cfd8cc] bg-white px-3 text-sm outline-none transition placeholder:text-[#9aa59a] focus:border-[#1a7f37] focus:ring-2 focus:ring-[#d8eedc]"
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-[#3d4a3d]">
                  Client filter
                </span>
                <select
                  value={clientFilter}
                  onChange={(event) => setClientFilter(event.target.value)}
                  className="mt-2 h-10 w-full rounded-md border border-[#cfd8cc] bg-white px-3 text-sm outline-none transition focus:border-[#1a7f37] focus:ring-2 focus:ring-[#d8eedc]"
                >
                  <option value="">All clients</option>
                  {clients.map((client) => (
                    <option key={client.id} value={client.id}>
                      {client.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <EntityTable
              rows={sites}
              columns={columns}
              getRowId={(site) => site.id}
              selectedRowId={selectedSiteId}
              onRowClick={(site) => {
                setSelectedSiteId(site.id);
                setMode("view");
              }}
              loading={loading}
              emptyTitle="No sites found"
              emptyDescription="Create a site from a client before adding site-level jobs."
            />
          </section>

          <DetailPanel
            title={
              mode === "create"
                ? "New Site"
                : selectedSite?.name ?? "Select a site"
            }
            subtitle={
              selectedSite
                ? clientNameById.get(selectedSite.client_id) ?? "Client not loaded"
                : undefined
            }
            actions={panelActions}
          >
            {mode === "create" || mode === "edit" ? (
              <SiteForm
                clients={clients}
                form={form}
                setForm={setForm}
                saving={saving}
                onCancel={() => setMode("view")}
                onSave={saveSite}
              />
            ) : selectedSite ? (
              <div className="space-y-6">
                <dl className="grid gap-4 sm:grid-cols-2">
                  <DetailField label="Status" value={<StatusBadge status={selectedSite.status} />} />
                  <DetailField
                    label="Client"
                    value={clientNameById.get(selectedSite.client_id)}
                  />
                  <DetailField label="Address" value={selectedSite.address} />
                  <DetailField label="City" value={selectedSite.city} />
                  <DetailField label="State" value={selectedSite.state} />
                  <DetailField label="ZIP" value={selectedSite.zip} />
                  <DetailField label="Drive URL" value={selectedSite.drive_folder_url} />
                  <DetailField label="Notes" value={selectedSite.notes} />
                </dl>

                <section>
                  <h3 className="text-sm font-semibold text-[#172017]">
                    Jobs for selected site
                  </h3>
                  {linkedLoading ? (
                    <p className="mt-2 text-sm text-[#667466]">Loading linked jobs...</p>
                  ) : linkedJobs.length > 0 ? (
                    <div className="mt-3 divide-y divide-[#edf0eb] rounded-md border border-[#e3e8e0]">
                      {linkedJobs.map((job) => (
                        <div key={job.id} className="px-3 py-2 text-sm text-[#263126]">
                          {[job.name, job.service_type, job.status]
                            .filter(Boolean)
                            .join(" - ")}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-2 text-sm text-[#667466]">
                      No linked jobs yet.
                    </p>
                  )}
                </section>
              </div>
            ) : (
              <EmptyState
                title="No site selected"
                description="Choose a row to see location details and linked jobs."
              />
            )}
          </DetailPanel>
        </div>
      </div>
    </AppShell>
  );
}

function SiteForm({
  clients,
  form,
  setForm,
  saving,
  onCancel,
  onSave,
}: {
  clients: Client[];
  form: SiteFormState;
  setForm: (form: SiteFormState) => void;
  saving: boolean;
  onCancel: () => void;
  onSave: () => void;
}) {
  function update(field: keyof SiteFormState, value: string) {
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

      <FormField label="Name">
        <input
          value={form.name}
          onChange={(event) => update("name", event.target.value)}
          className="form-input"
          required
        />
      </FormField>

      <FormField label="Status">
        <select
          value={form.status}
          onChange={(event) => update("status", event.target.value)}
          className="form-input"
        >
          {siteStatusOptions.map((status) => (
            <option key={status} value={status}>
              {status.replaceAll("_", " ")}
            </option>
          ))}
        </select>
      </FormField>

      <FormField label="Address">
        <textarea
          value={form.address}
          onChange={(event) => update("address", event.target.value)}
          className="form-textarea"
          rows={3}
        />
      </FormField>

      <div className="grid gap-4 sm:grid-cols-3">
        <FormField label="City">
          <input
            value={form.city}
            onChange={(event) => update("city", event.target.value)}
            className="form-input"
          />
        </FormField>
        <FormField label="State">
          <input
            value={form.state}
            onChange={(event) => update("state", event.target.value)}
            className="form-input"
          />
        </FormField>
        <FormField label="ZIP">
          <input
            value={form.zip}
            onChange={(event) => update("zip", event.target.value)}
            className="form-input"
          />
        </FormField>
      </div>

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
          {saving ? "Saving..." : "Save Site"}
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
