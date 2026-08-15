from __future__ import annotations

from datetime import date

from schemas.molecular import (
    ClinicalActionability,
    MolecularEvidenceDirection,
    MolecularEvidenceRecord,
    MolecularEvidenceStore,
    MolecularEvidenceTier,
)


# Production is intentionally empty until disease- and alteration-specific records
# have been independently verified and approved for use.
PRODUCTION_MOLECULAR_STORE = MolecularEvidenceStore()


def build_synthetic_molecular_store() -> MolecularEvidenceStore:
    return MolecularEvidenceStore(
        records=[
            MolecularEvidenceRecord(
                evidence_id="syn-flt3-001",
                source_id="synthetic-molecular-001",
                source_title="Synthetic FLT3 validation fixture",
                source_url="https://example.org/synthetic-flt3",
                source_type=MolecularEvidenceTier.SYNTHETIC,
                jurisdiction="US",
                publication_date=date(2026, 1, 1),
                accessed_date=date(2026, 8, 15),
                disease_terms=["acute myeloid leukemia", "AML"],
                gene="FLT3",
                alteration_terms=["ITD", "internal tandem duplication"],
                direction=MolecularEvidenceDirection.SUPPORTS_SENSITIVITY,
                actionability=ClinicalActionability.ESTABLISHED,
                therapy="synthetic targeted therapy",
                evidence_summary="Synthetic fixture used only to validate disease- and alteration-specific matching.",
                source_excerpt="Synthetic FLT3-ITD evidence statement for validation only.",
                source_locator="synthetic fixture section 1",
                source_verified=True,
                human_verified=True,
                synthetic=True,
            ),
            MolecularEvidenceRecord(
                evidence_id="syn-tp53-001",
                source_id="synthetic-molecular-002",
                source_title="Synthetic TP53 validation fixture",
                source_url="https://example.org/synthetic-tp53",
                source_type=MolecularEvidenceTier.SYNTHETIC,
                jurisdiction="US",
                accessed_date=date(2026, 8, 15),
                disease_terms=["acute myeloid leukemia", "AML"],
                gene="TP53",
                alteration_terms=[],
                direction=MolecularEvidenceDirection.PROGNOSTIC,
                actionability=ClinicalActionability.NOT_ESTABLISHED,
                evidence_summary="Synthetic prognostic fixture with no established therapeutic actionability.",
                source_excerpt="Synthetic TP53 prognostic evidence statement for validation only.",
                source_locator="synthetic fixture section 2",
                source_verified=True,
                human_verified=True,
                synthetic=True,
            ),
        ]
    )
