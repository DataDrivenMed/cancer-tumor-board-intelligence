from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from schemas.case import CancerTumorBoardCase


class WorkflowRunRequest(BaseModel):
    """Validated input accepted by the governed workflow endpoint."""

    model_config = ConfigDict(extra="forbid")

    case: CancerTumorBoardCase
    raw_extraction: dict[str, Any] | None = None


class EvidenceCandidateRequest(BaseModel):
    """Request a case-matched evidence candidate set for human review."""

    model_config = ConfigDict(extra="forbid")

    case: CancerTumorBoardCase
    mode: Literal["guided_fixture", "live"] = "guided_fixture"


class EvidenceCandidate(BaseModel):
    candidate_id: str
    channel: Literal["guideline", "molecular", "safety"]
    title: str
    source_title: str
    source_organization: str
    source_url: str
    source_locator: str
    exact_excerpt: str
    summary: str
    source_type: str
    source_date: str | None = None
    therapy_terms: list[str] = Field(default_factory=list)
    gene: str | None = None
    section: str | None = None
    verification_status: str
    synthetic: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceCandidateSetResponse(BaseModel):
    request_id: str
    api_version: str
    case_id: str
    research_use_only: bool = True
    mode: Literal["guided_fixture", "live"]
    candidate_set_id: str
    candidates: list[EvidenceCandidate]
    downstream_channels: list[dict[str, Any]]
    warnings: list[str]


class EvidenceDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1)
    decision: Literal["approved", "rejected"]
    reason: str = ""


class EvidenceCommissionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["guided_fixture", "live"]
    candidate_set_id: str = Field(min_length=64, max_length=64)
    decisions: list[EvidenceDecision]
    attested: bool = False


class CommissionedWorkflowRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case: CancerTumorBoardCase
    raw_extraction: dict[str, Any] | None = None
    evidence_commission: EvidenceCommissionInput


class SourceDocumentInput(BaseModel):
    """Transient document bytes accepted for governed extraction."""

    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(default="DOC-001", min_length=1, max_length=64)
    filename: str = Field(min_length=1, max_length=255)
    content_base64: str = Field(min_length=1, max_length=12_000_000)


