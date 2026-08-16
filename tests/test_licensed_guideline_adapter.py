from datetime import date

import pytest

from schemas.guideline import GuidanceStrength
from services.licensed_guideline_adapter import (
    GuidelineRecommendationAttestation,
    LicensedGuidelineMetadata,
    build_licensed_guideline_store,
    serialize_guideline_store,
)


def _metadata():
    return LicensedGuidelineMetadata(
        source_id="LICENSED-AML-001",
        title="Institution-authorized AML guideline",
        organization="Authorized Guideline Organization",
        jurisdiction="US",
        version="1.0",
        accessed_date=date(2026, 8, 16),
    )


def test_licensed_guideline_requires_exact_source_span():
    source_text = "Section A. Exact guideline statement for relapsed AML. Section B."
    attestation = GuidelineRecommendationAttestation(
        recommendation_id="REC-001",
        disease_terms=("acute myeloid leukemia", "aml"),
        disease_states=("relapsed",),
        question_domains=("treatment_management",),
        recommendation_text="Reviewed structured management statement.",
        exact_source_excerpt="Exact guideline statement for relapsed AML.",
        source_locator="Section A",
        strength=GuidanceStrength.STRONG,
    )

    store = build_licensed_guideline_store(
        source_text=source_text,
        metadata=_metadata(),
        attestations=[attestation],
    )
    assert store.sources[0].verified is True
    assert store.sources[0].license_status == "institution_authorized"
    assert store.recommendations[0].source_verified is True
    payload = serialize_guideline_store(store)
    assert payload["sources"][0]["source_id"] == "LICENSED-AML-001"
    assert payload["recommendations"][0]["recommendation_id"] == "REC-001"


def test_licensed_guideline_rejects_excerpt_not_in_source():
    attestation = GuidelineRecommendationAttestation(
        recommendation_id="REC-001",
        disease_terms=("aml",),
        disease_states=("relapsed",),
        question_domains=("treatment_management",),
        recommendation_text="Paraphrase.",
        exact_source_excerpt="Not in source.",
        source_locator="Section A",
    )
    with pytest.raises(ValueError, match="not present"):
        build_licensed_guideline_store(
            source_text="Actual licensed source text.",
            metadata=_metadata(),
            attestations=[attestation],
        )
