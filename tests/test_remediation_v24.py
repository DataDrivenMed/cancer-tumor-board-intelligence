from services.clinical_reconciliation_v24 import reconcile_clinical_fields_v24
from services.document_parser import parse_text
from qualification.remediation_cases_v24 import REMEDIATION_CASES_V24, REMEDIATION_REPEAT_CASE_IDS_V24, REMEDIATION_REPEAT_COUNT_V24
from qualification.remediation_protocol_v24 import remediation_protocol_metadata_v24


def test_v24_uncertain_diagnosis_cannot_end_with_confirmed_disease_state():
    doc = parse_text(
        "CT shows liver lesions and metastatic carcinoma is suspected. A liver biopsy is pending. ECOG is not documented.",
        document_id="T",
        filename="t.txt",
    )
    payload = {
        "diagnosis": {"field": "diagnosis", "value": "metastatic carcinoma", "status": "unknown", "confidence": 1.0, "source_segment_ids": ["S0001"], "source_excerpt": "metastatic carcinoma is suspected"},
        "disease_state": {"field": "disease_state", "value": "metastatic", "status": "confirmed", "confidence": 0.5, "source_segment_ids": ["S0001"], "source_excerpt": "metastatic"},
        "performance_status": {"field": "ECOG", "value": None, "status": "not_documented", "confidence": 1.0, "source_segment_ids": ["S0001"], "source_excerpt": "ECOG is not documented"},
        "pathology": [{"field": "liver biopsy", "value": None, "status": "pending", "confidence": 1.0, "source_segment_ids": ["S0001"], "source_excerpt": "A liver biopsy is pending"}],
        "missing_items": [],
        "diagnostic_certainty": "suspected",
        "stage": None,
    }
    out = reconcile_clinical_fields_v24(document=doc, payload=payload)
    assert out.payload["disease_state"]["value"] is None
    assert out.payload["disease_state"]["status"] == "unknown"
    categories = {item.get("category") for item in out.payload["missing_items"]}
    assert "pathology" in categories
    assert "performance_status" in categories


def test_v24_reconciliation_is_idempotent_for_missingness_and_invariant():
    doc = parse_text(
        "Metastatic carcinoma is suspected. Tissue diagnosis is pending. ECOG is not documented.",
        document_id="T2",
        filename="t2.txt",
    )
    payload = {
        "diagnosis": {"field": "diagnosis", "value": "metastatic carcinoma", "status": "unknown", "confidence": 1.0, "source_segment_ids": ["S0001"], "source_excerpt": "Metastatic carcinoma is suspected"},
        "disease_state": {"field": "disease_state", "value": "metastatic", "status": "confirmed", "confidence": 0.5, "source_segment_ids": ["S0001"], "source_excerpt": "metastatic"},
        "performance_status": {"field": "ECOG", "value": None, "status": "not_documented", "confidence": 1.0, "source_segment_ids": ["S0001"], "source_excerpt": "ECOG is not documented"},
        "pathology": [{"field": "tissue diagnosis", "value": None, "status": "pending", "confidence": 1.0, "source_segment_ids": ["S0001"], "source_excerpt": "Tissue diagnosis is pending"}],
        "missing_items": [],
        "diagnostic_certainty": "suspected",
        "stage": None,
    }
    once = reconcile_clinical_fields_v24(document=doc, payload=payload)
    twice = reconcile_clinical_fields_v24(document=doc, payload=once.payload)
    assert twice.payload == once.payload


def test_v24_fresh_suite_and_protocol_shape():
    assert tuple(case.case_id for case in REMEDIATION_CASES_V24) == tuple(f"X{i:02d}" for i in range(1, 13))
    assert len(REMEDIATION_REPEAT_CASE_IDS_V24) == 6
    assert REMEDIATION_REPEAT_COUNT_V24 == 3
    protocol = remediation_protocol_metadata_v24()
    assert protocol["planned_executions"] == 30
    assert len(protocol["remediation_fingerprint"]) == 64


def test_v24_newly_diagnosed_gold_requires_explicit_source_wording():
    for case in REMEDIATION_CASES_V24:
        if case.expected_disease_state == "newly diagnosed":
            assert "newly diagnosed" in case.narrative.lower()
