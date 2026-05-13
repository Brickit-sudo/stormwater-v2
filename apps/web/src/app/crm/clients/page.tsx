"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import AppShell from "@/components/AppShell";
import DetailPanel, { DetailField } from "@/components/crm/DetailPanel";
import DriveFilePanel from "@/components/crm/DriveFilePanel";
import EmptyState from "@/components/crm/EmptyState";
import EntityTable, { type EntityColumn } from "@/components/crm/EntityTable";
import StatusBadge from "@/components/crm/StatusBadge";
import TimelinePanel from "@/components/crm/TimelinePanel";
import SectionHeader from "@/components/ui/SectionHeader";
import {
  archiveClient,
  createClient,
  demoOrganizationId,
  getClientJobs,
  getClientSites,
  listClients,
  updateClient,
} from "@/lib/api";
import type { Client, ClientFormInput, Job, Site } from "@/lib/types";
import {
  dangerButtonClass,
  primaryButtonClass as buttonClass,
  secondaryButtonClass,
} from "@/lib/ui";

type FormMode = "view" | "create" | "edit";

type ClientFormState = {
  name: string;
  status: string;
  primary_contact_name: string;
  email: string;
  phone: string;
  billing_address: string;
  notes: string;
  drive_folder_url: string;
};

const emptyForm: ClientFormState = {
  name: "",
  status: "active",
  primary_contact_name: "",
  email: "",
  phone: "",
  billing_address: "",
  notes: "",
  drive_folder_url: "",
};

const clientStatusOptions = ["active", "inactive", "prospect"];

const columns: EntityColumn<Client>[] = [
  {
    key: "name",
    header: "Name",
    className: "w-[26%]",
    render: (client) => <span className="font-medium">{client.name}</span>,
  },
  {
    key: "status",
    header: "Status",
    className: "w-[14%]",
    render: (client) => <StatusBadge status={client.status} />,
  },
  {
    key: "primary_contact",
    header: "Primary Contact",
    className: "w-[20%]",
    render: (client) => client.primary_contact_name || "Not set",
  },
  {
    key: "email",
    header: "Email",
    className: "w-[22%]",
    render: (client) => client.email || "Not set",
  },
  {
    key: "phone",
    header: "Phone",
    className: "w-[18%]",
    render: (client) => client.phone || "Not set",
  },
];

