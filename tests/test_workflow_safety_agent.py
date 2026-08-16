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
        document_id="WF-SAFETY-DOC",
        source_excerpt=text,
        source_segment_ids=["S0001"],
        source_verified=True,
    )


def _fact(field: str, value: str) -> Fact:
    return Fact(field=field, value=value, provenance=[_prov(value)])


def test_workflow_safety_agent_emits_no_claim_without_authorized_source() -> None:
    case = CancerTumorBoardCase(
        case_id="WF-SAFETY-001",
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
        current_medications=[_fact("medication", "Synthetic current medication")],
        clinical_question=ClinicalQuestion(
            question_type="management",
            question="What treatment strategies should be discussed?",
        ),
    )

    result = run_workflow(case)
    assert result["routing"] is not None
    assert "safety" in result["routing"].selected_agents
    report = result["specialist_outputs"]["safety"]
    assert report.status == "source_unavailable"
    assert report.can_support_safety_claim is False
    assert report.recommendation_blocking is False
    assert result["final_decision"].decision_state == "abstain"
