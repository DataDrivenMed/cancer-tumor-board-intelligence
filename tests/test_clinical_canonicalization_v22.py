from services.clinical_canonicalization_v22 import canonicalize_clinical_fields_v22
from services.document_parser import parse_text


def _payload(diagnosis_value, diagnosis_status="confirmed", disease_value=None, disease_status="not_documented", disease_excerpt=None, conflicts=None):
    return {
        "diagnosis": {
            "field": "diagnosis",
            "value": diagnosis_value,
            "status": diagnosis_status,
            "confidence": 1.0,
            "source_segment_ids": ["S0001"],
            "source_excerpt": diagnosis_value,
        },
        "disease_state": {
            "field": "disease_state",
            "value": disease_value,
            "status": disease_status,
            "confidence": 1.0,
            "source_segment_ids": ["S0001"],
            "source_excerpt": disease_excerpt,
        },
        "conflicts": conflicts or [],
        "missing_items": [],
    }


def test_hepatic_metastases_canonicalize_to_metastatic():
    doc = parse_text("Pancreatic ductal adenocarcinoma with hepatic metastases.")
    payload = _payload(
        "Pancreatic ductal adenocarcinoma",
        disease_value="hepatic metastases",
        disease_status="confirmed",
        disease_excerpt="hepatic metastases",
    )
    result = canonicalize_clinical_fields_v22(document=doc, payload=payload)
    assert result.payload["disease_state"]["value"] == "metastatic"
    assert result.payload["disease_state"]["source_excerpt"] == "hepatic metastases"


def test_suspected_diagnosis_does_not_confirm_metastatic_state():
    doc = parse_text("Metastatic carcinoma is suspected, but tissue diagnosis is pending.")
    payload = _payload(
        "metastatic carcinoma",
        diagnosis_status="not_documented",
        disease_value="metastatic",
        disease_status="not_documented",
        disease_excerpt="Metastatic carcinoma",
    )
    payload["diagnosis"]["source_excerpt"] = "Metastatic carcinoma is suspected"
    result = canonicalize_clinical_fields_v22(document=doc, payload=payload)
    assert result.diagnostic_certainty == "suspected"
    assert result.payload["disease_state"]["value"] is None
    assert result.payload["disease_state"]["status"] == "unknown"


def test_stage_conflict_is_separated_from_disease_state():
    doc = parse_text("Oncology note lists stage IIIB. PET/CT labels the disease stage IV.")
    payload = _payload(
        "lung adenocarcinoma",
        disease_value="stage IIIB vs stage IV",
        disease_status="conflicting",
        disease_excerpt="stage IIIB",
        conflicts=[{
            "field": "stage",
            "value_a": "stage IIIB",
            "value_b": "stage IV",
            "severity": "high",
            "source_segment_ids": ["S0001"],
        }],
    )
    result = canonicalize_clinical_fields_v22(document=doc, payload=payload)
    assert result.payload["disease_state"]["value"] is None
    assert result.payload["disease_state"]["status"] == "conflicting"
    assert result.stage["status"] == "conflicting"


def test_progression_repairs_to_exact_source_excerpt():
    doc = parse_text(
        "Metastatic castration-resistant prostate adenocarcinoma. Current imaging demonstrates radiographic progression."
    )
    payload = _payload(
        "prostate adenocarcinoma",
        disease_value="radiographic progression",
        disease_status="confirmed",
        disease_excerpt="Metastatic castration-resistant prostate adenocarcinoma. Current imaging demonstrates radiographic progression.",
    )
    result = canonicalize_clinical_fields_v22(document=doc, payload=payload)
    assert result.payload["disease_state"]["value"] == "progressive"
    assert result.payload["disease_state"]["source_excerpt"] == "radiographic progression"


def test_missing_item_category_maps_tissue_diagnosis_to_pathology():
    doc = parse_text("Tissue diagnosis is pending.")
    payload = _payload("carcinoma", diagnosis_status="unknown")
    payload["missing_items"] = [{
        "field": "tissue diagnosis",
        "importance": "critical",
        "reason": "Tissue diagnosis is pending",
        "availability": "pending",
        "recommendation_blocking": True,
    }]
    result = canonicalize_clinical_fields_v22(document=doc, payload=payload)
    assert result.payload["missing_items"][0]["category"] == "pathology"
