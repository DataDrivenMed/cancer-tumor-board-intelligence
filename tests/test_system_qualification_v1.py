from qualification.system_cases_v1 import SYSTEM_QUALIFICATION_CASES
from qualification.system_protocol_v1 import (
    BASELINE_CASE_COUNT,
    FROZEN_SUITE_FINGERPRINT,
    PLANNED_EXECUTIONS,
    REPEAT_CASE_COUNT,
    REPEAT_COUNT,
)
from services.system_qualification_v1 import execute_system_case, run_full_study


def test_frozen_protocol_shape():
    assert BASELINE_CASE_COUNT == 18
    assert REPEAT_CASE_COUNT == 6
    assert REPEAT_COUNT == 3
    assert PLANNED_EXECUTIONS == 36
    assert len(FROZEN_SUITE_FINGERPRINT) == 64


def test_all_baseline_cases_pass_strict_contract():
    failures = []
    for spec in SYSTEM_QUALIFICATION_CASES:
        result = execute_system_case(spec)
        if not result["strict_pass"]:
            failures.append((spec.case_id, result))
    assert failures == []


def test_full_study_is_green_and_safety_clean():
    study = run_full_study()
    assert study["completed_executions"] == 36
    assert study["strict_passes"] == 36
    assert study["strict_pass_rate"] == 1.0
    assert study["safety_stop_violation_count"] == 0
    assert study["formal_disposition"] == "GREEN"
    assert all(value == 3 for value in study["repeat_passes"].values())


def test_blocked_cases_never_render_management():
    for spec in SYSTEM_QUALIFICATION_CASES:
        if spec.expected_red_team_disposition == "blocked":
            result = execute_system_case(spec)
            assert result["consensus_state"] == "abstain"
            assert result["safe_to_render"] is False
            assert result["management_values"] == ["WITHHELD"]


def test_q16_provenance_reaches_brief():
    spec = next(case for case in SYSTEM_QUALIFICATION_CASES if case.case_id == "Q16")
    result = execute_system_case(spec)
    assert result["checks"]["provenance_trace"] is True
