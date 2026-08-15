from __future__ import annotations

from orchestration.workflow import run_workflow
from schemas.case import (
    CancerTumorBoardCase,
    ClinicalQuestion,
    Fact,
    MissingItem,
    Provenance,
    TreatmentEpisode,
    TreatmentStatus,
)


def _provenance(value: str) -> Provenance:
    return Provenance(
        document_id="DOC-1",
        source_excerpt=value,
        source_segment_ids=["S0001"],
        source_verified=True,
    )


def _fact(field: str, value: str) -> Fact:
    return Fact(
        field=field,
        value=value,
        provenance=[_provenance(value)],
    )


def _case() -> CancerTumorBoardCase:
    return CancerTumorBoardCase(
        case_id="WF-QA-001",
        diagnosis=_fact("diagnosis", "acute myeloid leukemia"),
        disease_state=_fact("disease_state", "relapsed"),
        performance_status=_fact("ECOG", "1"),
        treatments=[
            TreatmentEpisode(
                episode_id="TX-001",
                regimen="synthetic prior regimen",
                treatment_status=TreatmentStatus.COMPLETED,
                provenance=[_provenance("synthetic prior regimen")],
            )
        ],
        clinical_question=ClinicalQuestion(
            question_type="relapsed_refractory_treatment",
            question="What should be discussed?",
        ),
    )


def test_workflow_blocks_before_routing_on_case_integrity_failure() -> None:
    case = _case()
    case.missing_items.append(MissingItem(
        field="final pathology",
        importance="critical",
        reason="Required pathology is pending.",
        availability="pending",
        recommendation_blocking=True,
    ))

    result = run_workflow(case)

    report = result["case_integrity_report"]
    assert report is not None
    assert report.safe_to_route_to_specialists is False
    assert result["routing"] is None
    assert result["specialist_outputs"] == {}
    assert result["final_decision"].decision_state == "abstain"
    assert "Case Integrity / Data QA" in result["final_decision"].abstention_reason


def test_workflow_exposes_integrity_report_when_routing_is_allowed() -> None:
    result = run_workflow(_case())

    report = result["case_integrity_report"]
    assert report is not None
    assert report.safe_to_route_to_specialists is True
    assert result["routing"] is not None
