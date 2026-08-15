import streamlit as st

from agents.translational import TranslationalBiologyAgent
from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Fact, MolecularFinding
from services.translational_sources import PRODUCTION_TRANSLATIONAL_STORE, SYNTHETIC_TRANSLATIONAL_STORE

st.set_page_config(page_title="Translational Biology Agent v1.0.0", layout="wide")
st.title("Translational Biology Agent v1.0.0")
st.caption("Research prototype. Translational evidence is not clinical actionability and does not establish treatment efficacy or eligibility.")


def make_case(gene="FLT3", alteration="FLT3-ITD", diagnosis="acute myeloid leukemia"):
    return CancerTumorBoardCase(
        case_id="translational-ui",
        diagnosis=Fact(field="diagnosis", value=diagnosis, human_verified=True),
        disease_state=Fact(field="disease_state", value="relapsed", human_verified=True),
        molecular_findings=[MolecularFinding(gene=gene, alteration_type=alteration, human_verified=True)],
        clinical_question=ClinicalQuestion(question_type="molecular", question="What is the translational significance?"),
    )

scenario = st.selectbox(
    "Validation scenario",
    [
        "Production-safe default",
        "Verified synthetic FLT3-ITD mechanistic match",
        "Gene match but alteration mismatch",
        "Synthetic TP53 preclinical resistance signal",
        "Disease-context mismatch",
    ],
)

if scenario == "Production-safe default":
    case = make_case()
    agent = TranslationalBiologyAgent(PRODUCTION_TRANSLATIONAL_STORE, production_mode=True)
elif scenario == "Verified synthetic FLT3-ITD mechanistic match":
    case = make_case()
    agent = TranslationalBiologyAgent(SYNTHETIC_TRANSLATIONAL_STORE, production_mode=False)
elif scenario == "Gene match but alteration mismatch":
    case = make_case(alteration="TKD point mutation")
    agent = TranslationalBiologyAgent(SYNTHETIC_TRANSLATIONAL_STORE, production_mode=False)
elif scenario == "Synthetic TP53 preclinical resistance signal":
    case = make_case(gene="TP53", alteration="mutation")
    agent = TranslationalBiologyAgent(SYNTHETIC_TRANSLATIONAL_STORE, production_mode=False)
else:
    case = make_case(diagnosis="multiple myeloma")
    agent = TranslationalBiologyAgent(SYNTHETIC_TRANSLATIONAL_STORE, production_mode=False)

if st.button("Run Translational Biology Agent", type="primary"):
    report = agent.run(case)
    c1, c2, c3 = st.columns(3)
    c1.metric("Status", report.status.replace("_", " ").upper())
    c2.metric("Mechanistic claim support", "YES" if report.can_support_mechanistic_claim else "NO")
    c3.metric("Clinical actionability claim", "YES" if report.can_support_clinical_actionability_claim else "NO")

    st.subheader("Findings")
    if report.findings:
        for finding in report.findings:
            with st.expander(finding.subject, expanded=True):
                st.write("Matched evidence IDs:", finding.matched_evidence_ids or "None")
                st.write("Strongest tier:", finding.strongest_tier.value if finding.strongest_tier else "None")
                st.write("Human translational support:", finding.human_translational_support)
                st.write("Clinical actionability claim:", finding.clinical_actionability_claim)
                st.write("Mechanisms:", finding.mechanisms or "None")
                st.write("Directions:", [d.value for d in finding.directions])
                st.write("Limitations:", finding.limitations or "None")
    else:
        st.info("No translational findings were produced.")

    st.subheader("Agent limitations")
    for item in report.limitations:
        st.write("-", item)
    st.subheader("Raw report")
    st.json(report.model_dump(mode="json"))
