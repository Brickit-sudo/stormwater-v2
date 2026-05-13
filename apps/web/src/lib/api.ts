import type {
  AiRequestInput,
  AiDraft,
  AiDraftCreateInput,
  AiDraftListOptions,
  AiDraftUpdateInput,
  AiStatus,
  ClientSummaryDraftInput,
  Client,
  ClientFormInput,
  DraftReplyInput,
  DraftReplyResponse,
  EmailActionItemsResponse,
  EmailImportBatch,
  EmailImportBatchCreateInput,
  EmailImportBatchListOptions,
  EmailMessage,
  EmailMessageCreateInput,
  EmailMessageListOptions,
  EmailMessageUpdateInput,
  EmailRecordLink,
  EmailRecordLinkCreateInput,
  EmailSummaryResponse,
  ExtractFileLinksInput,
  ExtractFileLinksResponse,
  EvidenceFile,
  EvidenceFileCreateInput,
  EvidenceFileListOptions,
  EvidenceFileUpdateInput,
  IntegrationsStatus,
  Job,
  JobFormInput,
  ListOptions,
  ListResponse,
  MaintenanceRecommendationDraftInput,
  MapSite,
  MapSiteListOptions,
  OutlookAuthStartResponse,
  OutlookAuthStatus,
  OutlookDisconnectResponse,
  OutlookDraftFromAiDraftInput,
  OutlookDraftFromAiDraftResponse,
  OutlookImportSelectedInput,
  OutlookImportSelectedResponse,
  OutlookPreviewInput,
  OutlookPreviewResponse,
  OutlookStatus,
  ReportSectionDraftInput,
  ReportSectionDraftResponse,
  Reminder,
  ReminderCreate,
  ReminderListOptions,
  ReminderUpdate,
  Site,
  SiteFormInput,
  SuggestRecordLinksInput,
  SuggestRecordLinksResponse,
  UUID,
} from "./types";

type QueryValue = string | number | boolean | null | undefined;

type ApiRequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
  query?: Record<string, QueryValue>;
};

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export const apiBaseUrl = (
  process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL
).replace(/\/+$/, "");

export const demoOrganizationId =
  process.env.NEXT_PUBLIC_DEMO_ORG_ID?.trim() ?? "";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function formatDetail(detail: unknown): string {
  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (!item || typeof item !== "object") {
          return String(item);
        }

        const entry = item as { loc?: unknown; msg?: unknown };
        const location = Array.isArray(entry.loc) ? entry.loc.join(".") : "";
        const message =
          typeof entry.msg === "string" ? entry.msg : JSON.stringify(item);
        return location ? `${location}: ${message}` : message;
      })
      .join("; ");
  }

  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }

  return "Unexpected API error.";
}

async function parseError(response: Response): Promise<string> {
  const fallback = `${response.status} ${response.statusText}`;

  try {
    const body = (await response.json()) as { detail?: unknown };
    return body.detail ? formatDetail(body.detail) : fallback;
  } catch {
    return fallback;
  }
}

function buildUrl(path: string, query?: Record<string, QueryValue>): string {
  const url = new URL(`${apiBaseUrl}${path}`);

  Object.entries(query ?? {}).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") {
      return;
    }
    url.searchParams.set(key, String(value));
  });

  return url.toString();
}

async function apiRequest<T>(
  path: string,
  { body, headers, query, ...options }: ApiRequestOptions = {},
): Promise<T> {
  const response = await fetch(buildUrl(path, query), {
    cache: "no-store",
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status);
  }

  return (await response.json()) as T;
}

function orgQuery({
  organizationId,
  search,
  status,
  clientId,
  siteId,
  limit,
  offset,
}: ListOptions): Record<string, QueryValue> {
  return {
    organization_id: organizationId,
    search,
    status,
    client_id: clientId,
    site_id: siteId,
    limit,
    offset,
  };
}

function reminderQuery({
  organizationId,
  status,
  priority,
  clientId,
  siteId,
  jobId,
  dueBefore,
  dueAfter,
  limit,
  offset,
}: ReminderListOptions): Record<string, QueryValue> {
  return {
    organization_id: organizationId,
    status,
    priority,
    client_id: clientId,
    site_id: siteId,
    job_id: jobId,
    due_before: dueBefore,
    due_after: dueAfter,
    limit,
    offset,
  };
}

