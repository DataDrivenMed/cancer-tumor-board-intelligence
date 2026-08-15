from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from qualification.remediation_cases_v24 import (
    REMEDIATION_CASES_V24,
    REMEDIATION_REPEAT_CASE_IDS_V24,
    REMEDIATION_REPEAT_COUNT_V24,
)


REMEDIATION_SUITE_VERSION = "2.4.0"
REMEDIATION_PROTOCOL_VERSION = "2.4.0"
EXTRACTION_VERSION = "2.4.0"
SCORING_VERSION = "2.4.0"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FROZEN_IMPLEMENTATION_PATHS = (
    "agents/extraction_v24.py",
    "agents/extraction_v22.py",
    "agents/extraction_v21.py",
    "qualification/scoring_v24.py",
    "qualification/scoring_v22.py",
    "qualification/scoring_v21.py",
    "schemas/case.py",
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
    "qualification/remediation_cases_v24.py",
    "qualification/remediation_protocol_v24.py",
)


def _sha256_file(relative_path: str) -> str:
    return hashlib.sha256((PROJECT_ROOT / relative_path).read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    return {path: _sha256_file(path) for path in FROZEN_IMPLEMENTATION_PATHS + REMEDIATION_SOURCE_PATHS}


def assert_remediation_suite_shape_v24() -> None:
    ids = tuple(case.case_id for case in REMEDIATION_CASES_V24)
    expected = tuple(f"X{i:02d}" for i in range(1, 13))
    if ids != expected:
        raise RuntimeError(f"v2.4 remediation membership/order changed: expected {expected}, got {ids}.")
    if len(set(ids)) != len(ids):
        raise RuntimeError("v2.4 remediation case IDs must be unique.")
    if not set(REMEDIATION_REPEAT_CASE_IDS_V24).issubset(set(ids)):
        raise RuntimeError("v2.4 repeated subset contains an unknown case ID.")
    if len(REMEDIATION_REPEAT_CASE_IDS_V24) != 6:
        raise RuntimeError("v2.4 repeated subset must contain exactly six frozen cases.")
    if REMEDIATION_REPEAT_COUNT_V24 != 3:
        raise RuntimeError("v2.4 repeat count must remain exactly three.")


def remediation_manifest_v24() -> dict:
    assert_remediation_suite_shape_v24()
    return {
        "remediation_suite_version": REMEDIATION_SUITE_VERSION,
        "remediation_protocol_version": REMEDIATION_PROTOCOL_VERSION,
        "extraction_version": EXTRACTION_VERSION,
        "scoring_version": SCORING_VERSION,
        "case_ids": [case.case_id for case in REMEDIATION_CASES_V24],
        "repeat_case_ids": list(REMEDIATION_REPEAT_CASE_IDS_V24),
        "repeat_count": REMEDIATION_REPEAT_COUNT_V24,
        "cases": [asdict(case) for case in REMEDIATION_CASES_V24],
        "source_hashes": source_hashes(),
    }


def remediation_fingerprint_v24() -> str:
    canonical = json.dumps(remediation_manifest_v24(), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def remediation_protocol_metadata_v24() -> dict:
    planned_executions = len(REMEDIATION_CASES_V24) + len(REMEDIATION_REPEAT_CASE_IDS_V24) * REMEDIATION_REPEAT_COUNT_V24
    return {
        "remediation_suite_version": REMEDIATION_SUITE_VERSION,
        "remediation_protocol_version": REMEDIATION_PROTOCOL_VERSION,
        "extraction_version": EXTRACTION_VERSION,
        "scoring_version": SCORING_VERSION,
        "case_count": len(REMEDIATION_CASES_V24),
        "repeat_case_count": len(REMEDIATION_REPEAT_CASE_IDS_V24),
        "repeat_count": REMEDIATION_REPEAT_COUNT_V24,
        "planned_executions": planned_executions,
        "remediation_fingerprint": remediation_fingerprint_v24(),
        "source_hashes": source_hashes(),
        "acceptance_policy": {
            "green": "30/30 strict overall passes, 100% exact provenance, zero prohibited assertions, zero unsupported provenance assertions, zero semantic-integrity errors, and every repeated case 3/3",
            "amber": "29/30 strict overall passes with 100% exact provenance, zero prohibited/unsupported assertions, zero semantic-integrity errors, and no repeated case failing more than once",
            "red": "28/30 or fewer strict passes, any provenance/safety failure, any semantic-integrity error, or any repeated case failing more than once",
        },
    }
