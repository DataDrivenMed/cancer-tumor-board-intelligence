from __future__ import annotations

from qualification.challenge_cases_v2 import (
    ALL_CHALLENGE_CASES,
    REPEATED_STOCHASTIC_CASE_IDS,
    REPEATED_STOCHASTIC_REPEATS,
    TARGETED_CASES,
    UNSEEN_CASES,
)
from qualification.challenge_protocol_v2 import (
    assert_challenge_suite_shape,
    challenge_fingerprint,
    challenge_protocol_metadata,
)
from services.challenge_validation import aggregate_challenge_study, expected_ids_for_stream, new_challenge_study


def test_challenge_suite_shape_and_membership():
    assert_challenge_suite_shape()
    assert len(TARGETED_CASES) == 10
    assert len(UNSEEN_CASES) == 10
    assert len(ALL_CHALLENGE_CASES) == 20
    assert tuple(c.case_id for c in TARGETED_CASES) == tuple(f"T{i:02d}" for i in range(1, 11))
    assert tuple(c.case_id for c in UNSEEN_CASES) == tuple(f"U{i:02d}" for i in range(1, 11))
    assert len(set(REPEATED_STOCHASTIC_CASE_IDS)) == 6
    assert set(REPEATED_STOCHASTIC_CASE_IDS).issubset({c.case_id for c in ALL_CHALLENGE_CASES})
    assert REPEATED_STOCHASTIC_REPEATS == 3


def test_challenge_fingerprint_and_protocol_are_populated():
    fingerprint = challenge_fingerprint()
    protocol = challenge_protocol_metadata()
    assert len(fingerprint) == 64
    assert protocol["challenge_fingerprint"] == fingerprint
    assert protocol["targeted_case_count"] == 10
    assert protocol["unseen_case_count"] == 10
    assert protocol["repeated_stochastic_case_count"] == 6
    assert protocol["repeated_stochastic_repeats"] == 3
    assert protocol["source_hashes"]


def test_stream_case_sequences_are_frozen():
    assert expected_ids_for_stream("targeted") == tuple(f"T{i:02d}" for i in range(1, 11))
    assert expected_ids_for_stream("unseen") == tuple(f"U{i:02d}" for i in range(1, 11))
    assert expected_ids_for_stream("stochastic") == REPEATED_STOCHASTIC_CASE_IDS


def test_new_study_starts_empty_and_not_started():
    study = new_challenge_study(model_name="test-model", reasoning_effort="high")
    summary = aggregate_challenge_study(study)
    assert study["targeted_run"] is None
    assert study["unseen_run"] is None
    assert study["stochastic_runs"] == []
    assert summary["classification"] == "NOT STARTED"
    assert summary["total_case_executions"] == 0


def test_planned_execution_count_is_38():
    planned = len(TARGETED_CASES) + len(UNSEEN_CASES) + len(REPEATED_STOCHASTIC_CASE_IDS) * REPEATED_STOCHASTIC_REPEATS
    assert planned == 38


def test_cases_have_nonempty_narratives_and_unique_ids():
    ids = [case.case_id for case in ALL_CHALLENGE_CASES]
    assert len(ids) == len(set(ids))
    assert all(case.narrative.strip() for case in ALL_CHALLENGE_CASES)
    assert all(case.title.strip() for case in ALL_CHALLENGE_CASES)
    assert all(case.target_failure_mode.strip() for case in ALL_CHALLENGE_CASES)
