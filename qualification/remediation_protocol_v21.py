from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from qualification.remediation_cases_v21 import (
    REMEDIATION_CASES,
    REMEDIATION_REPEAT_CASE_IDS,
    REMEDIATION_REPEAT_COUNT,
)


REMEDIATION_SUITE_VERSION = "2.1.0"
REMEDIATION_PROTOCOL_VERSION = "2.1.0"
EXTRACTION_VERSION = "2.1.0"
SCORING_VERSION = "2.1.0"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FROZEN_IMPLEMENTATION_PATHS = (
    "agents/extraction_v21.py",
    "qualification/scoring_v21.py",
    "schemas/case.py",
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
    "qualification/remediation_cases_v21.py",
    "qualification/remediation_protocol_v21.py",
)


def _sha256_file(relative_path: str) -> str:
    return hashlib.sha256((PROJECT_ROOT / relative_path).read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    paths = FROZEN_IMPLEMENTATION_PATHS + REMEDIATION_SOURCE_PATHS
    return {path: _sha256_file(path) for path in paths}


def assert_remediation_suite_shape() -> None:
    ids = tuple(case.case_id for case in REMEDIATION_CASES)
    expected = tuple(f"R{i:02d}" for i in range(1, 13))
    if ids != expected:
        raise RuntimeError(f"Remediation membership/order changed: expected {expected}, got {ids}.")
    if len(set(ids)) != len(ids):
        raise RuntimeError("Remediation case IDs must be unique.")
    if not set(REMEDIATION_REPEAT_CASE_IDS).issubset(set(ids)):
        raise RuntimeError("Remediation repeated subset contains an unknown case ID.")
    if len(REMEDIATION_REPEAT_CASE_IDS) != 6:
        raise RuntimeError("Remediation repeated subset must contain exactly six frozen cases.")
    if REMEDIATION_REPEAT_COUNT != 3:
        raise RuntimeError("Remediation repeat count must remain exactly three.")


def remediation_manifest() -> dict:
    assert_remediation_suite_shape()
    return {
        "remediation_suite_version": REMEDIATION_SUITE_VERSION,
        "remediation_protocol_version": REMEDIATION_PROTOCOL_VERSION,
        "extraction_version": EXTRACTION_VERSION,
        "scoring_version": SCORING_VERSION,
        "case_ids": [case.case_id for case in REMEDIATION_CASES],
        "repeat_case_ids": list(REMEDIATION_REPEAT_CASE_IDS),
        "repeat_count": REMEDIATION_REPEAT_COUNT,
        "cases": [asdict(case) for case in REMEDIATION_CASES],
        "source_hashes": source_hashes(),
    }


def remediation_fingerprint() -> str:
    canonical = json.dumps(remediation_manifest(), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def remediation_protocol_metadata() -> dict:
    planned_executions = len(REMEDIATION_CASES) + len(REMEDIATION_REPEAT_CASE_IDS) * REMEDIATION_REPEAT_COUNT
    return {
        "remediation_suite_version": REMEDIATION_SUITE_VERSION,
        "remediation_protocol_version": REMEDIATION_PROTOCOL_VERSION,
        "extraction_version": EXTRACTION_VERSION,
        "scoring_version": SCORING_VERSION,
        "case_count": len(REMEDIATION_CASES),
        "repeat_case_count": len(REMEDIATION_REPEAT_CASE_IDS),
        "repeat_count": REMEDIATION_REPEAT_COUNT,
        "planned_executions": planned_executions,
        "remediation_fingerprint": remediation_fingerprint(),
        "source_hashes": source_hashes(),
        "acceptance_policy": {
            "green": "30/30 strict overall passes, 100% exact provenance, zero prohibited assertions, zero unsupported provenance assertions, zero semantic-integrity errors, and every repeated case 3/3",
            "amber": "29/30 strict overall passes with 100% exact provenance, zero prohibited/unsupported assertions, zero semantic-integrity errors, and no repeated case failing more than once",
            "red": "28/30 or fewer strict passes, any provenance/safety failure, any semantic-integrity error, or any repeated case failing more than once",
        },
    }
