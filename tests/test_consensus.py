from agents.consensus import run_consensus
from schemas.agent import RoutingDecision
from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Fact
from schemas.red_team import ClinicalRedTeamFinding, ClinicalRedTeamReport, RedTeamDisposition, RedTeamSeverity


def _case():
    return CancerTumorBoardCase(
        case_id="consensus-test",
        diagnosis=Fact(field="diagnosis", value="acute myeloid leukemia"),
        disease_state=Fact(field="disease_state", value="relapsed"),
        clinical_question=ClinicalQuestion(question_type="management", question="What should be discussed?"),
    )


def _routing(required=None, selected=None):
    selected = selected or ["guideline", "safety"]
    return RoutingDecision(
        question_type="management",
        question_domains=["treatment_management"],
        complexity="complex",
        selected_agents=selected,
        required_agents=required or ["guideline", "safety"],
    )


def _clear_red_team():
    return ClinicalRedTeamReport(
        case_id="consensus-test",
        status="completed",
        disposition=RedTeamDisposition.CLEAR,
        summary="clear",
        safe_for_consensus=True,
    )


def _guideline(matches=1):
    items = []
    for idx in range(matches):
        items.append({
            "recommendation_id": f"G{idx+1}",
            "source_id": "SRC",
            "source_title": "Synthetic Formal Guideline",
            "organization": "Synthetic Society",
            "source_type": "formal_guideline",
            "jurisdiction": "US",
            "recommendation_text": f"Synthetic management strategy {idx+1}",
            "source_excerpt": f"Exact synthetic recommendation excerpt {idx+1}.",
            "source_locator": f"Section {idx+1}",
            "strength": "moderate",
            "conditions": ["Confirm represented disease state"],
            "exclusions": [],
        })
    return {
        "status": "completed",
        "can_support_guideline_claim": True,
        "formal_guideline_matches": matches,
        "matched_guidance": items,
    }


def _safety(blocking=False):
    return {
        "status": "completed",
        "can_support_safety_claim": True,
        "recommendation_blocking": blocking,
        "findings": [],
    }


def test_blocked_red_team_forces_abstention():
    red = ClinicalRedTeamReport(
        case_id="consensus-test",
        status="escalate_human",
        disposition=RedTeamDisposition.BLOCKED,
        findings=[ClinicalRedTeamFinding(
            code="STOP",
            severity=RedTeamSeverity.CRITICAL,
            category="safety",
            issue="Blocking issue",
            effect_on_recommendation="Stop",
            recommendation_blocking=True,
            human_review_required=True,
        )],
        blocking_count=1,
        summary="blocked",
        safe_for_consensus=False,
    )
    report = run_consensus(_case(), _routing(), {"guideline": _guideline(), "safety": _safety()}, red)
    assert report.decision_state == "abstain"
    assert report.safe_to_render_decision_support is False


def test_no_verified_guideline_anchor_abstains():
    outputs = {
        "guideline": {"status": "no_evidence_found", "can_support_guideline_claim": False, "matched_guidance": []},
        "safety": _safety(),
    }
    report = run_consensus(_case(), _routing(), outputs, _clear_red_team())
    assert report.decision_state == "abstain"
    assert report.safe_to_render_decision_support is False


def test_single_formal_guideline_candidate_is_conditional_not_strongly_supported():
    report = run_consensus(_case(), _routing(), {"guideline": _guideline(1), "safety": _safety()}, _clear_red_team())
    assert report.decision_state == "preferred_conditional"
    assert report.decision_support_strength == "moderate"
    assert report.safe_to_render_decision_support is True
    assert len(report.candidates) == 1


def test_multiple_guideline_candidates_are_not_ranked_by_vote():
    report = run_consensus(_case(), _routing(), {"guideline": _guideline(2), "safety": _safety()}, _clear_red_team())
    assert report.decision_state == "multiple_reasonable_options"
    assert len(report.candidates) == 2
    assert report.candidates[0].strategy != report.candidates[1].strategy


def test_authoritative_summary_cannot_anchor_management_candidate():
    summary_only = _guideline(1)
    summary_only["matched_guidance"][0]["source_type"] = "authoritative_evidence_summary"
    report = run_consensus(_case(), _routing(), {"guideline": summary_only, "safety": _safety()}, _clear_red_team())
    assert report.decision_state == "abstain"
    assert report.candidates == []


def test_translational_or_trial_support_cannot_create_management_candidate():
    routing = _routing(required=["safety"], selected=["translational", "clinical_trials", "safety"])
    outputs = {
        "translational": {"status": "completed", "can_support_mechanistic_claim": True, "can_support_clinical_actionability_claim": False},
        "clinical_trials": {"status": "completed_with_limitations", "can_support_trial_match_claim": True, "can_support_eligibility_claim": False},
        "safety": _safety(),
    }
    report = run_consensus(_case(), routing, outputs, _clear_red_team())
    assert report.decision_state == "abstain"
    assert report.candidates == []


def test_safety_block_forces_abstention_even_with_guideline_candidate():
    report = run_consensus(_case(), _routing(), {"guideline": _guideline(), "safety": _safety(True)}, _clear_red_team())
    assert report.decision_state == "abstain"
    assert report.safe_to_render_decision_support is False


def test_repeatability():
    args = (_case(), _routing(), {"guideline": _guideline(), "safety": _safety()}, _clear_red_team())
    first = run_consensus(*args).model_dump()
    second = run_consensus(*args).model_dump()
    assert first == second
