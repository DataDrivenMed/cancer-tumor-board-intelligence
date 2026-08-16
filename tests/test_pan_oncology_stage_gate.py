from __future__ import annotations

from agents.missing_information import run_missing_information
from schemas.case import CancerTumorBoardCase, ClinicalQuestion, DataStatus, Fact, Provenance
from schemas.missing_information import MissingInformationDisposition


def _case(stage: Fact | None) -> CancerTumorBoardCase:
    return CancerTumorBoardCase(
        case_id="PAN-STAGE-GATE",
        case_type="synthetic",
        disease_program="breast_oncology",
        tumor_board_type="breast_tumor_board",
        diagnosis=Fact(field="diagnosis", value="breast cancer"),
        disease_state=Fact(field="disease_state", value="localized"),
        stage=stage,
        performance_status=Fact(field="performance_status", value="ECOG 0"),
        clinical_question=ClinicalQuestion(
            question_type="treatment_management",
            question="Discuss management at tumor board.",
        ),
    )


def test_conflicting_explicit_stage_blocks_specialist_routing():
    stage = Fact(
        field="stage",
        value=None,
        status=DataStatus.CONFLICTING,
        provenance=[
            Provenance(
                document_id="DOC-1",
                source_excerpt="stage II",
                source_segment_ids=["S0001"],
                source_verified=True,
            ),
            Provenance(
                document_id="DOC-1",
                source_excerpt="stage III",
                source_segment_ids=["S0002"],
                source_verified=True,
            ),
        ],
    )
    report = run_missing_information(_case(stage))
    stage_items = [item for item in report.items if item.category == "stage"]
    assert len(stage_items) == 1
    assert stage_items[0].recommendation_blocking is True
    assert stage_items[0].availability == "conflicting"
    assert stage_items[0].source_segment_ids == ["S0001", "S0002"]
    assert report.disposition == MissingInformationDisposition.BLOCKED
    assert report.safe_to_route_to_specialists is False


def test_pending_explicit_stage_is_visible_but_not_globally_assumed_blocking():
    stage = Fact(
        field="stage",
        value=None,
        status=DataStatus.PENDING,
        provenance=[
            Provenance(
                document_id="DOC-2",
                source_excerpt="staging pending",
                source_segment_ids=["S0003"],
                source_verified=True,
            )
        ],
    )
    report = run_missing_information(_case(stage))
    stage_items = [item for item in report.items if item.category == "stage"]
    assert len(stage_items) == 1
    assert stage_items[0].recommendation_blocking is False
    assert stage_items[0].availability == "pending"
    assert report.safe_to_route_to_specialists is True


def test_absent_stage_is_not_assumed_missing_for_every_oncology_case():
    report = run_missing_information(_case(None))
    assert not any(item.category == "stage" for item in report.items)
