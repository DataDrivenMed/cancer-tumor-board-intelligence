from qualification.cases import CASES, get_case


def test_qualification_suite_has_ten_unique_cases():
    assert len(CASES) == 10
    assert len({case.case_id for case in CASES}) == 10


def test_all_cases_are_synthetic_and_have_gold_targets():
    for case in CASES:
        assert case.case_id.startswith("Q")
        assert case.title
        assert case.target_failure_mode
        assert case.narrative
        assert case.expected_diagnosis is not None or case.expected_diagnosis_status == "conflicting"


def test_critical_failure_modes_are_present():
    modes = " ".join(case.target_failure_mode.lower() for case in CASES)
    for concept in ["missing", "contradiction", "pending", "chronology", "molecular", "stage", "transplant", "historical", "abstention"]:
        assert concept in modes


def test_q03_requires_unresolved_conflicting_diagnosis():
    q03 = get_case("Q03")
    assert q03.expected_diagnosis is None
    assert q03.expected_diagnosis_status == "conflicting"
    assert q03.expected_conflict_fields == ("pathology",)


def test_q10_uses_strict_abstention_safety_gate():
    q10 = get_case("Q10")
    assert q10.strict_core_gate is True
    assert q10.require_no_molecular_findings is True
    assert q10.require_no_treatments is True
    assert "acute myeloid leukemia" in q10.prohibited_confirmed_values
    assert "pathology" in q10.expected_missing_fields
    assert "molecular" in q10.expected_missing_fields
    assert "treatment" in q10.expected_missing_fields


def test_get_case_round_trip():
    assert get_case("Q10").title == "Intentionally insufficient case"
