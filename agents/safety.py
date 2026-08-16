from __future__ import annotations

from schemas.case import CancerTumorBoardCase, DataStatus
from schemas.safety import (
    SafetyEvidenceRecord,
    SafetyEvidenceStore,
    SafetyFinding,
    SafetyReport,
    SafetySeverity,
)


AGENT_ID = "safety"
AGENT_VERSION = "1.0.0"


def _norm(value: object | None) -> str:
    return " ".join(str(value or "").lower().replace("_", " ").replace("-", " ").split())


def _therapy_text(case: CancerTumorBoardCase) -> str:
    parts: list[str] = []
    for episode in case.treatments:
        parts.extend([episode.regimen, *episode.agents])
    for fact in case.current_medications:
        if fact.status == DataStatus.CONFIRMED:
            parts.extend([fact.field, str(fact.value or "")])
    return _norm(" ".join(parts))


def _patient_context_text(case: CancerTumorBoardCase) -> str:
    parts: list[str] = []
    collections = [
        case.comorbidities,
        case.toxicities,
        case.labs,
        case.imaging,
        case.pathology,
        case.current_medications,
    ]
    for collection in collections:
        for fact in collection:
            if fact.status == DataStatus.CONFIRMED:
                parts.extend([fact.field, str(fact.value or "")])
    if case.performance_status is not None and case.performance_status.status == DataStatus.CONFIRMED:
        parts.extend([case.performance_status.field, str(case.performance_status.value or "")])
    return _norm(" ".join(parts))


def _record_matches(case: CancerTumorBoardCase, record: SafetyEvidenceRecord) -> tuple[bool, list[str], list[str]]:
    if not record.source_verified or not record.human_verified:
        return False, [], []

    therapy_text = _therapy_text(case)
    therapy_matches = [term for term in record.therapy_terms if _norm(term) and _norm(term) in therapy_text]
    if record.therapy_terms and not therapy_matches:
        return False, [], []

    diagnosis = _norm(case.diagnosis.value)
    if record.disease_terms and not any(_norm(term) in diagnosis or diagnosis in _norm(term) for term in record.disease_terms if _norm(term)):
        return False, [], []

    context = _patient_context_text(case)
    trigger_matches = [term for term in record.trigger_terms if _norm(term) and _norm(term) in context]
    if record.trigger_terms and not trigger_matches:
        return False, [], []

    return True, therapy_matches, trigger_matches


def _parameter_is_represented(case: CancerTumorBoardCase, parameter: str) -> bool:
    needle = _norm(parameter)
    if not needle:
        return False
    facts = [
        *case.labs,
        *case.imaging,
        *case.pathology,
        *case.comorbidities,
        *case.toxicities,
    ]
    for fact in facts:
        if fact.status != DataStatus.CONFIRMED:
            continue
        if needle in _norm(fact.field) or needle in _norm(fact.value):
            return True
    return False


class SafetyAgent:
    """Evidence-bounded safety specialist.

    Version 1 is deterministic. It matches represented therapies and patient-context
    triggers to pre-verified safety evidence. It never infers a contraindication,
    interaction, dose adjustment, or monitoring requirement from model memory.
    """

    agent_id = AGENT_ID
    agent_version = AGENT_VERSION

    def __init__(self, store: SafetyEvidenceStore | None = None, *, production_mode: bool = True) -> None:
        self.store = store or SafetyEvidenceStore()
        self.production_mode = production_mode

    def run(self, case: CancerTumorBoardCase) -> SafetyReport:
        if case.disease_program != "hematologic_malignancy":
            return SafetyReport(
                case_id=case.case_id,
                status="abstain_domain",
                summary="Safety Agent v1 is restricted to hematologic malignancy tumor-board cases.",
                limitations=["Case is outside the v1 hematologic-malignancy domain."],
            )

        usable = [
            record for record in self.store.records
            if record.source_verified and record.human_verified and not (self.production_mode and record.synthetic)
        ]
        if not usable:
            return SafetyReport(
                case_id=case.case_id,
                status="source_unavailable",
                summary="No verified production safety evidence records are available.",
                limitations=[
                    "The agent will not infer contraindications, interactions, toxicities, or monitoring requirements from model memory.",
                    "Absence of a matched safety record must not be interpreted as absence of risk.",
                ],
            )

        findings: list[SafetyFinding] = []
        for record in usable:
            matched, therapy_matches, trigger_matches = _record_matches(case, record)
            if not matched:
                continue
            unresolved = [p for p in record.required_parameters if not _parameter_is_represented(case, p)]
            blocking = bool(record.contraindication) or bool(
                unresolved and record.severity in {SafetySeverity.HIGH, SafetySeverity.CRITICAL}
            )
            findings.append(
                SafetyFinding(
                    evidence_id=record.evidence_id,
                    evidence_type=record.evidence_type,
                    severity=record.severity,
                    therapy_terms_matched=sorted(therapy_matches),
                    trigger_terms_matched=sorted(trigger_matches),
                    safety_issue=record.safety_issue,
                    source_title=record.source_title,
                    source_locator=record.source_locator,
                    source_excerpt=record.source_excerpt,
                    required_parameters=list(record.required_parameters),
                    unresolved_parameters=sorted(unresolved),
                    contraindication=record.contraindication,
                    recommendation_blocking=blocking,
                )
            )

        findings.sort(key=lambda f: (f.evidence_id, f.safety_issue))
        if not findings:
            return SafetyReport(
                case_id=case.case_id,
                status="no_evidence_found",
                summary="No verified safety record matched the represented therapies and patient context.",
                limitations=["No match does not establish that the therapy is safe or free of contraindications."],
            )

        blocking = any(f.recommendation_blocking for f in findings)
        unresolved = any(f.unresolved_parameters for f in findings)
        status = "completed_with_limitations" if unresolved else "completed"
        warnings = []
        if blocking:
            warnings.append("At least one matched safety finding is recommendation-blocking pending human review or resolution.")

        return SafetyReport(
            case_id=case.case_id,
            status=status,
            findings=findings,
            warnings=warnings,
            limitations=[
                "Safety matching does not replace prescribing information, pharmacy review, organ-function assessment, or clinician judgment.",
                "A matched warning is not itself a treatment recommendation; a non-match is not evidence of safety.",
            ],
            summary=f"Matched {len(findings)} verified safety evidence record(s) to represented case concepts.",
            can_support_safety_claim=True,
            recommendation_blocking=blocking,
        )