function emailMessageQuery({
  organizationId,
  search,
  status,
  clientId,
  siteId,
  jobId,
  provider,
  receivedBefore,
  receivedAfter,
  limit,
  offset,
}: EmailMessageListOptions): Record<string, QueryValue> {
  return {
    organization_id: organizationId,
    search,
    status,
    client_id: clientId,
    site_id: siteId,
    job_id: jobId,
    provider,
    received_before: receivedBefore,
    received_after: receivedAfter,
    limit,
    offset,
  };
}

function aiDraftQuery({
  organizationId,
  status,
  draftType,
  clientId,
  siteId,
  jobId,
  emailMessageId,
  limit,
  offset,
}: AiDraftListOptions): Record<string, QueryValue> {
  return {
    organization_id: organizationId,
    status,
    draft_type: draftType,
    client_id: clientId,
    site_id: siteId,
    job_id: jobId,
    email_message_id: emailMessageId,
    limit,
    offset,
  };
}

function emailImportBatchQuery({
  organizationId,
  status,
  provider,
  limit,
  offset,
}: EmailImportBatchListOptions): Record<string, QueryValue> {
  return {
    organization_id: organizationId,
    status,
    provider,
    limit,
    offset,
  };
}

export function listClients(options: ListOptions): Promise<ListResponse<Client>> {
  return apiRequest<ListResponse<Client>>("/v1/clients", {
    query: orgQuery(options),
  });
}

export function createClient(
  organizationId: UUID,
  input: ClientFormInput,
): Promise<Client> {
  return apiRequest<Client>("/v1/clients", {
    method: "POST",
    body: { ...input, organization_id: organizationId },
  });
}

export function updateClient(
  clientId: UUID,
  organizationId: UUID,
  input: Partial<ClientFormInput>,
): Promise<Client> {
  return apiRequest<Client>(`/v1/clients/${clientId}`, {
    method: "PATCH",
    query: { organization_id: organizationId },
    body: input,
  });
}

export function archiveClient(
  clientId: UUID,
  organizationId: UUID,
): Promise<Client> {
  return apiRequest<Client>(`/v1/clients/${clientId}`, {
    method: "DELETE",
    query: { organization_id: organizationId },
  });
}

export function getClientSites(
  clientId: UUID,
  options: ListOptions,
): Promise<ListResponse<Site>> {
  return apiRequest<ListResponse<Site>>(`/v1/clients/${clientId}/sites`, {
    query: orgQuery(options),
  });
}

export function getClientJobs(
  clientId: UUID,
  options: ListOptions,
): Promise<ListResponse<Job>> {
  return apiRequest<ListResponse<Job>>(`/v1/clients/${clientId}/jobs`, {
    query: orgQuery(options),
  });
}

export function listSites(options: ListOptions): Promise<ListResponse<Site>> {
  return apiRequest<ListResponse<Site>>("/v1/sites", {
    query: orgQuery(options),
  });
}

export function listMapSites(
  options: MapSiteListOptions,
): Promise<ListResponse<MapSite>> {
  return apiRequest<ListResponse<MapSite>>("/v1/sites/map", {
    query: {
      organization_id: options.organizationId,
      status: options.status,
      client_id: options.clientId,
      north: options.north,
      south: options.south,
      east: options.east,
      west: options.west,
      limit: options.limit,
      offset: options.offset,
    },
  });
}

export function createSite(
  organizationId: UUID,
  input: SiteFormInput,
): Promise<Site> {
  return apiRequest<Site>("/v1/sites", {
    method: "POST",
    body: { ...input, organization_id: organizationId },
  });
}

export function updateSite(
  siteId: UUID,
  organizationId: UUID,
  input: Partial<SiteFormInput>,
): Promise<Site> {
  return apiRequest<Site>(`/v1/sites/${siteId}`, {
    method: "PATCH",
    query: { organization_id: organizationId },
    body: input,
  });
}

export function archiveSite(siteId: UUID, organizationId: UUID): Promise<Site> {
  return apiRequest<Site>(`/v1/sites/${siteId}`, {
    method: "DELETE",
    query: { organization_id: organizationId },
  });
}

