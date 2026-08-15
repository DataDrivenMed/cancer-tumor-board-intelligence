from __future__ import annotations

from schemas.agent import FinalDecision, RedTeamFinding
from schemas.case import CancerTumorBoardCase
from services.audit import audit_event
from services.quality import inspect_case
from services.semantic_integrity import inspect_semantic_integrity, semantic_integrity_passes
from orchestration.router import route_case
from agents.case_integrity import run_case_integrity
from agents.missing_information import run_missing_information
from agents.mock_agents import (
    GuidelineMockAgent,
    MolecularMockAgent,
    TranslationalMockAgent,
    LiteratureMockAgent,
    TrialMockAgent,
    SafetyMockAgent,
)


AGENT_REGISTRY = {
    "guideline": GuidelineMockAgent(),
    "molecular": MolecularMockAgent(),
    "translational": TranslationalMockAgent(),
    "literature": LiteratureMockAgent(),
    "clinical_trials": TrialMockAgent(),
    "safety": SafetyMockAgent(),
}


def run_workflow(case: CancerTumorBoardCase, *, raw_extraction: dict | None = None) -> dict:
    audit = [audit_event("workflow_started", case.case_id)]

    semantic_findings = inspect_semantic_integrity(case, raw_extraction)
    audit.append(
        audit_event(
            "semantic_integrity_check_complete",
            f"{len(semantic_findings)} finding(s); pass={semantic_integrity_passes(semantic_findings)}",
        )
    )
    if not semantic_integrity_passes(semantic_findings):
        final = FinalDecision(
            decision_state="abstain",
            decision_support_strength="insufficient",
            abstention_reason="Structured case failed deterministic semantic-integrity validation.",
            discussion_priorities=[
                "Resolve semantic-integrity errors in the extracted case before routing to specialist agents."
            ],
        )
        audit.append(audit_event("workflow_abstained", "Semantic integrity gate failed"))
        return {
            "case": case,
            "routing": None,
            "specialist_outputs": {},
            "preliminary_synthesis": "",
            "red_team_findings": [
                RedTeamFinding(
                    severity="critical",
                    category="semantic_integrity",
                    issue=f.message,
                    effect_on_recommendation="Downstream reasoning is blocked until the structured representation is corrected.",
                )
                for f in semantic_findings
                if f.severity in {"error", "critical"}
            ],
            "semantic_integrity_findings": semantic_findings,
            "case_integrity_report": None,
            "missing_information_report": None,
            "final_decision": final,
            "audit_events": audit,
        }

    conflicts, missing = inspect_case(case)
    case.conflicts = conflicts
    case.missing_items = missing
    audit.append(audit_event("quality_check_complete", f"{len(conflicts)} conflicts; {len(missing)} missing items"))

    integrity_report = run_case_integrity(case)
    audit.append(
        audit_event(
            "case_integrity_check_complete",
            f"disposition={integrity_report.disposition.value}; findings={len(integrity_report.findings)}; "
            f"safe_to_route={integrity_report.safe_to_route_to_specialists}",
        )
    )
    if not integrity_report.safe_to_route_to_specialists:
        final = FinalDecision(
            decision_state="abstain",
            decision_support_strength="insufficient",
            abstention_reason="Canonical case failed the deterministic Case Integrity / Data QA routing gate.",
            discussion_priorities=[
                "Resolve recommendation-blocking data-quality findings before specialist-agent routing."
            ],
        )
        audit.append(audit_event("workflow_abstained", "Case Integrity / Data QA gate blocked routing"))
        return {
            "case": case,
            "routing": None,
            "specialist_outputs": {},
            "preliminary_synthesis": "",
            "red_team_findings": [
                RedTeamFinding(
                    severity="critical" if f.recommendation_blocking else "major",
                    category=f"case_integrity:{f.category}",
                    issue=f.message,
                    effect_on_recommendation="Downstream specialist reasoning is blocked until the case representation is corrected or reviewed.",
                )
                for f in integrity_report.findings
                if f.recommendation_blocking
            ],
            "semantic_integrity_findings": semantic_findings,
            "case_integrity_report": integrity_report,
            "missing_information_report": None,
            "final_decision": final,
            "audit_events": audit,
        }

    missing_report = run_missing_information(case)
    audit.append(
        audit_event(
            "missing_information_analysis_complete",
            f"disposition={missing_report.disposition.value}; items={len(missing_report.items)}; "
            f"blocking={missing_report.blocking_count}; safe_to_route={missing_report.safe_to_route_to_specialists}",
        )
    )
    if not missing_report.safe_to_route_to_specialists:
        final = FinalDecision(
            decision_state="abstain",
            decision_support_strength="insufficient",
            abstention_reason="Decision-critical information is missing or unresolved.",
            major_uncertainties=[item.field for item in missing_report.items if item.priority.value in {"high", "critical"}],
            discussion_priorities=[
                f"{item.action.value.replace('_', ' ').title()}: {item.field}"
                for item in missing_report.items
                if item.recommendation_blocking
            ],
        )
        audit.append(audit_event("workflow_abstained", "Missing Information Agent blocked specialist routing"))
        return {
            "case": case,
            "routing": None,
            "specialist_outputs": {},
            "preliminary_synthesis": "",
            "red_team_findings": [
                RedTeamFinding(
                    severity="critical" if item.priority.value == "critical" else "major",
                    category="missing_information",
                    issue=f"{item.field}: {item.reason}",
                    effect_on_recommendation="Specialist reasoning is blocked until this decision-critical information is resolved.",
                )
                for item in missing_report.items
                if item.recommendation_blocking
            ],
            "semantic_integrity_findings": semantic_findings,
            "case_integrity_report": integrity_report,
            "missing_information_report": missing_report,
            "final_decision": final,
            "audit_events": audit,
        }

    routing = route_case(case)
    audit.append(audit_event("routing_complete", ", ".join(routing.selected_agents)))

    specialist_outputs = {}
    for agent_id in routing.selected_agents:
        output = AGENT_REGISTRY[agent_id].run(case)
        specialist_outputs[agent_id] = output
        audit.append(audit_event("agent_complete", agent_id))

    preliminary = (
        "Skeleton synthesis only. The application has successfully routed the case "
        "through independent specialist placeholders. No clinical recommendation "
        "is generated until validated evidence connectors and model contracts are enabled."
    )

    red_team = [
        RedTeamFinding(
            severity="critical",
            category="evidence_unavailable",
            issue="No live clinical evidence sources are connected in the skeleton build.",
            effect_on_recommendation="Final clinical recommendation must be withheld.",
        )
    ]

    final = FinalDecision(
        decision_state="abstain",
        decision_support_strength="insufficient",
        abstention_reason="The skeleton build has no validated evidence connectors and therefore cannot support a clinical recommendation.",
        major_uncertainties=[item.field for item in missing_report.items if item.priority.value in {"high", "critical"}],
        discussion_priorities=[
            "Verify the structured patient facts.",
            "Resolve any decision-critical missing information.",
            "Connect and validate authoritative evidence sources before activating clinical recommendation logic.",
        ],
    )
    audit.append(audit_event("workflow_complete", final.decision_state))

    return {
        "case": case,
        "routing": routing,
        "specialist_outputs": specialist_outputs,
        "preliminary_synthesis": preliminary,
        "red_team_findings": red_team,
        "semantic_integrity_findings": semantic_findings,
        "case_integrity_report": integrity_report,
        "missing_information_report": missing_report,
        "final_decision": final,
        "audit_events": audit,
    }
