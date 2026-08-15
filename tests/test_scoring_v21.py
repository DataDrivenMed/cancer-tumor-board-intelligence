from qualification.cases import GoldCase
from qualification.scoring_v21 import _diagnosis_matches_v21, _disease_state_matches_v21
from schemas.case import DataStatus


def _gold(**overrides):
    values = dict(
        case_id="X01",
        title="test",
        target_failure_mode="test",
        narrative="test",
        expected_diagnosis="suspected metastatic carcinoma",
        expected_disease_state=None,
        expected_ecog=None,
        allow_null_diagnosis_if_uncertain=True,
        strict_core_gate=True,
    )
    values.update(overrides)
    return GoldCase(**values)


def test_radiographic_progression_is_equivalent_to_progressive():
    assert _disease_state_matches_v21("radiographic progression", "progressive")
    assert _disease_state_matches_v21("progressive disease", "progressive")


def test_uncertain_unknown_primary_diagnosis_matches_entity_when_status_preserves_uncertainty():
    gold = _gold()
    assert _diagnosis_matches_v21(
        gold,
        "metastatic carcinoma, primary site unknown",
        DataStatus.UNKNOWN,
    )


def test_uncertain_entity_does_not_pass_if_structured_status_falsely_confirms_it():
    gold = _gold()
    assert not _diagnosis_matches_v21(
        gold,
        "metastatic carcinoma, primary site unknown",
        DataStatus.CONFIRMED,
    )