export function getSiteJobs(
  siteId: UUID,
  options: ListOptions,
): Promise<ListResponse<Job>> {
  return apiRequest<ListResponse<Job>>(`/v1/sites/${siteId}/jobs`, {
    query: orgQuery(options),
  });
}

export function listJobs(options: ListOptions): Promise<ListResponse<Job>> {
  return apiRequest<ListResponse<Job>>("/v1/jobs", {
    query: orgQuery(options),
  });
}

export function createJob(
  organizationId: UUID,
  input: JobFormInput,
): Promise<Job> {
  return apiRequest<Job>("/v1/jobs", {
    method: "POST",
    body: { ...input, organization_id: organizationId },
  });
}

export function updateJob(
  jobId: UUID,
  organizationId: UUID,
  input: Partial<JobFormInput>,
): Promise<Job> {
  return apiRequest<Job>(`/v1/jobs/${jobId}`, {
    method: "PATCH",
    query: { organization_id: organizationId },
    body: input,
  });
}

export function archiveJob(jobId: UUID, organizationId: UUID): Promise<Job> {
  return apiRequest<Job>(`/v1/jobs/${jobId}`, {
    method: "DELETE",
    query: { organization_id: organizationId },
  });
}

export function listReminders(
  options: ReminderListOptions,
): Promise<ListResponse<Reminder>> {
  return apiRequest<ListResponse<Reminder>>("/v1/reminders", {
    query: reminderQuery(options),
  });
}

export function createReminder(
  organizationId: UUID,
  input: ReminderCreate,
): Promise<Reminder> {
  return apiRequest<Reminder>("/v1/reminders", {
    method: "POST",
    body: { ...input, organization_id: organizationId },
  });
}

export function updateReminder(
  reminderId: UUID,
  organizationId: UUID,
  input: ReminderUpdate,
): Promise<Reminder> {
  return apiRequest<Reminder>(`/v1/reminders/${reminderId}`, {
    method: "PATCH",
    query: { organization_id: organizationId },
    body: input,
  });
}

export function completeReminder(
  reminderId: UUID,
  organizationId: UUID,
): Promise<Reminder> {
  return updateReminder(reminderId, organizationId, { status: "completed" });
}

export function archiveReminder(
  reminderId: UUID,
  organizationId: UUID,
): Promise<Reminder> {
  return apiRequest<Reminder>(`/v1/reminders/${reminderId}`, {
    method: "DELETE",
    query: { organization_id: organizationId },
  });
}

export function listFiles(
  options: EvidenceFileListOptions,
): Promise<ListResponse<EvidenceFile>> {
  return apiRequest<ListResponse<EvidenceFile>>("/v1/files", {
    query: {
      organization_id: options.organizationId,
      client_id: options.clientId,
      site_id: options.siteId,
      job_id: options.jobId,
      limit: options.limit,
      offset: options.offset,
    },
  });
}

export function createFileLink(
  organizationId: UUID,
  input: EvidenceFileCreateInput,
): Promise<EvidenceFile> {
  return apiRequest<EvidenceFile>("/v1/files", {
    method: "POST",
    body: { ...input, organization_id: organizationId },
  });
}

export function updateFileLink(
  fileId: UUID,
  organizationId: UUID,
  input: EvidenceFileUpdateInput,
): Promise<EvidenceFile> {
  return apiRequest<EvidenceFile>(`/v1/files/${fileId}`, {
    method: "PATCH",
    query: { organization_id: organizationId },
    body: input,
  });
}

export function archiveFileLink(
  fileId: UUID,
  organizationId: UUID,
): Promise<EvidenceFile> {
  return apiRequest<EvidenceFile>(`/v1/files/${fileId}`, {
    method: "DELETE",
    query: { organization_id: organizationId },
  });
}

export function listEmailMessages(
  options: EmailMessageListOptions,
): Promise<ListResponse<EmailMessage>> {
  return apiRequest<ListResponse<EmailMessage>>("/v1/email-messages", {
    query: emailMessageQuery(options),
  });
}

export function getEmailMessage(
  emailMessageId: UUID,
  organizationId: UUID,
): Promise<EmailMessage> {
  return apiRequest<EmailMessage>(`/v1/email-messages/${emailMessageId}`, {
    query: { organization_id: organizationId },
  });
}

