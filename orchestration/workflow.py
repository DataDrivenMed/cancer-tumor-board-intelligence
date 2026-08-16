from __future__ import annotations

from schemas.agent import FinalDecision, RedTeamFinding
from schemas.case import CancerTumorBoardCase
from services.audit import audit_event
from services.quality import inspect_case
from services.semantic_integrity import inspect_semantic_integrity, semantic_integrity_passes
from services.guideline_sources import PRODUCTION_GUIDELINE_STORE
from services.molecular_sources import PRODUCTION_MOLECULAR_STORE
from services.translational_sources import PRODUCTION_TRANSLATIONAL_STORE
from services.safety_sources import PRODUCTION_SAFETY_STORE
from orchestration.router import route_case
from agents.case_integrity import run_case_integrity
from agents.missing_information import run_missing_information
from agents.guideline import GuidelineAgent
from agents.literature import LiteratureAgent
from agents.molecular import MolecularInterpretationAgent
from agents.translational import TranslationalBiologyAgent
from agents.clinical_trials import ClinicalTrialsAgent
from agents.safety import SafetyAgent
from agents.clinical_red_team import run_clinical_red_team
from agents.consensus import run_consensus
from agents.tumor_board_brief import render_tumor_board_brief


AGENT_REGISTRY = {
    "guideline": GuidelineAgent(PRODUCTION_GUIDELINE_STORE),
    "molecular": MolecularInterpretationAgent(PRODUCTION_MOLECULAR_STORE, production_mode=True),
    "translational": TranslationalBiologyAgent(PRODUCTION_TRANSLATIONAL_STORE, production_mode=True),
    # Production-safe defaults: live public-source access is opt-in. Dedicated
    # validation pages exercise the live PubMed and ClinicalTrials.gov adapters.
    "literature": LiteratureAgent(),
    "clinical_trials": ClinicalTrialsAgent(),
    "safety": SafetyAgent(PRODUCTION_SAFETY_STORE, production_mode=True),
}


def _abstain_result(
    *,
    case,
    final,
    audit,
    semantic_findings,
    red_team_findings,
    integrity_report=None,
    missing_report=None,
):
    return {
        "case": case,
        "routing": None,
        "specialist_outputs": {},
        "preliminary_synthesis": "",
        "red_team_findings": red_team_findings,
        "red_team_report": None,
        "consensus_report": None,
        "tumor_board_brief": None,
        "semantic_integrity_findings": semantic_findings,
        "case_integrity_report": integrity_report,
        "missing_information_report": missing_report,
        "final_decision": final,
        "audit_events": audit,
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
        return _abstain_result(
            case=case,
            final=final,
            audit=audit,
            semantic_findings=semantic_findings,
            red_team_findings=[
                RedTeamFinding(
                    severity="critical",
                    category="semantic_integrity",
                    issue=f.message,
                    effect_on_recommendation="Downstream reasoning is blocked until the structured representation is corrected.",
                )
                for f in semantic_findings
                if f.severity in {"error", "critical"}
            ],
        )

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
        return _abstain_result(
            case=case,
            final=final,
            audit=audit,
            semantic_findings=semantic_findings,
            integrity_report=integrity_report,
            red_team_findings=[
                RedTeamFinding(
                    severity="critical" if f.recommendation_blocking else "major",
                    category=f"case_integrity:{f.category}",
                    issue=f.message,
                    effect_on_recommendation="Downstream specialist reasoning is blocked until the case representation is corrected or reviewed.",
                )
                for f in integrity_report.findings
                if f.recommendation_blocking
            ],
        )

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
        return _abstain_result(
            case=case,
            final=final,
            audit=audit,
            semantic_findings=semantic_findings,
            integrity_report=integrity_report,
            missing_report=missing_report,
            red_team_findings=[
                RedTeamFinding(
                    severity="critical" if item.priority.value == "critical" else "major",
                    category="missing_information",
                    issue=f"{item.field}: {item.reason}",
                    effect_on_recommendation="Specialist reasoning is blocked until this decision-critical information is resolved.",
                )
                for item in missing_report.items
                if item.recommendation_blocking
            ],
        )

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

    red_team_report = run_clinical_red_team(case, routing, specialist_outputs)
    audit.append(
        audit_event(
            "clinical_red_team_complete",
            f"disposition={red_team_report.disposition.value}; findings={len(red_team_report.findings)}; "
            f"blocking={red_team_report.blocking_count}; safe_for_consensus={red_team_report.safe_for_consensus}",
        )
    )
    red_team = [
        RedTeamFinding(
            severity=finding.severity.value,
            category=finding.category,
            issue=finding.issue,
            effect_on_recommendation=finding.effect_on_recommendation,
        )
        for finding in red_team_report.findings
    ]

    consensus_report = run_consensus(case, routing, specialist_outputs, red_team_report)
    audit.append(
        audit_event(
            "consensus_complete",
            f"disposition={consensus_report.disposition.value}; decision_state={consensus_report.decision_state}; "
            f"candidates={len(consensus_report.candidates)}; safe_to_render={consensus_report.safe_to_render_decision_support}",
        )
    )

    tumor_board_brief = render_tumor_board_brief(case, specialist_outputs, red_team_report, consensus_report)
    audit.append(
        audit_event(
            "tumor_board_brief_complete",
            f"status={tumor_board_brief.status}; sections={len(tumor_board_brief.sections)}; "
            f"source_traces={tumor_board_brief.source_trace_count}; decision_state={tumor_board_brief.decision_state}",
        )
    )

    primary_strategy = None
    alternatives = []
    if consensus_report.safe_to_render_decision_support and consensus_report.candidates:
        primary_strategy = consensus_report.candidates[0].strategy
        alternatives = [candidate.strategy for candidate in consensus_report.candidates[1:]]

    final = FinalDecision(
        decision_state=consensus_report.decision_state,
        primary_strategy=primary_strategy,
        alternatives=alternatives,
        conditions=[
            item
            for candidate in consensus_report.candidates
            for item in candidate.conditions
        ],
        major_uncertainties=consensus_report.major_uncertainties,
        discussion_priorities=consensus_report.discussion_priorities,
        decision_support_strength=consensus_report.decision_support_strength,
        abstention_reason=consensus_report.abstention_reason,
    )

    preliminary = (
        "Deterministic evidence integration and tumor-board brief rendering complete. The Consensus Engine does not use "
        "agent voting. Explicit management candidates require verified formal or consensus guideline support; molecular, "
        "translational, literature, trial, and safety outputs remain bounded by their own claim gates. The final brief is "
        "a presentation transformer and cannot create new clinical claims."
    )
    audit.append(audit_event("workflow_complete", final.decision_state))

    return {
        "case": case,
        "routing": routing,
        "specialist_outputs": specialist_outputs,
        "preliminary_synthesis": preliminary,
        "red_team_findings": red_team,
        "red_team_report": red_team_report,
        "consensus_report": consensus_report,
        "tumor_board_brief": tumor_board_brief,
        "semantic_integrity_findings": semantic_findings,
        "case_integrity_report": integrity_report,
        "missing_information_report": missing_report,
        "final_decision": final,
        "audit_events": audit,
    }
