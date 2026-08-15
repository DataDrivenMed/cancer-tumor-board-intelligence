from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from schemas.evidence_gateway import (
    EvidenceIngestionPackage,
    EvidenceRecommendationRecord,
    EvidenceSourceManifest,
)
from schemas.guideline import GuidanceSourceType
from services.evidence_gateway import normalized_sha256, verify_evidence_package


st.set_page_config(page_title="Evidence Gateway", page_icon="🔐", layout="wide")
st.title("Evidence Gateway / Source Ingestion")
st.caption("Deterministic evidence trust boundary before specialist-agent use.")
st.warning("Development validation only. Synthetic fixtures below are not clinical evidence or recommendations.")

SOURCE_TEXT = "Synthetic authorized source. Exact AML statement appears here."


def manifest(**overrides) -> EvidenceSourceManifest:
    data = dict(
        source_id="DEMO-SRC-001",
        title="Synthetic Evidence Gateway Validation Source",
        organization="Synthetic Validation Authority",
        source_type=GuidanceSourceType.FORMAL_GUIDELINE,
        jurisdiction="TEST",
        url="https://example.org/synthetic-guidance",
        version="1.0",
        accessed_date=date(2026, 8, 15),
        license_status="institution_authorized",
        expected_content_sha256=normalized_sha256(SOURCE_TEXT),
        human_verified=True,
        verification_note="Synthetic validation fixture only.",
    )
    data.update(overrides)
    return EvidenceSourceManifest(**data)


def recommendation(**overrides) -> EvidenceRecommendationRecord:
    data = dict(
        recommendation_id="DEMO-REC-001",
        source_id="DEMO-SRC-001",
        disease_terms=["acute myeloid leukemia"],
        disease_states=["relapsed"],
        question_domains=["treatment_management"],
        recommendation_text="Synthetic recommendation for software validation only.",
        source_excerpt="Exact AML statement appears here.",
        source_locator="synthetic:section-1",
        human_verified=True,
    )
    data.update(overrides)
    return EvidenceRecommendationRecord(**data)


def package_for(name: str) -> EvidenceIngestionPackage:
    if name == "Accepted verified package":
        return EvidenceIngestionPackage(
            manifest=manifest(),
            source_text=SOURCE_TEXT,
            recommendations=[recommendation()],
        )
    if name == "Rejected hash mismatch":
        return EvidenceIngestionPackage(
            manifest=manifest(expected_content_sha256="0" * 64),
            source_text=SOURCE_TEXT,
            recommendations=[recommendation()],
        )
    if name == "Accepted source, rejected non-exact excerpt":
        return EvidenceIngestionPackage(
            manifest=manifest(),
            source_text=SOURCE_TEXT,
            recommendations=[recommendation(source_excerpt="Paraphrased AML statement")],
        )
    return EvidenceIngestionPackage(
        manifest=manifest(source_type=GuidanceSourceType.SYNTHETIC_FIXTURE, license_status="synthetic"),
        source_text=SOURCE_TEXT,
        recommendations=[recommendation()],
    )


scenario = st.selectbox(
    "Validation scenario",
    [
        "Accepted verified package",
        "Rejected hash mismatch",
        "Accepted source, rejected non-exact excerpt",
        "Synthetic source blocked in production",
    ],
)
production_mode = st.toggle("Production mode", value=True)
package = package_for(scenario)

left, right = st.columns([1, 1])
with left:
    st.markdown("### Source manifest")
    st.write(f"**Source ID:** {package.manifest.source_id}")
    st.write(f"**Type:** {package.manifest.source_type.value}")
    st.write(f"**License status:** {package.manifest.license_status}")
    st.write(f"**Human verified:** {package.manifest.human_verified}")
    st.code(package.manifest.expected_content_sha256, language=None)

if st.button("Run Evidence Gateway", type="primary"):
    result, store = verify_evidence_package(package, production_mode=production_mode)
    st.session_state["evidence_gateway_result"] = result
    st.session_state["evidence_gateway_store"] = store

result = st.session_state.get("evidence_gateway_result")
store = st.session_state.get("evidence_gateway_store")
if result is not None:
    with right:
        st.markdown("### Verification result")
        c1, c2, c3 = st.columns(3)
        c1.metric("Status", result.status.value.replace("_", " ").title())
        c2.metric("Accepted recommendations", len(result.accepted_recommendation_ids))
        c3.metric("Rejected recommendations", len(result.rejected_recommendation_ids))

        if result.status.value == "accepted":
            st.success("Package accepted into the verified evidence boundary.")
        elif result.status.value == "accepted_with_limitations":
            st.warning("Source verified, but one or more recommendation records were rejected.")
        else:
            st.error("Package rejected. No source content propagates into the Guideline Agent store.")

        st.write(f"**Can enter guideline store:** {result.can_enter_guideline_store}")
        st.code(result.content_sha256, language=None)

    if result.findings:
        st.markdown("### Findings")
        for finding in result.findings:
            if finding.severity == "error":
                st.error(f"{finding.code.value}: {finding.message}")
            else:
                st.warning(f"{finding.code.value}: {finding.message}")

    st.markdown("### Propagated evidence-store objects")
    st.write(f"Sources: {len(store.sources) if store is not None else 0}")
    st.write(f"Recommendations: {len(store.recommendations) if store is not None else 0}")

    with st.expander("Typed EvidenceIngestionResult"):
        st.json(result.model_dump(mode="json"))

st.divider()
st.info(
    "NCI PDQ should be classified as an authoritative evidence summary, not a formal guideline. "
    "The gateway does not infer this classification automatically; source governance must declare and verify it."
)
st.caption("No verified source -> no evidence claim. Exact source excerpt and frozen SHA-256 are mandatory for admitted recommendation records.")
