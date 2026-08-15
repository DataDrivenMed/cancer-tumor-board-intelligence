from services.disease_state_resolver import resolve_disease_state
from services.document_parser import parse_text


def _payload(diagnosis=None):
    return {
        "diagnosis": {
            "field": "diagnosis",
            "value": diagnosis,
            "status": "confirmed" if diagnosis else "unknown",
            "confidence": 1.0,
            "source_segment_ids": ["S0001"] if diagnosis else [],
            "source_excerpt": diagnosis,
        },
        "disease_state": {
            "field": "disease_state",
            "value": None,
            "status": "not_documented",
            "confidence": 1.0,
            "source_segment_ids": [],
            "source_excerpt": None,
        },
        "conflicts": [],
        "extraction_warnings": [],
    }


def test_promotes_explicit_metastatic_diagnosis_when_canonical_state_missing():
    doc = parse_text("He now has metastatic lung adenocarcinoma with liver lesions.")
    result = resolve_disease_state(document=doc, payload=_payload("lung adenocarcinoma"))
    state = result.payload["disease_state"]
    assert state["value"] == "metastatic"
    assert state["status"] == "confirmed"
    assert state["information_type"] == "observed"
    assert state["source_segment_ids"] == ["S0001"]
    assert result.events


def test_promotes_metastatic_as_derived_from_explicit_metastases_wording():
    doc = parse_text("Pancreatic ductal adenocarcinoma with liver metastases. ECOG is not documented.")
    result = resolve_disease_state(
        document=doc,
        payload=_payload("pancreatic ductal adenocarcinoma"),
    )
    state = result.payload["disease_state"]
    assert state["value"] == "metastatic"
    assert state["information_type"] == "derived"
    assert state["source_excerpt"].lower() == "metastases"


def test_does_not_promote_uncertain_suspected_metastatic_diagnosis():
    doc = parse_text("Metastatic carcinoma is suspected after imaging, but biopsy has not returned.")
    result = resolve_disease_state(document=doc, payload=_payload())
    assert result.payload["disease_state"]["value"] is None
    assert result.events == []


def test_does_not_use_remote_historical_state_without_current_diagnosis_anchor():
    doc = parse_text(
        "She had metastatic breast cancer in 2010 and is in remission.\n"
        "A new thyroid nodule is under evaluation."
    )
    result = resolve_disease_state(document=doc, payload=_payload("thyroid carcinoma"))
    assert result.payload["disease_state"]["value"] is None
    assert result.events == []


def test_abstains_when_relevant_conflict_is_present():
    payload = _payload("lung adenocarcinoma")
    payload["conflicts"] = [
        {
            "field": "stage",
            "value_a": "IIIB",
            "value_b": "IV",
            "severity": "high",
            "source_segment_ids": ["S0001"],
        }
    ]
    doc = parse_text("The PET report calls the lung adenocarcinoma metastatic.")
    result = resolve_disease_state(document=doc, payload=payload)
    assert result.payload["disease_state"]["value"] is None
    assert any("abstained" in warning for warning in result.warnings)
