from __future__ import annotations

from schemas.safety import (
    SafetyEvidenceRecord,
    SafetyEvidenceStore,
    SafetyEvidenceType,
    SafetySeverity,
)
from services.production_evidence_config import EvidenceConfigStatus, load_channel_payload


def _load_production_safety_store() -> tuple[SafetyEvidenceStore, EvidenceConfigStatus]:
    payload, status = load_channel_payload("safety")
    if payload is None:
        return SafetyEvidenceStore(), status

    try:
        if isinstance(payload, dict):
            records_payload = payload.get("records", [])
        elif isinstance(payload, list):
            records_payload = payload
        else:
            raise ValueError("Safety evidence configuration must be a JSON object or list.")
        store = SafetyEvidenceStore(
            records=[SafetyEvidenceRecord.model_validate(x) for x in records_payload]
        )
        return store, EvidenceConfigStatus(
            channel="safety",
            configured=True,
            loaded=True,
            record_count=len(store.records),
            configuration_origin=status.configuration_origin,
        )
    except Exception as exc:
        return SafetyEvidenceStore(), EvidenceConfigStatus(
            channel="safety",
            configured=True,
            loaded=False,
            error=f"{type(exc).__name__}: {exc}",
            configuration_origin=status.configuration_origin,
        )


# Real safety evidence must be independently verified and supplied through
# SAFETY_EVIDENCE_JSON or SAFETY_EVIDENCE_PATH. Invalid configuration fails closed.
PRODUCTION_SAFETY_STORE, PRODUCTION_SAFETY_STATUS = _load_production_safety_store()


def synthetic_safety_store() -> SafetyEvidenceStore:
    """Fictional safety evidence for deterministic validation only.

    These records are not clinical evidence and are blocked in production mode.
    """
    return SafetyEvidenceStore(
        records=[
            SafetyEvidenceRecord(
                evidence_id="SYN-SAFE-001",
                source_id="synthetic-label-001",
                source_title="Synthetic Drug X Safety Label",
                source_locator="Warnings > Cardiac monitoring",
                source_excerpt="Synthetic Drug X may prolong the QT interval; potassium, magnesium, and ECG assessment are required before treatment.",
                source_verified=True,
                human_verified=True,
                synthetic=True,
                therapy_terms=["synthetic drug x"],
                evidence_type=SafetyEvidenceType.MONITORING,
                severity=SafetySeverity.HIGH,
                safety_issue="QT-prolongation monitoring requirement",
                required_parameters=["potassium", "magnesium", "ecg"],
            ),
            SafetyEvidenceRecord(
                evidence_id="SYN-SAFE-002",
                source_id="synthetic-label-002",
                source_title="Synthetic Drug Y Safety Label",
                source_locator="Contraindications",
                source_excerpt="Synthetic Drug Y is contraindicated in patients with the represented synthetic hypersensitivity condition.",
                source_verified=True,
                human_verified=True,
                synthetic=True,
                therapy_terms=["synthetic drug y"],
                trigger_terms=["synthetic hypersensitivity"],
                evidence_type=SafetyEvidenceType.CONTRAINDICATION,
                severity=SafetySeverity.CRITICAL,
                safety_issue="Synthetic hypersensitivity contraindication",
                required_parameters=[],
                contraindication=True,
            ),
        ]
    )
