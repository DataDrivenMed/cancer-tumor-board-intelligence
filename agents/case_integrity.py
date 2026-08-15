from __future__ import annotations

from collections import Counter
from datetime import date
from hashlib import sha1

from schemas.case import CancerTumorBoardCase, DataStatus, InformationType, TreatmentStatus
from schemas.integrity import (
    CaseIntegrityReport,
    IntegrityCheckResult,
    IntegrityDisposition,
    IntegrityFinding,
    IntegritySeverity,
)


AGENT_ID = "case_integrity"
AGENT_VERSION = "1.0.0"
CHECK_VERSION = "1.0.0"


def _fid(code: str, field_path: str, message: str) -> str:
    raw = f"{code}|{field_path}|{message}".encode("utf-8")
    return f"INT-{sha1(raw).hexdigest()[:12]}"


def _segments_from_provenance(items) -> list[str]:
    out: list[str] = []
    for p in items or []:
        out.extend(p.source_segment_ids)
    return sorted(set(out))


def _finding(*, code: str, severity: IntegritySeverity, category: str, field_path: str, message: str,
             recommendation_blocking: bool = False, source_segment_ids: list[str] | None = None) -> IntegrityFinding:
    return IntegrityFinding(
        finding_id=_fid(code, field_path, message),
        code=code,
        severity=severity,
        category=category,
        field_path=field_path,
        message=message,
        recommendation_blocking=recommendation_blocking,
        source_segment_ids=source_segment_ids or [],
    )


def _all_fact_paths(case: CancerTumorBoardCase):
    yield "diagnosis", case.diagnosis
    yield "disease_state", case.disease_state
    if case.performance_status is not None:
        yield "performance_status", case.performance_status
    for name in ("pathology", "imaging", "labs", "comorbidities", "toxicities", "transplant_cellular_therapy", "current_medications"):
        for idx, fact in enumerate(getattr(case, name)):
            yield f"{name}[{idx}]", fact


def _requires_provenance(fact) -> bool:
    if fact.information_type != InformationType.OBSERVED:
        return False
    if fact.status in {
        DataStatus.UNKNOWN,
        DataStatus.NOT_DOCUMENTED,
        DataStatus.NOT_ASSESSED,
        DataStatus.NOT_APPLICABLE,
        DataStatus.UNAVAILABLE,
    } and fact.value is None:
        return False
    return fact.value is not None or fact.status in {DataStatus.CONFIRMED, DataStatus.PENDING, DataStatus.CONFLICTING}


def _check_provenance(case: CancerTumorBoardCase) -> IntegrityCheckResult:
    findings: list[IntegrityFinding] = []
    for path, fact in _all_fact_paths(case):
        if not _requires_provenance(fact):
            continue
        if not fact.provenance:
            findings.append(_finding(
                code="OBSERVED_FACT_NO_PROVENANCE",
                severity=IntegritySeverity.CRITICAL,
                category="provenance",
                field_path=path,
                message="Observed substantive fact has no provenance object.",
                recommendation_blocking=True,
            ))
            continue
        if not any(p.source_verified for p in fact.provenance):
            findings.append(_finding(
                code="OBSERVED_FACT_UNVERIFIED_PROVENANCE",
                severity=IntegritySeverity.CRITICAL,
                category="provenance",
                field_path=path,
                message="Observed substantive fact lacks verified source provenance.",
                recommendation_blocking=True,
                source_segment_ids=_segments_from_provenance(fact.provenance),
            ))

    for idx, item in enumerate(case.molecular_findings):
        path = f"molecular_findings[{idx}]"
        if not item.provenance or not any(p.source_verified for p in item.provenance):
            findings.append(_finding(
                code="MOLECULAR_FINDING_UNVERIFIED_PROVENANCE",
                severity=IntegritySeverity.CRITICAL,
                category="provenance",
                field_path=path,
                message="Molecular finding lacks verified source provenance.",
                recommendation_blocking=True,
                source_segment_ids=_segments_from_provenance(item.provenance),
            ))

    for idx, item in enumerate(case.treatments):
        path = f"treatments[{idx}]"
        if not item.provenance or not any(p.source_verified for p in item.provenance):
            findings.append(_finding(
                code="TREATMENT_UNVERIFIED_PROVENANCE",
                severity=IntegritySeverity.CRITICAL,
                category="provenance",
                field_path=path,
                message="Treatment episode lacks verified source provenance.",
                recommendation_blocking=True,
                source_segment_ids=_segments_from_provenance(item.provenance),
            ))
    return IntegrityCheckResult(check_id="verified_provenance", check_version=CHECK_VERSION, passed=not findings, findings=findings)


