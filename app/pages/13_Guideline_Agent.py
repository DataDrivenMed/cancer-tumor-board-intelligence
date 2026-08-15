from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.guideline import GuidelineAgent
from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Fact, Provenance
from services.guideline_sources import PRODUCTION_GUIDELINE_STORE, synthetic_guideline_store


st.set_page_config(page_title="Guideline Agent", page_icon="📚", layout="wide")
st.title("Guideline Agent v1.0.0")
st.caption("Verified-source, evidence-bounded guidance matching. No unsupported guideline claim is permitted.")
st.warning(
    "Development environment only. Synthetic/de-identified cases only. The built-in evidence fixture is fictional and is not clinical guidance."
)


def prov(text: str) -> Provenance:
    return Provenance(
        document_id="GUIDELINE-DEMO",
        source_excerpt=text,
        source_segment_ids=["S0001"],
        source_verified=True,
    )


def fact(field: str, value: str) -> Fact:
    return Fact(field=field, value=value, provenance=[prov(value)])


def demo_case(diagnosis: str = "acute myeloid leukemia", state: str = "relapsed") -> CancerTumorBoardCase:
    return CancerTumorBoardCase(
        case_id="GUIDELINE-DEMO-001",
        disease_program="hematologic_malignancy",
        diagnosis=fact("diagnosis", diagnosis),
        disease_state=fact("disease_state", state),
        performance_status=fact("ECOG", "1"),
        clinical_question=ClinicalQuestion(
            question_type="treatment_management",
            question="What treatment strategies should be discussed?",
        ),
    )


scenario = st.selectbox(
    "Validation scenario",
    [
        "Production-safe default: no authorized source",
        "Verified synthetic matching fixture",
        "Verified synthetic diagnosis mismatch",
    ],
)

case = demo_case()
if scenario == "Production-safe default: no authorized source":
    agent = GuidelineAgent(PRODUCTION_GUIDELINE_STORE, today=date.today())
    expected = "SOURCE UNAVAILABLE, zero claims"
elif scenario == "Verified synthetic matching fixture":
    agent = GuidelineAgent(synthetic_guideline_store(), allow_synthetic=True, today=date.today())
    expected = "COMPLETED WITH LIMITATIONS, one synthetic fixture match, no formal guideline claim"
else:
    case = demo_case(diagnosis="multiple myeloma", state="relapsed")
    agent = GuidelineAgent(synthetic_guideline_store(), allow_synthetic=True, today=date.today())
    expected = "NO EVIDENCE FOUND, zero matches"

left, right = st.columns([1, 1])
with left:
    st.markdown("### Canonical input")
    st.write(f"**Case:** {case.case_id}")
    st.write(f"**Diagnosis:** {case.diagnosis.value}")
    st.write(f"**Disease state:** {case.disease_state.value}")
    st.write(f"**Question:** {case.clinical_question.question}")
    st.info(f"Expected validation behavior: {expected}")

if st.button("Run Guideline Agent", type="primary"):
    st.session_state["guideline_agent_report"] = agent.run(case)

report = st.session_state.get("guideline_agent_report")
if report is not None:
    with right:
        st.markdown("### Guidance report")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Status", report.status.replace("_", " ").upper())
        c2.metric("Verified sources", report.verified_sources_considered)
        c3.metric("Matched statements", len(report.matched_guidance))
        c4.metric("Formal guideline matches", report.formal_guideline_matches)

        if report.can_support_guideline_claim:
            st.success("A verified formal/consensus guideline source supports at least one matched statement.")
        else:
            st.info("This execution cannot support a formal guideline claim.")

        st.write(report.summary)

    if report.matched_guidance:
        st.markdown("### Matched source-bounded statements")
        for match in report.matched_guidance:
            with st.container(border=True):
                st.write(f"**{match.source_title}**")
                st.write(f"Source type: `{match.source_type.value}` · Epistemic label: `{match.epistemic_label}`")
                st.write(f"Statement: {match.recommendation_text}")
                st.write(f"Exact source excerpt: {match.source_excerpt}")
                if match.source_locator:
                    st.write(f"Locator: `{match.source_locator}`")
                st.write("Matched on: " + ", ".join(match.match_dimensions))

    for warning in report.warnings:
        st.warning(warning)
    for limitation in report.limitations:
        st.info(limitation)

    with st.expander("Typed GuidelineReport"):
        st.json(report.model_dump(mode="json"))

st.divider()
st.caption(
    "NCI PDQ and similar evidence summaries must be labeled according to their actual source type. "
    "The agent must not relabel an evidence summary as a formal guideline. Licensed guideline content is not bundled in this public repository."
)
