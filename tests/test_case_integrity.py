from __future__ import annotations

from datetime import date

from agents.case_integrity import run_case_integrity
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
from schemas.integrity import IntegrityDisposition


def prov(*, verified: bool = True) -> Provenance:
    return Provenance(
        document_id="DOC-1",
        source_excerpt="source text",
        source_segment_ids=["S0001"],
        source_verified=verified,
    )


def fact(field: str, value, *, status: DataStatus = DataStatus.CONFIRMED, verified: bool = True) -> Fact:
    return Fact(field=field, value=value, status=status, provenance=[prov(verified=verified)])


def base_case() -> CancerTumorBoardCase:
    return CancerTumorBoardCase(
        case_id="QA-001",
        diagnosis=fact("diagnosis", "acute myeloid leukemia"),
        disease_state=fact("disease_state", "newly diagnosed"),
        performance_status=fact("ECOG", "1"),
        clinical_question=ClinicalQuestion(question_type="management", question="What should be discussed?"),
    )


def finding_codes(report) -> set[str]:
    return {f.code for f in report.findings}


def test_clean_case_passes_and_routes() -> None:
    report = run_case_integrity(base_case())
    assert report.disposition == IntegrityDisposition.PASS
    assert report.safe_to_route_to_specialists is True
    assert report.requires_human_review is False
    assert report.checks_run == 7
    assert report.checks_passed == 7


def test_unverified_observed_fact_blocks() -> None:
    case = base_case()
    case.diagnosis.provenance[0].source_verified = False
    report = run_case_integrity(case)
    assert report.disposition == IntegrityDisposition.BLOCK
    assert "OBSERVED_FACT_UNVERIFIED_PROVENANCE" in finding_codes(report)
    assert report.safe_to_route_to_specialists is False


def test_unconfirmed_diagnosis_cannot_have_confirmed_disease_state() -> None:
    case = base_case()
    case.diagnosis.status = DataStatus.PENDING
    report = run_case_integrity(case)
    assert report.disposition == IntegrityDisposition.BLOCK
    assert "CONFIRMED_DISEASE_STATE_WITH_UNCONFIRMED_DIAGNOSIS" in finding_codes(report)


def test_recommendation_blocking_missing_item_blocks() -> None:
    case = base_case()
    case.missing_items.append(MissingItem(
        field="bone marrow pathology",
        importance="critical",
        reason="Final pathology is pending.",
        availability="pending",
        recommendation_blocking=True,
    ))
    report = run_case_integrity(case)
    assert report.disposition == IntegrityDisposition.BLOCK
    assert report.recommendation_blocking_count >= 1
    assert "RECOMMENDATION_BLOCKING_INFORMATION_MISSING" in finding_codes(report)


def test_low_severity_unresolved_conflict_warns_but_routes() -> None:
    case = base_case()
    case.conflicts.append(Conflict(
        conflict_id="C-1",
        field="weight",
        value_a="70 kg",
        value_b="71 kg",
        severity="low",
        source_segment_ids=["S0001", "S0002"],
    ))
    report = run_case_integrity(case)
    assert report.disposition == IntegrityDisposition.PASS_WITH_WARNINGS
    assert report.safe_to_route_to_specialists is True
    assert report.requires_human_review is True


def test_high_severity_unresolved_conflict_blocks() -> None:
    case = base_case()
    case.conflicts.append(Conflict(
        conflict_id="C-2",
        field="stage",
        value_a="stage IIIB",
        value_b="stage IV",
        severity="high",
        source_segment_ids=["S0001", "S0002"],
    ))
    report = run_case_integrity(case)
    assert report.disposition == IntegrityDisposition.BLOCK
    assert "UNRESOLVED_SOURCE_CONFLICT" in finding_codes(report)


def test_duplicate_treatment_episode_ids_block() -> None:
    case = base_case()
    tx1 = TreatmentEpisode(episode_id="TX-001", regimen="R-CHOP", treatment_status=TreatmentStatus.STARTED, provenance=[prov()])
    tx2 = TreatmentEpisode(episode_id="TX-001", regimen="R-DHAP", treatment_status=TreatmentStatus.STARTED, provenance=[prov()])
    case.treatments = [tx1, tx2]
    report = run_case_integrity(case)
    assert report.disposition == IntegrityDisposition.BLOCK
    assert "DUPLICATE_TREATMENT_EPISODE_ID" in finding_codes(report)


def test_treatment_end_before_start_blocks() -> None:
    case = base_case()
    case.treatments = [TreatmentEpisode(
        episode_id="TX-001",
        regimen="azacitidine",
        treatment_status=TreatmentStatus.COMPLETED,
        start_date=date(2026, 2, 1),
        end_date=date(2026, 1, 1),
        provenance=[prov()],
    )]
    report = run_case_integrity(case)
    assert report.disposition == IntegrityDisposition.BLOCK
    assert "TREATMENT_END_BEFORE_START" in finding_codes(report)


def test_planned_treatment_with_end_date_blocks() -> None:
    case = base_case()
    case.treatments = [TreatmentEpisode(
        episode_id="TX-001",
        regimen="decitabine",
        treatment_status=TreatmentStatus.PLANNED,
        end_date=date(2026, 12, 1),
        provenance=[prov()],
    )]
    report = run_case_integrity(case)
    assert report.disposition == IntegrityDisposition.BLOCK
    assert "PLANNED_TREATMENT_HAS_END_DATE" in finding_codes(report)


def test_confirmed_diagnosis_without_value_blocks() -> None:
    case = base_case()
    case.diagnosis.value = None
    report = run_case_integrity(case)
    assert report.disposition == IntegrityDisposition.BLOCK
    assert "CONFIRMED_DIAGNOSIS_WITHOUT_VALUE" in finding_codes(report)


def test_findings_are_deterministic() -> None:
    case = base_case()
    case.diagnosis.status = DataStatus.PENDING
    first = run_case_integrity(case)
    second = run_case_integrity(case)
    assert first.model_dump() == second.model_dump()
