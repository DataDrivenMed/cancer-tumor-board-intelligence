from __future__ import annotations

from schemas.agent import RoutingDecision
from schemas.case import CancerTumorBoardCase


def route_case(case: CancerTumorBoardCase) -> RoutingDecision:
    selected = ["guideline", "literature", "clinical_trials", "safety"]
    rationale = ["Treatment-focused tumor-board question"]

    if case.molecular_findings:
        selected.extend(["molecular", "translational"])
        rationale.append("Molecular findings present")

    complexity = "complex"
    if len(case.treatments) >= 3:
        complexity = "high_complexity"
        rationale.append("Multiple prior treatment lines")

    if case.conflicts:
        rationale.append("Case contains unresolved conflicts")

    return RoutingDecision(
        question_type=case.clinical_question.question_type,
        complexity=complexity,
        selected_agents=selected,
        rationale=rationale,
    )
