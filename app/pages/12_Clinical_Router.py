from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestration.router import route_case
from schemas.case import (
    CancerTumorBoardCase,
    ClinicalQuestion,
    Fact,
    MolecularFinding,
    Provenance,
    TreatmentEpisode,
    TreatmentStatus,
)


st.set_page_config(page_title="Clinical Router", page_icon="🧭", layout="wide")
st.title("Clinical Router")
st.caption("Deterministic specialist-agent routing after upstream integrity and missing-information gates.")
st.warning("Development environment only. Synthetic/de-identified cases only. This page does not generate clinical recommendations.")


def prov(text: str) -> Provenance:
    return Provenance(
        document_id="ROUTER-DEMO",
        source_excerpt=text,
        source_segment_ids=["S0001"],
        source_verified=True,
    )


def fact(field: str, value: str) -> Fact:
    return Fact(field=field, value=value, provenance=[prov(value)])


def base_case(question_type: str, question: str) -> CancerTumorBoardCase:
    return CancerTumorBoardCase(
        case_id="ROUTER-DEMO-001",
        disease_program="hematologic_malignancy",
        diagnosis=fact("diagnosis", "acute myeloid leukemia"),
        disease_state=fact("disease_state", "newly diagnosed"),
        performance_status=fact("ECOG", "1"),
        clinical_question=ClinicalQuestion(question_type=question_type, question=question),
    )


def scenario_case(name: str) -> CancerTumorBoardCase:
    if name == "Management question":
        return base_case("management", "What treatment strategies should be discussed?")

    if name == "Molecular treatment question":
        case = base_case("management", "How should treatment be framed in the context of FLT3-ITD?")
        case.molecular_findings = [MolecularFinding(
            gene="FLT3",
            alteration_type="ITD",
            provenance=[prov("FLT3-ITD detected")],
        )]
        return case

    if name == "Pure safety question":
        return base_case("safety", "What toxicity, contraindication, and drug-interaction issues should be reviewed?")

    if name == "Translational biology question":
        return base_case(
            "translational_biology",
            "What resistance mechanisms and pathway biology should be discussed?",
        )

    case = base_case("management", "What treatment and trial options should be discussed?")
    case.case_id = "ROUTER-DEMO-HIGH-COMPLEXITY"
    case.disease_state = fact("disease_state", "relapsed refractory")
    case.molecular_findings = [MolecularFinding(
        gene="TP53",
        alteration_type="mutation",
        provenance=[prov("TP53 mutation detected")],
    )]
    case.treatments = [
        TreatmentEpisode(
            episode_id=f"TX-{idx:03d}",
            regimen=f"Synthetic regimen {idx}",
            treatment_status=TreatmentStatus.COMPLETED,
            provenance=[prov(f"Synthetic regimen {idx} completed")],
        )
        for idx in range(1, 4)
    ]
    return case


scenario = st.selectbox(
    "Synthetic routing scenario",
    [
        "Management question",
        "Molecular treatment question",
        "Pure safety question",
        "Translational biology question",
        "High-complexity relapsed case",
    ],
)
case = scenario_case(scenario)

left, right = st.columns([1, 1])
with left:
    st.markdown("### Canonical routing input")
    st.write(f"**Case:** {case.case_id}")
    st.write(f"**Question type:** {case.clinical_question.question_type}")
    st.write(f"**Question:** {case.clinical_question.question}")
    st.write(f"**Disease state:** {case.disease_state.value}")
    st.write(f"**Treatment episodes:** {len(case.treatments)}")
    st.write(f"**Molecular findings:** {len(case.molecular_findings)}")

if st.button("Run Clinical Router", type="primary"):
    st.session_state["clinical_router_report"] = route_case(case)

report = st.session_state.get("clinical_router_report")
if report is not None:
    with right:
        st.markdown("### Routing decision")
        c1, c2, c3 = st.columns(3)
        c1.metric("Router version", report.router_version)
        c2.metric("Complexity", report.complexity.replace("_", " ").title())
        c3.metric("Selected agents", len(report.selected_agents))

        st.markdown("**Question domains:** " + " · ".join(d.replace("_", " ").title() for d in report.question_domains))
        st.markdown("**Selected:** " + " · ".join(a.replace("_", " ").title() for a in report.selected_agents))
        st.markdown("**Required:** " + (" · ".join(a.replace("_", " ").title() for a in report.required_agents) or "None"))
        st.markdown("**Conditional:** " + (" · ".join(a.replace("_", " ").title() for a in report.conditional_agents) or "None"))
        st.markdown("**Omitted:** " + (" · ".join(a.replace("_", " ").title() for a in report.omitted_agents) or "None"))

        if report.safe_to_execute:
            st.success("Router output is safe to execute because upstream gates are assumed to have passed.")
        else:
            st.error("Routing execution blocked.")

    st.markdown("### Routing rationale")
    for item in report.rationale:
        st.write(f"• {item}")
    for warning in report.routing_warnings:
        st.warning(warning)

    with st.expander("Typed RoutingDecision"):
        st.json(report.model_dump(mode="json"))

st.divider()
st.caption(
    "The router selects bounded specialist services. Agent selection is not evidence, actionability, trial eligibility, or a clinical recommendation."
)
