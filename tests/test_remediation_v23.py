from services.clinical_canonicalization_v23 import canonicalize_clinical_fields_v23
from services.document_parser import parse_text
from qualification.remediation_protocol_v23 import assert_remediation_suite_shape_v23, remediation_protocol_metadata_v23


def _base_payload():
    return {
        "diagnosis": {
            "field": "diagnosis",
            "value": "metastatic carcinoma, primary site unknown",
            "status": "pending",
            "confidence": 0.9,
            "source_segment_ids": ["S0001"],
            "source_excerpt": "Metastatic carcinoma is suspected. Tissue diagnosis is pending and the primary site remains unknown.",
        },
        "disease_state": {
            "field": "disease_state",
            "value": "metastatic",
            "status": "pending",
            "confidence": 0.9,
            "source_segment_ids": ["S0001"],
            "source_excerpt": "metastatic carcinoma is suspected",
        },
        "performance_status": {
            "field": "ECOG",
            "value": None,
            "status": "not_documented",
            "confidence": 1.0,
            "source_segment_ids": ["S0001"],
            "source_excerpt": "ECOG is not documented",
        },
        "pathology": [{
            "field": "tissue diagnosis",
            "value": None,
            "status": "pending",
            "confidence": 1.0,
            "source_segment_ids": ["S0001"],
            "source_excerpt": "Tissue diagnosis is pending",
        }],
        "molecular_findings": [],
        "imaging": [],
        "labs": [],
        "comorbidities": [],
        "treatments": [],
        "toxicities": [],
        "transplant_cellular_therapy": [],
        "current_medications": [],
        "clinical_question": {"question_type": "unspecified", "question": "Not explicitly documented", "urgency": "unknown"},
        "conflicts": [],
        "missing_items": [
            {"field": "Molecular testing", "reason": "unavailable", "availability": "unavailable", "category": "molecular"},
        ],
        "extraction_warnings": [],
        "diagnostic_certainty": "suspected",
        "stage": None,
    }


def test_v23_repairs_uncertain_diagnosis_to_exact_source_entity():
    text = "Metastatic carcinoma is suspected. Tissue diagnosis is pending and the primary site remains unknown. ECOG is not documented."
    document = parse_text(text, document_id="T", filename="t.txt")
    result = canonicalize_clinical_fields_v23(document=document, payload=_base_payload())
    diagnosis = result.payload["diagnosis"]
    assert diagnosis["value"] == "metastatic carcinoma"
    assert diagnosis["source_excerpt"].lower() == "metastatic carcinoma is suspected"
    assert diagnosis["source_excerpt"] in text or diagnosis["source_excerpt"].lower() in text.lower()


def test_v23_reconciles_pending_pathology_into_missing_items():
    text = "Metastatic carcinoma is suspected. Tissue diagnosis is pending and the primary site remains unknown. ECOG is not documented."
    document = parse_text(text, document_id="T", filename="t.txt")
    result = canonicalize_clinical_fields_v23(document=document, payload=_base_payload())
    categories = [item.get("category") for item in result.payload["missing_items"]]
    assert "pathology" in categories
    assert "performance_status" in categories
    assert categories.count("pathology") == 1


def test_v23_does_not_duplicate_existing_pathology_missing_item():
    payload = _base_payload()
    payload["missing_items"].append({"field": "biopsy", "reason": "pending", "availability": "pending", "category": "pathology"})
    text = "Metastatic carcinoma is suspected. Tissue diagnosis is pending and the primary site remains unknown. ECOG is not documented."
    document = parse_text(text, document_id="T", filename="t.txt")
    result = canonicalize_clinical_fields_v23(document=document, payload=payload)
    assert sum(item.get("category") == "pathology" for item in result.payload["missing_items"]) == 1


def test_v23_protocol_shape_and_versions():
    assert_remediation_suite_shape_v23()
    protocol = remediation_protocol_metadata_v23()
    assert protocol["remediation_suite_version"] == "2.3.0"
    assert protocol["extraction_version"] == "2.3.0"
    assert protocol["scoring_version"] == "2.3.0"
    assert protocol["planned_executions"] == 30
    assert len(protocol["remediation_fingerprint"]) == 64
