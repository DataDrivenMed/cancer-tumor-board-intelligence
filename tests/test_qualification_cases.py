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
        assert case.expected_diagnosis


def test_critical_failure_modes_are_present():
    modes = " ".join(case.target_failure_mode.lower() for case in CASES)
    for concept in ["missing", "contradiction", "pending", "chronology", "molecular", "stage", "transplant", "historical", "abstention"]:
        assert concept in modes


def test_get_case_round_trip():
    assert get_case("Q10").title == "Intentionally insufficient case"
