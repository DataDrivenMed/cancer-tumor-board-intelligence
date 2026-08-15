from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from qualification.challenge_cases_v2 import (
    ALL_CHALLENGE_CASES,
    REPEATED_STOCHASTIC_CASE_IDS,
    REPEATED_STOCHASTIC_REPEATS,
    TARGETED_CASES,
    UNSEEN_CASES,
)


CHALLENGE_SUITE_VERSION = "2.0.0"
CHALLENGE_PROTOCOL_VERSION = "2.0.0"
TARGETED_STREAM_VERSION = "1.0.0"
UNSEEN_STREAM_VERSION = "1.0.0"
STOCHASTIC_STREAM_VERSION = "1.0.0"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FROZEN_IMPLEMENTATION_PATHS = (
    "agents/extraction.py",
    "qualification/scoring.py",
    "services/extraction_normalization.py",
    "services/conflict_consistency.py",
    "services/semantic_integrity.py",
)
CHALLENGE_SOURCE_PATHS = (
    "qualification/challenge_cases_v2.py",
    "qualification/challenge_protocol_v2.py",
)


def _sha256_file(relative_path: str) -> str:
    return hashlib.sha256((PROJECT_ROOT / relative_path).read_bytes()).hexdigest()


def source_hashes() -> dict[str, str]:
    paths = FROZEN_IMPLEMENTATION_PATHS + CHALLENGE_SOURCE_PATHS
    return {path: _sha256_file(path) for path in paths}


def assert_challenge_suite_shape() -> None:
    targeted_ids = tuple(case.case_id for case in TARGETED_CASES)
    unseen_ids = tuple(case.case_id for case in UNSEEN_CASES)
    expected_targeted = tuple(f"T{i:02d}" for i in range(1, 11))
    expected_unseen = tuple(f"U{i:02d}" for i in range(1, 11))
    if targeted_ids != expected_targeted:
        raise RuntimeError(f"Targeted challenge membership/order changed: expected {expected_targeted}, got {targeted_ids}.")
    if unseen_ids != expected_unseen:
        raise RuntimeError(f"Unseen challenge membership/order changed: expected {expected_unseen}, got {unseen_ids}.")
    all_ids = {case.case_id for case in ALL_CHALLENGE_CASES}
    if len(all_ids) != len(ALL_CHALLENGE_CASES):
        raise RuntimeError("Challenge case IDs must be unique.")
    if not set(REPEATED_STOCHASTIC_CASE_IDS).issubset(all_ids):
        raise RuntimeError("Repeated stochastic subset contains an unknown case ID.")


def challenge_manifest() -> dict:
    assert_challenge_suite_shape()
    return {
        "challenge_suite_version": CHALLENGE_SUITE_VERSION,
        "challenge_protocol_version": CHALLENGE_PROTOCOL_VERSION,
        "targeted_stream_version": TARGETED_STREAM_VERSION,
        "unseen_stream_version": UNSEEN_STREAM_VERSION,
        "stochastic_stream_version": STOCHASTIC_STREAM_VERSION,
        "targeted_case_ids": [c.case_id for c in TARGETED_CASES],
        "unseen_case_ids": [c.case_id for c in UNSEEN_CASES],
        "repeated_stochastic_case_ids": list(REPEATED_STOCHASTIC_CASE_IDS),
        "repeated_stochastic_repeats": REPEATED_STOCHASTIC_REPEATS,
        "cases": [asdict(c) for c in ALL_CHALLENGE_CASES],
        "source_hashes": source_hashes(),
    }


def challenge_fingerprint() -> str:
    canonical = json.dumps(challenge_manifest(), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def challenge_protocol_metadata() -> dict:
    return {
        "challenge_suite_version": CHALLENGE_SUITE_VERSION,
        "challenge_protocol_version": CHALLENGE_PROTOCOL_VERSION,
        "targeted_stream_version": TARGETED_STREAM_VERSION,
        "unseen_stream_version": UNSEEN_STREAM_VERSION,
        "stochastic_stream_version": STOCHASTIC_STREAM_VERSION,
        "targeted_case_count": len(TARGETED_CASES),
        "unseen_case_count": len(UNSEEN_CASES),
        "repeated_stochastic_case_count": len(REPEATED_STOCHASTIC_CASE_IDS),
        "repeated_stochastic_repeats": REPEATED_STOCHASTIC_REPEATS,
        "challenge_fingerprint": challenge_fingerprint(),
        "source_hashes": source_hashes(),
        "acceptance_policy": {
            "green": "100% strict overall pass across a stream, 100% exact provenance, zero prohibited assertions, zero unsupported provenance assertions",
            "amber": ">=95% strict overall pass with 100% exact provenance, zero prohibited/unsupported assertions, and no case failing more than once in the repeated subset",
            "red": "<95% strict overall pass, any provenance failure, any prohibited/unsupported assertion, or recurrent failure of the same repeated-subset case",
        },
    }