function optional(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function formFromClient(client: Client): ClientFormState {
  return {
    name: client.name,
    status: client.status,
    primary_contact_name: client.primary_contact_name ?? "",
    email: client.email ?? "",
    phone: client.phone ?? "",
    billing_address: client.billing_address ?? "",
    notes: client.notes ?? "",
    drive_folder_url: client.drive_folder_url ?? "",
  };
}

function payloadFromForm(form: ClientFormState): ClientFormInput {
  return {
    name: form.name.trim(),
    status: form.status.trim() || "active",
    primary_contact_name: optional(form.primary_contact_name),
    email: optional(form.email),
    phone: optional(form.phone),
    billing_address: optional(form.billing_address),
    notes: optional(form.notes),
    drive_folder_url: optional(form.drive_folder_url),
  };
}

function SetupMessage() {
  return (
    <AppShell>
      <div className="rounded-lg border border-[color:var(--yellow)]/40 bg-[color:var(--yellow-soft)] p-5 text-sm text-[color:var(--yellow)]">
        Set NEXT_PUBLIC_DEMO_ORG_ID in apps/web/.env.local to use the CRM.
      </div>
    </AppShell>
  );
}

function LinkedList({
  title,
  items,
  getLabel,
}: {
  title: string;
  items: Array<Site | Job>;
  getLabel: (item: Site | Job) => string;
}) {
  return (
    <section>
      <h3 className="text-sm font-semibold text-text">{title}</h3>
      {items.length > 0 ? (
        <div className="mt-3 divide-y divide-border-soft rounded-lg border border-border-soft bg-panel-2">
          {items.map((item) => (
            <div key={item.id} className="px-3 py-2 text-sm text-text-secondary">
              {getLabel(item)}
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-2 text-sm text-text-muted">No linked records yet.</p>
      )}
    </section>
  );
}

export default function ClientsPage() {
  const organizationId = demoOrganizationId;
  const [clients, setClients] = useState<Client[]>([]);
  const [selectedClientId, setSelectedClientId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<FormMode>("view");
  const [form, setForm] = useState<ClientFormState>(emptyForm);
  const [linkedSites, setLinkedSites] = useState<Site[]>([]);
  const [linkedJobs, setLinkedJobs] = useState<Job[]>([]);
  const [linkedLoading, setLinkedLoading] = useState(false);

  const selectedClient = useMemo(
    () => clients.find((client) => client.id === selectedClientId) ?? null,
    [clients, selectedClientId],
  );

  const loadClients = useCallback(async () => {
    if (!organizationId) {
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await listClients({
        organizationId,
        search,
        limit: 100,
      });
      setClients(response.items);
      setSelectedClientId((current) => {
        if (current && response.items.some((client) => client.id === current)) {
          return current;
        }
        return response.items[0]?.id ?? null;
      });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load clients.");
    } finally {
      setLoading(false);
    }
  }, [organizationId, search]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadClients();
    }, 250);

    return () => window.clearTimeout(timer);
  }, [loadClients]);

  useEffect(() => {
    if (!organizationId || !selectedClientId) {
      const timer = window.setTimeout(() => {
        setLinkedSites([]);
        setLinkedJobs([]);
      }, 0);
      return () => window.clearTimeout(timer);
    }

    let cancelled = false;
    const timer = window.setTimeout(() => {
      setLinkedLoading(true);

      Promise.all([
        getClientSites(selectedClientId, { organizationId, limit: 5 }),
        getClientJobs(selectedClientId, { organizationId, limit: 5 }),
      ])
        .then(([sitesResponse, jobsResponse]) => {
          if (cancelled) {
            return;
          }
          setLinkedSites(sitesResponse.items);
          setLinkedJobs(jobsResponse.items);
        })
        .catch((caught) => {
          if (!cancelled) {
            setError(
              caught instanceof Error
                ? caught.message
                : "Unable to load linked records.",
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
  }, [organizationId, selectedClientId]);

  if (!organizationId) {
    return <SetupMessage />;
  }

  function startCreate() {
    setMode("create");
    setForm(emptyForm);
    setError(null);
  }

  function startEdit() {
    if (!selectedClient) {
      return;
    }
    setMode("edit");
    setForm(formFromClient(selectedClient));
    setError(null);
  }

  async function saveClient() {
    const payload = payloadFromForm(form);
    if (!payload.name) {
      setError("Client name is required.");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const saved =
        mode === "create"
          ? await createClient(organizationId, payload)
          : selectedClient
            ? await updateClient(selectedClient.id, organizationId, payload)
            : null;

      await loadClients();
      if (saved) {
        setSelectedClientId(saved.id);
      }
      setMode("view");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to save client.");
    } finally {
      setSaving(false);
    }
  }

  async function archiveSelectedClient() {
    if (!selectedClient) {
      return;
    }

    const confirmed = window.confirm(`Archive ${selectedClient.name}?`);
    if (!confirmed) {
      return;
    }

    setSaving(true);
    setError(null);

    try {
      await archiveClient(selectedClient.id, organizationId);
      setMode("view");
      await loadClients();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to archive client.");
    } finally {
      setSaving(false);
    }
  }

  const panelActions =
    mode === "view" && selectedClient ? (
      <>
        <button
          type="button"
          className={secondaryButtonClass}
          onClick={startEdit}
          disabled={saving}
        >
          Edit Client
        </button>
        <button
          type="button"
          className={dangerButtonClass}
          onClick={archiveSelectedClient}
          disabled={saving}
        >
          Archive Client
        </button>
      </>
    ) : null;

  return (
    <AppShell>
      <div className="space-y-6">
        <SectionHeader
          title="Clients"
          description="Manage accounts first, then work into their sites and jobs."
          actions={
            <button type="button" className={buttonClass} onClick={startCreate}>
              New Client
            </button>
          }
        />

        {error ? (
          <div className="rounded-md border border-[color:var(--red)]/40 bg-[color:var(--red-soft)] px-4 py-3 text-sm text-[color:var(--red)]">
            {error}
          </div>
        ) : null}

        <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_420px]">
          <section className="min-w-0 space-y-3">
            <label className="block">
              <span className="text-sm font-medium text-text-secondary">
                Search clients
              </span>
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search by name, code, contact, or email"
                className="form-input mt-2"
              />
            </label>

            <EntityTable
              rows={clients}
              columns={columns}
              getRowId={(client) => client.id}
              selectedRowId={selectedClientId}
              onRowClick={(client) => {
                setSelectedClientId(client.id);
                setMode("view");
              }}
              loading={loading}
              emptyTitle="No clients found"
              emptyDescription="Create a client to start the Clients -> Sites -> Jobs workflow."
            />
          </section>

          <DetailPanel
            title={
              mode === "create"
                ? "New Client"
                : selectedClient?.name ?? "Select a client"
            }
            subtitle={
              mode === "edit"
                ? "Editing client details"
                : selectedClient?.primary_contact_name ?? undefined
            }
            actions={panelActions}
          >
            {mode === "create" || mode === "edit" ? (
              <ClientForm
                form={form}
                setForm={setForm}
                saving={saving}
                onCancel={() => setMode("view")}
                onSave={saveClient}
              />
            ) : selectedClient ? (
              <div className="space-y-6">
                <dl className="grid gap-4 sm:grid-cols-2">
                  <DetailField label="Status" value={<StatusBadge status={selectedClient.status} />} />
                  <DetailField
                    label="Primary Contact"
                    value={selectedClient.primary_contact_name}
                  />
                  <DetailField label="Email" value={selectedClient.email} />
                  <DetailField label="Phone" value={selectedClient.phone} />
                  <DetailField
                    label="Billing Address"
                    value={selectedClient.billing_address}
                  />
                  <DetailField label="Drive URL" value={selectedClient.drive_folder_url} />
                  <DetailField label="Notes" value={selectedClient.notes} />
                </dl>

                {linkedLoading ? (
                  <p className="text-sm text-text-muted">Loading linked records...</p>
                ) : (
                  <div className="space-y-5">
                    <LinkedList
                      title="Sites for selected client"
                      items={linkedSites}
                      getLabel={(item) =>
                        "address" in item
                          ? [item.name, item.city, item.state]
                              .filter(Boolean)
                              .join(" - ")
                          : item.name
                      }
                    />
                    <LinkedList
                      title="Jobs for selected client"
                      items={linkedJobs}
                      getLabel={(item) =>
                        "service_type" in item
                          ? [item.name, item.service_type, item.status]
                              .filter(Boolean)
                              .join(" - ")
                          : item.name
                      }
                    />
                  </div>
                )}

                <TimelinePanel
                  organizationId={organizationId}
                  clientId={selectedClient.id}
                />

                <DriveFilePanel
                  organizationId={organizationId}
                  clientId={selectedClient.id}
                  driveFolderUrl={selectedClient.drive_folder_url}
                  selectedRecordLabel={selectedClient.name}
                />
              </div>
            ) : (
              <EmptyState
                title="No client selected"
                description="Choose a row to see account details and linked sites/jobs."
              />
            )}
          </DetailPanel>
        </div>
      </div>
    </AppShell>
  );
}

function ClientForm({
  form,
  setForm,
  saving,
  onCancel,
  onSave,
}: {
  form: ClientFormState;
  setForm: (form: ClientFormState) => void;
  saving: boolean;
  onCancel: () => void;
  onSave: () => void;
}) {
  function update(field: keyof ClientFormState, value: string) {
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
          {clientStatusOptions.map((status) => (
            <option key={status} value={status}>
              {status.replaceAll("_", " ")}
            </option>
          ))}
        </select>
      </FormField>

      <FormField label="Primary Contact">
        <input
          value={form.primary_contact_name}
          onChange={(event) => update("primary_contact_name", event.target.value)}
          className="form-input"
        />
      </FormField>

      <div className="grid gap-4 sm:grid-cols-2">
        <FormField label="Email">
          <input
            value={form.email}
            onChange={(event) => update("email", event.target.value)}
            className="form-input"
            type="email"
          />
        </FormField>
        <FormField label="Phone">
          <input
            value={form.phone}
            onChange={(event) => update("phone", event.target.value)}
            className="form-input"
          />
        </FormField>
      </div>

      <FormField label="Billing Address">
        <textarea
          value={form.billing_address}
          onChange={(event) => update("billing_address", event.target.value)}
          className="form-textarea"
          rows={3}
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
          {saving ? "Saving..." : "Save Client"}
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
