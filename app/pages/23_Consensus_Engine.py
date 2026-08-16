from __future__ import annotations

import copy
import streamlit as st

from agents.consensus import run_consensus
from schemas.agent import RoutingDecision
from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Fact
from schemas.red_team import ClinicalRedTeamFinding, ClinicalRedTeamReport, RedTeamDisposition, RedTeamSeverity


st.set_page_config(page_title="Consensus Engine v1.0.0", layout="wide")
st.title("Consensus Engine v1.0.0")
st.caption("Deterministic evidence integration after Clinical Red Team. Synthetic validation scenarios only.")

st.warning(
    "Research prototype only. Consensus is decision support, not an autonomous treatment directive. "
    "Agent agreement is never treated as truth."
)


def make_case() -> CancerTumorBoardCase:
    return CancerTumorBoardCase(
        case_id="CONSENSUS-DEMO-001",
        diagnosis=Fact(field="diagnosis", value="synthetic hematologic malignancy"),
        disease_state=Fact(field="disease_state", value="synthetic relapsed state"),
        clinical_question=ClinicalQuestion(question_type="management", question="Synthetic management question"),
    )


def make_routing(selected=None, required=None) -> RoutingDecision:
    selected = selected or ["guideline", "safety"]
    return RoutingDecision(
        question_type="management",
        question_domains=["treatment_management"],
        complexity="complex",
        selected_agents=selected,
        required_agents=required or selected,
    )


def clear_red_team() -> ClinicalRedTeamReport:
    return ClinicalRedTeamReport(
        case_id="CONSENSUS-DEMO-001",
        status="completed",
        disposition=RedTeamDisposition.CLEAR,
        summary="No structural challenge in synthetic scenario.",
        safe_for_consensus=True,
    )


def blocked_red_team() -> ClinicalRedTeamReport:
    return ClinicalRedTeamReport(
        case_id="CONSENSUS-DEMO-001",
        status="escalate_human",
        disposition=RedTeamDisposition.BLOCKED,
        findings=[ClinicalRedTeamFinding(
            code="SYNTHETIC_BLOCK",
            severity=RedTeamSeverity.CRITICAL,
            category="safety",
            issue="Synthetic recommendation-blocking Red Team finding.",
            effect_on_recommendation="Do not proceed until adjudicated.",
            recommendation_blocking=True,
            human_review_required=True,
        )],
        blocking_count=1,
        critical_count=1,
        summary="Synthetic blocked Red Team scenario.",
        safe_for_consensus=False,
    )


def guideline_output(count=1, source_type="formal_guideline") -> dict:
    matches = []
    for idx in range(count):
        matches.append({
            "recommendation_id": f"SYN-G{idx+1}",
            "source_type": source_type,
            "recommendation_text": f"Synthetic management strategy {idx+1}",
            "source_excerpt": f"Exact synthetic recommendation excerpt {idx+1}.",
            "source_locator": f"Synthetic section {idx+1}",
            "strength": "moderate",
            "conditions": ["Confirm case-specific applicability"],
            "exclusions": [],
        })
    return {
        "status": "completed",
        "can_support_guideline_claim": source_type in {"formal_guideline", "consensus_guideline"},
        "formal_guideline_matches": count if source_type in {"formal_guideline", "consensus_guideline"} else 0,
        "matched_guidance": matches,
    }


def safety_output(blocking=False) -> dict:
    return {
        "status": "completed_with_limitations" if blocking else "completed",
        "can_support_safety_claim": True,
        "recommendation_blocking": blocking,
        "findings": [{"safety_issue": "synthetic blocker"}] if blocking else [],
    }


scenario = st.selectbox(
    "Validation scenario",
    [
        "1. One verified formal-guideline candidate",
        "2. Multiple verified formal-guideline candidates",
        "3. No verified guideline anchor",
        "4. Authoritative evidence summary only",
        "5. Translational and trial signals without guideline anchor",
        "6. Clinical Red Team blocked",
        "7. Recommendation-blocking safety condition",
    ],
)

case = make_case()
red = clear_red_team()
routing = make_routing()
outputs = {"guideline": guideline_output(1), "safety": safety_output()}

if scenario.startswith("2."):
    outputs["guideline"] = guideline_output(2)
elif scenario.startswith("3."):
    outputs["guideline"] = {
        "status": "no_evidence_found",
        "can_support_guideline_claim": False,
        "formal_guideline_matches": 0,
        "matched_guidance": [],
    }
elif scenario.startswith("4."):
    outputs["guideline"] = guideline_output(1, "authoritative_evidence_summary")
elif scenario.startswith("5."):
    routing = make_routing(selected=["translational", "clinical_trials", "safety"], required=["safety"])
    outputs = {
        "translational": {"status": "completed", "can_support_mechanistic_claim": True, "can_support_clinical_actionability_claim": False},
        "clinical_trials": {"status": "completed_with_limitations", "can_support_trial_match_claim": True, "can_support_eligibility_claim": False},
        "safety": safety_output(),
    }
elif scenario.startswith("6."):
    red = blocked_red_team()
elif scenario.startswith("7."):
    outputs["safety"] = safety_output(True)

report = run_consensus(case, routing, outputs, red)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Disposition", report.disposition.value.upper())
c2.metric("Decision state", report.decision_state.upper())
c3.metric("Candidates", len(report.candidates))
c4.metric("Safe to render", "YES" if report.safe_to_render_decision_support else "NO")

st.subheader("Consensus summary")
st.write(report.summary)

if report.abstention_reason:
    st.error(report.abstention_reason)

if report.candidates:
    st.subheader("Evidence-anchored management candidates")
    for candidate in report.candidates:
        with st.expander(candidate.strategy, expanded=True):
            st.write(f"**Source type:** {candidate.source_type}")
            st.write(f"**Evidence strength:** {candidate.evidence_strength or 'not stated'}")
            st.write(f"**Exact source excerpt:** {candidate.source_excerpt}")
            st.write(f"**Locator:** {candidate.source_locator or 'not stated'}")
            if candidate.conditions:
                st.write("**Conditions:** " + "; ".join(candidate.conditions))

st.subheader("Evidence channels")
for channel in report.evidence_channels:
    st.write(
        f"**{channel.agent_id}** · {channel.state.value.upper()} · status={channel.status} · "
        f"supports decision={'YES' if channel.supports_decision else 'NO'}"
    )
    st.caption(channel.rationale)

if report.red_team_challenges:
    st.subheader("Preserved Red Team challenges")
    for item in report.red_team_challenges:
        st.write(f"- {item}")

st.subheader("Consensus invariants")
st.code(
    "AGENT AGREEMENT != TRUTH\n"
    "NO VERIFIED FORMAL/CONSENSUS GUIDELINE ANCHOR -> NO MANAGEMENT CANDIDATE\n"
    "TRANSLATIONAL SIGNAL != TREATMENT RECOMMENDATION\n"
    "TRIAL MATCH != TREATMENT RECOMMENDATION OR ELIGIBILITY\n"
    "SAFETY BLOCK -> ABSTAIN\n"
    "RED TEAM BLOCK -> ABSTAIN"
)

with st.expander("Raw structured report"):
    st.json(report.model_dump(mode="json"))
