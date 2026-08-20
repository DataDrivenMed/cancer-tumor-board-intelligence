from __future__ import annotations

import os
import re
from base64 import b64decode
from binascii import Error as Base64Error
from pathlib import Path
from typing import Callable
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from api.contracts import (
    CaseUpdateAssessmentRequest,
    CaseUpdateAssessmentResponse,
    CaseExtractionRequest,
    CaseExtractionResponse,
    CaseVersionDetail,
    CaseVersionDetailResponse,
    CaseVersionListResponse,
    CaseVersionSaveRequest,
    CaseVersionSaveResponse,
    CaseVersionSummary,
    ProductCaseListResponse,
    CommissionedWorkflowRunRequest,
    EvidenceCandidate,
    EvidenceCandidateRequest,
    EvidenceCandidateSetResponse,
    EvaluationSummaryResponse,
    HealthResponse,
    HumanDecisionRecordRequest,
    HumanDecisionRecordResponse,
    RuntimeStatusResponse,
    ReleaseReadinessResponse,
    SourceSegmentResponse,
    TargetedWorkflowRunRequest,
    WorkflowRunRequest,
    WorkflowRunResponse,
    WorkflowEvaluationRequest,
    WorkflowEvaluationResponse,
)
from agents.extraction_v25 import extract_case_v25
from api.events import workflow_events
from orchestration.context import WorkflowContext
from orchestration.workflow import run_workflow
from services.document_parser import parse_upload
from services.deidentification import screen_deidentified_text
from services.deployment_profile import allowed_case_types, synthetic_evaluation_enabled, validate_case_boundary
from services.evidence_commissioning_api import (
    build_commissioned_context,
    collect_commissioning_snapshot,
)
from services.human_decision import build_human_decision_receipt
from services.case_versions import (
    SQLiteCaseVersionStore,
    assess_case_update,
    case_version_store_from_environment,
    evidence_changed_agents,
)
from services.model_gateway import ModelGatewayError
from services.runtime_agents import build_workflow_context
from services.targeted_rerun import rehydrate_specialist_outputs
from services.audit import audit_event
from services.auth import AuthenticationError, authenticate_authorization_header
from services.release_readiness import release_readiness_snapshot
from services.workflow_evaluation import evaluate_workflow_package, summarize_workflow_evaluations


API_VERSION = "0.6.0"
SERVICE_NAME = "tumor-board-intelligence-api"
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_SUPPORTED_DOCUMENT_TYPES = {".pdf", ".docx", ".txt", ".md"}
_MAX_DOCUMENT_BYTES = 8 * 1024 * 1024
_DEFAULT_MAX_REQUEST_BYTES = 16 * 1024 * 1024


def _allowed_origins() -> list[str]:
    configured = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return ["http://localhost:3000", "http://127.0.0.1:3000"]


def _allowed_hosts() -> list[str]:
    configured = os.getenv("TRUSTED_HOSTS", "").strip()
    if configured:
        return [host.strip() for host in configured.split(",") if host.strip()]
    return ["localhost", "127.0.0.1", "testserver"]


