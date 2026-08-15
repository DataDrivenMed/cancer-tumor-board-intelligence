from __future__ import annotations

from hashlib import sha256
import streamlit as st

from schemas.full_text_appraisal import (
    ApplicabilityAssessment,
    ApplicabilityJudgement,
    EffectEstimate,
    EndpointRecord,
    FullTextAppraisalCandidate,
    FullTextSourceSnapshot,
    PICOField,
    RiskOfBiasAssessment,
    RiskOfBiasJudgement,
    StructuredPICO,
)
from services.full_text_appraisal import appraise_full_text


st.set_page_config(page_title="Full-Text Evidence Appraisal", layout="wide")
st.title("Full-Text Evidence Appraisal v1.0.0")
st.caption("Deterministic verification of a human-authored PICO, endpoint, effect-size, risk-of-bias, and applicability appraisal against a frozen full-text snapshot.")
st.warning("Research prototype only. A verified appraisal does not constitute a patient-specific treatment recommendation.")

TEXT = (
    "Adults with relapsed acute myeloid leukemia were randomized to regimen A or regimen B. "
    "The primary endpoint was overall survival. Median overall survival was 9.0 months with regimen A "
    "and 6.0 months with regimen B, hazard ratio 0.70, 95% CI 0.55-0.89."
)

scenario = st.selectbox(
    "Validation scenario",
    [
        "Fully verified exact appraisal",
        "Rejected hash mismatch",
        "Rejected non-exact PICO excerpt",
        "Partially verified risk-of-bias review missing",
        "Partially verified applicability unclear",
    ],
)

source = FullTextSourceSnapshot(
    pmid="12345678",
    title="Synthetic randomized AML study",
    full_text=TEXT,
    full_text_sha256=sha256(TEXT.encode("utf-8")).hexdigest(),
    source_type="synthetic_fixture",
    source_verified=True,
)

candidate = FullTextAppraisalCandidate(
    appraisal_id="APP-001",
    pmid="12345678",
    study_design="randomized controlled trial",
    pico=StructuredPICO(
        population=PICOField(value="Adults with relapsed AML", source_excerpt="Adults with relapsed acute myeloid leukemia"),
        intervention=PICOField(value="regimen A", source_excerpt="regimen A"),
        comparator=PICOField(value="regimen B", source_excerpt="regimen B"),
        outcome=PICOField(value="overall survival", source_excerpt="The primary endpoint was overall survival"),
    ),
    endpoints=[EndpointRecord(name="overall survival", endpoint_type="primary", source_excerpt="The primary endpoint was overall survival")],
    effect_estimates=[EffectEstimate(
        endpoint_name="overall survival",
        effect_measure="hazard ratio",
        effect_value="0.70",
        confidence_interval="95% CI 0.55-0.89",
        source_excerpt="Median overall survival was 9.0 months with regimen A and 6.0 months with regimen B, hazard ratio 0.70, 95% CI 0.55-0.89",
    )],
    risk_of_bias=RiskOfBiasAssessment(
        randomization=RiskOfBiasJudgement.LOW,
        deviations_from_intervention=RiskOfBiasJudgement.LOW,
        missing_outcome_data=RiskOfBiasJudgement.LOW,
        outcome_measurement=RiskOfBiasJudgement.LOW,
        selective_reporting=RiskOfBiasJudgement.LOW,
        overall=RiskOfBiasJudgement.LOW,
        reviewer_rationale="Synthetic low-risk fixture.",
        human_verified=True,
    ),
    applicability=ApplicabilityAssessment(
        judgement=ApplicabilityJudgement.HIGH,
        disease_match="exact",
        disease_state_match="relapsed",
        population_match="adult",
        treatment_context_match="salvage",
        reviewer_rationale="Synthetic high-applicability fixture.",
        human_verified=True,
    ),
    linked_claim_ids=["CLM-001"],
    human_verified=True,
)

if scenario == "Rejected hash mismatch":
    source.full_text_sha256 = "0" * 64
elif scenario == "Rejected non-exact PICO excerpt":
    candidate.pico.population.source_excerpt = "Adults with relapsed AML"
elif scenario == "Partially verified risk-of-bias review missing":
    candidate.risk_of_bias.human_verified = False
elif scenario == "Partially verified applicability unclear":
    candidate.applicability.judgement = ApplicabilityJudgement.UNCLEAR

if st.button("Run Full-Text Appraisal", type="primary"):
    report = appraise_full_text(source, candidate)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Status", report.status.value.upper())
    c2.metric("PICO verified", "YES" if report.pico_verified else "NO")
    c3.metric("Effect estimates", report.effect_estimates_verified)
    c4.metric("Can influence synthesis", "YES" if report.can_influence_synthesis else "NO")

    st.subheader("Gate results")
    st.write(report.summary)
    st.write(f"Risk of bias verified: {'YES' if report.risk_of_bias_verified else 'NO'}")
    st.write(f"Applicability verified: {'YES' if report.applicability_verified else 'NO'}")
    st.write(f"Full-text-promoted claim IDs: {', '.join(report.linked_claims_verified_for_full_text) or 'None'}")

    if report.findings:
        st.subheader("Findings")
        st.dataframe([f.model_dump() for f in report.findings], use_container_width=True)

    with st.expander("Frozen full-text snapshot"):
        st.code(source.full_text)
        st.code(source.full_text_sha256)

    with st.expander("Typed appraisal report"):
        st.json(report.model_dump(mode="json"))

st.divider()
st.markdown("**Core invariant:** full-text appraisal is a verification layer, not an autonomous critical-appraisal oracle. PICO, risk-of-bias, applicability, and clinical interpretation remain explicit reviewed assertions with exact source traceability.")
