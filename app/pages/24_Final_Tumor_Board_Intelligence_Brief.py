from __future__ import annotations

import streamlit as st

from agents.tumor_board_brief import render_tumor_board_brief
from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Fact, MissingItem, Provenance, TreatmentEpisode, TreatmentStatus
from schemas.consensus import ConsensusCandidate, ConsensusDisposition, ConsensusEvidenceChannel, ConsensusReport, EvidenceChannelState
from schemas.red_team import ClinicalRedTeamFinding, ClinicalRedTeamReport, RedTeamDisposition, RedTeamSeverity


st.set_page_config(page_title="Tumor Board Intelligence Brief v1.0.0", layout="wide")
st.title("Tumor Board Intelligence Brief v1.0.0")
st.caption("Deterministic final presentation layer. Synthetic validation scenarios only.")
st.warning(
    "Research prototype only. The brief is decision support, not an autonomous treatment directive. "
    "It cannot create new clinical claims or override Consensus, Safety, or Clinical Red Team gates."
)


def prov(doc: str, segment: str, excerpt: str) -> Provenance:
    return Provenance(document_id=doc, source_excerpt=excerpt, source_segment_ids=[segment], source_verified=True)


def make_case(blocking_missing: bool = False) -> CancerTumorBoardCase:
    case = CancerTumorBoardCase(
        case_id="BRIEF-DEMO-001",
        age=61,
        sex="female",
        diagnosis=Fact(field="diagnosis", value="synthetic acute myeloid leukemia", provenance=[prov("DOC-1", "S1", "Synthetic AML")]),
        disease_state=Fact(field="disease_state", value="relapsed", provenance=[prov("DOC-1", "S2", "Relapsed disease")]),
        performance_status=Fact(field="ECOG", value="1", provenance=[prov("DOC-1", "S3", "ECOG 1")]),
        treatments=[TreatmentEpisode(
            episode_id="TX-1",
            regimen="Synthetic prior regimen",
            treatment_status=TreatmentStatus.COMPLETED,
            provenance=[prov("DOC-1", "S4", "Synthetic prior regimen completed")],
        )],
        clinical_question=ClinicalQuestion(question_type="management", question="What management strategies should be discussed?"),
    )
    if blocking_missing:
        case.missing_items = [MissingItem(
            field="decision-critical synthetic result",
            importance="critical",
            reason="Result is not represented in the source case.",
            recommendation_blocking=True,
        )]
    return case


def clear_red() -> ClinicalRedTeamReport:
    return ClinicalRedTeamReport(
        case_id="BRIEF-DEMO-001",
        status="completed",
        disposition=RedTeamDisposition.CLEAR,
        summary="No deterministic Red Team violation in synthetic fixture.",
        safe_for_consensus=True,
    )


def blocked_red() -> ClinicalRedTeamReport:
    return ClinicalRedTeamReport(
        case_id="BRIEF-DEMO-001",
        status="escalate_human",
        disposition=RedTeamDisposition.BLOCKED,
        findings=[ClinicalRedTeamFinding(
            code="SYNTHETIC_BLOCK",
            severity=RedTeamSeverity.CRITICAL,
            category="safety",
            issue="Synthetic unresolved safety blocker.",
            effect_on_recommendation="Withhold management strategy until adjudicated.",
            recommendation_blocking=True,
            human_review_required=True,
        )],
        critical_count=1,
        blocking_count=1,
        summary="Synthetic Red Team blocker.",
        safe_for_consensus=False,
    )


def guideline_output(count: int = 1) -> dict:
    return {
        "status": "completed",
        "can_support_guideline_claim": True,
        "formal_guideline_matches": count,
        "matched_guidance": [
            {
                "recommendation_id": f"SYN-G{idx+1}",
                "source_id": "SYN-GUIDE",
                "source_title": "Synthetic Formal Guideline",
                "source_type": "formal_guideline",
                "recommendation_text": f"Synthetic guideline-supported management strategy {idx+1}",
                "source_excerpt": f"Exact synthetic supporting excerpt {idx+1}.",
                "source_locator": f"Section {idx+1}",
            }
            for idx in range(count)
        ],
    }


