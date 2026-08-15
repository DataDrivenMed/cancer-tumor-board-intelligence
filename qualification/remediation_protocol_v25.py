from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from qualification.remediation_cases_v25 import (
    REMEDIATION_CASES_V25,
    REMEDIATION_REPEAT_CASE_IDS_V25,
    REMEDIATION_REPEAT_COUNT_V25,
)

REMEDIATION_SUITE_VERSION = "2.5.0"
REMEDIATION_PROTOCOL_VERSION = "2.5.0"
EXTRACTION_VERSION = "2.5.0"
SCORING_VERSION = "2.5.0"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FROZEN_IMPLEMENTATION_PATHS = (
    "agents/extraction_v25.py",
    "agents/extraction_v24.py",
    "agents/extraction_v22.py",
    "agents/extraction_v21.py",
    "qualification/scoring_v25.py",
    "qualification/scoring_v24.py",
    "qualification/scoring_v22.py",
    "qualification/scoring_v21.py",
    "schemas/case.py",
    "services/extraction_hardening_v25.py",
    "services/semantic_integrity_v25.py",
    "services/clinical_reconciliation_v24.py",
    "services/clinical_canonicalization_v22.py",
    "services/extraction_audit.py",
    "services/normalization_pipeline.py",
    "services/extraction_normalization.py",
    "services/disease_state_resolver.py",
    "services/treatment_completeness.py",
    "services/conflict_consistency.py",
    "services/semantic_integrity.py",
    "services/model_gateway.py",
)
REMEDIATION_SOURCE_PATHS = (
    "qualification/remediation_cases_v25.py",
    "qualification/remediation_protocol_v25.py",
)


def _sha256_file(relative_path: str) -> str:
    return hashlib.sha256((PROJECT_ROOT / relative_path).read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    return {path: _sha256_file(path) for path in FROZEN_IMPLEMENTATION_PATHS + REMEDIATION_SOURCE_PATHS}


def assert_remediation_suite_shape_v25() -> None:
    ids = tuple(case.case_id for case in REMEDIATION_CASES_V25)
    expected = tuple(f"Y{i:02d}" for i in range(1, 13))
    if ids != expected:
        raise RuntimeError(f"v2.5 remediation membership/order changed: expected {expected}, got {ids}.")
    if len(set(ids)) != len(ids):
        raise RuntimeError("v2.5 remediation case IDs must be unique.")
    if not set(REMEDIATION_REPEAT_CASE_IDS_V25).issubset(set(ids)):
        raise RuntimeError("v2.5 repeated subset contains an unknown case ID.")
    if len(REMEDIATION_REPEAT_CASE_IDS_V25) != 6:
        raise RuntimeError("v2.5 repeated subset must contain exactly six frozen cases.")
    if REMEDIATION_REPEAT_COUNT_V25 != 3:
        raise RuntimeError("v2.5 repeat count must remain exactly three.")


def remediation_manifest_v25() -> dict:
    assert_remediation_suite_shape_v25()
    return {
        "remediation_suite_version": REMEDIATION_SUITE_VERSION,
        "remediation_protocol_version": REMEDIATION_PROTOCOL_VERSION,
        "extraction_version": EXTRACTION_VERSION,
        "scoring_version": SCORING_VERSION,
        "case_ids": [case.case_id for case in REMEDIATION_CASES_V25],
        "repeat_case_ids": list(REMEDIATION_REPEAT_CASE_IDS_V25),
        "repeat_count": REMEDIATION_REPEAT_COUNT_V25,
        "cases": [asdict(case) for case in REMEDIATION_CASES_V25],
        "source_hashes": source_hashes(),
    }


def remediation_fingerprint_v25() -> str:
    canonical = json.dumps(remediation_manifest_v25(), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def remediation_protocol_metadata_v25() -> dict:
    planned = len(REMEDIATION_CASES_V25) + len(REMEDIATION_REPEAT_CASE_IDS_V25) * REMEDIATION_REPEAT_COUNT_V25
    return {
        "remediation_suite_version": REMEDIATION_SUITE_VERSION,
        "remediation_protocol_version": REMEDIATION_PROTOCOL_VERSION,
        "extraction_version": EXTRACTION_VERSION,
        "scoring_version": SCORING_VERSION,
        "case_count": len(REMEDIATION_CASES_V25),
        "repeat_case_count": len(REMEDIATION_REPEAT_CASE_IDS_V25),
        "repeat_count": REMEDIATION_REPEAT_COUNT_V25,
        "planned_executions": planned,
        "remediation_fingerprint": remediation_fingerprint_v25(),
        "source_hashes": source_hashes(),
        "acceptance_policy": {
            "green": "30/30 strict overall passes, 100% exact provenance, zero prohibited assertions, zero unsupported provenance assertions, zero semantic-integrity errors, no duplicate treatment episodes, deterministic missing-information ontology consistency, and every repeated case 3/3",
            "amber": "29/30 strict overall passes with all safety, provenance, duplicate-treatment, and ontology-integrity gates perfect, and no repeated case failing more than once",
            "red": "28/30 or fewer strict passes, any provenance/safety failure, any semantic-integrity error, any duplicate treatment episode, any ontology mismatch, or any repeated case failing more than once",
        },
    }
