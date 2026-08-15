from __future__ import annotations

from schemas.agent import FinalDecision, RedTeamFinding
from schemas.case import CancerTumorBoardCase
from services.audit import audit_event
from services.quality import inspect_case
from services.semantic_integrity import inspect_semantic_integrity, semantic_integrity_passes
from services.guideline_sources import PRODUCTION_GUIDELINE_STORE
from services.molecular_sources import PRODUCTION_MOLECULAR_STORE
from services.translational_sources import PRODUCTION_TRANSLATIONAL_STORE
from orchestration.router import route_case
from agents.case_integrity import run_case_integrity
from agents.missing_information import run_missing_information
from agents.guideline import GuidelineAgent
from agents.literature import LiteratureAgent
from agents.molecular import MolecularInterpretationAgent
from agents.translational import TranslationalBiologyAgent
from agents.mock_agents import (
    TrialMockAgent,
    SafetyMockAgent,
)


AGENT_REGISTRY = {
    "guideline": GuidelineAgent(PRODUCTION_GUIDELINE_STORE),
    "molecular": MolecularInterpretationAgent(PRODUCTION_MOLECULAR_STORE, production_mode=True),
    "translational": TranslationalBiologyAgent(PRODUCTION_TRANSLATIONAL_STORE, production_mode=True),
    # Production-safe default: live PubMed access is opt-in and requires an explicit
    # NCBI contact email. The Streamlit Literature page exercises the live adapter.
    "literature": LiteratureAgent(),
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
        status = getattr(output, "status", "unknown")
        if hasattr(status, "value"):
            status = status.value
        audit.append(audit_event("agent_complete", f"{agent_id}; status={status}"))

    preliminary = (
        "Skeleton synthesis only. The application has routed the case through specialist contracts. "
        "Guideline, literature, molecular, and translational layers enforce explicit evidence boundaries. "
        "Production molecular and translational stores remain empty until independently verified disease- and alteration-specific evidence records are loaded."
    )

    red_team = [
        RedTeamFinding(
            severity="critical",
            category="evidence_unavailable",
            issue="The complete validated evidence stack is not yet connected for all specialist agents.",
            effect_on_recommendation="Final clinical recommendation must be withheld.",
        )
    ]

    final = FinalDecision(
        decision_state="abstain",
        decision_support_strength="insufficient",
        abstention_reason="The current build does not yet have a complete validated evidence stack and therefore cannot support a clinical recommendation.",
        major_uncertainties=[item.field for item in missing_report.items if item.priority.value in {"high", "critical"}],
        discussion_priorities=[
            "Verify the structured patient facts.",
            "Resolve any decision-critical missing information.",
            "Connect, authorize, and validate the evidence sources required by each selected specialist agent before activating recommendation logic.",
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
