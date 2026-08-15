from __future__ import annotations

from datetime import date

from agents.guideline import GuidelineEvidenceStore
from schemas.guideline import (
    GuidanceRecommendation,
    GuidanceSource,
    GuidanceSourceType,
    GuidanceStrength,
)


# Production-safe default. No clinical guidance content is bundled until a source has
# been explicitly licensed/authorized, ingested, versioned, hashed, and verified.
PRODUCTION_GUIDELINE_STORE = GuidelineEvidenceStore()


def synthetic_guideline_store() -> GuidelineEvidenceStore:
    """Synthetic evidence only for deterministic software testing and UI demonstrations.

    These statements are intentionally fictional and must never be interpreted as
    clinical guidance. GuidelineAgent requires allow_synthetic=True to use them.
    """
    source = GuidanceSource(
        source_id="SYN-GUIDE-001",
        title="Synthetic Hematologic Malignancy Guidance Fixture",
        organization="Synthetic Validation Authority",
        source_type=GuidanceSourceType.SYNTHETIC_FIXTURE,
        jurisdiction="TEST",
        version="1.0",
        publication_date=date(2026, 1, 1),
        review_due_date=date(2099, 1, 1),
        accessed_date=date(2026, 1, 1),
        license_status="synthetic",
        verified=True,
        content_hash="synthetic-fixture-not-clinical-evidence",
    )
    rec = GuidanceRecommendation(
        recommendation_id="SYN-REC-AML-RELAPSE-001",
        source_id=source.source_id,
        disease_terms=["acute myeloid leukemia", "aml"],
        disease_states=["relapsed"],
        question_domains=["treatment_management"],
        recommendation_text="SYNTHETIC FIXTURE: discuss options Alpha and Beta in the validation environment.",
        source_excerpt="SYNTHETIC FIXTURE ONLY: relapsed AML management statement Alpha/Beta.",
        source_locator="fixture:section-1",
        strength=GuidanceStrength.NOT_STATED,
        evidence_level="synthetic",
        source_verified=True,
    )
    return GuidelineEvidenceStore(sources=(source,), recommendations=(rec,))
