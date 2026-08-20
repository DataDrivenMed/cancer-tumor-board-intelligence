export type ApiConnectionState = "checking" | "ready" | "unavailable";

export type RuntimeStatus = Record<string, Record<string, unknown>>;

export interface WorkflowEvent {
  sequence: number;
  event_id: string;
  timestamp: string;
  source_event: string;
  phase: "intake" | "verify" | "evidence" | "analyze" | "brief";
  status: "started" | "completed" | "blocked";
  title: string;
  clinical_consequence: string;
  audit_detail: string;
}

export interface WorkflowRunResponse {
  request_id: string;
  api_version: string;
  case_id: string;
  research_use_only: boolean;
  runtime_status: RuntimeStatus;
  events: WorkflowEvent[];
  result: Record<string, unknown>;
  evidence_commission?: Record<string, unknown> | null;
  rerun?: TargetedRerunReceipt | null;
}

export interface RuntimeStatusResponse {
  request_id: string;
  api_version: string;
  research_use_only: boolean;
  runtime_status: RuntimeStatus;
}

export interface ExtractionSourceSegment {
  segment_id: string;
  text: string;
  page: number | null;
  paragraph: number | null;
}

export interface CaseExtractionResponse {
  request_id: string;
  api_version: string;
  research_use_only: boolean;
  extraction_version: string;
  case: Record<string, unknown>;
  raw_extraction: Record<string, unknown>;
  source_segments: ExtractionSourceSegment[];
  provenance_total: number;
  provenance_verified: number;
  provenance_failures: string[];
  warnings: string[];
  normalization_events: Record<string, unknown>[];
  diagnostic_certainty: string;
  deidentification_screen: {
    status: "clear" | "blocked";
    finding_count: number;
    scanner_version: string;
    original_document_retained: boolean;
    boundary: string;
  };
}

export type EvidenceMode = "guided_fixture" | "live";
export type EvidenceChannel = "guideline" | "molecular" | "safety";

export interface EvidenceCandidate {
  candidate_id: string;
  channel: EvidenceChannel;
  title: string;
  source_title: string;
  source_organization: string;
  source_url: string;
  source_locator: string;
  exact_excerpt: string;
  summary: string;
  source_type: string;
  source_date: string | null;
  therapy_terms: string[];
  gene: string | null;
  section: string | null;
  verification_status: string;
  synthetic: boolean;
  metadata: Record<string, unknown>;
}

export interface EvidenceCandidateSetResponse {
  request_id: string;
  api_version: string;
  case_id: string;
  research_use_only: boolean;
  mode: EvidenceMode;
  candidate_set_id: string;
  candidates: EvidenceCandidate[];
  downstream_channels: Record<string, unknown>[];
  warnings: string[];
}

export interface EvidenceDecision {
  candidate_id: string;
  decision: "approved" | "rejected";
  reason: string;
}

export interface EvidenceCommissionInput {
  mode: EvidenceMode;
  candidate_set_id: string;
  decisions: EvidenceDecision[];
  attested: boolean;
}

export type ClinicianJudgmentPosition =
  | "agree"
  | "partially_agree"
  | "disagree"
  | "insufficient_context";

export type ClinicianJudgmentReason =
  | "clinical_context_not_represented"
  | "evidence_interpretation_differs"
  | "patient_preference"
  | "institutional_practice"
  | "safety_concern"
  | "other";

export type BoardDecisionOutcome =
  | "endorsed_system_supported_option"
  | "selected_alternative"
  | "deferred_pending_information"
  | "no_decision"
  | "other";

export interface HumanDecisionRecordInput {
  case_id: string;
  case_type: "synthetic" | "deidentified_research";
  workflow_request_id: string;
  system_decision: Record<string, unknown>;
  clinician_judgment: {
    position: ClinicianJudgmentPosition;
    reason_codes: ClinicianJudgmentReason[];
    rationale: string;
    attested: boolean;
  };
  board_decision: {
    status: "pending" | "recorded";
    outcome: BoardDecisionOutcome | null;
    decision: string;
    rationale: string;
    board_date: string | null;
    attested: boolean;
  };
}

export interface HumanDecisionEvent {
  event: string;
  actor: string;
  timestamp: string;
  detail: string;
}

export interface HumanDecisionRecordResponse extends HumanDecisionRecordInput {
  request_id: string;
  api_version: string;
  research_use_only: boolean;
  recorded_at: string;
  decision_record_id: string;
  decision_events: HumanDecisionEvent[];
  persisted: false;
}

export type CaseVersionTrigger =
  | "initial_board_review"
  | "new_document"
  | "new_result"
  | "clinical_change"
  | "evidence_update"
  | "correction"
  | "other";

