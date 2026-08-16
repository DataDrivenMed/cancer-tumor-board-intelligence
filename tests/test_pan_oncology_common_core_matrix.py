from __future__ import annotations

from itertools import product

import pytest

from agents.clinical_trials import ClinicalTrialsAgent
from agents.guideline import GuidelineAgent
from agents.literature import LiteratureAgent
from agents.missing_information import run_missing_information
from agents.molecular import MolecularInterpretationAgent
from agents.safety import SafetyAgent
from agents.translational import TranslationalBiologyAgent
from orchestration.router import route_case
from schemas.case import (
    CancerTumorBoardCase,
    ClinicalQuestion,
    Conflict,
    DataStatus,
    Fact,
    MolecularFinding,
    TreatmentEpisode,
)
from services.oncology_programs import PROGRAMS, assign_case_program


SCENARIOS = (
    "routine_management",
    "localized_explicit_stage",
    "metastatic_management",
    "progressive_with_prior_therapy",
    "multi_line_treatment_history",
    "represented_molecular_finding",
    "trial_question",
    "safety_question",
    "guideline_alignment_question",
    "performance_status_pending",
    "adversarial_stage_conflict",
    "adversarial_high_case_conflict",
    "adversarial_diagnosis_pending",
    "adversarial_empty_evidence",
    "adversarial_unregistered_reassignment_guard",
)


def _base_case(program, scenario: str) -> CancerTumorBoardCase:
    diagnosis = program.diagnosis_terms[0]
    case = CancerTumorBoardCase(
        case_id=f"CORE-{program.program_id}-{scenario}",
        case_type="synthetic",
        disease_program=program.program_id,
        tumor_board_type=program.board_type,
        age=62,
        sex="female",
        diagnosis=Fact(field="diagnosis", value=diagnosis),
        disease_state=Fact(field="disease_state", value="localized"),
        performance_status=Fact(field="performance_status", value="ECOG 1"),
        clinical_question=ClinicalQuestion(
            question_type="treatment_management",
            question="Discuss management options for this synthetic qualification case.",
        ),
    )

    if scenario == "localized_explicit_stage":
        case.stage = Fact(field="stage", value="stage II", status=DataStatus.CONFIRMED)
    elif scenario == "metastatic_management":
        case.disease_state = Fact(field="disease_state", value="metastatic")
    elif scenario == "progressive_with_prior_therapy":
        case.disease_state = Fact(field="disease_state", value="progressive")
        case.treatments = [TreatmentEpisode(episode_id="TX-001", regimen="synthetic prior regimen")]
    elif scenario == "multi_line_treatment_history":
        case.disease_state = Fact(field="disease_state", value="progressive")
        case.treatments = [
            TreatmentEpisode(episode_id="TX-001", regimen="synthetic regimen one", line_of_therapy=1),
            TreatmentEpisode(episode_id="TX-002", regimen="synthetic regimen two", line_of_therapy=2),
            TreatmentEpisode(episode_id="TX-003", regimen="synthetic regimen three", line_of_therapy=3),
        ]
    elif scenario == "represented_molecular_finding":
        case.molecular_findings = [MolecularFinding(gene="SYNGENE", alteration_type="synthetic variant")]
        case.clinical_question = ClinicalQuestion(
            question_type="molecular_management",
            question="Review the represented synthetic molecular finding.",
        )
    elif scenario == "trial_question":
        case.clinical_question = ClinicalQuestion(
            question_type="clinical_trial",
            question="Identify potentially relevant trials without determining eligibility.",
        )
    elif scenario == "safety_question":
        case.clinical_question = ClinicalQuestion(
            question_type="safety",
            question="Review safety and toxicity considerations.",
        )
    elif scenario == "guideline_alignment_question":
        case.clinical_question = ClinicalQuestion(
            question_type="guideline_alignment",
            question="Assess alignment with verified guidance.",
        )
    elif scenario == "performance_status_pending":
        case.performance_status = Fact(field="performance_status", value=None, status=DataStatus.PENDING)
    elif scenario == "adversarial_stage_conflict":
        case.stage = Fact(field="stage", value=None, status=DataStatus.CONFLICTING)
    elif scenario == "adversarial_high_case_conflict":
        case.conflicts = [
            Conflict(
                conflict_id="CON-001",
                field="disease_state",
                value_a="localized",
                value_b="metastatic",
                severity="high",
                resolution_status="unresolved",
            )
        ]
    elif scenario == "adversarial_diagnosis_pending":
        case.diagnosis = Fact(field="diagnosis", value=None, status=DataStatus.PENDING)
    elif scenario in {"adversarial_empty_evidence", "adversarial_unregistered_reassignment_guard"}:
        pass

    return case