def _check_conflicts(case: CancerTumorBoardCase) -> IntegrityCheckResult:
    findings: list[IntegrityFinding] = []
    for idx, conflict in enumerate(case.conflicts):
        if conflict.resolution_status != "unresolved":
            continue
        blocking = conflict.severity in {"high", "critical"}
        severity = IntegritySeverity.CRITICAL if conflict.severity == "critical" else (
            IntegritySeverity.MAJOR if conflict.severity == "high" else IntegritySeverity.WARNING
        )
        findings.append(_finding(
            code="UNRESOLVED_SOURCE_CONFLICT",
            severity=severity,
            category="conflict",
            field_path=f"conflicts[{idx}].{conflict.field}",
            message=f"Unresolved conflict: {conflict.value_a!r} versus {conflict.value_b!r}.",
            recommendation_blocking=blocking,
            source_segment_ids=sorted(set(conflict.source_segment_ids)),
        ))
    return IntegrityCheckResult(check_id="unresolved_conflicts", check_version=CHECK_VERSION, passed=not findings, findings=findings)


def _check_missing_information(case: CancerTumorBoardCase) -> IntegrityCheckResult:
    findings: list[IntegrityFinding] = []
    for idx, item in enumerate(case.missing_items):
        if not item.recommendation_blocking:
            continue
        severity = IntegritySeverity.CRITICAL if item.importance == "critical" else IntegritySeverity.MAJOR
        findings.append(_finding(
            code="RECOMMENDATION_BLOCKING_INFORMATION_MISSING",
            severity=severity,
            category="missing_information",
            field_path=f"missing_items[{idx}].{item.field}",
            message=f"Decision-critical information is unresolved: {item.reason}",
            recommendation_blocking=True,
        ))
    return IntegrityCheckResult(check_id="blocking_missing_information", check_version=CHECK_VERSION, passed=not findings, findings=findings)


def _diagnostic_certainty(case: CancerTumorBoardCase) -> str:
    status = case.diagnosis.status
    if status == DataStatus.CONFIRMED:
        return "confirmed"
    if status in {DataStatus.PENDING, DataStatus.UNKNOWN, DataStatus.NOT_DOCUMENTED, DataStatus.CONFLICTING}:
        return "unconfirmed"
    return "unknown"


def _check_diagnostic_state(case: CancerTumorBoardCase) -> IntegrityCheckResult:
    findings: list[IntegrityFinding] = []
    certainty = _diagnostic_certainty(case)
    if certainty != "confirmed" and case.disease_state.status == DataStatus.CONFIRMED and case.disease_state.value is not None:
        findings.append(_finding(
            code="CONFIRMED_DISEASE_STATE_WITH_UNCONFIRMED_DIAGNOSIS",
            severity=IntegritySeverity.CRITICAL,
            category="diagnostic_certainty",
            field_path="disease_state",
            message="Disease state is confirmed while the underlying diagnosis is not confirmed.",
            recommendation_blocking=True,
            source_segment_ids=_segments_from_provenance(case.disease_state.provenance),
        ))
    return IntegrityCheckResult(check_id="diagnosis_disease_state_invariant", check_version=CHECK_VERSION, passed=not findings, findings=findings)


def _check_treatment_identity(case: CancerTumorBoardCase) -> IntegrityCheckResult:
    findings: list[IntegrityFinding] = []
    ids = [t.episode_id for t in case.treatments]
    for episode_id, count in Counter(ids).items():
        if count > 1:
            findings.append(_finding(
                code="DUPLICATE_TREATMENT_EPISODE_ID",
                severity=IntegritySeverity.MAJOR,
                category="treatment",
                field_path="treatments",
                message=f"Treatment episode_id {episode_id!r} appears {count} times.",
                recommendation_blocking=True,
            ))
    return IntegrityCheckResult(check_id="treatment_identity", check_version=CHECK_VERSION, passed=not findings, findings=findings)


