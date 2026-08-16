from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from schemas.agent import RoutingDecision
from schemas.case import CancerTumorBoardCase
from schemas.red_team import (
    ClinicalRedTeamFinding,
    ClinicalRedTeamReport,
    RedTeamDisposition,
    RedTeamSeverity,
)


AGENT_ID = "clinical_red_team"
AGENT_VERSION = "1.0.0"

_BLOCKING_STATUSES = {
    "insufficient_input",
    "source_unavailable",
    "verification_failed",
    "schema_error",
    "tool_failure",
    "abstain_domain",
    "escalate_human",
}


def _value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _status(obj: Any) -> str:
    value = _value(obj, "status", "unknown")
    return str(getattr(value, "value", value))


def _bool(obj: Any, key: str) -> bool:
    return bool(_value(obj, key, False))


def _list(obj: Any, key: str) -> list[Any]:
    value = _value(obj, key, [])
    return list(value or [])


def _severity_rank(severity: RedTeamSeverity) -> int:
    return {
        RedTeamSeverity.MINOR: 0,
        RedTeamSeverity.MODERATE: 1,
        RedTeamSeverity.MAJOR: 2,
        RedTeamSeverity.CRITICAL: 3,
    }[severity]


def _finding(
    *,
    code: str,
    severity: RedTeamSeverity,
    category: str,
    issue: str,
    effect: str,
    agents: list[str] | None = None,
    blocking: bool = False,
    human: bool = False,
) -> ClinicalRedTeamFinding:
    return ClinicalRedTeamFinding(
        code=code,
        severity=severity,
        category=category,
        issue=issue,
        effect_on_recommendation=effect,
        source_agent_ids=sorted(set(agents or [])),
        recommendation_blocking=blocking,
        human_review_required=human,
    )


