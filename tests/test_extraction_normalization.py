from services.extraction_normalization import normalize_extraction_output, normalize_structured_output
from services.semantic_integrity import inspect_raw_semantic_integrity, semantic_integrity_passes


def _base_raw():
    return {
        "care_site": None,
        "sex": "female",
        "diagnosis": {
            "field": "diagnosis",
            "value": "AML",
            "status": "confirmed",
            "confidence": 1.0,
            "source_segment_ids": ["S0001"],
            "source_excerpt": "AML",
        },
        "conflicts": [],
        "treatments": [],
        "current_medications": [],
        "transplant_cellular_therapy": [],
        "missing_items": [],
        "extraction_warnings": [],
    }


def test_unresolved_diagnosis_conflict_cannot_keep_confirmed_canonical_diagnosis():
    raw = _base_raw()
    raw["diagnosis"] = {
        "field": "diagnosis",
        "value": "acute myeloid leukemia",
        "status": "confirmed",
        "confidence": 1.0,
        "source_segment_ids": ["S0001"],
        "source_excerpt": "acute myeloid leukemia with 24% blasts",
    }
    raw["conflicts"] = [
        {
            "field": "diagnosis",
            "value_a": "myelodysplastic syndrome with excess blasts, 14% blasts",
            "value_b": "acute myeloid leukemia with 24% blasts",
            "severity": "high",
            "source_segment_ids": ["S0001"],
        }
    ]
    normalized = normalize_extraction_output(raw)
    assert normalized["diagnosis"]["value"] is None
    assert normalized["diagnosis"]["status"] == "conflicting"
    assert normalized["diagnosis"]["confidence"] <= 0.5
    assert normalized["diagnosis"]["source_segment_ids"] == []
    assert normalized["diagnosis"]["source_excerpt"] is None
    assert len(normalized["conflicts"]) == 1
    assert any("unresolved diagnosis-level conflict" in w for w in normalized["extraction_warnings"])


def test_stage_conflict_does_not_clear_confirmed_diagnosis():
    raw = _base_raw()
    raw["conflicts"] = [
        {
            "field": "stage",
            "value_a": "III",
            "value_b": "IV",
            "severity": "high",
            "source_segment_ids": ["S0001"],
        }
    ]
    normalized = normalize_extraction_output(raw)
    assert normalized["diagnosis"]["value"] == "AML"
    assert normalized["diagnosis"]["status"] == "confirmed"


def test_already_conflicting_null_diagnosis_is_left_unchanged():
    raw = _base_raw()
    raw["diagnosis"] = {
        "field": "diagnosis",
        "value": None,
        "status": "conflicting",
        "confidence": 0.4,
        "source_segment_ids": [],
        "source_excerpt": None,
    }
    raw["conflicts"] = [
        {
            "field": "diagnosis",
            "value_a": "MDS",
            "value_b": "AML",
            "severity": "high",
            "source_segment_ids": ["S0001"],
        }
    ]
    normalized = normalize_extraction_output(raw)
    assert normalized["diagnosis"] == raw["diagnosis"]


def test_serialized_json_scalar_is_cleared():
    raw = _base_raw()
    raw["care_site"] = '{"field":"care_site","value":null,"status":"not_documented"}'
    normalized = normalize_extraction_output(raw)
    assert normalized["care_site"] is None
    assert any("malformed serialized JSON" in w for w in normalized["extraction_warnings"])
    assert semantic_integrity_passes(inspect_raw_semantic_integrity(normalized))


def test_not_started_therapy_is_removed_from_administered_history():
    raw = _base_raw()
    raw["treatments"] = [
        {
            "regimen": "R-CHOP",
            "source_excerpt": "R-CHOP has not yet started",
        }
    ]
    normalized = normalize_extraction_output(raw)
    assert normalized["treatments"] == []
    assert any("R-CHOP" in item["field"] for item in normalized["missing_items"])
    assert semantic_integrity_passes(inspect_raw_semantic_integrity(normalized))


def test_historical_medication_is_removed_from_current_medications():
    raw = _base_raw()
    raw["current_medications"] = [
        {
            "field": "lenalidomide maintenance",
            "value": None,
            "status": "confirmed",
            "source_excerpt": "followed by lenalidomide maintenance",
        }
    ]
    normalized = normalize_extraction_output(raw)
    assert normalized["current_medications"] == []
    assert semantic_integrity_passes(inspect_raw_semantic_integrity(normalized))


def test_explicit_current_medication_confirmed_null_gets_source_supported_value():
    raw = _base_raw()
    raw["current_medications"] = [
        {
            "field": "acyclovir",
            "value": None,
            "status": "confirmed",
            "source_excerpt": "currently taking acyclovir",
        }
    ]
    normalized = normalize_extraction_output(raw)
    assert normalized["current_medications"][0]["value"] == "acyclovir"
    assert semantic_integrity_passes(inspect_raw_semantic_integrity(normalized))


def test_confirmed_null_transplant_gets_exact_source_supported_field_value():
    raw = _base_raw()
    raw["transplant_cellular_therapy"] = [
        {
            "field": "autologous stem cell transplant",
            "value": None,
            "status": "confirmed",
            "source_excerpt": "autologous stem cell transplant in February 2023",
        }
    ]
    normalized = normalize_extraction_output(raw)
    assert normalized["transplant_cellular_therapy"][0]["value"] == "autologous stem cell transplant"
    assert semantic_integrity_passes(inspect_raw_semantic_integrity(normalized))


def test_non_extraction_schema_is_untouched():
    payload = {"care_site": '{"x":1}'}
    assert normalize_structured_output("other_schema", payload) == payload
