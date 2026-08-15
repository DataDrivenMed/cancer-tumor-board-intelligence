from qualification.remediation_cases_v21 import (
    REMEDIATION_CASES,
    REMEDIATION_REPEAT_CASE_IDS,
    REMEDIATION_REPEAT_COUNT,
)
from qualification.remediation_protocol_v21 import (
    assert_remediation_suite_shape,
    remediation_protocol_metadata,
)


def test_remediation_suite_shape_is_frozen():
    assert_remediation_suite_shape()
    assert [case.case_id for case in REMEDIATION_CASES] == [f"R{i:02d}" for i in range(1, 13)]
    assert len(REMEDIATION_REPEAT_CASE_IDS) == 6
    assert REMEDIATION_REPEAT_COUNT == 3


def test_remediation_protocol_has_complete_fingerprint_and_30_executions():
    protocol = remediation_protocol_metadata()
    assert protocol["remediation_suite_version"] == "2.1.0"
    assert protocol["planned_executions"] == 30
    assert len(protocol["remediation_fingerprint"]) == 64
    assert protocol["source_hashes"]
    assert all(len(value) == 64 for value in protocol["source_hashes"].values())
