from __future__ import annotations

import json
from datetime import date

import pytest

from schemas.safety import SafetyEvidenceType, SafetySeverity
from services.fda_label_adapter import (
    FDALabelClient,
    SafetyRecordAttestation,
    build_attested_safety_store,
)


def test_fda_label_retrieval_requires_attestation_before_store_admission():
    payload = {
        "results": [
            {
                "effective_time": "20260801",
                "set_id": "set-123",
                "id": "spl-456",
                "openfda": {
                    "generic_name": ["Example Drug"],
                    "application_number": ["NDA000001"],
                },
                "contraindications": [
                    "Example Drug is contraindicated in patients with Example Condition."
                ],
                "warnings_and_cautions": [
                    "Monitor Example Parameter before and during treatment."
                ],
            }
        ]
    }

    def transport(url, timeout):
        assert url.startswith("https://api.fda.gov/drug/label.json?")
        return json.dumps(payload).encode("utf-8")

    candidates = FDALabelClient(transport=transport).fetch_sections(
        therapy="Example Drug",
        accessed_date=date(2026, 8, 16),
    )
    assert len(candidates) == 2
    contraindication_index = next(i for i, c in enumerate(candidates) if c.section == "contraindications")

    store = build_attested_safety_store(
        candidates,
        [
            SafetyRecordAttestation(
                candidate_index=contraindication_index,
                evidence_id="FDA-SAFE-EXAMPLE-001",
                evidence_type=SafetyEvidenceType.CONTRAINDICATION,
                severity=SafetySeverity.CRITICAL,
                safety_issue="Example Condition contraindication",
                exact_excerpt="Example Drug is contraindicated in patients with Example Condition.",
                therapy_terms=("Example Drug",),
                trigger_terms=("Example Condition",),
                contraindication=True,
            )
        ],
    )

    assert len(store.records) == 1
    record = store.records[0]
    assert record.source_verified is True
    assert record.human_verified is True
    assert record.contraindication is True
    assert record.source_id == "set-123"


def test_fda_attestation_rejects_non_source_excerpt():
    payload = {
        "results": [
            {
                "effective_time": "20260801",
                "set_id": "set-123",
                "warnings": ["Exact FDA source sentence."],
            }
        ]
    }

    def transport(url, timeout):
        return json.dumps(payload).encode("utf-8")

    candidates = FDALabelClient(transport=transport).fetch_sections(therapy="Example Drug")

    with pytest.raises(ValueError, match="not an exact span"):
        build_attested_safety_store(
            candidates,
            [
                SafetyRecordAttestation(
                    candidate_index=0,
                    evidence_id="FDA-SAFE-BAD-001",
                    evidence_type=SafetyEvidenceType.WARNING,
                    severity=SafetySeverity.HIGH,
                    safety_issue="Invented warning",
                    exact_excerpt="This sentence was not present in the label.",
                    therapy_terms=("Example Drug",),
                )
            ],
        )
