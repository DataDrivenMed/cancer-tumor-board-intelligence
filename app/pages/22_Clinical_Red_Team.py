from __future__ import annotations

import copy
import streamlit as st

from agents.clinical_red_team import run_clinical_red_team
from schemas.agent import RoutingDecision
from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Fact


st.set_page_config(page_title="Clinical Red Team v1.0.0", layout="wide")
st.title("Clinical Red Team v1.0.0")
st.caption("Deterministic adversarial challenge layer before consensus. Synthetic validation scenarios only.")

st.warning(
    "Research prototype only. A CLEAR Red Team result does not establish clinical correctness, efficacy, or patient safety."
)


def make_case() -> CancerTumorBoardCase:
    return CancerTumorBoardCase(
        case_id="REDTEAM-DEMO-001",
        diagnosis=Fact(field="diagnosis", value="synthetic hematologic malignancy"),
        disease_state=Fact(field="disease_state", value="synthetic relapsed state"),
        clinical_question=ClinicalQuestion(
            question_type="management",
            question="Synthetic tumor-board management question",
        ),
    )


def make_routing() -> RoutingDecision:
    selected = ["guideline", "molecular", "translational", "clinical_trials", "safety"]
    return RoutingDecision(
        question_type="management",
        question_domains=["treatment_management"],
        complexity="complex",
        selected_agents=selected,
        required_agents=selected,
    )


def clean_outputs() -> dict:
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
            "matches": [
                {
                    "nct_id": "NCT-SYNTHETIC",
                    "eligibility_determined": False,
                    "eligible": None,
                }
            ],
        },
        "safety": {
            "status": "completed",
            "findings": [],
            "can_support_safety_claim": False,
            "recommendation_blocking": False,
        },
    }


scenario = st.selectbox(
    "Validation scenario",
    [
        "1. Clean structural evidence stack",
        "2. Missing required Safety Agent output",
        "3. Translational evidence promoted to clinical actionability",
        "4. Trial match promoted to patient eligibility",
        "5. Recommendation-blocking safety finding",
        "6. Bounded search returns no evidence",
    ],
)

outputs = copy.deepcopy(clean_outputs())

if scenario.startswith("2."):
    outputs.pop("safety")
elif scenario.startswith("3."):
    outputs["translational"]["can_support_clinical_actionability_claim"] = True
elif scenario.startswith("4."):
    outputs["clinical_trials"]["can_support_eligibility_claim"] = True
    outputs["clinical_trials"]["matches"][0]["eligibility_determined"] = True
    outputs["clinical_trials"]["matches"][0]["eligible"] = True
elif scenario.startswith("5."):
    outputs["safety"] = {
        "status": "completed_with_limitations",
        "findings": [{"safety_issue": "synthetic unresolved required monitoring parameter"}],
        "can_support_safety_claim": True,
        "recommendation_blocking": True,
    }
elif scenario.startswith("6."):
    outputs["molecular"] = {
        "status": "no_evidence_found",
        "can_support_clinical_actionability_claim": False,
        "interpretations": [],
    }

report = run_clinical_red_team(make_case(), make_routing(), outputs)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Disposition", report.disposition.value.upper())
c2.metric("Blocking findings", report.blocking_count)
c3.metric("Critical findings", report.critical_count)
c4.metric("Safe for consensus", "YES" if report.safe_for_consensus else "NO")

st.subheader("Red Team summary")
st.write(report.summary)

if report.findings:
    st.subheader("Challenges")
    for finding in report.findings:
        with st.expander(f"{finding.severity.value.upper()} · {finding.code}", expanded=True):
            st.write(f"**Category:** {finding.category}")
            st.write(f"**Issue:** {finding.issue}")
            st.write(f"**Effect on recommendation:** {finding.effect_on_recommendation}")
            st.write(f"**Recommendation blocking:** {'YES' if finding.recommendation_blocking else 'NO'}")
            st.write(f"**Human review required:** {'YES' if finding.human_review_required else 'NO'}")
            if finding.source_agent_ids:
                st.write("**Source agent(s):** " + ", ".join(finding.source_agent_ids))
else:
    st.success("No deterministic Red Team violation was found in this synthetic structural scenario.")

st.subheader("Safety invariants exercised")
st.code(
    "AGENT AGREEMENT != TRUTH\n"
    "NO EVIDENCE FOUND != NEGATIVE EVIDENCE\n"
    "TRANSLATIONAL EVIDENCE != CLINICAL ACTIONABILITY\n"
    "TRIAL MATCH != TRIAL ELIGIBILITY\n"
    "RECOMMENDATION-BLOCKING SAFETY FINDING -> STOP\n"
    "REQUIRED SPECIALIST FAILURE -> STOP"
)

with st.expander("Raw structured report"):
    st.json(report.model_dump(mode="json"))

st.info(
    "The v1 Red Team is intentionally deterministic and does not invent alternative diagnoses or therapies. "
    "Clinical alternative-generation must be evidence-grounded and belongs downstream of verified specialist evidence."
)