class CaseExtractionRequest(BaseModel):
    """Synthetic or de-identified document extraction request."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(default="EXTRACTED-001", min_length=1, max_length=128)
    case_type: Literal["synthetic", "deidentified_research"] = "synthetic"
    document: SourceDocumentInput
    deidentification_attested: bool = False

    @model_validator(mode="after")
    def require_deidentification_attestation(self) -> "CaseExtractionRequest":
        if self.case_type == "deidentified_research" and not self.deidentification_attested:
            raise ValueError("De-identification attestation is required for real clinical source material.")
        return self


class SourceSegmentResponse(BaseModel):
    segment_id: str
    text: str
    page: int | None = None
    paragraph: int | None = None


class CaseExtractionResponse(BaseModel):
    """Auditable extraction package for clinician review."""

    request_id: str
    api_version: str
    research_use_only: bool = True
    extraction_version: str
    case: CancerTumorBoardCase
    raw_extraction: dict[str, Any]
    source_segments: list[SourceSegmentResponse]
    provenance_total: int
    provenance_verified: int
    provenance_failures: list[str]
    warnings: list[str]
    normalization_events: list[dict[str, Any]]
    diagnostic_certainty: str
    deidentification_screen: dict[str, Any]


class WorkflowEvent(BaseModel):
    """User-facing activity derived from one real backend audit event."""

    sequence: int = Field(ge=1)
    event_id: str
    timestamp: str
    source_event: str
    phase: Literal["intake", "verify", "evidence", "analyze", "brief"]
    status: Literal["started", "completed", "blocked"]
    title: str
    clinical_consequence: str
    audit_detail: str = ""


class WorkflowRunResponse(BaseModel):
    """Stable API envelope around the existing governed workflow result."""

    request_id: str
    api_version: str
    case_id: str
    research_use_only: bool = True
    runtime_status: dict[str, Any]
    events: list[WorkflowEvent]
    result: dict[str, Any]
    evidence_commission: dict[str, Any] | None = None
    rerun: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str
    api_version: str


class RuntimeStatusResponse(BaseModel):
    request_id: str
    api_version: str
    research_use_only: bool = True
    runtime_status: dict[str, Any]


HumanJudgmentPosition = Literal[
    "agree",
    "partially_agree",
    "disagree",
    "insufficient_context",
]
HumanJudgmentReason = Literal[
    "clinical_context_not_represented",
    "evidence_interpretation_differs",
    "patient_preference",
    "institutional_practice",
    "safety_concern",
    "other",
]
BoardDecisionOutcome = Literal[
    "endorsed_system_supported_option",
    "selected_alternative",
    "deferred_pending_information",
    "no_decision",
    "other",
]


class ClinicianJudgmentInput(BaseModel):
    """A human interpretation appended after the system synthesis."""

    model_config = ConfigDict(extra="forbid")

    position: HumanJudgmentPosition
    reason_codes: list[HumanJudgmentReason] = Field(default_factory=list)
    rationale: str = Field(default="", max_length=4000)
    attested: bool = False

    @model_validator(mode="after")
    def validate_judgment(self) -> "ClinicianJudgmentInput":
        if not self.attested:
            raise ValueError("Clinician attestation is required before recording judgment.")
        if self.position != "agree":
            if not self.reason_codes:
                raise ValueError("A reason code is required when the clinician does not fully agree.")
            if not self.rationale.strip():
                raise ValueError("A rationale is required when the clinician does not fully agree.")
        return self


class BoardDecisionInput(BaseModel):
    """The eventual board decision, or an explicit pending state."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["pending", "recorded"] = "pending"
    outcome: BoardDecisionOutcome | None = None
    decision: str = Field(default="", max_length=4000)
    rationale: str = Field(default="", max_length=4000)
    board_date: str | None = Field(default=None, max_length=32)
    attested: bool = False

    @model_validator(mode="after")
    def validate_recorded_decision(self) -> "BoardDecisionInput":
        if self.status == "recorded":
            if not self.outcome:
                raise ValueError("A board outcome is required when the decision is recorded.")
            if not self.decision.strip():
                raise ValueError("Board decision text is required when the decision is recorded.")
            if not self.rationale.strip():
                raise ValueError("A board rationale is required when the decision is recorded.")
            if not self.attested:
                raise ValueError("Board attestation is required when the decision is recorded.")
        return self


