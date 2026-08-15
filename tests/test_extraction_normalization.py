from services.extraction_normalization import normalize_extraction_output, normalize_structured_output
from services.semantic_integrity import inspect_raw_semantic_integrity, semantic_integrity_passes


def _base_raw():
    return {
        "care_site": None,
        "sex": "female",
        "treatments": [],
        "current_medications": [],
        "transplant_cellular_therapy": [],
        "missing_items": [],
        "extraction_warnings": [],
    }


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