def run_clinical_red_team(
    case: CancerTumorBoardCase,
    routing: RoutingDecision,
    specialist_outputs: Mapping[str, Any],
) -> ClinicalRedTeamReport:
    """Independently challenge the specialist evidence stack before consensus.

    The v1 red team is deterministic. It does not invent alternative treatment,
    diagnosis, toxicity, or trial assertions. It challenges structural failures,
    evidence-promotion errors, unresolved safety hazards, and missing required
    specialist outputs. Findings are preserved rather than averaged away.
    """

    findings: list[ClinicalRedTeamFinding] = []
    selected = list(routing.selected_agents)
    required = set(routing.required_agents)

    for agent_id in selected:
        if agent_id not in specialist_outputs:
            findings.append(
                _finding(
                    code="REQUIRED_SPECIALIST_OUTPUT_MISSING" if agent_id in required else "SELECTED_SPECIALIST_OUTPUT_MISSING",
                    severity=RedTeamSeverity.CRITICAL if agent_id in required else RedTeamSeverity.MAJOR,
                    category="orchestration",
                    issue=f"Selected specialist '{agent_id}' has no output.",
                    effect="Consensus cannot treat the evidence stack as complete.",
                    agents=[agent_id],
                    blocking=agent_id in required,
                    human=True,
                )
            )
            continue

        output = specialist_outputs[agent_id]
        status = _status(output)
        if status in _BLOCKING_STATUSES:
            findings.append(
                _finding(
                    code="REQUIRED_SPECIALIST_FAILED" if agent_id in required else "SPECIALIST_FAILED",
                    severity=RedTeamSeverity.CRITICAL if agent_id in required else RedTeamSeverity.MAJOR,
                    category="evidence_availability",
                    issue=f"Specialist '{agent_id}' returned status '{status}'.",
                    effect=(
                        "A required evidence channel is unavailable or failed verification; recommendation synthesis must not proceed."
                        if agent_id in required
                        else "The specialist evidence stack is incomplete and any synthesis must explicitly preserve this limitation."
                    ),
                    agents=[agent_id],
                    blocking=agent_id in required,
                    human=True,
                )
            )
        elif status == "no_evidence_found":
            findings.append(
                _finding(
                    code="NO_EVIDENCE_FOUND_NOT_NEGATIVE_EVIDENCE",
                    severity=RedTeamSeverity.MODERATE,
                    category="evidence_interpretation",
                    issue=f"Specialist '{agent_id}' found no evidence under its bounded search or match rule.",
                    effect="Do not convert a bounded no-result into evidence that an option, hazard, biomarker, or trial does not exist.",
                    agents=[agent_id],
                    blocking=False,
                    human=True,
                )
            )

    unresolved_high_conflicts = [
        conflict
        for conflict in case.conflicts
        if conflict.resolution_status == "unresolved" and conflict.severity in {"high", "critical"}
    ]
    for conflict in unresolved_high_conflicts:
        findings.append(
            _finding(
                code="UNRESOLVED_HIGH_SEVERITY_CASE_CONFLICT",
                severity=RedTeamSeverity.CRITICAL,
                category="case_conflict",
                issue=f"Unresolved {conflict.severity} conflict remains for '{conflict.field}'.",
                effect="Patient-state uncertainty is decision-critical; consensus must stop until the conflict is resolved or explicitly adjudicated.",
                blocking=True,
                human=True,
            )
        )

    blocking_missing = [item for item in case.missing_items if item.recommendation_blocking]
    for item in blocking_missing:
        findings.append(
            _finding(
                code="RECOMMENDATION_BLOCKING_INFORMATION_MISSING",
                severity=RedTeamSeverity.CRITICAL,
                category="missing_information",
                issue=f"Recommendation-blocking information remains missing: {item.field}.",
                effect="Consensus must not infer the missing value or proceed as though it were normal, negative, or not applicable.",
                blocking=True,
                human=True,
            )
        )

    molecular = specialist_outputs.get("molecular")
    if molecular is not None:
        report_support = _bool(molecular, "can_support_clinical_actionability_claim")
        item_support = any(_bool(item, "can_support_clinical_actionability_claim") for item in _list(molecular, "interpretations"))
        if item_support and not report_support:
            findings.append(
                _finding(
                    code="MOLECULAR_ACTIONABILITY_INTERNAL_INCONSISTENCY",
                    severity=RedTeamSeverity.CRITICAL,
                    category="claim_promotion",
                    issue="A molecular interpretation supports clinical actionability while the report-level actionability gate is false.",
                    effect="Clinical actionability must be withheld until the inconsistency is resolved.",
                    agents=["molecular"],
                    blocking=True,
                    human=True,
                )
            )

    translational = specialist_outputs.get("translational")
    if translational is not None and _bool(translational, "can_support_clinical_actionability_claim"):
        findings.append(
            _finding(
                code="TRANSLATIONAL_EVIDENCE_PROMOTED_TO_CLINICAL_ACTIONABILITY",
                severity=RedTeamSeverity.CRITICAL,
                category="claim_promotion",
                issue="Translational evidence was marked as supporting clinical actionability.",
                effect="Mechanistic, preclinical, or human-translational evidence cannot independently establish treatment actionability.",
                agents=["translational"],
                blocking=True,
                human=True,
            )
        )

    trials = specialist_outputs.get("clinical_trials")
    if trials is not None:
        if _bool(trials, "can_support_eligibility_claim"):
            findings.append(
                _finding(
                    code="TRIAL_MATCH_PROMOTED_TO_ELIGIBILITY",
                    severity=RedTeamSeverity.CRITICAL,
                    category="claim_promotion",
                    issue="Clinical-trials output was marked as supporting a patient eligibility claim.",
                    effect="Trial match is not eligibility; eligibility requires criterion-level review and study-team confirmation.",
                    agents=["clinical_trials"],
                    blocking=True,
                    human=True,
                )
            )
        for match in _list(trials, "matches"):
            if _bool(match, "eligibility_determined") or _value(match, "eligible", None) is not None:
                findings.append(
                    _finding(
                        code="PATIENT_TRIAL_ELIGIBILITY_AUTOMATICALLY_DETERMINED",
                        severity=RedTeamSeverity.CRITICAL,
                        category="claim_promotion",
                        issue=f"Trial match '{_value(match, 'nct_id', 'unknown')}' contains an automated patient-specific eligibility determination.",
                        effect="Remove the eligibility assertion and retain unresolved inclusion/exclusion domains for human adjudication.",
                        agents=["clinical_trials"],
                        blocking=True,
                        human=True,
                    )
                )

    safety = specialist_outputs.get("safety")
    if safety is not None:
        if _bool(safety, "recommendation_blocking"):
            findings.append(
                _finding(
                    code="SAFETY_RECOMMENDATION_BLOCK",
                    severity=RedTeamSeverity.CRITICAL,
                    category="safety",
                    issue="Safety Agent identified a recommendation-blocking contraindication, hazard, or unresolved required parameter.",
                    effect="Recommendation synthesis must stop until the safety issue is resolved or explicitly adjudicated by a qualified human reviewer.",
                    agents=["safety"],
                    blocking=True,
                    human=True,
                )
            )
        if _list(safety, "findings") and not _bool(safety, "can_support_safety_claim"):
            findings.append(
                _finding(
                    code="SAFETY_FINDINGS_WITHOUT_CLAIM_SUPPORT",
                    severity=RedTeamSeverity.MAJOR,
                    category="internal_consistency",
                    issue="Safety findings are present while the report-level safety-claim gate is false.",
                    effect="The findings must not influence synthesis until their source-verification state is reconciled.",
                    agents=["safety"],
                    blocking=False,
                    human=True,
                )
            )

    guideline = specialist_outputs.get("guideline")
    if guideline is not None:
        formal_matches = int(_value(guideline, "formal_guideline_matches", 0) or 0)
        if formal_matches == 0 and _bool(guideline, "can_support_guideline_claim"):
            findings.append(
                _finding(
                    code="GUIDELINE_CLAIM_WITHOUT_FORMAL_OR_CONSENSUS_SUPPORT",
                    severity=RedTeamSeverity.CRITICAL,
                    category="claim_promotion",
                    issue="Guideline claim support is true despite zero formal guideline matches.",
                    effect="Authoritative summaries or other non-guideline sources must not be represented as formal guideline support.",
                    agents=["guideline"],
                    blocking=True,
                    human=True,
                )
            )

    # Deterministic sort prevents stochastic presentation differences.
    findings = sorted(
        findings,
        key=lambda item: (
            -_severity_rank(item.severity),
            item.category,
            item.code,
            item.issue,
        ),
    )

    critical_count = sum(f.severity == RedTeamSeverity.CRITICAL for f in findings)
    major_count = sum(f.severity == RedTeamSeverity.MAJOR for f in findings)
    blocking_count = sum(f.recommendation_blocking for f in findings)
    challenged_agents = sorted({agent for finding in findings for agent in finding.source_agent_ids})

    if blocking_count:
        disposition = RedTeamDisposition.BLOCKED
        status = "escalate_human"
        safe_for_consensus = False
        summary = f"Clinical Red Team blocked consensus with {blocking_count} recommendation-blocking finding(s)."
    elif findings:
        disposition = RedTeamDisposition.CHALLENGED
        status = "completed_with_limitations"
        safe_for_consensus = True
        summary = f"Clinical Red Team identified {len(findings)} non-blocking challenge(s) that must remain visible in consensus."
    else:
        disposition = RedTeamDisposition.CLEAR
        status = "completed"
        safe_for_consensus = True
        summary = "Clinical Red Team found no deterministic promotion, orchestration, conflict, or safety-gate violation in the supplied specialist outputs."

    return ClinicalRedTeamReport(
        case_id=case.case_id,
        status=status,
        disposition=disposition,
        findings=findings,
        critical_count=critical_count,
        major_count=major_count,
        blocking_count=blocking_count,
        challenged_agent_ids=challenged_agents,
        summary=summary,
        limitations=[
            "Red Team v1 is a deterministic structural and epistemic challenger, not an autonomous oncologist.",
            "A CLEAR disposition does not establish clinical correctness, treatment efficacy, or patient safety.",
            "The agent does not invent alternative diagnoses or treatments; unsupported alternatives require independently verified evidence.",
            "Agent agreement is not treated as truth, and future consensus must preserve disagreements and uncertainty rather than average them away.",
        ],
        safe_for_consensus=safe_for_consensus,
    )
