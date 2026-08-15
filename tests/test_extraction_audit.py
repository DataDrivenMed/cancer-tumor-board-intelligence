from services.extraction_audit import make_normalization_event
from services.normalization_pipeline import normalize_primary_extraction


def _base_raw():
    return {
        "care_site": '{"field":"care_site","value":null}',
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


def test_audit_event_detaches_before_and_after_values():
    before = {"value": "a"}
    after = {"value": "b"}
    event = make_normalization_event(
        rule="test",
        field_path="x",
        before=before,
        after=after,
        reason="test",
    )
    before["value"] = "changed"
    after["value"] = "changed"
    assert event.before == {"value": "a"}
    assert event.after == {"value": "b"}


def test_primary_normalization_retains_raw_input_and_emits_change_event():
    raw = _base_raw()
    normalized, events = normalize_primary_extraction(raw)
    assert raw["care_site"] == '{"field":"care_site","value":null}'
    assert normalized["care_site"] is None
    assert any(event.field_path == "care_site" for event in events)