export function createEmailMessage(
  organizationId: UUID,
  input: EmailMessageCreateInput,
): Promise<EmailMessage> {
  return apiRequest<EmailMessage>("/v1/email-messages", {
    method: "POST",
    body: { ...input, organization_id: organizationId },
  });
}

export function updateEmailMessage(
  emailMessageId: UUID,
  organizationId: UUID,
  input: EmailMessageUpdateInput,
): Promise<EmailMessage> {
  return apiRequest<EmailMessage>(`/v1/email-messages/${emailMessageId}`, {
    method: "PATCH",
    query: { organization_id: organizationId },
    body: input,
  });
}

export function archiveEmailMessage(
  emailMessageId: UUID,
  organizationId: UUID,
): Promise<EmailMessage> {
  return apiRequest<EmailMessage>(`/v1/email-messages/${emailMessageId}`, {
    method: "DELETE",
    query: { organization_id: organizationId },
  });
}

export function listEmailRecordLinks(
  organizationId: UUID,
  emailMessageId: UUID,
): Promise<ListResponse<EmailRecordLink>> {
  return apiRequest<ListResponse<EmailRecordLink>>("/v1/email-record-links", {
    query: {
      organization_id: organizationId,
      email_message_id: emailMessageId,
    },
  });
}

export function createEmailRecordLink(
  organizationId: UUID,
  input: EmailRecordLinkCreateInput,
): Promise<EmailRecordLink> {
  return apiRequest<EmailRecordLink>("/v1/email-record-links", {
    method: "POST",
    body: { ...input, organization_id: organizationId },
  });
}

export function deleteEmailRecordLink(
  linkId: UUID,
  organizationId: UUID,
): Promise<EmailRecordLink> {
  return apiRequest<EmailRecordLink>(`/v1/email-record-links/${linkId}`, {
    method: "DELETE",
    query: { organization_id: organizationId },
  });
}

export function listAiDrafts(
  options: AiDraftListOptions,
): Promise<ListResponse<AiDraft>> {
  return apiRequest<ListResponse<AiDraft>>("/v1/ai-drafts", {
    query: aiDraftQuery(options),
  });
}

export function getAiDraft(
  draftId: UUID,
  organizationId: UUID,
): Promise<AiDraft> {
  return apiRequest<AiDraft>(`/v1/ai-drafts/${draftId}`, {
    query: { organization_id: organizationId },
  });
}

export function createAiDraft(
  organizationId: UUID,
  input: AiDraftCreateInput,
): Promise<AiDraft> {
  return apiRequest<AiDraft>("/v1/ai-drafts", {
    method: "POST",
    body: { ...input, organization_id: organizationId },
  });
}

export function updateAiDraft(
  draftId: UUID,
  organizationId: UUID,
  input: AiDraftUpdateInput,
): Promise<AiDraft> {
  return apiRequest<AiDraft>(`/v1/ai-drafts/${draftId}`, {
    method: "PATCH",
    query: { organization_id: organizationId },
    body: input,
  });
}

export function archiveAiDraft(
  draftId: UUID,
  organizationId: UUID,
): Promise<AiDraft> {
  return apiRequest<AiDraft>(`/v1/ai-drafts/${draftId}`, {
    method: "DELETE",
    query: { organization_id: organizationId },
  });
}

export function listEmailImportBatches(
  options: EmailImportBatchListOptions,
): Promise<ListResponse<EmailImportBatch>> {
  return apiRequest<ListResponse<EmailImportBatch>>("/v1/email-import-batches", {
    query: emailImportBatchQuery(options),
  });
}

export function getEmailImportBatch(
  batchId: UUID,
  organizationId: UUID,
): Promise<EmailImportBatch> {
  return apiRequest<EmailImportBatch>(`/v1/email-import-batches/${batchId}`, {
    query: { organization_id: organizationId },
  });
}

export function createEmailImportBatch(
  organizationId: UUID,
  input: EmailImportBatchCreateInput,
): Promise<EmailImportBatch> {
  return apiRequest<EmailImportBatch>("/v1/email-import-batches", {
    method: "POST",
    body: { ...input, organization_id: organizationId },
  });
}

