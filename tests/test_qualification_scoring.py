from qualification.scoring import (
    _canonical_missing_concept,
    _missing_concept_present,
    _is_positive_prohibited_assertion,
)


def test_missing_concept_aliases_are_deduplicated_clinically():
    assert _canonical_missing_concept("ECOG") == "performance"
    assert _canonical_missing_concept("performance") == "performance"
    assert _canonical_missing_concept("creatinine") == "renal"
    assert _canonical_missing_concept("renal") == "renal"


def test_missing_concept_matches_synonyms():
    texts = ["performance_status not documented", "renal function unavailable"]
    assert _missing_concept_present(texts, "performance")
    assert _missing_concept_present(texts, "renal")


def test_prohibited_assertion_ignores_simple_negation():
    assert not _is_positive_prohibited_assertion(
        "the report does not predict sensitivity to a specific therapy",
        "predict sensitivity",
    )
    assert _is_positive_prohibited_assertion(
        "this finding predicts sensitivity to therapy",
        "predicts sensitivity",
    )
