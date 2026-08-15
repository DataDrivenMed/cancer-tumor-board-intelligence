from qualification.remediation_cases_v25 import REMEDIATION_CASES_V25, REMEDIATION_REPEAT_CASE_IDS_V25
from qualification.remediation_protocol_v25 import assert_remediation_suite_shape_v25, remediation_protocol_metadata_v25


def test_v25_suite_shape_and_ids():
    assert_remediation_suite_shape_v25()
    assert [c.case_id for c in REMEDIATION_CASES_V25] == [f"Y{i:02d}" for i in range(1, 13)]
    assert len(REMEDIATION_REPEAT_CASE_IDS_V25) == 6


def test_v25_protocol_plans_thirty_executions_and_fingerprint():
    protocol = remediation_protocol_metadata_v25()
    assert protocol["planned_executions"] == 30
    assert protocol["case_count"] == 12
    assert protocol["repeat_case_count"] == 6
    assert protocol["repeat_count"] == 3
    assert len(protocol["remediation_fingerprint"]) == 64


def test_newly_diagnosed_gold_requires_explicit_source_wording():
    for case in REMEDIATION_CASES_V25:
        if case.expected_disease_state == "newly diagnosed":
            assert "newly diagnosed" in case.narrative.lower()