def consensus(render: bool = True, count: int = 1) -> ConsensusReport:
    candidates = [
        ConsensusCandidate(
            candidate_id=f"guideline:SYN-G{idx+1}",
            strategy=f"Synthetic guideline-supported management strategy {idx+1}",
            source_agent_id="guideline",
            source_record_id=f"SYN-G{idx+1}",
            source_type="formal_guideline",
            evidence_strength="moderate",
            source_excerpt=f"Exact synthetic supporting excerpt {idx+1}.",
            source_locator=f"Section {idx+1}",
            conditions=["Confirm case-specific applicability"],
        )
        for idx in range(count)
    ] if render else []
    return ConsensusReport(
        case_id="BRIEF-DEMO-001",
        status="completed" if render else "completed_with_limitations",
        disposition=(ConsensusDisposition.CONDITIONAL if count == 1 else ConsensusDisposition.READY) if render else ConsensusDisposition.ABSTAIN,
        decision_state=("preferred_conditional" if count == 1 else "multiple_reasonable_options") if render else "abstain",
        decision_support_strength="moderate" if render else "insufficient",
        candidates=candidates,
        evidence_channels=[ConsensusEvidenceChannel(
            agent_id="guideline",
            state=EvidenceChannelState.SUPPORTIVE if render else EvidenceChannelState.LIMITING,
            status="completed" if render else "no_evidence_found",
            supports_decision=render,
            rationale="Synthetic guideline channel for renderer validation.",
        )],
        summary="Synthetic consensus fixture.",
        abstention_reason=None if render else "No verified formal/consensus guideline anchor.",
        safe_to_render_decision_support=render,
    )


scenario = st.selectbox(
    "Validation scenario",
    [
        "1. One consensus-authorized management candidate",
        "2. Multiple reasonable options",
        "3. Consensus abstains",
        "4. Clinical Red Team blocker",
        "5. Recommendation-blocking missing information preserved",
    ],
)

case = make_case(False)
red = clear_red()
con = consensus(True, 1)
outputs = {
    "guideline": guideline_output(1),
    "literature": {"status": "no_evidence_found", "articles": []},
    "molecular": {"status": "no_evidence_found", "interpretations": [], "can_support_clinical_actionability_claim": False},
    "translational": {"status": "no_evidence_found", "findings": [], "can_support_mechanistic_claim": False},
    "clinical_trials": {"status": "no_evidence_found", "matches": [], "can_support_trial_match_claim": False, "can_support_eligibility_claim": False},
    "safety": {"status": "completed", "findings": [], "can_support_safety_claim": False, "recommendation_blocking": False},
}

if scenario.startswith("2."):
    con = consensus(True, 2)
    outputs["guideline"] = guideline_output(2)
elif scenario.startswith("3."):
    con = consensus(False)
elif scenario.startswith("4."):
    red = blocked_red()
    con = consensus(False)
elif scenario.startswith("5."):
    case = make_case(True)
    con = consensus(False)

brief = render_tumor_board_brief(case, outputs, red, con)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Brief status", brief.status.upper())
c2.metric("Decision state", brief.decision_state.upper())
c3.metric("Source traces", brief.source_trace_count)
c4.metric("Decision support only", "YES" if brief.decision_support_only else "NO")

if brief.critical_warnings:
    for warning in brief.critical_warnings:
        st.error(warning)

st.subheader("Tumor Board Intelligence Brief")
for section in brief.sections:
    with st.expander(section.title, expanded=section.section_id in {"patient_snapshot", "clinical_question", "management_strategy", "red_team"}):
        if section.section_note:
            st.caption(section.section_note)
        if not section.items:
            st.write("No represented item in this section.")
        for item in section.items:
            st.markdown(f"**{item.label}:** {item.value}")
            if item.epistemic_label:
                st.caption(f"Epistemic label: {item.epistemic_label}")
            if item.source_refs:
                st.caption("Source refs: " + ", ".join(item.source_refs))
            for limitation in item.limitations:
                st.caption("Limitation: " + limitation)

st.subheader("Renderer invariants")
st.code(
    "CANONICAL FACTS ONLY -> PATIENT SNAPSHOT\n"
    "CONSENSUS AUTHORIZATION ONLY -> MANAGEMENT STRATEGY\n"
    "CONSENSUS ABSTAIN -> STRATEGY WITHHELD\n"
    "RED TEAM CHALLENGE -> PRESERVED\n"
    "MISSING/CONFLICTING DATA -> PRESERVED, NOT INFERRED\n"
    "TRIAL MATCH != ELIGIBILITY\n"
    "TRANSLATIONAL SIGNAL != CLINICAL ACTIONABILITY\n"
    "NO NEW CLAIMS CREATED BY RENDERER"
)

with st.expander("Raw structured brief"):
    st.json(brief.model_dump(mode="json"))
