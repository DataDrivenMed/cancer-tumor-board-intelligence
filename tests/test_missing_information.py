from __future__ import annotations

from schemas.case import (
    CancerTumorBoardCase,
    ClinicalQuestion,
    Conflict,
    DataStatus,
    Fact,
    MissingItem,
    Provenance,
    TreatmentEpisode,
    TreatmentStatus,
)
from schemas.missing_information import MissingInformationDisposition
from agents.missing_information import run_missing_information


def prov() -> Provenance:
    return Provenance(
        document_id="DOC-1",
        source_excerpt="source text",
        source_segment_ids=["S0001"],
        source_verified=True,
    )


def fact(field: str, value, *, status: DataStatus = DataStatus.CONFIRMED) -> Fact:
    return Fact(field=field, value=value, status=status, provenance=[prov()])


def clean_case() -> CancerTumorBoardCase:
    return CancerTumorBoardCase(
        case_id="MISS-001",
        diagnosis=fact("diagnosis", "acute myeloid leukemia"),
        disease_state=fact("disease_state", "newly diagnosed"),
        performance_status=fact("ECOG", "1"),
        molecular_findings=[],
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


def fields(report) -> set[str]:
    return {item.field for item in report.items}


def test_clean_diagnostic_case_is_ready() -> None:
    report = run_missing_information(clean_case())
    assert report.disposition == MissingInformationDisposition.READY
    assert report.safe_to_route_to_specialists is True
    assert report.items == []


def test_unconfirmed_diagnosis_blocks() -> None:
    case = clean_case()
    case.diagnosis.status = DataStatus.PENDING
    report = run_missing_information(case)
    assert report.disposition == MissingInformationDisposition.BLOCKED
    assert report.safe_to_route_to_specialists is False
    assert "diagnostic confirmation" in fields(report)


def test_missing_performance_status_is_high_but_not_blocking() -> None:
    case = clean_case()
    case.performance_status = None
    report = run_missing_information(case)
    item = next(x for x in report.items if x.field == "performance status")
    assert item.priority.value == "high"
    assert item.recommendation_blocking is False
    assert report.disposition == MissingInformationDisposition.CONDITIONAL


def test_relapsed_case_without_treatment_history_blocks() -> None:
    case = clean_case()
    case.disease_state.value = "relapsed"
    case.treatments = []
    report = run_missing_information(case)
    item = next(x for x in report.items if x.field == "prior treatment history")
    assert item.priority.value == "critical"
    assert item.recommendation_blocking is True
    assert report.disposition == MissingInformationDisposition.BLOCKED


def test_existing_missing_item_is_preserved_and_prioritized() -> None:
    case = clean_case()
    case.missing_items = [
        MissingItem(
            field="bone marrow pathology",
            importance="critical",
            reason="Final pathology is pending.",
            availability="pending",
            recommendation_blocking=True,
        )
    ]
    report = run_missing_information(case)
    item = next(x for x in report.items if x.field == "bone marrow pathology")
    assert item.category == "pathology"
    assert item.action.value == "review"
    assert item.priority_score == 100
    assert report.blocking_count == 1


def test_high_conflict_becomes_blocking_resolution_item() -> None:
    case = clean_case()
    case.conflicts = [
        Conflict(
            conflict_id="C1",
            field="stage",
            value_a="III",
            value_b="IV",
            severity="high",
            source_segment_ids=["S0001", "S0002"],
        )
    ]
    report = run_missing_information(case)
    item = next(x for x in report.items if x.category == "conflict_resolution")
    assert item.recommendation_blocking is True
    assert item.action.value == "resolve_conflict"
    assert item.source_segment_ids == ["S0001", "S0002"]


def test_treatment_or_trial_question_without_molecular_data_is_conditional() -> None:
    case = clean_case()
    case.clinical_question = ClinicalQuestion(
        question_type="relapsed_refractory_treatment",
        question="What treatment or trial options should be discussed?",
    )
    report = run_missing_information(case)
    item = next(x for x in report.items if x.field == "molecular/cytogenetic characterization")
    assert item.category == "molecular"
    assert item.priority.value == "moderate"
    assert item.recommendation_blocking is False


def test_non_treatment_question_does_not_require_molecular_characterization() -> None:
    case = clean_case()
    report = run_missing_information(case)
    assert "molecular/cytogenetic characterization" not in fields(report)


def test_agent_is_deterministic() -> None:
    case = clean_case()
    case.performance_status = None
    first = run_missing_information(case)
    second = run_missing_information(case)
    assert first.model_dump() == second.model_dump()
