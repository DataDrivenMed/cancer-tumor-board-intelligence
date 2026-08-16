from __future__ import annotations

from orchestration.workflow import run_workflow
from schemas.case import (
    CancerTumorBoardCase,
    ClinicalQuestion,
    Fact,
    Provenance,
    TreatmentEpisode,
    TreatmentStatus,
)


def _prov(text: str) -> Provenance:
    return Provenance(
        document_id="WF-REDTEAM-DOC",
        source_excerpt=text,
        source_segment_ids=["S0001"],
        source_verified=True,
    )


def _fact(field: str, value: str) -> Fact:
    return Fact(field=field, value=value, provenance=[_prov(value)])


def test_workflow_runs_clinical_red_team_after_specialists() -> None:
    case = CancerTumorBoardCase(
        case_id="WF-REDTEAM-001",
        diagnosis=_fact("diagnosis", "acute myeloid leukemia"),
        disease_state=_fact("disease_state", "relapsed"),
        performance_status=_fact("ECOG", "1"),
        treatments=[
            TreatmentEpisode(
                episode_id="TX-001",
                regimen="Synthetic prior regimen",
                treatment_status=TreatmentStatus.COMPLETED,
                provenance=[_prov("Synthetic prior regimen completed")],
            )
        ],
        clinical_question=ClinicalQuestion(
            question_type="management",
            question="What treatment strategies should be discussed?",
        ),
    )

    result = run_workflow(case)
    assert result["routing"] is not None
    assert result["red_team_report"] is not None
    assert result["red_team_report"].agent_id == "clinical_red_team"
    assert result["final_decision"].decision_state == "abstain"
    assert any(event.event_type == "clinical_red_team_complete" for event in result["audit_events"])
