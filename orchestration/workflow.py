from __future__ import annotations

from schemas.agent import FinalDecision, RedTeamFinding
from schemas.case import CancerTumorBoardCase
from services.audit import audit_event
from services.quality import inspect_case
from orchestration.router import route_case
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


def run_workflow(case: CancerTumorBoardCase) -> dict:
    audit = [audit_event("workflow_started", case.case_id)]

    conflicts, missing = inspect_case(case)
    case.conflicts = conflicts
    case.missing_items = missing
    audit.append(audit_event("quality_check_complete", f"{len(conflicts)} conflicts; {len(missing)} missing items"))

    if any(c.severity == "critical" and c.resolution_status == "unresolved" for c in conflicts):
        final = FinalDecision(
            decision_state="abstain",
            decision_support_strength="insufficient",
            abstention_reason="Critical unresolved case conflict.",
            discussion_priorities=["Resolve critical source conflict before treatment ranking."],
        )
        audit.append(audit_event("workflow_abstained", "Critical unresolved conflict"))
        return {
            "case": case,
            "routing": None,
            "specialist_outputs": {},
            "preliminary_synthesis": "",
            "red_team_findings": [],
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
        major_uncertainties=[m.field for m in missing if m.importance in {"high", "critical"}],
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
        "final_decision": final,
        "audit_events": audit,
    }
