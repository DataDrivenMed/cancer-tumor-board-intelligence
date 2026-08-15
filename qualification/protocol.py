from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from qualification.cases import CASES


QUALIFICATION_SUITE_VERSION = "1.0.0"
QUALIFICATION_PROTOCOL_VERSION = "1.0.0"
EXTRACTION_PROMPT_VERSION = "1.0.0"
SCORING_VERSION = "1.0.0"
SEMANTIC_INTEGRITY_VERSION = "1.0.0"
NORMALIZATION_VERSION = "1.0.0"
TARGET_REPEATABILITY_RUNS = 5
EXPECTED_CASE_IDS = tuple(f"Q{i:02d}" for i in range(1, 11))

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_FROZEN_SOURCE_PATHS = (
    "qualification/cases.py",
    "agents/extraction.py",
    "qualification/scoring.py",
    "services/extraction_normalization.py",
    "services/conflict_consistency.py",
    "services/semantic_integrity.py",
)


def _sha256_file(relative_path: str) -> str:
    path = _PROJECT_ROOT / relative_path
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen_source_hashes() -> dict[str, str]:
    """Hash implementation files that define the frozen v1 qualification behavior."""
    return {relative_path: _sha256_file(relative_path) for relative_path in _FROZEN_SOURCE_PATHS}


def suite_manifest() -> dict:
    """Return the logical and implementation manifest for Qualification Suite v1.0.

    The fingerprint covers every gold-case field plus the extraction prompt/schema,
    scorer, normalization, conflict consistency, and semantic-integrity source files.
    Any substantive change therefore produces a different fingerprint and cannot be
    silently mixed into an in-progress repeatability study.
    """
    case_rows = [asdict(case) for case in CASES]
    return {
        "qualification_suite_version": QUALIFICATION_SUITE_VERSION,
        "qualification_protocol_version": QUALIFICATION_PROTOCOL_VERSION,
        "extraction_prompt_version": EXTRACTION_PROMPT_VERSION,
        "scoring_version": SCORING_VERSION,
        "semantic_integrity_version": SEMANTIC_INTEGRITY_VERSION,
        "normalization_version": NORMALIZATION_VERSION,
        "case_ids": [case.case_id for case in CASES],
        "cases": case_rows,
        "frozen_source_hashes": frozen_source_hashes(),
    }


def suite_fingerprint() -> str:
    canonical = json.dumps(suite_manifest(), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def protocol_metadata() -> dict:
    return {
        "qualification_suite_version": QUALIFICATION_SUITE_VERSION,
        "qualification_protocol_version": QUALIFICATION_PROTOCOL_VERSION,
        "extraction_prompt_version": EXTRACTION_PROMPT_VERSION,
        "scoring_version": SCORING_VERSION,
        "semantic_integrity_version": SEMANTIC_INTEGRITY_VERSION,
        "normalization_version": NORMALIZATION_VERSION,
        "target_repeatability_runs": TARGET_REPEATABILITY_RUNS,
        "suite_fingerprint": suite_fingerprint(),
        "frozen_source_hashes": frozen_source_hashes(),
    }


def assert_frozen_suite_shape() -> None:
    actual = tuple(case.case_id for case in CASES)
    if actual != EXPECTED_CASE_IDS:
        raise RuntimeError(
            "Qualification Suite v1.0 case membership/order changed without a protocol version update: "
            f"expected {EXPECTED_CASE_IDS}, got {actual}."
        )