MATRIX = tuple(product(PROGRAMS, SCENARIOS))


@pytest.mark.parametrize(
    "program,scenario",
    MATRIX,
    ids=[f"{program.program_id}:{scenario}" for program, scenario in MATRIX],
)
def test_pan_oncology_common_core_matrix(program, scenario):
    """Qualification of common platform mechanics across 14 x 15 synthetic executions.

    This suite intentionally does not claim disease-specific clinical correctness.
    It verifies deterministic program assignment, routing, missing-information gates,
    domain boundaries, and fail-closed specialist behavior with no evidence stores.
    """
    case = _base_case(program, scenario)

    if scenario == "adversarial_unregistered_reassignment_guard":
        case.disease_program = "unregistered_program"
        case.tumor_board_type = "unknown_board"
        assigned = assign_case_program(case)
        assert assigned.disease_program == program.program_id
        assert assigned.tumor_board_type == program.board_type
        case = assigned

    if scenario == "adversarial_diagnosis_pending":
        missing = run_missing_information(case)
        assert missing.safe_to_route_to_specialists is False
        assert missing.blocking_count >= 1
        return

    routing = route_case(case)
    missing = run_missing_information(case)

    assert routing.safe_to_execute is True
    assert "safety" in routing.selected_agents
    assert "safety" in routing.required_agents

    if scenario == "safety_question":
        assert routing.selected_agents == ["safety"]
    elif scenario == "trial_question":
        assert "clinical_trials" in routing.selected_agents
    elif scenario == "represented_molecular_finding":
        assert "molecular" in routing.selected_agents
    elif scenario == "adversarial_stage_conflict":
        assert missing.safe_to_route_to_specialists is False
        assert any(item.category == "stage" and item.recommendation_blocking for item in missing.items)
    elif scenario == "adversarial_high_case_conflict":
        assert missing.safe_to_route_to_specialists is False
        assert routing.requires_human_review is True
    elif scenario == "performance_status_pending":
        assert missing.requires_human_review is True
        assert any(item.category == "performance_status" for item in missing.items)
    elif scenario == "progressive_with_prior_therapy":
        assert not any(item.field == "prior treatment history" for item in missing.items)

    outputs = {
        "guideline": GuidelineAgent().run(case),
        "molecular": MolecularInterpretationAgent().run(case),
        "translational": TranslationalBiologyAgent().run(case),
        "literature": LiteratureAgent().run(case),
        "clinical_trials": ClinicalTrialsAgent().run(case),
        "safety": SafetyAgent().run(case),
    }

    for output in outputs.values():
        assert output.status != "abstain_domain"

    # No configured verified evidence means no specialist may silently promote a
    # treatment, safety, molecular, trial, literature, or guidance claim.
    assert outputs["guideline"].can_support_guideline_claim is False
    assert outputs["molecular"].can_support_clinical_actionability_claim is False
    assert outputs["translational"].can_support_clinical_actionability_claim is False
    assert outputs["literature"].can_support_literature_claim is False
    assert outputs["clinical_trials"].can_support_trial_match_claim is False
    assert outputs["safety"].can_support_safety_claim is False


def test_common_core_matrix_has_210_executions():
    assert len(PROGRAMS) == 14
    assert len(SCENARIOS) == 15
    assert len(MATRIX) == 210
