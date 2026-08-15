from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

from qualification.cases import CASES


QUALIFICATION_SUITE_VERSION = "1.0.0"
QUALIFICATION_PROTOCOL_VERSION = "1.0.0"
EXTRACTION_PROMPT_VERSION = "1.0.0"
SCORING_VERSION = "1.0.0"
SEMANTIC_INTEGRITY_VERSION = "1.0.0"
NORMALIZATION_VERSION = "1.0.0"
TARGET_REPEATABILITY_RUNS = 5
EXPECTED_CASE_IDS = tuple(f"Q{i:02d}" for i in range(1, 11))


def suite_manifest() -> dict:
    """Return the immutable logical manifest used to identify qualification v1.0.

    The fingerprint intentionally includes every gold-case field. Any modification
    to a narrative, expectation, safety condition, or case ordering changes the
    fingerprint and prevents accidental aggregation with prior repeatability runs.
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
    }


def assert_frozen_suite_shape() -> None:
    actual = tuple(case.case_id for case in CASES)
    if actual != EXPECTED_CASE_IDS:
        raise RuntimeError(
            "Qualification Suite v1.0 case membership/order changed without a protocol version update: "
            f"expected {EXPECTED_CASE_IDS}, got {actual}."
        )
