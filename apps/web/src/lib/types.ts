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

export type MapSite = {
  id: UUID;
  name: string;
  client_id: UUID;
  client_name: string | null;
  status: string;
  address: string | null;
  city: string | null;
  state: string | null;
  latitude: string | number;
  longitude: string | number;
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

export type TimelineEntryType =
  | "record"
  | "job"
  | "reminder"
  | "file"
  | "email"
  | "email_link"
  | "ai_draft"
  | "import_batch"
  | "outlook_draft";

export type TimelineEntry = {
  id: string;
  type: TimelineEntryType;
  title: string;
  description: string | null;
  occurred_at: string;
  source_table: string;
  source_id: UUID;
  status: string | null;
  priority: string | null;
  related_client_id: UUID | null;
  related_site_id: UUID | null;
  related_job_id: UUID | null;
  href: string | null;
  metadata: Record<string, unknown> | null;
};

export type TimelineListOptions = {
  organizationId: UUID;
  clientId?: UUID;
  siteId?: UUID;
  jobId?: UUID;
  limit?: number;
};

export type ReportReadinessOverallStatus =
  | "ready"
  | "needs_attention"
  | "blocked";

export type ReportReadinessCheckStatus = "pass" | "warning" | "fail";

export type ReportReadinessSeverity = "low" | "medium" | "high";

export type ReportReadinessGroup =
  | "Required"
  | "Supporting Evidence"
  | "Open Issues"
  | "Draft / Communication Context";

export type ReportReadinessCheck = {
  key: string;
  label: string;
  group: ReportReadinessGroup;
  status: ReportReadinessCheckStatus;
  severity: ReportReadinessSeverity;
  message: string;
  related_count: number | null;
  suggested_next_step: string | null;
};

export type ReportReadiness = {
  job_id: UUID;
  overall_status: ReportReadinessOverallStatus;
  score: number | null;
  summary: string;
  checks: ReportReadinessCheck[];
  blockers: ReportReadinessCheck[];
  warnings: ReportReadinessCheck[];
  ready_items: ReportReadinessCheck[];
};

export type MapSiteListOptions = {
  organizationId: UUID;
  status?: string;
  clientId?: UUID;
  north?: number;
  south?: number;
  east?: number;
  west?: number;
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
  | "google_drive"
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

export type EmailMessageStatus = "unlinked" | "linked" | "archived";

export type EmailMessage = {
  id: UUID;
  organization_id: UUID;
  import_batch_id: UUID | null;
  client_id: UUID | null;
  site_id: UUID | null;
  job_id: UUID | null;
  provider: string;
  provider_message_id: string | null;
  provider_conversation_id: string | null;
  internet_message_id: string | null;
  subject: string;
  sender: string;
  recipients_json: Array<Record<string, unknown>>;
  received_at: string | null;
  snippet: string | null;
  body_text: string;
  body_html: string | null;
  attachments_json: Array<Record<string, unknown>>;
  links_json: Array<Record<string, unknown>>;
  web_link: string | null;
  status: EmailMessageStatus;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
};

export type EmailMessageCreateInput = {
  import_batch_id?: UUID | null;
  client_id?: UUID | null;
  site_id?: UUID | null;
  job_id?: UUID | null;
  provider?: string;
  provider_message_id?: string | null;
  provider_conversation_id?: string | null;
  internet_message_id?: string | null;
  subject: string;
  sender: string;
  recipients_json?: Array<Record<string, unknown>>;
  received_at?: string | null;
  snippet?: string | null;
  body_text?: string;
  body_html?: string | null;
  attachments_json?: Array<Record<string, unknown>>;
  links_json?: Array<Record<string, unknown>>;
  web_link?: string | null;
  status?: EmailMessageStatus;
};

export type EmailMessageUpdateInput = Partial<EmailMessageCreateInput>;

export type EmailMessageListOptions = {
  organizationId: UUID;
  search?: string;
  status?: EmailMessageStatus;
  clientId?: UUID;
  siteId?: UUID;
  jobId?: UUID;
  provider?: string;
  receivedBefore?: string;
  receivedAfter?: string;
  limit?: number;
  offset?: number;
};

export type EmailRecordLink = {
  id: UUID;
  organization_id: UUID;
  email_message_id: UUID;
  client_id: UUID | null;
  site_id: UUID | null;
  job_id: UUID | null;
  link_reason: string;
  confidence: number;
  created_at: string;
};

export type EmailRecordLinkCreateInput = {
  email_message_id: UUID;
  client_id?: UUID | null;
  site_id?: UUID | null;
  job_id?: UUID | null;
  link_reason?: string;
  confidence?: number;
};

export type EmailImportBatchStatus =
  | "previewed"
  | "imported"
  | "failed"
  | "archived"
  | "seed";

export type EmailImportBatch = {
  id: UUID;
  organization_id: UUID;
  provider: string;
  import_mode: string;
  folder_id: string | null;
  search_query: string | null;
  date_from: string | null;
  date_to: string | null;
  status: EmailImportBatchStatus;
  preview_count: number;
  imported_count: number;
  skipped_count: number;
  duplicate_count: number;
  error_count: number;
  request_json: Record<string, unknown> | null;
  result_summary_json: Record<string, unknown> | null;
  created_at: string;
  completed_at: string | null;
  archived_at: string | null;
};

export type EmailImportBatchCreateInput = {
  provider?: string;
  import_mode?: string;
  folder_id?: string | null;
  search_query?: string | null;
  date_from?: string | null;
  date_to?: string | null;
  status?: EmailImportBatchStatus;
  preview_count?: number;
  imported_count?: number;
  skipped_count?: number;
  duplicate_count?: number;
  error_count?: number;
  request_json?: Record<string, unknown> | null;
  result_summary_json?: Record<string, unknown> | null;
  completed_at?: string | null;
};

export type EmailImportBatchListOptions = {
  organizationId: UUID;
  status?: EmailImportBatchStatus;
  provider?: string;
  limit?: number;
  offset?: number;
};

export type OutlookStatus = {
  configured: boolean;
  configured_fields: string[];
  missing_fields: string[];
  graph_base_url: string;
  auth_mode: string;
  message: string;
};

export type OutlookConnectionStatus =
  | "connected"
  | "expired"
  | "disconnected"
  | "error"
  | string;

export type OutlookAuthStatus = {
  configured: boolean;
  configured_fields: string[];
  missing_fields: string[];
  graph_base_url: string;
  auth_mode: string;
  connection_status: OutlookConnectionStatus;
  connected: boolean;
  email_address: string | null;
  display_name: string | null;
  scopes: string[];
  expires_at: string | null;
  connected_at: string | null;
  last_used_at: string | null;
  token_storage_mode: string;
  message: string;
};

export type OutlookAuthStartResponse = {
  configured: boolean;
  auth_url: string;
  state: string;
  message: string;
};

export type OutlookDisconnectResponse = {
  disconnected: boolean;
  connection_status: OutlookConnectionStatus;
  message: string;
};

export type IntegrationProviderStatus = {
  provider: string;
  label: string;
  configured: boolean;
  status: "configured" | "missing" | "deferred" | string;
  missing_fields: string[];
  enabled_capabilities: string[];
  deferred_capabilities: string[];
  message: string;
  model: string | null;
};

export type IntegrationsStatus = {
  outlook: IntegrationProviderStatus;
  gmail: IntegrationProviderStatus;
  google_drive: IntegrationProviderStatus;
  onedrive: IntegrationProviderStatus;
  ai: IntegrationProviderStatus;
};

export type OutlookPreviewMessage = {
  provider_message_id: string;
  provider_conversation_id: string | null;
  internet_message_id: string | null;
  subject: string;
  sender: string;
  recipients: Array<Record<string, unknown>>;
  received_at: string | null;
  snippet: string | null;
  body_preview: string | null;
  body_text: string | null;
  has_attachments: boolean;
  web_link: string | null;
};

export type OutlookPreviewInput = {
  organization_id: UUID;
  search_query?: string | null;
  folder_id?: string | null;
  date_from?: string | null;
  date_to?: string | null;
  limit?: number;
  access_token?: string | null;
};

export type OutlookPreviewResponse = {
  items: OutlookPreviewMessage[];
  count: number;
  limit: number;
  capped: boolean;
};

export type OutlookImportSelectedInput = {
  organization_id: UUID;
  search_query?: string | null;
  folder_id?: string | null;
  date_from?: string | null;
  date_to?: string | null;
  limit?: number;
  selected_messages: OutlookPreviewMessage[];
  access_token?: string | null;
};

export type OutlookImportSelectedResponse = {
  batch: EmailImportBatch;
  imported_messages: EmailMessage[];
  imported_count: number;
  skipped_count: number;
  duplicate_count: number;
  error_count: number;
  capped: boolean;
};

export type AiDraftStatus = "draft" | "reviewed" | "used" | "archived";

export type AiDraft = {
  id: UUID;
  organization_id: UUID;
  client_id: UUID | null;
  site_id: UUID | null;
  job_id: UUID | null;
  email_message_id: UUID | null;
  draft_type: string;
  title: string;
  prompt_context: string | null;
  draft_text: string;
  status: AiDraftStatus;
  provider: string | null;
  provider_draft_id: string | null;
  provider_web_link: string | null;
  provider_status: string | null;
  pushed_to_provider_at: string | null;
  provider_error: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
};

export type AiDraftCreateInput = {
  client_id?: UUID | null;
  site_id?: UUID | null;
  job_id?: UUID | null;
  email_message_id?: UUID | null;
  draft_type?: string;
  title: string;
  prompt_context?: string | null;
  draft_text: string;
  status?: AiDraftStatus;
};

export type AiDraftUpdateInput = Partial<AiDraftCreateInput>;

export type AiDraftListOptions = {
  organizationId: UUID;
  status?: AiDraftStatus;
  draftType?: string;
  clientId?: UUID;
  siteId?: UUID;
  jobId?: UUID;
  emailMessageId?: UUID;
  limit?: number;
  offset?: number;
};

export type OutlookDraftFromAiDraftInput = {
  organization_id: UUID;
  ai_draft_id: UUID;
  to_recipients: string[];
  subject?: string | null;
  body_override?: string | null;
};

export type OutlookDraftFromAiDraftResponse = {
  ai_draft_id: UUID;
  provider: string;
  provider_draft_id: string;
  provider_web_link: string | null;
  provider_status: string;
  pushed_to_provider_at: string;
};

export type AiStatus = {
  configured: boolean;
  enabled: boolean;
  provider: string;
  model: string | null;
  missing_fields: string[];
  message: string;
};

export type SavedDraftRef = {
  id: UUID;
  draft_type: string;
  title: string;
  status: string;
};

export type AiRequestInput = {
  organization_id: UUID;
  email_message_id?: UUID | null;
  client_id?: UUID | null;
  site_id?: UUID | null;
  job_id?: UUID | null;
  user_context?: string | null;
  save_draft?: boolean;
};

export type EmailSummaryResult = {
  summary: string;
  key_points: string[];
  questions: string[];
  recommended_next_step: string;
};

export type AiOperationResponse = {
  available: boolean;
  source: string;
  model: string | null;
  error_code: string | null;
  message: string;
  saved_draft: SavedDraftRef | null;
};

export type EmailSummaryResponse = AiOperationResponse & {
  result: EmailSummaryResult | null;
};

export type ActionItemSuggestion = {
  title: string;
  priority: ReminderPriority | string;
  due_hint: string | null;
  reason: string;
  suggested_owner: string | null;
};

export type EmailActionItemsResponse = AiOperationResponse & {
  items: ActionItemSuggestion[];
};

export type FileLinkCandidate = {
  url: string;
  link_type: "google_drive" | "onedrive" | "sharepoint" | "generic_url" | string;
  label: string;
  confidence: number;
};

export type ExtractFileLinksInput = AiRequestInput & {
  text?: string | null;
};

export type ExtractFileLinksResponse = AiOperationResponse & {
  links: FileLinkCandidate[];
};

export type RecordLinkSuggestion = {
  target_type: "client" | "site" | "job" | string;
  target_id: UUID;
  target_name: string;
  confidence: number;
  reason: string;
};

export type SuggestRecordLinksInput = AiRequestInput & {
  text?: string | null;
};

export type SuggestRecordLinksResponse = AiOperationResponse & {
  suggestions: RecordLinkSuggestion[];
};

export type DraftReplyInput = AiRequestInput & {
  tone?: string;
};

export type DraftReplyResult = {
  subject: string;
  body: string;
  tone: string;
  review_note: string;
};

export type DraftReplyResponse = AiOperationResponse & {
  result: DraftReplyResult | null;
};

export type ReportSectionDraftInput = AiRequestInput & {
  section_heading?: string;
};

export type MaintenanceRecommendationDraftInput = AiRequestInput & {
  system_type?: string | null;
};

export type ClientSummaryDraftInput = AiRequestInput & {
  audience?: string;
};

export type ReportSectionDraftResult = {
  heading: string;
  draft_text: string;
  cautions: string[];
};

export type ReportSectionDraftResponse = AiOperationResponse & {
  result: ReportSectionDraftResult | null;
};
