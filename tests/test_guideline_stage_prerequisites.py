from __future__ import annotations

from datetime import date

from agents.guideline import GuidelineAgent, GuidelineEvidenceStore
from schemas.case import CancerTumorBoardCase, ClinicalQuestion, DataStatus, Fact, Provenance
from schemas.guideline import GuidanceRecommendation, GuidanceSource, GuidanceSourceType


def _store() -> GuidelineEvidenceStore:
    source = GuidanceSource(
        source_id="SYN-STAGE-GUIDE",
        title="Synthetic stage-dependent consensus fixture",
        organization="Synthetic Qualification Authority",
        source_type=GuidanceSourceType.CONSENSUS_GUIDELINE,
        publication_date=date(2026, 1, 1),
        license_status="synthetic",
        verified=True,
    )
    rec = GuidanceRecommendation(
        recommendation_id="SYN-STAGE-REC",
        source_id=source.source_id,
        disease_terms=["breast cancer"],
        disease_states=["localized"],
        stage_terms=["stage ii"],
        question_domains=["treatment_management"],
        therapy_terms=["synthetic therapy"],
        recommendation_text="Synthetic fixture recommendation for software qualification only.",
        source_excerpt="Synthetic stage II recommendation fixture.",
        source_locator="synthetic:stage-fixture",
        source_verified=True,
    )
    return GuidelineEvidenceStore(sources=(source,), recommendations=(rec,))


def _case(stage: Fact | None) -> CancerTumorBoardCase:
    return CancerTumorBoardCase(
        case_id="STAGE-GUIDE-CASE",
        case_type="synthetic",
        disease_program="breast_oncology",
        tumor_board_type="breast_tumor_board",
        diagnosis=Fact(field="diagnosis", value="breast cancer"),
        disease_state=Fact(field="disease_state", value="localized"),
        stage=stage,
        performance_status=Fact(field="performance_status", value="ECOG 0"),
        clinical_question=ClinicalQuestion(
            question_type="treatment_management",
            question="Discuss treatment management.",
        ),
    )


def _stage(value: str, *, human_verified: bool, source_verified: bool = True) -> Fact:
    return Fact(
        field="stage",
        value=value,
        status=DataStatus.CONFIRMED,
        provenance=[
            Provenance(
                document_id="DOC-STAGE",
                source_excerpt=value,
                source_segment_ids=["S0001"],
                source_verified=source_verified,
            )
        ],
        human_verified=human_verified,
    )


def test_stage_dependent_guidance_requires_explicit_verified_confirmed_stage():
    report = GuidelineAgent(_store()).run(_case(_stage("stage II", human_verified=True)))
    assert report.can_support_guideline_claim is True
    assert len(report.matched_guidance) == 1
    assert "verified_explicit_stage_prerequisite" in report.matched_guidance[0].match_dimensions


def test_stage_dependent_guidance_does_not_match_without_stage():
    report = GuidelineAgent(_store()).run(_case(None))
    assert report.can_support_guideline_claim is False
    assert report.matched_guidance == []
    assert any("stage-dependent" in item for item in report.limitations)


def test_stage_dependent_guidance_does_not_match_unconfirmed_stage():
    report = GuidelineAgent(_store()).run(_case(_stage("stage II", human_verified=False)))
    assert report.can_support_guideline_claim is False


def test_stage_dependent_guidance_does_not_match_unverified_source():
    report = GuidelineAgent(_store()).run(_case(_stage("stage II", human_verified=True, source_verified=False)))
    assert report.can_support_guideline_claim is False


def test_stage_dependent_guidance_does_not_match_wrong_stage():
    report = GuidelineAgent(_store()).run(_case(_stage("stage III", human_verified=True)))
    assert report.can_support_guideline_claim is False


def test_guidance_without_stage_prerequisite_remains_backward_compatible():
    store = _store()
    rec = store.recommendations[0].model_copy(update={"stage_terms": []})
    report = GuidelineAgent(GuidelineEvidenceStore(sources=store.sources, recommendations=(rec,))).run(_case(None))
    assert report.can_support_guideline_claim is True
