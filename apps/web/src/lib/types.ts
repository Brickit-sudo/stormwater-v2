export type UUID = string;

export type ListResponse<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type Client = {
  id: UUID;
  organization_id: UUID;
  client_code: string | null;
  name: string;
  status: string;
  primary_contact_name: string | null;
  email: string | null;
  phone: string | null;
  billing_address: string | null;
  notes: string | null;
  drive_folder_url: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
};

export type Site = {
  id: UUID;
  organization_id: UUID;
  client_id: UUID;
  site_code: string | null;
  name: string;
  address: string | null;
  city: string | null;
  state: string | null;
  zip: string | null;
  latitude: string | number | null;
  longitude: string | number | null;
  status: string;
  notes: string | null;
  drive_folder_url: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
};

export type Job = {
  id: UUID;
  organization_id: UUID;
  client_id: UUID;
  site_id: UUID;
  job_code: string | null;
  name: string;
  service_type: string | null;
  status: string;
  assigned_to: UUID | null;
  scheduled_date: string | null;
  due_date: string | null;
  completed_date: string | null;
  scope: string | null;
  notes: string | null;
  drive_folder_url: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
};

export type ClientFormInput = {
  client_code?: string | null;
  name: string;
  status: string;
  primary_contact_name?: string | null;
  email?: string | null;
  phone?: string | null;
  billing_address?: string | null;
  notes?: string | null;
  drive_folder_url?: string | null;
};

export type SiteFormInput = {
  client_id: UUID;
  site_code?: string | null;
  name: string;
  status: string;
  address?: string | null;
  city?: string | null;
  state?: string | null;
  zip?: string | null;
  notes?: string | null;
  drive_folder_url?: string | null;
};

export type JobFormInput = {
  client_id: UUID;
  site_id: UUID;
  job_code?: string | null;
  name: string;
  service_type?: string | null;
  status: string;
  scheduled_date?: string | null;
  due_date?: string | null;
  completed_date?: string | null;
  scope?: string | null;
  notes?: string | null;
  drive_folder_url?: string | null;
};

export type ListOptions = {
  organizationId: UUID;
  search?: string;
  status?: string;
  clientId?: UUID;
  siteId?: UUID;
  limit?: number;
  offset?: number;
};