class HumanDecisionRecordRequest(BaseModel):
    """Validated three-layer handoff from system output to human decision."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1, max_length=128)
    case_type: str = Field(min_length=1, max_length=64)
    workflow_request_id: str = Field(min_length=1, max_length=128)
    system_decision: dict[str, Any]
    clinician_judgment: ClinicianJudgmentInput
    board_decision: BoardDecisionInput = Field(default_factory=BoardDecisionInput)


class HumanDecisionRecordResponse(BaseModel):
    """Stateless, auditable Phase 7 receipt. Persistence begins in Phase 8."""

    request_id: str
    api_version: str
    case_id: str
    case_type: str
    research_use_only: bool = True
    recorded_at: str
    decision_record_id: str
    workflow_request_id: str
    system_decision: dict[str, Any]
    clinician_judgment: ClinicianJudgmentInput
    board_decision: BoardDecisionInput
    decision_events: list[dict[str, Any]]
    persisted: Literal[False] = False


CaseVersionTrigger = Literal[
    "initial_board_review",
    "new_document",
    "new_result",
    "clinical_change",
    "evidence_update",
    "correction",
    "other",
]


class CaseVersionSaveRequest(BaseModel):
    """Complete governed snapshot saved as one immutable case version."""

    model_config = ConfigDict(extra="forbid")

    case: CancerTumorBoardCase
    raw_extraction: dict[str, Any] | None = None
    workflow: WorkflowRunResponse
    evidence_review: dict[str, Any]
    human_decision: HumanDecisionRecordResponse
    parent_version_id: str | None = Field(default=None, max_length=128)
    trigger: CaseVersionTrigger = "initial_board_review"
    change_summary: str = Field(min_length=3, max_length=1000)


class CaseVersionSummary(BaseModel):
    version_id: str
    case_id: str
    version_number: int = Field(ge=1)
    parent_version_id: str | None = None
    created_at: str
    trigger: CaseVersionTrigger
    change_summary: str
    content_hash: str
    workflow_request_id: str
    decision_record_id: str
    decision_state: str
    board_status: str


class CaseVersionDetail(CaseVersionSummary):
    case: dict[str, Any]
    raw_extraction: dict[str, Any] | None = None
    workflow: dict[str, Any]
    evidence_review: dict[str, Any]
    human_decision: dict[str, Any]


class CaseVersionSaveResponse(BaseModel):
    request_id: str
    api_version: str
    research_use_only: bool = True
    persisted: Literal[True] = True
    storage: Literal["sqlite", "postgresql"] = "sqlite"
    created: bool
    version: CaseVersionDetail


class CaseVersionListResponse(BaseModel):
    request_id: str
    api_version: str
    case_id: str
    research_use_only: bool = True
    versions: list[CaseVersionSummary]


class ProductCaseListResponse(BaseModel):
    request_id: str
    api_version: str
    research_use_only: bool = True
    cases: list[CaseVersionSummary]


class CaseVersionDetailResponse(BaseModel):
    request_id: str
    api_version: str
    research_use_only: bool = True
    version: CaseVersionDetail


class CaseUpdateAssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_version_id: str = Field(min_length=1, max_length=128)
    updated_case: CancerTumorBoardCase
    trigger: CaseVersionTrigger
    change_summary: str = Field(min_length=3, max_length=1000)
    attested: bool = False


class CaseUpdateAssessmentResponse(BaseModel):
    request_id: str
    api_version: str
    case_id: str
    research_use_only: bool = True
    base_version_id: str
    trigger: CaseVersionTrigger
    change_summary: str
    changed_paths: list[str]
    changed_roots: list[str]
    change_severity: str
    specialist_agents_to_rerun: list[str]
    specialist_agents_eligible_for_reuse: list[str]
    always_rerun_controls: list[str]
    evidence_review_required: bool
    prior_decision_status: Literal["historical_only"]
    explanation: str


class TargetedWorkflowRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_version_id: str = Field(min_length=1, max_length=128)
    case: CancerTumorBoardCase
    raw_extraction: dict[str, Any] | None = None
    evidence_commission: EvidenceCommissionInput
    trigger: CaseVersionTrigger
    change_summary: str = Field(min_length=3, max_length=1000)
    update_attested: bool = False


class WorkflowEvaluationRequest(BaseModel):
    """A workflow package evaluated against deterministic governance invariants."""

    model_config = ConfigDict(extra="forbid")

    workflow: WorkflowRunResponse
    case_type: str | None = Field(default=None, max_length=64)
    evidence_review: dict[str, Any] | None = None
    human_decision: dict[str, Any] | None = None


class EvaluationGate(BaseModel):
    gate_id: str
    category: str
    status: Literal["pass", "warning", "fail"]
    critical: bool
    detail: str


class WorkflowEvaluationResponse(BaseModel):
    request_id: str
    api_version: str
    research_use_only: bool = True
    evaluator_version: str
    evaluated_at: str
    status: Literal["pass", "warning", "fail"]
    release_eligible: bool
    scope: Literal["research_software_governance"]
    gates: list[EvaluationGate]
    metrics: dict[str, Any]
    limitations: str


class EvaluationMetricValue(BaseModel):
    metric_id: str
    label: str
    numerator: int
    denominator: int
    value: float | None
    target: float


class EvaluationGuardrailValue(BaseModel):
    metric_id: str
    label: str
    value: int
    target: int


class EvaluationSummaryResponse(BaseModel):
    request_id: str
    api_version: str
    research_use_only: bool = True
    generated_at: str
    scope: Literal["saved_research_case_versions"]
    versions_evaluated: int
    cases_evaluated: int
    current_state: Literal["baseline_pending", "pass", "action_required"]
    primary_metrics: list[EvaluationMetricValue]
    guardrails: list[EvaluationGuardrailValue]
    limitations: str


class ReleaseReadinessCheck(BaseModel):
    check_id: str
    category: str
    level: Literal["local_research", "production_research", "clinical_release"]
    status: Literal["ready", "blocked", "attention"]
    detail: str
    remediation: str


class ReleaseReadinessResponse(BaseModel):
    request_id: str
    api_version: str
    research_use_only: bool = True
    overall_state: Literal["production_research_ready", "production_research_blocked"]
    local_research_ready: bool
    production_research_ready: bool
    clinical_release_authorized: Literal[False] = False
    checks: list[ReleaseReadinessCheck]
    boundary: str
