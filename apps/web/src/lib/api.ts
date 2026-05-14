import type {
  AiRequestInput,
  AiDraft,
  AiDraftCreateInput,
  AiDraftListOptions,
  AiDraftUpdateInput,
  AiStatus,
  AuthStatusResponse,
  BmpSystem,
  BmpSystemListOptions,
  ClientSummaryDraftInput,
  Client,
  ClientFormInput,
  DocumentExtractedField,
  DocumentExtractedFieldCreateInput,
  DocumentExtractedFieldUpdateInput,
  DocumentLinkSuggestion,
  DocumentLinkSuggestionCreateInput,
  DocumentLinkSuggestionUpdateInput,
  DocumentRecord,
  DocumentRecordCreateInput,
  DocumentRecordListOptions,
  DocumentRecordUpdateInput,
  DocumentTextChunk,
  DocumentTextChunkCreateInput,
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
  GlobalSearchOptions,
  IntegrationsStatus,
  Job,
  JobFormInput,
  KnowledgeItem,
  KnowledgeItemCreateInput,
  KnowledgeItemListOptions,
  KnowledgeItemUpdateInput,
  ListOptions,
  ListResponse,
  LoginInput,
  LogoutResponse,
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
  ProductDecision,
  ProductDecisionInput,
  ProductDecisionListOptions,
  ProductDecisionUpdateInput,
  ProductIdea,
  ProductIdeaInput,
  ProductIdeaListOptions,
  ProductIdeaUpdateInput,
  ReportSectionDraftInput,
  ReportSectionDraftResponse,
  ReportReadiness,
  Observation,
  ObservationListOptions,
  RecordLink,
  RecordLinkCreateInput,
  RecordLinkListOptions,
  RecordLinkUpdateInput,
  RecordNote,
  RecordNoteCreateInput,
  RecordNoteListOptions,
  RecordNoteUpdateInput,
  Reminder,
  ReminderCreate,
  ReminderListOptions,
  ReminderUpdate,
  SearchResponse,
  Site,
  SiteFormInput,
  TimelineEntry,
  TimelineListOptions,
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
    credentials: "include",
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

export function getCurrentAuth(): Promise<AuthStatusResponse> {
  return apiRequest<AuthStatusResponse>("/v1/auth/me");
}

export function loginWithPassword(input: LoginInput): Promise<AuthStatusResponse> {
  return apiRequest<AuthStatusResponse>("/v1/auth/login", {
    method: "POST",
    body: input,
  });
}

export function logoutCurrentUser(): Promise<LogoutResponse> {
  return apiRequest<LogoutResponse>("/v1/auth/logout", {
    method: "POST",
  });
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

function timelineQuery({
  organizationId,
  clientId,
  siteId,
  jobId,
  limit,
}: TimelineListOptions): Record<string, QueryValue> {
  return {
    organization_id: organizationId,
    client_id: clientId,
    site_id: siteId,
    job_id: jobId,
    limit,
  };
}

function searchQuery({
  organizationId,
  q,
  types,
  limit,
}: GlobalSearchOptions): Record<string, QueryValue> {
  return {
    organization_id: organizationId,
    q,
    types: types?.join(","),
    limit,
  };
}

function productIdeaQuery({
  organizationId,
  status,
  priority,
  category,
  lane,
  bossDemoRelevant,
  limit,
  offset,
}: ProductIdeaListOptions): Record<string, QueryValue> {
  return {
    organization_id: organizationId,
    status,
    priority,
    category,
    lane,
    boss_demo_relevant: bossDemoRelevant,
    limit,
    offset,
  };
}

function productDecisionQuery({
  organizationId,
  status,
  relatedIdeaId,
  limit,
  offset,
}: ProductDecisionListOptions): Record<string, QueryValue> {
  return {
    organization_id: organizationId,
    status,
    related_idea_id: relatedIdeaId,
    limit,
    offset,
  };
}

export function globalSearch(
  options: GlobalSearchOptions,
): Promise<SearchResponse> {
  return apiRequest<SearchResponse>("/v1/search", {
    query: searchQuery(options),
  });
}

export function listProductIdeas(
  options: ProductIdeaListOptions,
): Promise<ListResponse<ProductIdea>> {
  return apiRequest<ListResponse<ProductIdea>>("/v1/product-ideas", {
    query: productIdeaQuery(options),
  });
}

export function getProductIdea(
  ideaId: UUID,
  organizationId: UUID,
): Promise<ProductIdea> {
  return apiRequest<ProductIdea>(`/v1/product-ideas/${ideaId}`, {
    query: { organization_id: organizationId },
  });
}

export function createProductIdea(
  organizationId: UUID,
  input: ProductIdeaInput,
): Promise<ProductIdea> {
  return apiRequest<ProductIdea>("/v1/product-ideas", {
    method: "POST",
    body: { ...input, organization_id: organizationId },
  });
}

export function updateProductIdea(
  ideaId: UUID,
  organizationId: UUID,
  input: ProductIdeaUpdateInput,
): Promise<ProductIdea> {
  return apiRequest<ProductIdea>(`/v1/product-ideas/${ideaId}`, {
    method: "PATCH",
    query: { organization_id: organizationId },
    body: input,
  });
}

export function archiveProductIdea(
  ideaId: UUID,
  organizationId: UUID,
): Promise<ProductIdea> {
  return apiRequest<ProductIdea>(`/v1/product-ideas/${ideaId}`, {
    method: "DELETE",
    query: { organization_id: organizationId },
  });
}

export function listProductDecisions(
  options: ProductDecisionListOptions,
): Promise<ListResponse<ProductDecision>> {
  return apiRequest<ListResponse<ProductDecision>>("/v1/product-decisions", {
    query: productDecisionQuery(options),
  });
}

export function createProductDecision(
  organizationId: UUID,
  input: ProductDecisionInput,
): Promise<ProductDecision> {
  return apiRequest<ProductDecision>("/v1/product-decisions", {
    method: "POST",
    body: { ...input, organization_id: organizationId },
  });
}

export function updateProductDecision(
  decisionId: UUID,
  organizationId: UUID,
  input: ProductDecisionUpdateInput,
): Promise<ProductDecision> {
  return apiRequest<ProductDecision>(`/v1/product-decisions/${decisionId}`, {
    method: "PATCH",
    query: { organization_id: organizationId },
    body: input,
  });
}

export function archiveProductDecision(
  decisionId: UUID,
  organizationId: UUID,
): Promise<ProductDecision> {
  return apiRequest<ProductDecision>(`/v1/product-decisions/${decisionId}`, {
    method: "DELETE",
    query: { organization_id: organizationId },
  });
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

export function listTimeline(
  options: TimelineListOptions,
): Promise<ListResponse<TimelineEntry>> {
  return apiRequest<ListResponse<TimelineEntry>>("/v1/timeline", {
    query: timelineQuery(options),
  });
}

export function getJobReportReadiness(
  jobId: UUID,
  organizationId: UUID,
): Promise<ReportReadiness> {
  return apiRequest<ReportReadiness>(`/v1/jobs/${jobId}/report-readiness`, {
    query: { organization_id: organizationId },
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

export function listBmpSystems(
  options: BmpSystemListOptions,
): Promise<ListResponse<BmpSystem>> {
  return apiRequest<ListResponse<BmpSystem>>("/v1/bmp-systems", {
    query: {
      organization_id: options.organizationId,
      site_id: options.siteId,
      limit: options.limit,
      offset: options.offset,
    },
  });
}

export function listObservations(
  options: ObservationListOptions,
): Promise<ListResponse<Observation>> {
  return apiRequest<ListResponse<Observation>>("/v1/observations", {
    query: {
      organization_id: options.organizationId,
      job_id: options.jobId,
      site_id: options.siteId,
      system_id: options.systemId,
      limit: options.limit,
      offset: options.offset,
    },
  });
}

export function listRecordLinks(
  options: RecordLinkListOptions,
): Promise<ListResponse<RecordLink>> {
  return apiRequest<ListResponse<RecordLink>>("/v1/record-links", {
    query: {
      organization_id: options.organizationId,
      source_type: options.sourceType,
      source_id: options.sourceId,
      target_type: options.targetType,
      target_id: options.targetId,
      relationship_type: options.relationshipType,
      limit: options.limit,
      offset: options.offset,
    },
  });
}

export function createRecordLink(
  organizationId: UUID,
  input: RecordLinkCreateInput,
): Promise<RecordLink> {
  return apiRequest<RecordLink>("/v1/record-links", {
    method: "POST",
    body: { ...input, organization_id: organizationId },
  });
}

export function updateRecordLink(
  linkId: UUID,
  organizationId: UUID,
  input: RecordLinkUpdateInput,
): Promise<RecordLink> {
  return apiRequest<RecordLink>(`/v1/record-links/${linkId}`, {
    method: "PATCH",
    query: { organization_id: organizationId },
    body: input,
  });
}

export function archiveRecordLink(
  linkId: UUID,
  organizationId: UUID,
): Promise<RecordLink> {
  return apiRequest<RecordLink>(`/v1/record-links/${linkId}`, {
    method: "DELETE",
    query: { organization_id: organizationId },
  });
}

export function listRecordNotes(
  options: RecordNoteListOptions,
): Promise<ListResponse<RecordNote>> {
  return apiRequest<ListResponse<RecordNote>>("/v1/record-notes", {
    query: {
      organization_id: options.organizationId,
      parent_type: options.parentType,
      parent_id: options.parentId,
      note_type: options.noteType,
      limit: options.limit,
      offset: options.offset,
    },
  });
}

export function createRecordNote(
  organizationId: UUID,
  input: RecordNoteCreateInput,
): Promise<RecordNote> {
  return apiRequest<RecordNote>("/v1/record-notes", {
    method: "POST",
    body: { ...input, organization_id: organizationId },
  });
}

export function updateRecordNote(
  noteId: UUID,
  organizationId: UUID,
  input: RecordNoteUpdateInput,
): Promise<RecordNote> {
  return apiRequest<RecordNote>(`/v1/record-notes/${noteId}`, {
    method: "PATCH",
    query: { organization_id: organizationId },
    body: input,
  });
}

export function archiveRecordNote(
  noteId: UUID,
  organizationId: UUID,
): Promise<RecordNote> {
  return apiRequest<RecordNote>(`/v1/record-notes/${noteId}`, {
    method: "DELETE",
    query: { organization_id: organizationId },
  });
}

export function listKnowledgeItems(
  options: KnowledgeItemListOptions,
): Promise<ListResponse<KnowledgeItem>> {
  return apiRequest<ListResponse<KnowledgeItem>>("/v1/knowledge-items", {
    query: {
      organization_id: options.organizationId,
      client_id: options.clientId,
      site_id: options.siteId,
      job_id: options.jobId,
      knowledge_type: options.knowledgeType,
      limit: options.limit,
      offset: options.offset,
    },
  });
}

export function createKnowledgeItem(
  organizationId: UUID,
  input: KnowledgeItemCreateInput,
): Promise<KnowledgeItem> {
  return apiRequest<KnowledgeItem>("/v1/knowledge-items", {
    method: "POST",
    body: { ...input, organization_id: organizationId },
  });
}

export function updateKnowledgeItem(
  itemId: UUID,
  organizationId: UUID,
  input: KnowledgeItemUpdateInput,
): Promise<KnowledgeItem> {
  return apiRequest<KnowledgeItem>(`/v1/knowledge-items/${itemId}`, {
    method: "PATCH",
    query: { organization_id: organizationId },
    body: input,
  });
}

export function archiveKnowledgeItem(
  itemId: UUID,
  organizationId: UUID,
): Promise<KnowledgeItem> {
  return apiRequest<KnowledgeItem>(`/v1/knowledge-items/${itemId}`, {
    method: "DELETE",
    query: { organization_id: organizationId },
  });
}

export function listDocuments(
  options: DocumentRecordListOptions,
): Promise<ListResponse<DocumentRecord>> {
  return apiRequest<ListResponse<DocumentRecord>>("/v1/documents", {
    query: {
      organization_id: options.organizationId,
      client_id: options.clientId,
      site_id: options.siteId,
      job_id: options.jobId,
      status: options.status,
      document_type: options.documentType,
      extraction_status: options.extractionStatus,
      limit: options.limit,
      offset: options.offset,
    },
  });
}

export function createDocument(
  organizationId: UUID,
  input: DocumentRecordCreateInput,
): Promise<DocumentRecord> {
  return apiRequest<DocumentRecord>("/v1/documents", {
    method: "POST",
    body: { ...input, organization_id: organizationId },
  });
}

export function updateDocument(
  documentId: UUID,
  organizationId: UUID,
  input: DocumentRecordUpdateInput,
): Promise<DocumentRecord> {
  return apiRequest<DocumentRecord>(`/v1/documents/${documentId}`, {
    method: "PATCH",
    query: { organization_id: organizationId },
    body: input,
  });
}

export function archiveDocument(
  documentId: UUID,
  organizationId: UUID,
): Promise<DocumentRecord> {
  return apiRequest<DocumentRecord>(`/v1/documents/${documentId}`, {
    method: "DELETE",
    query: { organization_id: organizationId },
  });
}

export function listDocumentChunks(
  documentId: UUID,
  organizationId: UUID,
): Promise<ListResponse<DocumentTextChunk>> {
  return apiRequest<ListResponse<DocumentTextChunk>>(
    `/v1/documents/${documentId}/chunks`,
    { query: { organization_id: organizationId } },
  );
}

export function createDocumentChunk(
  documentId: UUID,
  organizationId: UUID,
  input: DocumentTextChunkCreateInput,
): Promise<DocumentTextChunk> {
  return apiRequest<DocumentTextChunk>(`/v1/documents/${documentId}/chunks`, {
    method: "POST",
    body: { ...input, organization_id: organizationId },
  });
}

export function listDocumentExtractedFields(
  documentId: UUID,
  organizationId: UUID,
): Promise<ListResponse<DocumentExtractedField>> {
  return apiRequest<ListResponse<DocumentExtractedField>>(
    `/v1/documents/${documentId}/extracted-fields`,
    { query: { organization_id: organizationId } },
  );
}

export function createDocumentExtractedField(
  documentId: UUID,
  organizationId: UUID,
  input: DocumentExtractedFieldCreateInput,
): Promise<DocumentExtractedField> {
  return apiRequest<DocumentExtractedField>(
    `/v1/documents/${documentId}/extracted-fields`,
    {
      method: "POST",
      body: { ...input, organization_id: organizationId },
    },
  );
}

export function updateDocumentExtractedField(
  documentId: UUID,
  fieldId: UUID,
  organizationId: UUID,
  input: DocumentExtractedFieldUpdateInput,
): Promise<DocumentExtractedField> {
  return apiRequest<DocumentExtractedField>(
    `/v1/documents/${documentId}/extracted-fields/${fieldId}`,
    {
      method: "PATCH",
      query: { organization_id: organizationId },
      body: input,
    },
  );
}

export function listDocumentLinkSuggestions(
  documentId: UUID,
  organizationId: UUID,
): Promise<ListResponse<DocumentLinkSuggestion>> {
  return apiRequest<ListResponse<DocumentLinkSuggestion>>(
    `/v1/documents/${documentId}/link-suggestions`,
    { query: { organization_id: organizationId } },
  );
}

export function createDocumentLinkSuggestion(
  documentId: UUID,
  organizationId: UUID,
  input: DocumentLinkSuggestionCreateInput,
): Promise<DocumentLinkSuggestion> {
  return apiRequest<DocumentLinkSuggestion>(
    `/v1/documents/${documentId}/link-suggestions`,
    {
      method: "POST",
      body: { ...input, organization_id: organizationId },
    },
  );
}

export function updateDocumentLinkSuggestion(
  documentId: UUID,
  suggestionId: UUID,
  organizationId: UUID,
  input: DocumentLinkSuggestionUpdateInput,
): Promise<DocumentLinkSuggestion> {
  return apiRequest<DocumentLinkSuggestion>(
    `/v1/documents/${documentId}/link-suggestions/${suggestionId}`,
    {
      method: "PATCH",
      query: { organization_id: organizationId },
      body: input,
    },
  );
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
