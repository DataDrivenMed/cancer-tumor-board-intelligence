from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.guideline import GuidelineAgent
from services.evidence_gateway import verify_evidence_package
from services.nci_pdq_aml_adapter import (
    NCI_AML_PDQ_URL,
    attest_nci_aml_pdq_candidate,
    build_nci_aml_pdq_candidate,
    fetch_nci_aml_pdq,
)
from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Fact, Provenance


st.set_page_config(page_title="NCI PDQ AML Adapter", page_icon="📚", layout="wide")
st.title("NCI PDQ AML Authoritative Evidence Adapter")
st.caption("Live public-source ingestion with hashing, exact excerpts, metadata capture, and explicit human attestation.")
st.warning(
    "Development environment only. NCI PDQ is classified here as an authoritative evidence summary, not a formal guideline. "
    "This page does not generate a clinical recommendation."
)

st.markdown(f"**Source:** {NCI_AML_PDQ_URL}")
st.markdown(
    "The adapter fetches the current NCI AML PDQ page, converts visible text deterministically, computes a SHA-256 snapshot, "
    "extracts the published update date, and prepares bounded candidate evidence statements. Nothing is admitted to the Evidence Gateway until you attest that you reviewed it."
)

if st.button("Fetch live NCI AML PDQ", type="primary"):
    try:
        with st.spinner("Fetching and freezing the current NCI page snapshot..."):
            snap = fetch_nci_aml_pdq()
            build = build_nci_aml_pdq_candidate(snap)
        st.session_state["nci_pdq_snapshot"] = snap
        st.session_state["nci_pdq_build"] = build
        st.session_state.pop("nci_pdq_gateway_result", None)
        st.session_state.pop("nci_pdq_guideline_report", None)
    except Exception as exc:
        st.error(f"Fetch failed safely: {exc}")

build = st.session_state.get("nci_pdq_build")
if build is not None:
    manifest = build.package.manifest
    st.markdown("### Frozen source snapshot")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Source type", manifest.source_type.value.replace("_", " ").title())
    c2.metric("Updated", str(manifest.updated_date or "unparsed"))
    c3.metric("Candidates found", len(build.package.recommendations))
    c4.metric("Expected candidates", build.expected_candidate_count)
    st.code(manifest.expected_content_sha256, language=None)

    for warning in build.warnings:
        st.warning(warning)

    st.markdown("### Human source review")
    source_verified = st.checkbox(
        "I reviewed the fetched source identity, NCI origin, update metadata, and authoritative-evidence-summary classification.",
        key="nci_source_verified",
    )

    verified_ids: set[str] = set()
    for record in build.package.recommendations:
        with st.expander(f"{record.recommendation_id} · {record.source_locator}"):
            st.write(record.source_excerpt)
            st.caption(
                "This exact text exists in the frozen source snapshot. It is evidence-summary content, not a formal guideline recommendation."
            )
            if st.checkbox(
                "I verified this exact excerpt and locator against the fetched NCI source.",
                key=f"verify_{record.recommendation_id}",
            ):
                verified_ids.add(record.recommendation_id)

    if st.button("Attest and run Evidence Gateway"):
        package = attest_nci_aml_pdq_candidate(
            build,
            source_human_verified=source_verified,
            verified_recommendation_ids=verified_ids,
            verification_note="Reviewer attestation completed in NCI PDQ AML Adapter page.",
        )
        result, store = verify_evidence_package(package, production_mode=True)
        st.session_state["nci_pdq_gateway_result"] = result
        st.session_state["nci_pdq_store"] = store

    result = st.session_state.get("nci_pdq_gateway_result")
    if result is not None:
        st.markdown("### Evidence Gateway result")
        a, b, c = st.columns(3)
        a.metric("Status", result.status.value.replace("_", " ").title())
        b.metric("Accepted statements", len(result.accepted_recommendation_ids))
        c.metric("Rejected statements", len(result.rejected_recommendation_ids))
        if result.can_enter_guideline_store:
            st.success("Verified source snapshot may enter the bounded evidence store.")
        else:
            st.error("Source snapshot is blocked from the evidence store.")
        for finding in result.findings:
            (st.error if finding.severity == "error" else st.warning)(f"{finding.code.value}: {finding.message}")

        if result.can_enter_guideline_store and result.accepted_recommendation_ids:
            st.markdown("### Boundary check through Guideline Agent")
            prov = Provenance(
                document_id="NCI-PDQ-ADAPTER-DEMO",
                source_excerpt="acute myeloid leukemia",
                source_segment_ids=["S0001"],
                source_verified=True,
            )
            demo_case = CancerTumorBoardCase(
                case_id="NCI-PDQ-AML-DEMO",
                diagnosis=Fact(field="diagnosis", value="acute myeloid leukemia", provenance=[prov]),
                disease_state=Fact(field="disease_state", value="recurrent", provenance=[prov]),
                performance_status=Fact(field="ECOG", value="1", provenance=[prov]),
                clinical_question=ClinicalQuestion(
                    question_type="management",
                    question="What treatment approaches should be discussed for recurrent AML?",
                ),
            )
            report = GuidelineAgent(st.session_state["nci_pdq_store"]).run(demo_case)
            st.session_state["nci_pdq_guideline_report"] = report
            x, y, z = st.columns(3)
            x.metric("Guideline Agent status", report.status.replace("_", " ").title())
            y.metric("Evidence matches", len(report.matched_guidance))
            z.metric("Formal guideline matches", report.formal_guideline_matches)
            if report.can_support_guideline_claim:
                st.error("Unexpected boundary violation: PDQ must not support a formal guideline claim.")
            else:
                st.success("Boundary preserved: NCI PDQ evidence can inform the evidence layer but cannot masquerade as a formal guideline.")

        with st.expander("Evidence Gateway result JSON"):
            st.json(result.model_dump(mode="json"))

st.divider()
st.caption(
    "The adapter never auto-attests evidence. A live source change causes exact candidate statements to fail closed until reviewed. "
    "No patient data are transmitted to NCI by this page."
)
