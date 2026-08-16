from __future__ import annotations

import json
from pathlib import Path

from agents.clinical_trials import ClinicalTrialsAgent
from agents.guideline import GuidelineAgent
from agents.literature import LiteratureAgent
from agents.molecular import MolecularInterpretationAgent
from agents.safety import SafetyAgent
from agents.translational import TranslationalBiologyAgent
from schemas.case import CancerTumorBoardCase
from services.oncology_programs import (
    PROGRAMS,
    assign_case_program,
    classify_diagnosis,
    registered_program_ids,
)


REPRESENTATIVE_DIAGNOSES = {
    "hematologic_malignancy": "acute myeloid leukemia",
    "breast_oncology": "invasive ductal breast carcinoma",
    "thoracic_oncology": "metastatic non-small cell lung cancer",
    "gastrointestinal_oncology": "metastatic colorectal cancer",
    "genitourinary_oncology": "metastatic renal cell carcinoma",
    "gynecologic_oncology": "high-grade serous ovarian cancer",
    "head_neck_oncology": "oropharyngeal squamous cell carcinoma",
    "neuro_oncology": "glioblastoma",
    "cutaneous_oncology": "cutaneous melanoma",
    "sarcoma_oncology": "soft tissue sarcoma",
    "endocrine_neuroendocrine_oncology": "thyroid cancer",
    "ophthalmic_oncology": "uveal melanoma",
    "pediatric_oncology": "neuroblastoma",
    "rare_unknown_primary_oncology": "carcinoma of unknown primary",
}


def _fixture() -> CancerTumorBoardCase:
    path = Path(__file__).resolve().parents[1] / "synthetic_cases" / "syn_aml_001.json"
    return CancerTumorBoardCase.model_validate(json.loads(path.read_text(encoding="utf-8")))


def test_registry_has_representative_diagnosis_for_every_program():
    assert set(registered_program_ids()) == set(REPRESENTATIVE_DIAGNOSES)
    assert len(PROGRAMS) == len(REPRESENTATIVE_DIAGNOSES)


def test_representative_diagnoses_classify_to_expected_programs():
    for expected, diagnosis in REPRESENTATIVE_DIAGNOSES.items():
        assert classify_diagnosis(diagnosis).program_id == expected


def test_assignment_preserves_diagnosis_and_sets_board_metadata():
    case = _fixture().model_copy(deep=True)
    case.diagnosis.value = "metastatic colorectal cancer"
    assigned = assign_case_program(case)
    assert assigned.diagnosis.value == "metastatic colorectal cancer"
    assert assigned.disease_program == "gastrointestinal_oncology"
    assert assigned.tumor_board_type == "gastrointestinal_tumor_board"


def test_all_specialists_accept_registered_solid_tumor_program_and_fail_closed_without_sources():
    case = _fixture().model_copy(deep=True)
    case.diagnosis.value = "metastatic non-small cell lung cancer"
    case.disease_program = "thoracic_oncology"
    case.tumor_board_type = "thoracic_tumor_board"

    reports = [
        GuidelineAgent().run(case),
        MolecularInterpretationAgent().run(case),
        TranslationalBiologyAgent().run(case),
        LiteratureAgent().run(case),
        ClinicalTrialsAgent().run(case),
        SafetyAgent().run(case),
    ]
    assert all(report.status != "abstain_domain" for report in reports)
    assert all(report.status in {"source_unavailable", "no_evidence_found"} for report in reports)


def test_unregistered_non_oncology_program_abstains():
    case = _fixture().model_copy(deep=True)
    case.disease_program = "cardiology"
    assert GuidelineAgent().run(case).status == "abstain_domain"
    assert MolecularInterpretationAgent().run(case).status == "abstain_domain"
    assert TranslationalBiologyAgent().run(case).status == "abstain_domain"
    assert LiteratureAgent().run(case).status == "abstain_domain"
    assert ClinicalTrialsAgent().run(case).status == "abstain_domain"
    assert SafetyAgent().run(case).status == "abstain_domain"
