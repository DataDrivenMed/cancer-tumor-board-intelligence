from __future__ import annotations

from schemas.case import (
    CancerTumorBoardCase,
    ClinicalQuestion,
    DataStatus,
    Fact,
    Provenance,
    TreatmentEpisode,
    TreatmentStatus,
)
from orchestration.workflow import run_workflow


def prov() -> Provenance:
    return Provenance(
        document_id="DOC-1",
        source_excerpt="source text",
        source_segment_ids=["S0001"],
        source_verified=True,
    )


def fact(field: str, value, *, status: DataStatus = DataStatus.CONFIRMED) -> Fact:
    return Fact(field=field, value=value, status=status, provenance=[prov()])


def base_case() -> CancerTumorBoardCase:
    return CancerTumorBoardCase(
        case_id="WF-MISS-001",
        diagnosis=fact("diagnosis", "acute myeloid leukemia"),
        disease_state=fact("disease_state", "newly diagnosed"),
        performance_status=fact("ECOG", "1"),
        treatments=[
            TreatmentEpisode(
                episode_id="TX-001",
                regimen="azacitidine",
                treatment_status=TreatmentStatus.STARTED,
                provenance=[prov()],
            )
        ],
        clinical_question=ClinicalQuestion(
            question_type="diagnostic_review",
            question="Confirm the current diagnostic representation.",
        ),
    )


def test_workflow_exposes_missing_information_report_when_routing_allowed() -> None:
    result = run_workflow(base_case())
    report = result["missing_information_report"]
    assert report is not None
    assert report.safe_to_route_to_specialists is True
    assert result["routing"] is not None


def test_missing_information_gate_blocks_before_specialists() -> None:
    case = base_case()
    case.disease_state.value = "relapsed"
    case.treatments = []
    result = run_workflow(case)
    report = result["missing_information_report"]
    assert report is not None
    assert report.safe_to_route_to_specialists is False
    assert report.blocking_count >= 1
    assert result["routing"] is None
    assert result["specialist_outputs"] == {}
    assert result["final_decision"].decision_state == "abstain"
    assert "missing" in result["final_decision"].abstention_reason.lower()