export function getIntegrationsStatus(
  organizationId?: UUID,
): Promise<IntegrationsStatus> {
  return apiRequest<IntegrationsStatus>("/v1/integrations/status", {
    query: { organization_id: organizationId },
  });
}

export function getAiStatus(): Promise<AiStatus> {
  return apiRequest<AiStatus>("/v1/ai/status");
}

export function summarizeEmail(
  input: AiRequestInput,
): Promise<EmailSummaryResponse> {
  return apiRequest<EmailSummaryResponse>("/v1/ai/email-summary", {
    method: "POST",
    body: input,
  });
}

export function extractEmailActionItems(
  input: AiRequestInput,
): Promise<EmailActionItemsResponse> {
  return apiRequest<EmailActionItemsResponse>("/v1/ai/email-action-items", {
    method: "POST",
    body: input,
  });
}

export function extractFileLinks(
  input: ExtractFileLinksInput,
): Promise<ExtractFileLinksResponse> {
  return apiRequest<ExtractFileLinksResponse>("/v1/ai/extract-file-links", {
    method: "POST",
    body: input,
  });
}

export function suggestRecordLinks(
  input: SuggestRecordLinksInput,
): Promise<SuggestRecordLinksResponse> {
  return apiRequest<SuggestRecordLinksResponse>("/v1/ai/suggest-record-links", {
    method: "POST",
    body: input,
  });
}

export function draftEmailReply(
  input: DraftReplyInput,
): Promise<DraftReplyResponse> {
  return apiRequest<DraftReplyResponse>("/v1/ai/draft-reply", {
    method: "POST",
    body: input,
  });
}

export function generateReportSectionDraft(
  input: ReportSectionDraftInput,
): Promise<ReportSectionDraftResponse> {
  return apiRequest<ReportSectionDraftResponse>("/v1/ai/report-section-draft", {
    method: "POST",
    body: input,
  });
}

export function generateMaintenanceRecommendationDraft(
  input: MaintenanceRecommendationDraftInput,
): Promise<ReportSectionDraftResponse> {
  return apiRequest<ReportSectionDraftResponse>("/v1/ai/maintenance-recommendation-draft", {
    method: "POST",
    body: input,
  });
}

export function generateClientSummaryDraft(
  input: ClientSummaryDraftInput,
): Promise<ReportSectionDraftResponse> {
  return apiRequest<ReportSectionDraftResponse>("/v1/ai/client-summary-draft", {
    method: "POST",
    body: input,
  });
}

export function getOutlookStatus(): Promise<OutlookStatus> {
  return apiRequest<OutlookStatus>("/v1/outlook/status");
}

export function getOutlookAuthStatus(
  organizationId: UUID,
): Promise<OutlookAuthStatus> {
  return apiRequest<OutlookAuthStatus>("/v1/outlook/auth/status", {
    query: { organization_id: organizationId },
  });
}

export function startOutlookAuth(
  organizationId: UUID,
): Promise<OutlookAuthStartResponse> {
  return apiRequest<OutlookAuthStartResponse>("/v1/outlook/auth/start", {
    query: { organization_id: organizationId },
  });
}

export function disconnectOutlook(
  organizationId: UUID,
): Promise<OutlookDisconnectResponse> {
  return apiRequest<OutlookDisconnectResponse>("/v1/outlook/auth/disconnect", {
    method: "POST",
    body: { organization_id: organizationId },
  });
}

export function createOutlookDraftFromAiDraft(
  input: OutlookDraftFromAiDraftInput,
): Promise<OutlookDraftFromAiDraftResponse> {
  return apiRequest<OutlookDraftFromAiDraftResponse>("/v1/outlook/drafts/from-ai-draft", {
    method: "POST",
    body: input,
  });
}

export function previewOutlookMessages(
  input: OutlookPreviewInput,
): Promise<OutlookPreviewResponse> {
  return apiRequest<OutlookPreviewResponse>("/v1/outlook/preview", {
    method: "POST",
    body: input,
  });
}

export function importSelectedOutlookMessages(
  input: OutlookImportSelectedInput,
): Promise<OutlookImportSelectedResponse> {
  return apiRequest<OutlookImportSelectedResponse>("/v1/outlook/import-selected", {
    method: "POST",
    body: input,
  });
}
