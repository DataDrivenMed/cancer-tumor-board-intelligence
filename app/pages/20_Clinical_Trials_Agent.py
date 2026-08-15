from __future__ import annotations

import streamlit as st

from agents.clinical_trials import ClinicalTrialsAgent
from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Fact, MolecularFinding
from services.clinicaltrials_client import ClinicalTrialsClient


st.set_page_config(page_title="Clinical Trials Agent v1", layout="wide")
st.title("Clinical Trials Agent v1.0.0")
st.caption("Live ClinicalTrials.gov API v2 retrieval. Trial match is not trial eligibility.")
st.warning("Research prototype. Use synthetic or de-identified inputs only. Do not enter PHI.")


def make_case(label: str) -> CancerTumorBoardCase:
    if label == "Relapsed AML with FLT3":
        diagnosis = "Acute myeloid leukemia"
        genes = [MolecularFinding(gene="FLT3", alteration_type="ITD")]
    elif label == "Relapsed AML without represented molecular finding":
        diagnosis = "Acute myeloid leukemia"
        genes = []
    else:
        diagnosis = "Multiple myeloma"
        genes = [MolecularFinding(gene="KRAS", alteration_type="mutation")]
    return CancerTumorBoardCase(
        case_id="synthetic-trial-demo",
        diagnosis=Fact(field="diagnosis", value=diagnosis),
        disease_state=Fact(field="disease_state", value="relapsed"),
        molecular_findings=genes,
        clinical_question=ClinicalQuestion(question_type="trial", question="What clinical trials may be relevant?"),
    )


scenario = st.selectbox(
    "Synthetic scenario",
    ["Relapsed AML with FLT3", "Relapsed AML without represented molecular finding", "Relapsed multiple myeloma"],
)
limit = st.slider("Maximum retrieved studies", min_value=5, max_value=25, value=10, step=5)

st.info(
    "The external query uses only structured diagnosis and represented gene symbols. "
    "The free-text tumor-board narrative and care-site are not sent to ClinicalTrials.gov."
)

if st.button("Run live ClinicalTrials.gov retrieval", type="primary"):
    case = make_case(scenario)
    agent = ClinicalTrialsAgent(ClinicalTrialsClient(), page_size=limit)
    with st.spinner("Querying the official ClinicalTrials.gov API v2..."):
        report = agent.run(case)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Status", report.status.replace("_", " ").upper())
    c2.metric("Retrieved records", len(report.records))
    c3.metric("Possible matches", len(report.matches))
    c4.metric("Eligibility claim", "YES" if report.can_support_eligibility_claim else "NO")

    if report.search_trace:
        st.subheader("Search trace")
        st.write({
            "condition": report.search_trace.query_condition,
            "terms": report.search_trace.query_terms,
            "api_version": report.search_trace.api_version,
            "data_timestamp": report.search_trace.data_timestamp,
        })

    st.subheader("Possible matches")
    if not report.matches:
        st.write("No possible matches passed the deterministic active-recruitment plus structured-concept rule.")
    for match in report.matches:
        with st.expander(f"{match.nct_id} · {match.title}"):
            st.write("Recruitment status:", match.overall_status)
            st.write("Matched concepts:", match.matched_concepts)
            st.write("Eligibility determined:", match.eligibility_determined)
            st.write("Unresolved eligibility domains:", match.unresolved_eligibility_domains)
            st.write(match.rationale)
            st.link_button("Open ClinicalTrials.gov record", match.source_url)

    st.subheader("Safety boundary")
    st.error("TRIAL MATCH ≠ TRIAL ELIGIBILITY. A study-team review is required before any eligibility claim.")
    for item in report.limitations:
        st.write("-", item)

    with st.expander("Raw structured report"):
        st.json(report.model_dump(mode="json"))
