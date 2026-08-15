from __future__ import annotations

from schemas.safety import (
    SafetyEvidenceRecord,
    SafetyEvidenceStore,
    SafetyEvidenceType,
    SafetySeverity,
)


# Production-safe default. Real safety evidence must be independently verified,
# versioned, and loaded from an authorized source before it can affect synthesis.
PRODUCTION_SAFETY_STORE = SafetyEvidenceStore()


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
                evidence_type=SafetyEvidenceType.CONTRAINDICATION,
                severity=SafetySeverity.CRITICAL,
                safety_issue="Synthetic contraindication",
                required_parameters=[],
                contraindication=True,
            ),
        ]
    )