export interface CaseVersionSummary {
  version_id: string;
  case_id: string;
  version_number: number;
  parent_version_id: string | null;
  created_at: string;
  trigger: CaseVersionTrigger;
  change_summary: string;
  content_hash: string;
  workflow_request_id: string;
  decision_record_id: string;
  decision_state: string;
  board_status: string;
}

export interface CaseVersionDetail extends CaseVersionSummary {
  case: Record<string, unknown>;
  raw_extraction: Record<string, unknown> | null;
  workflow: WorkflowRunResponse;
  evidence_review: Record<string, unknown>;
  human_decision: HumanDecisionRecordResponse;
}

export interface CaseVersionSaveResponse {
  request_id: string;
  api_version: string;
  research_use_only: boolean;
  persisted: true;
  storage: "sqlite" | "postgresql";
  created: boolean;
  version: CaseVersionDetail;
}

export interface CaseVersionListResponse {
  request_id: string;
  api_version: string;
  case_id: string;
  research_use_only: boolean;
  versions: CaseVersionSummary[];
}

export interface ProductCaseListResponse {
  request_id: string;
  api_version: string;
  research_use_only: boolean;
  cases: CaseVersionSummary[];
}

export interface CaseVersionDetailResponse {
  request_id: string;
  api_version: string;
  research_use_only: boolean;
  version: CaseVersionDetail;
}

export interface CaseUpdateAssessment {
  request_id: string;
  api_version: string;
  case_id: string;
  research_use_only: boolean;
  base_version_id: string;
  trigger: CaseVersionTrigger;
  change_summary: string;
  changed_paths: string[];
  changed_roots: string[];
  change_severity: string;
  specialist_agents_to_rerun: string[];
  specialist_agents_eligible_for_reuse: string[];
  always_rerun_controls: string[];
  evidence_review_required: boolean;
  prior_decision_status: "historical_only";
  explanation: string;
}

export interface TargetedRerunReceipt {
  base_version_id: string;
  trigger: CaseVersionTrigger;
  change_summary: string;
  changed_paths: string[];
  always_rerun_controls: string[];
  specialist_agents_executed: string[];
  specialist_agents_reused: string[];
  prior_decision_status: "historical_only";
}

export interface EvaluationMetricValue {
  metric_id: string;
  label: string;
  numerator: number;
  denominator: number;
  value: number | null;
  target: number;
}

export interface EvaluationGuardrailValue {
  metric_id: string;
  label: string;
  value: number;
  target: number;
}

export interface EvaluationSummary {
  request_id: string;
  api_version: string;
  research_use_only: boolean;
  generated_at: string;
  scope: "saved_research_case_versions";
  versions_evaluated: number;
  cases_evaluated: number;
  current_state: "baseline_pending" | "pass" | "action_required";
  primary_metrics: EvaluationMetricValue[];
  guardrails: EvaluationGuardrailValue[];
  limitations: string;
}

export interface ReleaseReadinessCheck {
  check_id: string;
  category: string;
  level: "local_research" | "production_research" | "clinical_release";
  status: "ready" | "blocked" | "attention";
  detail: string;
  remediation: string;
}

export interface ReleaseReadiness {
  request_id: string;
  api_version: string;
  research_use_only: boolean;
  overall_state: "production_research_ready" | "production_research_blocked";
  local_research_ready: boolean;
  production_research_ready: boolean;
  clinical_release_authorized: false;
  checks: ReleaseReadinessCheck[];
  boundary: string;
}

const DEFAULT_API_URL = "/api/backend";

function apiUrl(path: string): string {
  const base = DEFAULT_API_URL.replace(/\/$/, "");
  return `${base}${path}`;
}

function requestId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `web-${Date.now().toString(36)}`;
}

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20_000);
  try {
    const response = await fetch(apiUrl(path), {
      ...init,
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        "X-Request-ID": requestId(),
        ...(init?.headers || {}),
      },
      signal: controller.signal,
    });
    if (!response.ok) {
      const body = (await response.json().catch(() => null)) as { detail?: string } | null;
      throw new Error(body?.detail || `The API returned status ${response.status}.`);
    }
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("The governed workflow did not respond within 20 seconds.");
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export async function getRuntimeStatus(): Promise<RuntimeStatusResponse> {
  return apiRequest<RuntimeStatusResponse>("/api/v1/runtime/status");
}

export async function getEvaluationSummary(): Promise<EvaluationSummary> {
  return apiRequest<EvaluationSummary>("/api/v1/evaluations/summary");
}

export async function getReleaseReadiness(): Promise<ReleaseReadiness> {
  return apiRequest<ReleaseReadiness>("/api/v1/release/readiness");
}

