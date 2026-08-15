from qualification.cases import CASES
from qualification.protocol import (
    EXPECTED_CASE_IDS,
    QUALIFICATION_SUITE_VERSION,
    assert_frozen_suite_shape,
    protocol_metadata,
    suite_fingerprint,
)


def test_frozen_suite_v1_has_expected_case_membership_and_order():
    assert QUALIFICATION_SUITE_VERSION == "1.0.0"
    assert tuple(case.case_id for case in CASES) == EXPECTED_CASE_IDS
    assert_frozen_suite_shape()


def test_suite_fingerprint_is_stable_for_same_manifest():
    first = suite_fingerprint()
    second = suite_fingerprint()
    assert first == second
    assert len(first) == 64
    assert protocol_metadata()["suite_fingerprint"] == first
