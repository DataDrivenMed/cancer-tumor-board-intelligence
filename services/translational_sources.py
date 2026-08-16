from __future__ import annotations

from schemas.translational import (
    TranslationalDirection,
    TranslationalEvidenceRecord,
    TranslationalEvidenceStore,
    TranslationalEvidenceTier,
)
from services.production_evidence_config import EvidenceConfigStatus, load_channel_payload


def _load_production_translational_store() -> tuple[TranslationalEvidenceStore, EvidenceConfigStatus]:
    payload, status = load_channel_payload("translational")
    if payload is None:
        return TranslationalEvidenceStore(), status

    try:
        if isinstance(payload, dict):
            records_payload = payload.get("records", [])
        elif isinstance(payload, list):
            records_payload = payload
        else:
            raise ValueError("Translational evidence configuration must be a JSON object or list.")
        store = TranslationalEvidenceStore(
            records=[TranslationalEvidenceRecord.model_validate(x) for x in records_payload]
        )
        return store, EvidenceConfigStatus(
            channel="translational",
            configured=True,
            loaded=True,
            record_count=len(store.records),
            configuration_origin=status.configuration_origin,
        )
    except Exception as exc:
        return TranslationalEvidenceStore(), EvidenceConfigStatus(
            channel="translational",
            configured=True,
            loaded=False,
            error=f"{type(exc).__name__}: {exc}",
            configuration_origin=status.configuration_origin,
        )


# Production is fail-closed until a governed source package is configured through
# TRANSLATIONAL_EVIDENCE_JSON or TRANSLATIONAL_EVIDENCE_PATH.
PRODUCTION_TRANSLATIONAL_STORE, PRODUCTION_TRANSLATIONAL_STATUS = _load_production_translational_store()


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
