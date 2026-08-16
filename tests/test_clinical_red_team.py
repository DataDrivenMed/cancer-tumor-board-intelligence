from __future__ import annotations

from agents.clinical_red_team import run_clinical_red_team
from schemas.agent import RoutingDecision
from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Conflict, Fact, MissingItem
from schemas.red_team import RedTeamDisposition


def _case() -> CancerTumorBoardCase:
    return CancerTumorBoardCase(
        case_id="red-team-test",
        diagnosis=Fact(field="diagnosis", value="acute myeloid leukemia"),
        disease_state=Fact(field="disease_state", value="relapsed"),
        clinical_question=ClinicalQuestion(question_type="management", question="What should be discussed?"),
    )


def _routing(selected=None, required=None) -> RoutingDecision:
    selected = selected or ["guideline", "molecular", "translational", "clinical_trials", "safety"]
    required = required if required is not None else list(selected)
    return RoutingDecision(
        question_type="management",
        question_domains=["treatment_management"],
        complexity="complex",
        selected_agents=selected,
        required_agents=required,
    )


def _clean_outputs():
    return {
        "guideline": {
            "status": "completed",
            "formal_guideline_matches": 1,
            "can_support_guideline_claim": True,
        },
        "molecular": {
            "status": "completed",
            "can_support_clinical_actionability_claim": False,
            "interpretations": [{"can_support_clinical_actionability_claim": False}],
        },
        "translational": {
            "status": "completed",
            "can_support_clinical_actionability_claim": False,
        },
        "clinical_trials": {
            "status": "completed_with_limitations",
            "can_support_eligibility_claim": False,
            "matches": [{"nct_id": "NCT00000000", "eligibility_determined": False, "eligible": None}],
        },
        "safety": {
            "status": "completed",
            "findings": [],
            "can_support_safety_claim": False,
            "recommendation_blocking": False,
        },
    }


def test_clean_stack_is_clear_but_not_claimed_clinically_correct():
    report = run_clinical_red_team(_case(), _routing(), _clean_outputs())
    assert report.disposition == RedTeamDisposition.CLEAR
    assert report.safe_for_consensus is True
    assert report.findings == []
    assert "does not establish clinical correctness" in report.limitations[1]


def test_missing_required_specialist_blocks_consensus():
    outputs = _clean_outputs()
    outputs.pop("safety")
    report = run_clinical_red_team(_case(), _routing(), outputs)
    assert report.disposition == RedTeamDisposition.BLOCKED
    assert report.safe_for_consensus is False
    assert any(f.code == "REQUIRED_SPECIALIST_OUTPUT_MISSING" for f in report.findings)


def test_translational_actionability_promotion_is_blocked():
    outputs = _clean_outputs()
    outputs["translational"]["can_support_clinical_actionability_claim"] = True
    report = run_clinical_red_team(_case(), _routing(), outputs)
    assert report.disposition == RedTeamDisposition.BLOCKED
    assert any(f.code == "TRANSLATIONAL_EVIDENCE_PROMOTED_TO_CLINICAL_ACTIONABILITY" for f in report.findings)


def test_trial_match_cannot_be_promoted_to_patient_eligibility():
    outputs = _clean_outputs()
    outputs["clinical_trials"]["matches"][0]["eligibility_determined"] = True
    outputs["clinical_trials"]["matches"][0]["eligible"] = True
    report = run_clinical_red_team(_case(), _routing(), outputs)
    assert report.disposition == RedTeamDisposition.BLOCKED
    assert any(f.code == "PATIENT_TRIAL_ELIGIBILITY_AUTOMATICALLY_DETERMINED" for f in report.findings)


def test_safety_recommendation_block_is_preserved():
    outputs = _clean_outputs()
    outputs["safety"] = {
        "status": "completed_with_limitations",
        "findings": [{"safety_issue": "synthetic unresolved parameter"}],
        "can_support_safety_claim": True,
        "recommendation_blocking": True,
    }
    report = run_clinical_red_team(_case(), _routing(), outputs)
    assert report.disposition == RedTeamDisposition.BLOCKED
    assert any(f.code == "SAFETY_RECOMMENDATION_BLOCK" for f in report.findings)


def test_unresolved_high_severity_case_conflict_blocks():
    case = _case()
    case.conflicts = [
        Conflict(
            conflict_id="C1",
            field="disease_state",
            value_a="relapsed",
            value_b="refractory",
            severity="high",
            resolution_status="unresolved",
        )
    ]
    report = run_clinical_red_team(case, _routing(), _clean_outputs())
    assert report.disposition == RedTeamDisposition.BLOCKED
    assert any(f.code == "UNRESOLVED_HIGH_SEVERITY_CASE_CONFLICT" for f in report.findings)


def test_recommendation_blocking_missing_information_blocks():
    case = _case()
    case.missing_items = [
        MissingItem(
            field="decision-critical synthetic parameter",
            importance="critical",
            reason="Required for safe decision support.",
            recommendation_blocking=True,
        )
    ]
    report = run_clinical_red_team(case, _routing(), _clean_outputs())
    assert report.disposition == RedTeamDisposition.BLOCKED
    assert any(f.code == "RECOMMENDATION_BLOCKING_INFORMATION_MISSING" for f in report.findings)


def test_no_evidence_found_is_challenged_not_treated_as_negative_evidence():
    outputs = _clean_outputs()
    outputs["molecular"] = {
        "status": "no_evidence_found",
        "can_support_clinical_actionability_claim": False,
        "interpretations": [],
    }
    report = run_clinical_red_team(_case(), _routing(), outputs)
    assert report.disposition == RedTeamDisposition.CHALLENGED
    assert report.safe_for_consensus is True
    assert any(f.code == "NO_EVIDENCE_FOUND_NOT_NEGATIVE_EVIDENCE" for f in report.findings)


def test_required_source_unavailable_blocks():
    outputs = _clean_outputs()
    outputs["guideline"]["status"] = "source_unavailable"
    report = run_clinical_red_team(_case(), _routing(), outputs)
    assert report.disposition == RedTeamDisposition.BLOCKED
    assert any(f.code == "REQUIRED_SPECIALIST_FAILED" for f in report.findings)


def test_repeatability_and_stable_finding_order():
    outputs = _clean_outputs()
    outputs["translational"]["can_support_clinical_actionability_claim"] = True
    outputs["clinical_trials"]["can_support_eligibility_claim"] = True
    first = run_clinical_red_team(_case(), _routing(), outputs).model_dump()
    second = run_clinical_red_team(_case(), _routing(), outputs).model_dump()
    assert first == second
