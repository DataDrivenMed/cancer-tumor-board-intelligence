import streamlit as st

from agents.safety import SafetyAgent
from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Fact
from services.safety_sources import PRODUCTION_SAFETY_STORE, synthetic_safety_store


st.set_page_config(page_title="Safety Agent v1.0.0", layout="wide")
st.title("Safety Agent v1.0.0")
st.caption("Deterministic, evidence-bounded safety analysis. Synthetic cases and synthetic evidence only on this validation page.")

scenario = st.selectbox(
    "Scenario",
    [
        "Production-safe default",
        "Verified synthetic monitoring match",
        "Synthetic monitoring parameters missing",
        "Synthetic conditional contraindication",
        "Therapy mismatch",
    ],
)


def build_case(medication: str, *, monitoring: bool = True, hypersensitivity: bool = False) -> CancerTumorBoardCase:
    labs = []
    if monitoring:
        labs = [
            Fact(field="potassium", value="4.1 mmol/L"),
            Fact(field="magnesium", value="2.0 mg/dL"),
            Fact(field="ECG", value="QTc documented"),
        ]
    comorbidities = [Fact(field="allergy", value="synthetic hypersensitivity")] if hypersensitivity else []
    return CancerTumorBoardCase(
        case_id="safety-validation",
        diagnosis=Fact(field="diagnosis", value="acute myeloid leukemia"),
        disease_state=Fact(field="disease_state", value="relapsed"),
        current_medications=[Fact(field="medication", value=medication)],
        labs=labs,
        comorbidities=comorbidities,
        clinical_question=ClinicalQuestion(question_type="safety", question="Review treatment safety."),
    )


if scenario == "Production-safe default":
    case = build_case("Synthetic Drug X")
    agent = SafetyAgent(PRODUCTION_SAFETY_STORE, production_mode=True)
elif scenario == "Verified synthetic monitoring match":
    case = build_case("Synthetic Drug X", monitoring=True)
    agent = SafetyAgent(synthetic_safety_store(), production_mode=False)
elif scenario == "Synthetic monitoring parameters missing":
    case = build_case("Synthetic Drug X", monitoring=False)
    agent = SafetyAgent(synthetic_safety_store(), production_mode=False)
elif scenario == "Synthetic conditional contraindication":
    case = build_case("Synthetic Drug Y", hypersensitivity=True)
    agent = SafetyAgent(synthetic_safety_store(), production_mode=False)
else:
    case = build_case("Unrelated Therapy")
    agent = SafetyAgent(synthetic_safety_store(), production_mode=False)

report = agent.run(case)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Status", report.status.upper())
c2.metric("Findings", len(report.findings))
c3.metric("Safety claim support", "YES" if report.can_support_safety_claim else "NO")
c4.metric("Recommendation blocking", "YES" if report.recommendation_blocking else "NO")

st.subheader("Findings")
if not report.findings:
    st.info("No matched safety findings.")
for finding in report.findings:
    with st.expander(f"{finding.evidence_id} · {finding.evidence_type.value} · {finding.severity.value}", expanded=True):
        st.write(f"**Issue:** {finding.safety_issue}")
        st.write(f"**Therapy match:** {', '.join(finding.therapy_terms_matched) or 'none'}")
        st.write(f"**Trigger match:** {', '.join(finding.trigger_terms_matched) or 'none required'}")
        st.write(f"**Required parameters:** {', '.join(finding.required_parameters) or 'none'}")
        st.write(f"**Unresolved parameters:** {', '.join(finding.unresolved_parameters) or 'none'}")
        st.write(f"**Source:** {finding.source_title} · {finding.source_locator}")
        st.code(finding.source_excerpt)
        st.write(f"**Contraindication:** {finding.contraindication}")
        st.write(f"**Recommendation blocking:** {finding.recommendation_blocking}")

if report.warnings:
    st.subheader("Warnings")
    for warning in report.warnings:
        st.warning(warning)

st.subheader("Limitations")
for item in report.limitations:
    st.write(f"- {item}")

st.divider()
st.caption("Synthetic evidence on this page is fictional and must never be treated as clinical evidence. A non-match is not evidence of safety.")