export async function extractCaseDocument(input: {
  caseId: string;
  caseType: "synthetic" | "deidentified_research";
  documentId: string;
  filename: string;
  contentBase64: string;
  deidentificationAttested: boolean;
}): Promise<CaseExtractionResponse> {
  return apiRequest<CaseExtractionResponse>("/api/v1/cases/extract", {
    method: "POST",
    body: JSON.stringify({
      case_id: input.caseId,
      case_type: input.caseType,
      deidentification_attested: input.deidentificationAttested,
      document: {
        document_id: input.documentId,
        filename: input.filename,
        content_base64: input.contentBase64,
      },
    }),
  });
}

export async function getEvidenceCandidates(
  casePayload: Record<string, unknown>,
  mode: EvidenceMode,
): Promise<EvidenceCandidateSetResponse> {
  return apiRequest<EvidenceCandidateSetResponse>("/api/v1/evidence/candidates", {
    method: "POST",
    body: JSON.stringify({ case: casePayload, mode }),
  });
}

export async function runGovernedWorkflow(
  casePayload: Record<string, unknown>,
  rawExtraction?: Record<string, unknown> | null,
): Promise<WorkflowRunResponse> {
  return apiRequest<WorkflowRunResponse>("/api/v1/workflows/run", {
    method: "POST",
    body: JSON.stringify({
      case: casePayload,
      ...(rawExtraction ? { raw_extraction: rawExtraction } : {}),
    }),
  });
}

export async function runCommissionedWorkflow(
  casePayload: Record<string, unknown>,
  rawExtraction: Record<string, unknown> | null,
  evidenceCommission: EvidenceCommissionInput,
): Promise<WorkflowRunResponse> {
  return apiRequest<WorkflowRunResponse>("/api/v1/workflows/run-commissioned", {
    method: "POST",
    body: JSON.stringify({
      case: casePayload,
      ...(rawExtraction ? { raw_extraction: rawExtraction } : {}),
      evidence_commission: evidenceCommission,
    }),
  });
}

export async function recordHumanDecision(
  input: HumanDecisionRecordInput,
): Promise<HumanDecisionRecordResponse> {
  return apiRequest<HumanDecisionRecordResponse>("/api/v1/decisions/record", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function saveCaseVersion(input: {
  casePayload: Record<string, unknown>;
  rawExtraction: Record<string, unknown> | null;
  workflow: WorkflowRunResponse;
  evidenceReview: Record<string, unknown>;
  humanDecision: HumanDecisionRecordResponse;
  parentVersionId: string | null;
  trigger: CaseVersionTrigger;
  changeSummary: string;
}): Promise<CaseVersionSaveResponse> {
  return apiRequest<CaseVersionSaveResponse>("/api/v1/cases/versions", {
    method: "POST",
    body: JSON.stringify({
      case: input.casePayload,
      raw_extraction: input.rawExtraction,
      workflow: input.workflow,
      evidence_review: input.evidenceReview,
      human_decision: input.humanDecision,
      parent_version_id: input.parentVersionId,
      trigger: input.trigger,
      change_summary: input.changeSummary,
    }),
  });
}

export async function listCaseVersions(caseId: string): Promise<CaseVersionListResponse> {
  return apiRequest<CaseVersionListResponse>(`/api/v1/cases/${encodeURIComponent(caseId)}/versions`);
}

export async function listProductCases(): Promise<ProductCaseListResponse> {
  return apiRequest<ProductCaseListResponse>("/api/v1/product/cases");
}

export async function getCaseVersion(caseId: string, versionId: string): Promise<CaseVersionDetailResponse> {
  return apiRequest<CaseVersionDetailResponse>(
    `/api/v1/cases/${encodeURIComponent(caseId)}/versions/${encodeURIComponent(versionId)}`,
  );
}

export async function assessCaseUpdate(input: {
  baseVersionId: string;
  updatedCase: Record<string, unknown>;
  trigger: CaseVersionTrigger;
  changeSummary: string;
  attested: boolean;
}): Promise<CaseUpdateAssessment> {
  return apiRequest<CaseUpdateAssessment>("/api/v1/case-version-updates/assess", {
    method: "POST",
    body: JSON.stringify({
      base_version_id: input.baseVersionId,
      updated_case: input.updatedCase,
      trigger: input.trigger,
      change_summary: input.changeSummary,
      attested: input.attested,
    }),
  });
}

export async function runTargetedWorkflow(input: {
  baseVersionId: string;
  casePayload: Record<string, unknown>;
  rawExtraction: Record<string, unknown> | null;
  evidenceCommission: EvidenceCommissionInput;
  trigger: CaseVersionTrigger;
  changeSummary: string;
}): Promise<WorkflowRunResponse> {
  return apiRequest<WorkflowRunResponse>("/api/v1/workflows/rerun-targeted", {
    method: "POST",
    body: JSON.stringify({
      base_version_id: input.baseVersionId,
      case: input.casePayload,
      raw_extraction: input.rawExtraction,
      evidence_commission: input.evidenceCommission,
      trigger: input.trigger,
      change_summary: input.changeSummary,
      update_attested: true,
    }),
  });
}
