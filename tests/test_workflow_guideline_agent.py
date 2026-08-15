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
        document_id="WF-GUIDE-DOC",
        source_excerpt=text,
        source_segment_ids=["S0001"],
        source_verified=True,
    )


def _fact(field: str, value: str) -> Fact:
    return Fact(field=field, value=value, provenance=[_prov(value)])


def test_workflow_guideline_agent_emits_no_claim_without_authorized_source() -> None:
    case = CancerTumorBoardCase(
        case_id="WF-GUIDE-001",
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
    assert "guideline" in result["routing"].selected_agents
    report = result["specialist_outputs"]["guideline"]
    assert report.status == "source_unavailable"
    assert report.matched_guidance == []
    assert report.can_support_guideline_claim is False
    assert result["final_decision"].decision_state == "abstain"