def _enabled(name: str, *, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _max_request_bytes() -> int:
    try:
        configured = int(os.getenv("MAX_REQUEST_BYTES", str(_DEFAULT_MAX_REQUEST_BYTES)))
    except ValueError:
        return _DEFAULT_MAX_REQUEST_BYTES
    return min(max(configured, 1024), 64 * 1024 * 1024)


def get_workflow_context() -> WorkflowContext:
    """Create isolated governed dependencies for exactly one HTTP request."""

    return build_workflow_context()


def get_extraction_runner() -> Callable:
    """Return the configured extraction implementation for this request."""

    return extract_case_v25


def get_evidence_collector() -> Callable:
    """Return the request-scoped evidence candidate collector."""

    return collect_commissioning_snapshot


def get_case_version_store() -> SQLiteCaseVersionStore:
    """Open the configured tenant-aware case-version repository."""

    return case_version_store_from_environment()


def _request_id(request: Request) -> str:
    value = getattr(request.state, "request_id", "")
    return value if value else uuid4().hex


def _enforce_case_boundary(case) -> None:
    try:
        validate_case_boundary(case)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


def _principal(request: Request):
    principal = getattr(request.state, "principal", None)
    if principal is None:
        return authenticate_authorization_header(request.headers.get("Authorization"))
    return principal


def create_app() -> FastAPI:
    deployment_environment = os.getenv("DEPLOYMENT_ENV", "local").strip().lower()
    docs_enabled = _enabled("ENABLE_API_DOCS", default=deployment_environment != "production")
    application = FastAPI(
        title="Cancer Tumor Board Intelligence API",
        version=API_VERSION,
        description=(
            "Research decision-support API for synthetic or fully de-identified oncology cases. "
            "It is not validated for autonomous or unsupervised patient care."
        ),
        docs_url="/docs" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
        redoc_url=None,
    )
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=_allowed_hosts())
    application.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    @application.middleware("http")
    async def apply_http_boundaries(request: Request, call_next):
        def harden(response):
            response.headers["X-Request-ID"] = request.state.request_id
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
            response.headers["Cross-Origin-Resource-Policy"] = "same-site"
            response.headers["Cache-Control"] = "no-store"
            if request.url.path in {"/health", "/ready"} or request.url.path.startswith("/api/"):
                response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
            if _enabled("REQUIRE_HTTPS"):
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            return response

        supplied = request.headers.get("X-Request-ID", "").strip()
        request.state.request_id = supplied if _REQUEST_ID.fullmatch(supplied) else uuid4().hex
        public_paths = {"/health", "/api/v1/release/readiness"}
        if request.url.path.startswith("/api/") and request.url.path not in public_paths:
            try:
                request.state.principal = authenticate_authorization_header(
                    request.headers.get("Authorization")
                )
            except AuthenticationError as exc:
                response = JSONResponse(status_code=401, content={"detail": str(exc)})
                response.headers["WWW-Authenticate"] = "Bearer"
                return harden(response)
        else:
            request.state.principal = None
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                too_large = int(content_length) > _max_request_bytes()
            except ValueError:
                return harden(JSONResponse(status_code=400, content={"detail": "Content-Length must be an integer."}))
            if too_large:
                response = JSONResponse(
                    status_code=413,
                    content={"detail": "Request body exceeds the configured service limit."},
                )
            else:
                response = await call_next(request)
        else:
            response = await call_next(request)
        return harden(response)

    @application.get("/health", response_model=HealthResponse, tags=["service"])
    def health() -> HealthResponse:
        return HealthResponse(service=SERVICE_NAME, api_version=API_VERSION)

    @application.get("/ready", response_model=HealthResponse, tags=["service"])
    def ready(
        store: SQLiteCaseVersionStore = Depends(get_case_version_store),
    ) -> HealthResponse:
        """Confirm that the service and configured durable case store are reachable."""

        try:
            store.list_cases(organization_id="__readiness__")
        except Exception as exc:
            raise HTTPException(status_code=503, detail="The durable case store is unavailable.") from exc
        return HealthResponse(service=SERVICE_NAME, api_version=API_VERSION)

    @application.get(
        "/api/v1/runtime/status",
        response_model=RuntimeStatusResponse,
        tags=["service"],
    )
    def runtime_status(
        request: Request,
        context: WorkflowContext = Depends(get_workflow_context),
    ) -> RuntimeStatusResponse:
        return RuntimeStatusResponse(
            request_id=_request_id(request),
            api_version=API_VERSION,
            runtime_status=context.status_snapshot(),
        )

    @application.post(
        "/api/v1/cases/extract",
        response_model=CaseExtractionResponse,
        tags=["intake"],
    )
    def extract_case_document(
        payload: CaseExtractionRequest,
        request: Request,
        runner: Callable = Depends(get_extraction_runner),
    ) -> CaseExtractionResponse:
        """Parse and extract one transient synthetic or de-identified source document."""

        if synthetic_evaluation_enabled():
            raise HTTPException(
                status_code=403,
                detail=(
                    "Document upload is disabled in the synthetic evaluation. "
                    "Use the bundled guided AML source packet."
                ),
            )

        suffix = Path(payload.document.filename).suffix.lower()
        if suffix not in _SUPPORTED_DOCUMENT_TYPES:
            raise HTTPException(
                status_code=422,
                detail="Supported document types are PDF, DOCX, TXT, and Markdown.",
            )

        try:
            document_bytes = b64decode(payload.document.content_base64, validate=True)
        except (Base64Error, ValueError):
            raise HTTPException(status_code=422, detail="Document content is not valid base64.") from None

        if len(document_bytes) > _MAX_DOCUMENT_BYTES:
            raise HTTPException(status_code=413, detail="Document exceeds the 8 MB local intake limit.")

        try:
            parsed = parse_upload(
                payload.document.filename,
                document_bytes,
                document_id=payload.document.document_id,
            )
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        if not parsed.segments:
            raise HTTPException(status_code=422, detail="The document contains no extractable text.")

        deidentification_screen = screen_deidentified_text(
            [payload.document.filename, *(segment.text for segment in parsed.segments)]
        )
        if payload.case_type == "deidentified_research" and deidentification_screen["status"] == "blocked":
            categories = sorted({item["category"] for item in deidentification_screen["findings"]})
            raise HTTPException(
                status_code=422,
                detail=(
                    "Possible identifiers remain in the uploaded document: "
                    f"{', '.join(categories)}. Remove them at the source and upload the revised document."
                ),
            )

        token = os.getenv("MODEL_AUTH_TOKEN") or os.getenv("HF_TOKEN") or ""
        base_url = os.getenv("MODEL_BASE_URL", "").strip()
        if not token and not base_url:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Live extraction is not configured. Set MODEL_AUTH_TOKEN or configure a local "
                    "MODEL_BASE_URL, then retry."
                ),
            )

        model = os.getenv("MODEL_NAME", "openai/gpt-oss-120b:fireworks-ai")
        try:
            package = runner(
                document=parsed,
                api_key=token,
                model=model,
                case_id=payload.case_id,
            )
        except ModelGatewayError as exc:
            raise HTTPException(status_code=503, detail=f"Live extraction could not complete: {exc}") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        case = package.case.model_copy(
            update={"case_id": payload.case_id, "case_type": payload.case_type},
            deep=True,
        )
        return CaseExtractionResponse(
            request_id=_request_id(request),
            api_version=API_VERSION,
            extraction_version=package.extraction_version,
            case=case,
            raw_extraction=package.raw_extraction,
            source_segments=[
                SourceSegmentResponse(
                    segment_id=segment.segment_id,
                    text=segment.text,
                    page=segment.page,
                    paragraph=segment.paragraph,
                )
                for segment in parsed.segments
            ],
            provenance_total=package.provenance_total,
            provenance_verified=package.provenance_verified,
            provenance_failures=package.provenance_failures,
            warnings=package.warnings,
            normalization_events=package.normalization_events,
            diagnostic_certainty=package.diagnostic_certainty,
            deidentification_screen=deidentification_screen,
        )

    @application.post(
        "/api/v1/workflows/run",
        response_model=WorkflowRunResponse,
        tags=["workflow"],
    )
    def execute_workflow(
        payload: WorkflowRunRequest,
        request: Request,
        context: WorkflowContext = Depends(get_workflow_context),
    ) -> WorkflowRunResponse:
        _enforce_case_boundary(payload.case)

        request_id = _request_id(request)
        result = run_workflow(
            payload.case,
            raw_extraction=payload.raw_extraction,
            context=context,
        )
        encoded_result = jsonable_encoder(result)
        return WorkflowRunResponse(
            request_id=request_id,
            api_version=API_VERSION,
            case_id=payload.case.case_id,
            runtime_status=context.status_snapshot(),
            events=workflow_events(encoded_result.get("audit_events", []), request_id=request_id),
            result=encoded_result,
        )

    @application.post(
        "/api/v1/evidence/candidates",
        response_model=EvidenceCandidateSetResponse,
        tags=["evidence"],
    )
    def evidence_candidates(
        payload: EvidenceCandidateRequest,
        request: Request,
        collector: Callable = Depends(get_evidence_collector),
    ) -> EvidenceCandidateSetResponse:
        _enforce_case_boundary(payload.case)
        snapshot = collector(payload.case, mode=payload.mode)
        return EvidenceCandidateSetResponse(
            request_id=_request_id(request),
            api_version=API_VERSION,
            case_id=payload.case.case_id,
            mode=payload.mode,
            candidate_set_id=snapshot.candidate_set_id,
            candidates=[EvidenceCandidate.model_validate(candidate) for candidate in snapshot.candidates],
            downstream_channels=[
                {
                    "channel": "literature",
                    "mode": "retrieval_then_independent_verification",
                    "manual_commissioning": False,
                    "boundary": "Discovery does not establish applicability.",
                },
                {
                    "channel": "clinical_trials",
                    "mode": "official_registry_discovery",
                    "manual_commissioning": False,
                    "boundary": "Possible matching does not establish eligibility.",
                },
                {
                    "channel": "translational",
                    "mode": "governed_store",
                    "manual_commissioning": False,
                    "boundary": "Mechanistic evidence cannot independently support clinical action.",
                },
            ],
            warnings=list(snapshot.warnings),
        )

    @application.post(
        "/api/v1/workflows/run-commissioned",
        response_model=WorkflowRunResponse,
        tags=["workflow", "evidence"],
    )
    def execute_commissioned_workflow(
        payload: CommissionedWorkflowRunRequest,
        request: Request,
        collector: Callable = Depends(get_evidence_collector),
    ) -> WorkflowRunResponse:
        _enforce_case_boundary(payload.case)
        snapshot = collector(payload.case, mode=payload.evidence_commission.mode)
        try:
            context, receipt = build_commissioned_context(
                snapshot,
                candidate_set_id=payload.evidence_commission.candidate_set_id,
                decisions=[decision.model_dump() for decision in payload.evidence_commission.decisions],
                attested=payload.evidence_commission.attested,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        request_id = _request_id(request)
        result = run_workflow(
            payload.case,
            raw_extraction=payload.raw_extraction,
            context=context,
        )
        encoded_result = jsonable_encoder(result)
        return WorkflowRunResponse(
            request_id=request_id,
            api_version=API_VERSION,
            case_id=payload.case.case_id,
            runtime_status=context.status_snapshot(),
            events=workflow_events(encoded_result.get("audit_events", []), request_id=request_id),
            result=encoded_result,
            evidence_commission=receipt,
        )

    @application.post(
        "/api/v1/decisions/record",
        response_model=HumanDecisionRecordResponse,
        tags=["brief", "human-decision"],
    )
    def record_human_decision(
        payload: HumanDecisionRecordRequest,
        request: Request,
    ) -> HumanDecisionRecordResponse:
        """Validate and return a stateless human decision receipt.

        This endpoint never rewrites the supplied system synthesis. Durable case
        versions and later amendments are intentionally reserved for Phase 8.
        """

        if payload.case_type not in allowed_case_types():
            raise HTTPException(
                status_code=403,
                detail=(
                    "Decision capture is limited to the synthetic teaching case in this evaluation."
                    if synthetic_evaluation_enabled()
                    else "Decision capture accepts only synthetic or fully de-identified research cases."
                ),
            )
        if synthetic_evaluation_enabled() and payload.case_id != "TBI-AML-042":
            raise HTTPException(
                status_code=403,
                detail="Decision capture is limited to the bundled AML teaching case.",
            )
        receipt = build_human_decision_receipt(payload)
        return HumanDecisionRecordResponse(
            request_id=_request_id(request),
            api_version=API_VERSION,
            case_id=payload.case_id,
            case_type=payload.case_type,
            **receipt,
        )

    @application.post(
        "/api/v1/cases/versions",
        response_model=CaseVersionSaveResponse,
        tags=["versions"],
    )
    def save_case_version(
        payload: CaseVersionSaveRequest,
        request: Request,
        store: SQLiteCaseVersionStore = Depends(get_case_version_store),
    ) -> CaseVersionSaveResponse:
        _enforce_case_boundary(payload.case)
        try:
            version, created = store.save_version(
                case=jsonable_encoder(payload.case),
                raw_extraction=payload.raw_extraction,
                workflow=payload.workflow.model_dump(),
                evidence_review=payload.evidence_review,
                human_decision=payload.human_decision.model_dump(),
                parent_version_id=payload.parent_version_id,
                trigger=payload.trigger,
                change_summary=payload.change_summary,
                organization_id=_principal(request).organization_id,
                created_by=_principal(request).user_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return CaseVersionSaveResponse(
            request_id=_request_id(request),
            api_version=API_VERSION,
            storage="postgresql" if os.getenv("DATABASE_URL", "").strip() else "sqlite",
            created=created,
            version=CaseVersionDetail.model_validate(version),
        )

    @application.get(
        "/api/v1/cases/{case_id}/versions",
        response_model=CaseVersionListResponse,
        tags=["versions"],
    )
    def list_case_versions(
        case_id: str,
        request: Request,
        store: SQLiteCaseVersionStore = Depends(get_case_version_store),
    ) -> CaseVersionListResponse:
        return CaseVersionListResponse(
            request_id=_request_id(request),
            api_version=API_VERSION,
            case_id=case_id,
            versions=[
                CaseVersionSummary.model_validate(item)
                for item in store.list_versions(
                    case_id,
                    organization_id=_principal(request).organization_id,
                )
            ],
        )

    @application.get(
        "/api/v1/cases/{case_id}/versions/{version_id}",
        response_model=CaseVersionDetailResponse,
        tags=["versions"],
    )
    def get_case_version(
        case_id: str,
        version_id: str,
        request: Request,
        store: SQLiteCaseVersionStore = Depends(get_case_version_store),
    ) -> CaseVersionDetailResponse:
        version = store.get_version(
            version_id,
            case_id=case_id,
            organization_id=_principal(request).organization_id,
        )
        if not version:
            raise HTTPException(status_code=404, detail="The requested case version was not found.")
        return CaseVersionDetailResponse(
            request_id=_request_id(request),
            api_version=API_VERSION,
            version=CaseVersionDetail.model_validate(version),
        )

    @application.post(
        "/api/v1/case-version-updates/assess",
        response_model=CaseUpdateAssessmentResponse,
        tags=["versions", "workflow"],
    )
    def assess_version_update(
        payload: CaseUpdateAssessmentRequest,
        request: Request,
        store: SQLiteCaseVersionStore = Depends(get_case_version_store),
    ) -> CaseUpdateAssessmentResponse:
        if not payload.attested:
            raise HTTPException(status_code=409, detail="Human update attestation is required before impact assessment.")
        base = store.get_version(
            payload.base_version_id,
            organization_id=_principal(request).organization_id,
        )
        if not base:
            raise HTTPException(status_code=404, detail="The selected base version was not found.")
        _enforce_case_boundary(payload.updated_case)
        try:
            assessment = assess_case_update(base["case"], jsonable_encoder(payload.updated_case))
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return CaseUpdateAssessmentResponse(
            request_id=_request_id(request),
            api_version=API_VERSION,
            case_id=payload.updated_case.case_id,
            base_version_id=payload.base_version_id,
            trigger=payload.trigger,
            change_summary=payload.change_summary,
            **assessment,
        )

    @application.post(
        "/api/v1/workflows/rerun-targeted",
        response_model=WorkflowRunResponse,
        tags=["versions", "workflow", "evidence"],
    )
    def execute_targeted_rerun(
        payload: TargetedWorkflowRunRequest,
        request: Request,
        collector: Callable = Depends(get_evidence_collector),
        store: SQLiteCaseVersionStore = Depends(get_case_version_store),
    ) -> WorkflowRunResponse:
        if not payload.update_attested:
            raise HTTPException(status_code=409, detail="Human update attestation is required before a targeted rerun.")
        _enforce_case_boundary(payload.case)
        base = store.get_version(
            payload.base_version_id,
            case_id=payload.case.case_id,
            organization_id=_principal(request).organization_id,
        )
        if not base:
            raise HTTPException(status_code=404, detail="The selected base version was not found for this case.")
        try:
            assessment = assess_case_update(base["case"], jsonable_encoder(payload.case))
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        snapshot = collector(payload.case, mode=payload.evidence_commission.mode)
        try:
            context, evidence_receipt = build_commissioned_context(
                snapshot,
                candidate_set_id=payload.evidence_commission.candidate_set_id,
                decisions=[decision.model_dump() for decision in payload.evidence_commission.decisions],
                attested=payload.evidence_commission.attested,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        rerun_agents = set(assessment["specialist_agents_to_rerun"])
        rerun_agents.update(
            evidence_changed_agents(
                base.get("evidence_review") or {},
                [decision.model_dump() for decision in payload.evidence_commission.decisions],
            )
        )
        prior_outputs = rehydrate_specialist_outputs(
            ((base.get("workflow") or {}).get("result") or {}).get("specialist_outputs")
        )
        result = run_workflow(
            payload.case,
            raw_extraction=payload.raw_extraction,
            context=context,
            reuse_specialist_outputs=prior_outputs,
            rerun_agents=rerun_agents,
        )
        result["audit_events"].insert(
            1,
            audit_event(
                "targeted_rerun_started",
                f"base_version={payload.base_version_id}; changed={','.join(assessment['changed_roots'])}",
            ),
        )
        encoded_result = jsonable_encoder(result)
        routed = encoded_result.get("routing") or {}
        selected_agents = set(routed.get("selected_agents") or [])
        reused_agents = sorted(selected_agents.intersection(prior_outputs) - rerun_agents)
        executed_agents = sorted(selected_agents - set(reused_agents))
        request_id = _request_id(request)
        return WorkflowRunResponse(
            request_id=request_id,
            api_version=API_VERSION,
            case_id=payload.case.case_id,
            runtime_status=context.status_snapshot(),
            events=workflow_events(encoded_result.get("audit_events", []), request_id=request_id),
            result=encoded_result,
            evidence_commission=evidence_receipt,
            rerun={
                "base_version_id": payload.base_version_id,
                "trigger": payload.trigger,
                "change_summary": payload.change_summary,
                "changed_paths": assessment["changed_paths"],
                "always_rerun_controls": assessment["always_rerun_controls"],
                "specialist_agents_executed": executed_agents,
                "specialist_agents_reused": reused_agents,
                "prior_decision_status": "historical_only",
            },
        )

    @application.post(
        "/api/v1/evaluations/workflow",
        response_model=WorkflowEvaluationResponse,
        tags=["evaluation"],
    )
    def evaluate_workflow(
        payload: WorkflowEvaluationRequest,
        request: Request,
    ) -> WorkflowEvaluationResponse:
        evaluation = evaluate_workflow_package(
            payload.workflow.model_dump(),
            case_type=payload.case_type,
            evidence_review=payload.evidence_review,
            human_decision=payload.human_decision,
        )
        return WorkflowEvaluationResponse(
            request_id=_request_id(request),
            api_version=API_VERSION,
            **evaluation,
        )

    @application.get(
        "/api/v1/evaluations/summary",
        response_model=EvaluationSummaryResponse,
        tags=["evaluation"],
    )
    def evaluation_summary(
        request: Request,
        store: SQLiteCaseVersionStore = Depends(get_case_version_store),
    ) -> EvaluationSummaryResponse:
        summary = summarize_workflow_evaluations(
            store.list_all_versions(organization_id=_principal(request).organization_id)
        )
        return EvaluationSummaryResponse(
            request_id=_request_id(request),
            api_version=API_VERSION,
            **summary,
        )

    @application.get(
        "/api/v1/release/readiness",
        response_model=ReleaseReadinessResponse,
        tags=["service", "release"],
    )
    def release_readiness(request: Request) -> ReleaseReadinessResponse:
        return ReleaseReadinessResponse(
            request_id=_request_id(request),
            api_version=API_VERSION,
            **release_readiness_snapshot(),
        )

    @application.get(
        "/api/v1/product/cases",
        response_model=ProductCaseListResponse,
        tags=["product", "versions"],
    )
    def product_cases(
        request: Request,
        store: SQLiteCaseVersionStore = Depends(get_case_version_store),
    ) -> ProductCaseListResponse:
        return ProductCaseListResponse(
            request_id=_request_id(request),
            api_version=API_VERSION,
            cases=[
                CaseVersionSummary.model_validate(item)
                for item in store.list_cases(
                    organization_id=_principal(request).organization_id
                )
            ],
        )

    return application


app = create_app()
