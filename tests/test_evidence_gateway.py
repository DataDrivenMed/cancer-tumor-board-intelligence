from __future__ import annotations

from datetime import date

from agents.guideline import GuidelineAgent
from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Fact, Provenance
from schemas.evidence_gateway import (
    EvidenceIngestionPackage,
    EvidenceRecommendationRecord,
    EvidenceSourceManifest,
    EvidenceVerificationCode,
)
from schemas.guideline import GuidanceSourceType
from services.evidence_gateway import normalized_sha256, verify_evidence_package


SOURCE_TEXT = "Synthetic authorized source. Exact AML statement appears here."


def _manifest(**overrides) -> EvidenceSourceManifest:
    data = dict(
        source_id="SRC-001",
        title="Synthetic authorized source",
        organization="Test Authority",
        source_type=GuidanceSourceType.FORMAL_GUIDELINE,
        jurisdiction="US",
        url="https://example.org/guideline",
        version="1.0",
        accessed_date=date(2026, 8, 15),
        license_status="institution_authorized",
        expected_content_sha256=normalized_sha256(SOURCE_TEXT),
        human_verified=True,
    )
    data.update(overrides)
    return EvidenceSourceManifest(**data)


def _record(**overrides) -> EvidenceRecommendationRecord:
    data = dict(
        recommendation_id="REC-001",
        source_id="SRC-001",
        disease_terms=["acute myeloid leukemia"],
        disease_states=["relapsed"],
        question_domains=["treatment_management"],
        recommendation_text="Validated synthetic recommendation for testing.",
        source_excerpt="Exact AML statement appears here.",
        source_locator="section:test",
        human_verified=True,
    )
    data.update(overrides)
    return EvidenceRecommendationRecord(**data)


def _case() -> CancerTumorBoardCase:
    p = Provenance(document_id="D", source_excerpt="x", source_segment_ids=["S1"], source_verified=True)
    return CancerTumorBoardCase(
        case_id="CASE-1",
        diagnosis=Fact(field="diagnosis", value="acute myeloid leukemia", provenance=[p]),
        disease_state=Fact(field="disease_state", value="relapsed", provenance=[p]),
        performance_status=Fact(field="ECOG", value="1", provenance=[p]),
        clinical_question=ClinicalQuestion(question_type="management", question="What treatment should be discussed?"),
    )


def test_verified_package_enters_store_and_supports_guideline_match() -> None:
    package = EvidenceIngestionPackage(manifest=_manifest(), source_text=SOURCE_TEXT, recommendations=[_record()])
    result, store = verify_evidence_package(package)

    assert result.status.value == "accepted"
    assert result.source_verified is True
    assert result.can_enter_guideline_store is True
    assert result.accepted_recommendation_ids == ["REC-001"]

    report = GuidelineAgent(store, today=date(2026, 8, 15)).run(_case())
    assert report.status == "completed"
    assert report.can_support_guideline_claim is True
    assert len(report.matched_guidance) == 1


def test_hash_mismatch_rejects_entire_source() -> None:
    package = EvidenceIngestionPackage(
        manifest=_manifest(expected_content_sha256="0" * 64),
        source_text=SOURCE_TEXT,
        recommendations=[_record()],
    )
    result, store = verify_evidence_package(package)

    assert result.status.value == "rejected"
    assert result.can_enter_guideline_store is False
    assert store.sources == ()
    assert EvidenceVerificationCode.CONTENT_HASH_MISMATCH in {f.code for f in result.findings}


def test_non_exact_excerpt_is_rejected_but_verified_source_can_enter_with_limitations() -> None:
    package = EvidenceIngestionPackage(
        manifest=_manifest(),
        source_text=SOURCE_TEXT,
        recommendations=[_record(source_excerpt="Paraphrased AML statement")],
    )
    result, store = verify_evidence_package(package)

    assert result.status.value == "accepted_with_limitations"
    assert result.accepted_recommendation_ids == []
    assert result.rejected_recommendation_ids == ["REC-001"]
    assert len(store.sources) == 1
    assert store.recommendations == ()
    assert EvidenceVerificationCode.RECOMMENDATION_EXCERPT_NOT_EXACT in {f.code for f in result.findings}


def test_unverified_recommendation_is_not_propagated() -> None:
    package = EvidenceIngestionPackage(
        manifest=_manifest(),
        source_text=SOURCE_TEXT,
        recommendations=[_record(human_verified=False)],
    )
    result, store = verify_evidence_package(package)

    assert result.accepted_recommendation_ids == []
    assert store.recommendations == ()
    assert EvidenceVerificationCode.RECOMMENDATION_NOT_HUMAN_VERIFIED in {f.code for f in result.findings}


def test_unknown_license_rejects_source() -> None:
    package = EvidenceIngestionPackage(
        manifest=_manifest(license_status="unknown"),
        source_text=SOURCE_TEXT,
        recommendations=[_record()],
    )
    result, _ = verify_evidence_package(package)

    assert result.status.value == "rejected"
    assert EvidenceVerificationCode.LICENSE_NOT_AUTHORIZED in {f.code for f in result.findings}


def test_synthetic_source_is_blocked_in_production_but_allowed_in_test_mode() -> None:
    manifest = _manifest(source_type=GuidanceSourceType.SYNTHETIC_FIXTURE, license_status="synthetic")
    package = EvidenceIngestionPackage(manifest=manifest, source_text=SOURCE_TEXT, recommendations=[_record()])

    prod_result, _ = verify_evidence_package(package, production_mode=True)
    test_result, test_store = verify_evidence_package(package, production_mode=False)

    assert prod_result.status.value == "rejected"
    assert EvidenceVerificationCode.SYNTHETIC_SOURCE_PRODUCTION_BLOCK in {f.code for f in prod_result.findings}
    assert test_result.status.value == "accepted"
    assert len(test_store.recommendations) == 1


def test_same_input_has_same_hash_and_same_result() -> None:
    package = EvidenceIngestionPackage(manifest=_manifest(), source_text=SOURCE_TEXT, recommendations=[_record()])
    first, _ = verify_evidence_package(package)
    second, _ = verify_evidence_package(package)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
