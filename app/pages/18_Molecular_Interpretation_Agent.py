from __future__ import annotations

import streamlit as st

from agents.molecular import MolecularInterpretationAgent
from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Fact, MolecularFinding
from services.molecular_sources import build_synthetic_molecular_store


st.set_page_config(page_title="Molecular Interpretation Agent", layout="wide")
st.title("Molecular Interpretation Agent v1.0.0")
st.caption("Validation interface. Synthetic/de-identified cases only. Molecular evidence is disease- and alteration-specific; mechanism is not treated as clinical actionability.")

scenario = st.selectbox(
    "Validation scenario",
    [
        "Production-safe default: no verified molecular store",
        "Verified synthetic FLT3-ITD match",
        "Gene match but alteration mismatch",
        "Prognostic TP53 signal without therapy actionability",
        "Disease-context mismatch",
    ],
)


def build_case(name: str) -> tuple[CancerTumorBoardCase, bool]:
    gene = "FLT3"
    alteration = "ITD"
    diagnosis = "acute myeloid leukemia"
    production = False
    if name.startswith("Production-safe"):
        production = True
    elif name.startswith("Gene match"):
        alteration = "D835"
    elif name.startswith("Prognostic"):
        gene = "TP53"
        alteration = "mutation"
    elif name.startswith("Disease-context"):
        diagnosis = "multiple myeloma"

    case = CancerTumorBoardCase(
        case_id="molecular-validation",
        diagnosis=Fact(field="diagnosis", value=diagnosis),
        disease_state=Fact(field="disease_state", value="relapsed"),
        molecular_findings=[MolecularFinding(gene=gene, alteration_type=alteration)],
        clinical_question=ClinicalQuestion(
            question_type="molecular",
            question="What is the molecular significance and is there verified clinical actionability?",
        ),
    )
    return case, production


if st.button("Run Molecular Interpretation Agent", type="primary"):
    case, production = build_case(scenario)
    if production:
        agent = MolecularInterpretationAgent()
    else:
        agent = MolecularInterpretationAgent(build_synthetic_molecular_store(), production_mode=False)
    report = agent.run(case)

    c1, c2, c3 = st.columns(3)
    c1.metric("Status", report.status.replace("_", " ").upper())
    c2.metric("Findings", len(report.interpretations))
    c3.metric("Can support clinical actionability", "YES" if report.can_support_clinical_actionability_claim else "NO")

    st.subheader("Interpretations")
    for item in report.interpretations:
        with st.expander(f"{item.gene} | {item.alteration or 'alteration not specified'}", expanded=True):
            st.write("Clinical actionability:", item.clinical_actionability.value)
            st.write("Matched evidence IDs:", item.matched_evidence_ids or "None")
            st.write("Evidence directions:", [d.value for d in item.evidence_directions] or "None")
            st.write("Therapies:", item.therapies or "None")
            st.write("Resistance signal:", item.resistance_signal)
            st.write("Diagnostic signal:", item.diagnostic_signal)
            st.write("Prognostic signal:", item.prognostic_signal)
            st.write("Can support actionability claim:", item.can_support_clinical_actionability_claim)
            if item.limitations:
                st.warning("\n".join(item.limitations))

    if report.limitations:
        st.subheader("Safety boundaries")
        for limitation in report.limitations:
            st.info(limitation)

    with st.expander("Full typed report"):
        st.json(report.model_dump(mode="json"))

st.divider()
st.markdown(
    "**Expected validation behavior**\n\n"
    "- Production-safe default: `SOURCE_UNAVAILABLE`, actionability `NO`.\n"
    "- Synthetic FLT3-ITD: `COMPLETED`, established actionability in the synthetic fixture only.\n"
    "- FLT3 D835 mismatch: `NO_EVIDENCE_FOUND`, no inferred actionability.\n"
    "- TP53 synthetic prognostic fixture: prognostic signal present, therapy actionability `NO`.\n"
    "- Disease mismatch: `NO_EVIDENCE_FOUND`."
)
