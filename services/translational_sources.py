from __future__ import annotations

from schemas.translational import (
    TranslationalDirection,
    TranslationalEvidenceRecord,
    TranslationalEvidenceStore,
    TranslationalEvidenceTier,
)


# Production store is intentionally empty. Verified translational evidence must be
# ingested through a governed, source-traceable process rather than model memory.
PRODUCTION_TRANSLATIONAL_STORE = TranslationalEvidenceStore()


SYNTHETIC_TRANSLATIONAL_STORE = TranslationalEvidenceStore(
    records=[
        TranslationalEvidenceRecord(
            evidence_id="syn-flt3-itd-mech-001",
            source_id="synthetic-translational-fixture",
            gene="FLT3",
            alteration_terms=["FLT3-ITD", "internal tandem duplication", "ITD"],
            disease_terms=["acute myeloid leukemia", "AML"],
            model_system="synthetic human translational cohort",
            evidence_tier=TranslationalEvidenceTier.T1_HUMAN_TRANSLATIONAL,
            direction=TranslationalDirection.SUPPORTS_MECHANISM,
            mechanism="Synthetic fixture: constitutive FLT3 signaling associated with proliferative signaling in AML.",
            intervention=None,
            source_excerpt="Synthetic fixture excerpt for deterministic validation only.",
            source_locator="synthetic://translational/flt3-itd",
            source_verified=True,
            human_verified=True,
            synthetic=True,
        ),
        TranslationalEvidenceRecord(
            evidence_id="syn-tp53-resistance-001",
            source_id="synthetic-translational-fixture",
            gene="TP53",
            alteration_terms=["mutation", "pathogenic variant"],
            disease_terms=["acute myeloid leukemia", "AML"],
            model_system="synthetic preclinical model",
            evidence_tier=TranslationalEvidenceTier.T2_IN_VIVO_PRECLINICAL,
            direction=TranslationalDirection.SUPPORTS_RESISTANCE,
            mechanism="Synthetic fixture: TP53-disrupted model demonstrates resistance-associated phenotype.",
            intervention="synthetic investigational therapy",
            source_excerpt="Synthetic fixture excerpt for deterministic validation only.",
            source_locator="synthetic://translational/tp53",
            source_verified=True,
            human_verified=True,
            synthetic=True,
        ),
    ]
)
