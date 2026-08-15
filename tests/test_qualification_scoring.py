from qualification.scoring import (
    _canonical_missing_concept,
    _diagnosis_matches,
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


def test_diagnosis_matcher_accepts_standard_abbreviations():
    assert _diagnosis_matches("Acute Myeloid Leukemia", "AML")
    assert _diagnosis_matches("AML", "acute myeloid leukemia")
    assert _diagnosis_matches("DLBCL", "diffuse large B-cell lymphoma")
    assert not _diagnosis_matches("multiple myeloma", "AML")


def test_diagnosis_matcher_preserves_uncertain_hematologic_category():
    assert _diagnosis_matches("suspected hematologic malignancy", "suspected hematologic malignancy")
    assert _diagnosis_matches("hematologic malignancy, suspected", "suspected hematologic malignancy")
    assert not _diagnosis_matches("acute myeloid leukemia", "suspected hematologic malignancy")


def test_prohibited_assertion_ignores_simple_negation():
    assert not _is_positive_prohibited_assertion(
        "the report does not predict sensitivity to a specific therapy",
        "predict sensitivity",
    )
    assert _is_positive_prohibited_assertion(
        "this finding predicts sensitivity to therapy",
        "predicts sensitivity",
    )
