from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Fact, DataStatus, TreatmentEpisode, Provenance
from services.semantic_integrity import inspect_raw_semantic_integrity, inspect_semantic_integrity, semantic_integrity_passes


def _base_case(**updates):
    case = CancerTumorBoardCase(
        case_id="TEST",
        diagnosis=Fact(field="diagnosis", value="AML", status=DataStatus.CONFIRMED),
        disease_state=Fact(field="disease_state", value="relapsed", status=DataStatus.CONFIRMED),
        clinical_question=ClinicalQuestion(question_type="management", question="test"),
    )
    for key, value in updates.items():
        setattr(case, key, value)
    return case


def test_serialized_json_string_in_care_site_is_rejected():
    raw = {
        "care_site": '{"field":"care_site","value":null,"status":"not_documented"}',
        "treatments": [],
        "current_medications": [],
        "transplant_cellular_therapy": [],
    }
    findings = inspect_raw_semantic_integrity(raw)
    assert any(f.code == "SERIALIZED_JSON_IN_SCALAR" for f in findings)
    assert not semantic_integrity_passes(findings)


def test_unstarted_therapy_cannot_be_administered_treatment_episode():
    provenance = Provenance(
        document_id="D1",
        source_excerpt="R-CHOP has not yet started",
        source_segment_ids=["S0001"],
        source_verified=True,
    )
    case = _base_case(
        treatments=[TreatmentEpisode(episode_id="TX-001", regimen="R-CHOP", provenance=[provenance])]
    )
    findings = inspect_semantic_integrity(case)
    assert any(f.code == "UNSTARTED_THERAPY_AS_ADMINISTERED" for f in findings)
    assert not semantic_integrity_passes(findings)


def test_historical_medication_is_not_accepted_as_current_without_temporal_support():
    raw = {
        "care_site": None,
        "treatments": [],
        "current_medications": [
            {
                "field": "lenalidomide maintenance",
                "value": None,
                "status": "confirmed",
                "source_excerpt": "followed by lenalidomide maintenance",
            }
        ],
        "transplant_cellular_therapy": [],
    }
    findings = inspect_raw_semantic_integrity(raw)
    codes = {f.code for f in findings}
    assert "CURRENT_MEDICATION_TEMPORALITY_UNVERIFIED" in codes
    assert "CONFIRMED_NULL_CURRENT_MEDICATION_VALUE" in codes
    assert not semantic_integrity_passes(findings)


def test_confirmed_null_transplant_representation_is_rejected():
    raw = {
        "care_site": None,
        "treatments": [],
        "current_medications": [],
        "transplant_cellular_therapy": [
            {
                "field": "autologous stem cell transplant",
                "value": None,
                "status": "confirmed",
                "source_excerpt": "autologous stem cell transplant in February 2023",
            }
        ],
    }
    findings = inspect_raw_semantic_integrity(raw)
    assert any(f.code == "CONFIRMED_NULL_TRANSPLANT_VALUE" for f in findings)
    assert not semantic_integrity_passes(findings)


def test_clean_raw_extraction_passes_semantic_integrity():
    raw = {
        "care_site": None,
        "treatments": [
            {
                "regimen": "azacitidine plus venetoclax",
                "source_excerpt": "received azacitidine plus venetoclax beginning January 2025",
            }
        ],
        "current_medications": [],
        "transplant_cellular_therapy": [],
    }
    findings = inspect_raw_semantic_integrity(raw)
    assert findings == []
    assert semantic_integrity_passes(findings)