def _check_treatment_temporality(case: CancerTumorBoardCase) -> IntegrityCheckResult:
    findings: list[IntegrityFinding] = []
    for idx, tx in enumerate(case.treatments):
        if tx.start_date and tx.end_date and tx.end_date < tx.start_date:
            findings.append(_finding(
                code="TREATMENT_END_BEFORE_START",
                severity=IntegritySeverity.CRITICAL,
                category="temporal_consistency",
                field_path=f"treatments[{idx}]",
                message=f"Treatment end date {tx.end_date.isoformat()} precedes start date {tx.start_date.isoformat()}.",
                recommendation_blocking=True,
                source_segment_ids=_segments_from_provenance(tx.provenance),
            ))
        if tx.treatment_status == TreatmentStatus.PLANNED and tx.end_date is not None:
            findings.append(_finding(
                code="PLANNED_TREATMENT_HAS_END_DATE",
                severity=IntegritySeverity.MAJOR,
                category="temporal_consistency",
                field_path=f"treatments[{idx}]",
                message="Planned treatment has an end date, which is internally inconsistent.",
                recommendation_blocking=True,
                source_segment_ids=_segments_from_provenance(tx.provenance),
            ))
    return IntegrityCheckResult(check_id="treatment_temporality", check_version=CHECK_VERSION, passed=not findings, findings=findings)


def _check_schema_consistency(case: CancerTumorBoardCase) -> IntegrityCheckResult:
    findings: list[IntegrityFinding] = []
    if case.diagnosis.status == DataStatus.CONFIRMED and (case.diagnosis.value is None or str(case.diagnosis.value).strip() == ""):
        findings.append(_finding(
            code="CONFIRMED_DIAGNOSIS_WITHOUT_VALUE",
            severity=IntegritySeverity.CRITICAL,
            category="schema_consistency",
            field_path="diagnosis",
            message="Diagnosis is marked confirmed but has no value.",
            recommendation_blocking=True,
        ))
    if case.performance_status is not None and case.performance_status.status == DataStatus.CONFIRMED and case.performance_status.value is None:
        findings.append(_finding(
            code="CONFIRMED_PERFORMANCE_STATUS_WITHOUT_VALUE",
            severity=IntegritySeverity.MAJOR,
            category="schema_consistency",
            field_path="performance_status",
            message="Performance status is marked confirmed but has no value.",
            recommendation_blocking=True,
        ))
    return IntegrityCheckResult(check_id="schema_consistency", check_version=CHECK_VERSION, passed=not findings, findings=findings)


def run_case_integrity(case: CancerTumorBoardCase) -> CaseIntegrityReport:
    """Run deterministic pre-routing integrity checks over the canonical case.

    This agent does not infer missing patient facts, does not retrieve external evidence,
    and does not modify the canonical case. It only evaluates whether the case is safe
    to propagate to downstream specialist agents.
    """
    checks = [
        _check_provenance(case),
        _check_schema_consistency(case),
        _check_diagnostic_state(case),
        _check_conflicts(case),
        _check_missing_information(case),
        _check_treatment_identity(case),
        _check_treatment_temporality(case),
    ]
    findings = [f for check in checks for f in check.findings]
    critical = sum(f.severity == IntegritySeverity.CRITICAL for f in findings)
    major = sum(f.severity == IntegritySeverity.MAJOR for f in findings)
    warnings = sum(f.severity == IntegritySeverity.WARNING for f in findings)
    blocking = sum(f.recommendation_blocking for f in findings)

    if blocking or critical:
        disposition = IntegrityDisposition.BLOCK
    elif findings:
        disposition = IntegrityDisposition.PASS_WITH_WARNINGS
    else:
        disposition = IntegrityDisposition.PASS

    return CaseIntegrityReport(
        case_id=case.case_id,
        disposition=disposition,
        checks_run=len(checks),
        checks_passed=sum(check.passed for check in checks),
        critical_count=critical,
        major_count=major,
        warning_count=warnings,
        recommendation_blocking_count=blocking,
        findings=findings,
        check_results=checks,
        requires_human_review=disposition != IntegrityDisposition.PASS,
        safe_to_route_to_specialists=disposition != IntegrityDisposition.BLOCK,
    )
