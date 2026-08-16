from __future__ import annotations

from agents.tumor_board_brief import render_tumor_board_brief
from schemas.agent import RoutingDecision
from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Fact, Provenance
from schemas.consensus import ConsensusCandidate, ConsensusDisposition, ConsensusReport
from schemas.red_team import ClinicalRedTeamFinding, ClinicalRedTeamReport, RedTeamDisposition, RedTeamSeverity


def _prov() -> Provenance:
    return Provenance(document_id="DOC-1", source_excerpt="Synthetic source text", source_segment_ids=["S1"], source_verified=True)


def _case() -> CancerTumorBoardCase:
    return CancerTumorBoardCase(
        case_id="BRIEF-001",
        age=61,
        sex="female",
        diagnosis=Fact(field="diagnosis", value="synthetic AML", provenance=[_prov()]),
        disease_state=Fact(field="disease_state", value="relapsed", provenance=[_prov()]),
        performance_status=Fact(field="ECOG", value="1", provenance=[_prov()]),
        clinical_question=ClinicalQuestion(question_type="management", question="What should be discussed?"),
    )


def _red(clear=True) -> ClinicalRedTeamReport:
    if clear:
        return ClinicalRedTeamReport(
            case_id="BRIEF-001",
            status="completed",
            disposition=RedTeamDisposition.CLEAR,
            summary="clear",
            safe_for_consensus=True,
        )
    return ClinicalRedTeamReport(
        case_id="BRIEF-001",
        status="escalate_human",
        disposition=RedTeamDisposition.BLOCKED,
        findings=[ClinicalRedTeamFinding(
            code="BLOCK",
            severity=RedTeamSeverity.CRITICAL,
            category="safety",
            issue="Synthetic blocker",
            effect_on_recommendation="Withhold strategy",
            recommendation_blocking=True,
            human_review_required=True,
        )],
        critical_count=1,
        blocking_count=1,
        summary="blocked",
        safe_for_consensus=False,
    )


def _consensus(render=True) -> ConsensusReport:
    return ConsensusReport(
        case_id="BRIEF-001",
        status="completed" if render else "completed_with_limitations",
        disposition=ConsensusDisposition.CONDITIONAL if render else ConsensusDisposition.ABSTAIN,
        decision_state="preferred_conditional" if render else "abstain",
        decision_support_strength="moderate" if render else "insufficient",
        candidates=[ConsensusCandidate(
            candidate_id="guideline:G1",
            strategy="Synthetic guideline-supported strategy",
            source_agent_id="guideline",
            source_record_id="G1",
            source_type="formal_guideline",
            evidence_strength="moderate",
            source_excerpt="Exact synthetic excerpt",
            source_locator="Section 1",
            conditions=["Confirm case fit"],
        )] if render else [],
        summary="synthetic",
        abstention_reason=None if render else "No verified management anchor",
        safe_to_render_decision_support=render,
    )


def test_brief_renders_only_consensus_authorized_strategy():
    report = render_tumor_board_brief(_case(), {}, _red(), _consensus(True))
    management = next(s for s in report.sections if s.section_id == "management_strategy")
    assert management.items[0].value == "Synthetic guideline-supported strategy"
    assert report.decision_support_only is True
    assert report.safe_to_display is True


def test_brief_withholds_strategy_when_consensus_abstains():
    report = render_tumor_board_brief(_case(), {}, _red(), _consensus(False))
    management = next(s for s in report.sections if s.section_id == "management_strategy")
    assert management.items[0].value == "WITHHELD"
    assert report.status == "abstain"


def test_brief_preserves_red_team_blocker():
    report = render_tumor_board_brief(_case(), {}, _red(False), _consensus(False))
    red = next(s for s in report.sections if s.section_id == "red_team")
    assert any(item.label == "BLOCK" for item in red.items)
    assert any("Recommendation-blocking" in limitation for item in red.items for limitation in item.limitations)


def test_canonical_fact_provenance_is_exposed():
    report = render_tumor_board_brief(_case(), {}, _red(), _consensus(False))
    snapshot = next(s for s in report.sections if s.section_id == "patient_snapshot")
    diagnosis = next(item for item in snapshot.items if item.label == "Diagnosis")
    assert "DOC-1" in diagnosis.source_refs
    assert "S1" in diagnosis.source_refs


def test_renderer_is_deterministic():
    first = render_tumor_board_brief(_case(), {}, _red(), _consensus(True)).model_dump(mode="json")
    second = render_tumor_board_brief(_case(), {}, _red(), _consensus(True)).model_dump(mode="json")
    assert first == second
