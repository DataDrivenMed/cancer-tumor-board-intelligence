from __future__ import annotations

import pytest

from agents.clinical_trials import ClinicalTrialsAgent
from agents.guideline import GuidelineAgent
from agents.literature import LiteratureAgent
from agents.molecular import MolecularInterpretationAgent
from agents.safety import SafetyAgent
from agents.translational import TranslationalBiologyAgent
from orchestration.router import route_case
from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Fact
from services.oncology_programs import PROGRAMS, assign_case_program, classify_diagnosis, is_registered_oncology_program


def _case(program_id: str, board_type: str, diagnosis: str) -> CancerTumorBoardCase:
    return CancerTumorBoardCase(
        case_id=f"PAN-{program_id}",
        case_type="synthetic",
        disease_program=program_id,
        tumor_board_type=board_type,
        age=62,
        sex="female",
        diagnosis=Fact(field="diagnosis", value=diagnosis),
        disease_state=Fact(field="disease_state", value="metastatic"),
        performance_status=Fact(field="performance_status", value="ECOG 1"),
        clinical_question=ClinicalQuestion(
            question_type="treatment_management",
            question="What management options should be discussed at tumor board?",
        ),
    )


def test_registry_contains_major_pan_oncology_programs():
    ids = {program.program_id for program in PROGRAMS}
    expected = {
        "hematologic_malignancy",
        "breast_oncology",
        "thoracic_oncology",
        "gastrointestinal_oncology",
        "genitourinary_oncology",
        "gynecologic_oncology",
        "head_neck_oncology",
        "neuro_oncology",
        "cutaneous_oncology",
        "sarcoma_oncology",
        "endocrine_neuroendocrine_oncology",
        "ophthalmic_oncology",
        "pediatric_oncology",
        "rare_unknown_primary_oncology",
    }
    assert expected.issubset(ids)
    assert len(ids) == len(PROGRAMS)


@pytest.mark.parametrize("program", PROGRAMS, ids=lambda program: program.program_id)
def test_each_program_classifies_and_routes_without_domain_abstention(program):
    diagnosis = program.diagnosis_terms[0]
    assert classify_diagnosis(diagnosis).program_id == program.program_id
    assert is_registered_oncology_program(program.program_id)

    case = _case(program.program_id, program.board_type, diagnosis)
    routing = route_case(case)
    assert routing.safe_to_execute is True
    assert "safety" in routing.required_agents
    assert "guideline" in routing.selected_agents
    assert "literature" in routing.selected_agents
    assert "clinical_trials" in routing.selected_agents

    outputs = {
        "guideline": GuidelineAgent().run(case),
        "molecular": MolecularInterpretationAgent().run(case),
        "translational": TranslationalBiologyAgent().run(case),
        "literature": LiteratureAgent().run(case),
        "clinical_trials": ClinicalTrialsAgent().run(case),
        "safety": SafetyAgent().run(case),
    }
    for name, output in outputs.items():
        assert output.status != "abstain_domain", f"{name} incorrectly abstained for {program.program_id}"

    # Empty/unconfigured evidence stores must never be upgraded into a clinical claim.
    assert outputs["guideline"].can_support_guideline_claim is False
    assert outputs["molecular"].can_support_clinical_actionability_claim is False
    assert outputs["translational"].can_support_clinical_actionability_claim is False
    assert outputs["literature"].can_support_literature_claim is False
    assert outputs["clinical_trials"].can_support_trial_match_claim is False
    assert outputs["safety"].can_support_safety_claim is False


@pytest.mark.parametrize("program", PROGRAMS, ids=lambda program: program.program_id)
def test_assign_case_program_sets_board_metadata(program):
    case = _case("rare_unknown_primary_oncology", "rare_unknown_primary_tumor_board", program.diagnosis_terms[0])
    assigned = assign_case_program(case)
    assert assigned.disease_program == program.program_id
    assert assigned.tumor_board_type == program.board_type
    assert assigned.diagnosis.value == case.diagnosis.value


def test_unregistered_program_abstains_in_all_specialist_agents():
    case = _case("not_an_oncology_program", "unknown_board", "malignancy")
    outputs = [
        GuidelineAgent().run(case),
        MolecularInterpretationAgent().run(case),
        TranslationalBiologyAgent().run(case),
        LiteratureAgent().run(case),
        ClinicalTrialsAgent().run(case),
        SafetyAgent().run(case),
    ]
    assert all(output.status == "abstain_domain" for output in outputs)
