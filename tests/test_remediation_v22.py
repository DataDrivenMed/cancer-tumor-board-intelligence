from qualification.remediation_cases_v22 import (
    REMEDIATION_CASES_V22,
    REMEDIATION_REPEAT_CASE_IDS_V22,
    REMEDIATION_REPEAT_COUNT_V22,
)
from qualification.remediation_protocol_v22 import (
    assert_remediation_suite_shape_v22,
    remediation_protocol_metadata_v22,
)
from services.remediation_validation_v22 import (
    aggregate_study_v22,
    new_remediation_study_v22,
)


def test_v22_suite_shape_and_counts():
    assert_remediation_suite_shape_v22()
    assert [case.case_id for case in REMEDIATION_CASES_V22] == [f"S{i:02d}" for i in range(1, 13)]
    assert len(REMEDIATION_REPEAT_CASE_IDS_V22) == 6
    assert REMEDIATION_REPEAT_COUNT_V22 == 3


def test_v22_protocol_has_fingerprint_and_30_executions():
    protocol = remediation_protocol_metadata_v22()
    assert protocol["remediation_suite_version"] == "2.2.0"
    assert protocol["planned_executions"] == 30
    assert len(protocol["remediation_fingerprint"]) == 64
    assert protocol["source_hashes"]


def test_v22_new_study_is_empty_and_safe():
    study = new_remediation_study_v22(model_name="test-model", reasoning_effort="high")
    summary = aggregate_study_v22(study)
    assert summary["classification"] == "NOT STARTED"
    assert summary["total_case_executions"] == 0
    assert summary["exact_provenance_rate"] == 1.0
    assert summary["safety_stop"] is False
