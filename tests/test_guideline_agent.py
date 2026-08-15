from __future__ import annotations

from datetime import date

from agents.guideline import GuidelineAgent, GuidelineEvidenceStore
from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Fact, Provenance
from schemas.guideline import (
    GuidanceRecommendation,
    GuidanceSource,
    GuidanceSourceType,
    GuidanceStrength,
)
from services.guideline_sources import synthetic_guideline_store


def _fact(field: str, value: str) -> Fact:
    return Fact(
        field=field,
        value=value,
        provenance=[Provenance(document_id="DOC-1", source_excerpt=value, source_segment_ids=["S1"], source_verified=True)],
    )


def _case(*, diagnosis: str = "acute myeloid leukemia", state: str = "relapsed", question: str = "What treatment should be discussed?") -> CancerTumorBoardCase:
    return CancerTumorBoardCase(
        case_id="GUIDE-CASE-1",
        diagnosis=_fact("diagnosis", diagnosis),
        disease_state=_fact("disease_state", state),
        performance_status=_fact("ECOG", "1"),
        clinical_question=ClinicalQuestion(question_type="treatment_management", question=question),
    )


def _formal_store(*, verified: bool = True, review_due: date | None = date(2099, 1, 1)) -> GuidelineEvidenceStore:
    source = GuidanceSource(
        source_id="FORMAL-1",
        title="Synthetic Formal Guideline Test Record",
        organization="Test Society",
        source_type=GuidanceSourceType.FORMAL_GUIDELINE,
        jurisdiction="US",
        version="test",
        review_due_date=review_due,
        license_status="synthetic",
        verified=verified,
    )
    rec = GuidanceRecommendation(
        recommendation_id="REC-1",
        source_id="FORMAL-1",
        disease_terms=["acute myeloid leukemia", "aml"],
        disease_states=["relapsed"],
        question_domains=["treatment_management"],
        recommendation_text="TEST ONLY: verified source-supported statement.",
        source_excerpt="TEST ONLY exact source excerpt.",
        source_locator="section:test",
        strength=GuidanceStrength.STRONG,
        source_verified=verified,
    )
    return GuidelineEvidenceStore(sources=(source,), recommendations=(rec,))


def test_no_source_means_no_guideline_claim() -> None:
    report = GuidelineAgent().run(_case())
    assert report.status == "source_unavailable"
    assert report.matched_guidance == []
    assert report.can_support_guideline_claim is False


def test_unverified_source_is_not_propagated() -> None:
    report = GuidelineAgent(_formal_store(verified=False)).run(_case())
    assert report.status == "verification_failed"
    assert report.matched_guidance == []
    assert report.can_support_guideline_claim is False


def test_verified_formal_guideline_matches_case() -> None:
    report = GuidelineAgent(_formal_store(), today=date(2026, 8, 15)).run(_case())
    assert report.status == "completed"
    assert report.formal_guideline_matches == 1
    assert report.can_support_guideline_claim is True
    assert report.matched_guidance[0].epistemic_label == "guideline_supported"
    assert report.matched_guidance[0].source_excerpt == "TEST ONLY exact source excerpt."


def test_diagnosis_mismatch_does_not_match() -> None:
    report = GuidelineAgent(_formal_store(), today=date(2026, 8, 15)).run(_case(diagnosis="multiple myeloma"))
    assert report.status == "no_evidence_found"
    assert report.matched_guidance == []


def test_state_mismatch_does_not_match() -> None:
    report = GuidelineAgent(_formal_store(), today=date(2026, 8, 15)).run(_case(state="newly diagnosed"))
    assert report.status == "no_evidence_found"


def test_outdated_source_is_excluded() -> None:
    report = GuidelineAgent(_formal_store(review_due=date(2025, 1, 1)), today=date(2026, 8, 15)).run(_case())
    assert report.status == "no_evidence_found"
    assert report.matched_guidance == []
    assert any("excluded" in warning for warning in report.warnings)


def test_synthetic_source_requires_explicit_opt_in() -> None:
    store = synthetic_guideline_store()
    blocked = GuidelineAgent(store, today=date(2026, 8, 15)).run(_case())
    allowed = GuidelineAgent(store, allow_synthetic=True, today=date(2026, 8, 15)).run(_case())
    assert blocked.status == "verification_failed"
    assert blocked.matched_guidance == []
    assert allowed.status == "completed_with_limitations"
    assert len(allowed.matched_guidance) == 1
    assert allowed.matched_guidance[0].epistemic_label == "synthetic_fixture"
    assert allowed.can_support_guideline_claim is False


def test_authoritative_summary_cannot_be_mislabeled_as_formal_guideline() -> None:
    source = GuidanceSource(
        source_id="SUMMARY-1",
        title="Evidence Summary Test",
        organization="Test Public Agency",
        source_type=GuidanceSourceType.AUTHORITATIVE_EVIDENCE_SUMMARY,
        jurisdiction="US",
        review_due_date=date(2099, 1, 1),
        license_status="public",
        verified=True,
    )
    rec = GuidanceRecommendation(
        recommendation_id="SUMMARY-REC-1",
        source_id="SUMMARY-1",
        disease_terms=["acute myeloid leukemia"],
        disease_states=["relapsed"],
        question_domains=["treatment_management"],
        recommendation_text="TEST evidence-summary statement.",
        source_excerpt="TEST exact evidence-summary excerpt.",
        source_verified=True,
    )
    report = GuidelineAgent(GuidelineEvidenceStore((source,), (rec,)), today=date(2026, 8, 15)).run(_case())
    assert report.status == "completed_with_limitations"
    assert report.formal_guideline_matches == 0
    assert report.can_support_guideline_claim is False
    assert report.matched_guidance[0].epistemic_label == "authoritative_evidence_summary"


def test_same_input_same_store_is_deterministic() -> None:
    agent = GuidelineAgent(_formal_store(), today=date(2026, 8, 15))
    first = agent.run(_case()).model_dump()
    second = agent.run(_case()).model_dump()
    assert first == second
