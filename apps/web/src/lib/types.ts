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

export type ReminderStatus = "open" | "snoozed" | "completed" | "archived";

export type ReminderPriority = "low" | "medium" | "high";

export type Reminder = {
  id: UUID;
  organization_id: UUID;
  client_id: UUID | null;
  site_id: UUID | null;
  job_id: UUID | null;
  assigned_to: UUID | null;
  source_type: string | null;
  source_id: string | null;
  title: string;
  description: string | null;
  status: ReminderStatus;
  priority: ReminderPriority;
  due_at: string | null;
  reminder_at: string | null;
  completed_at: string | null;
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

export type ReminderCreate = {
  title: string;
  description?: string | null;
  status?: ReminderStatus;
  priority?: ReminderPriority;
  due_at?: string | null;
  reminder_at?: string | null;
  completed_at?: string | null;
  assigned_to?: UUID | null;
  source_type?: string | null;
  source_id?: string | null;
  client_id?: UUID | null;
  site_id?: UUID | null;
  job_id?: UUID | null;
};

export type ReminderUpdate = Partial<ReminderCreate>;

export type ReminderListOptions = {
  organizationId: UUID;
  status?: ReminderStatus;
  priority?: ReminderPriority;
  clientId?: UUID;
  siteId?: UUID;
  jobId?: UUID;
  dueBefore?: string;
  dueAfter?: string;
  limit?: number;
  offset?: number;
};

export type EvidenceFileSource =
  | "drive_link"
  | "upload_placeholder"
  | "report_export"
  | "photo"
  | "other";

export type EvidenceFile = {
  id: UUID;
  organization_id: UUID;
  client_id: UUID | null;
  site_id: UUID | null;
  job_id: UUID | null;
  observation_id: UUID | null;
  system_id: UUID | null;
  source: string | null;
  file_name: string;
  mime_type: string | null;
  size_bytes: number | null;
  drive_file_id: string | null;
  drive_folder_id: string | null;
  public_url: string | null;
  sort_order: number;
  caption: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
};

export type EvidenceFileCreateInput = {
  file_name: string;
  source?: EvidenceFileSource | string | null;
  public_url?: string | null;
  drive_file_id?: string | null;
  mime_type?: string | null;
  size_bytes?: number | null;
  caption?: string | null;
  sort_order?: number | null;
  client_id?: UUID | null;
  site_id?: UUID | null;
  job_id?: UUID | null;
};

export type EvidenceFileUpdateInput = {
  file_name?: string;
  source?: EvidenceFileSource | string | null;
  public_url?: string | null;
  drive_file_id?: string | null;
  mime_type?: string | null;
  size_bytes?: number | null;
  caption?: string | null;
  sort_order?: number | null;
};

export type EvidenceFileListOptions = {
  organizationId: UUID;
  clientId?: UUID;
  siteId?: UUID;
  jobId?: UUID;
  limit?: number;
  offset?: number;
};
