from __future__ import annotations

import sys
from hashlib import sha256
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from schemas.evidence_verifier import (
    EvidenceClaimCandidate,
    EvidenceClaimType,
    EvidenceDirection,
    EvidenceSourceSnapshot,
)
from services.evidence_verifier import verify_evidence_claims


st.set_page_config(page_title="Evidence Verifier", page_icon="✅", layout="wide")
st.title("Evidence Verifier v1.0.0")
st.caption("Deterministic claim-level provenance and completeness gate for candidate literature evidence.")
st.warning(
    "Development validation only. The built-in records are synthetic. Exact source-span verification does not establish clinical truth or patient-specific appropriateness."
)

ABSTRACT = (
    "In this synthetic randomized trial, 120 adults with relapsed AML were assigned to Treatment A or Treatment B. "
    "The primary endpoint was complete remission. Complete remission occurred in 48% with Treatment A and 31% with Treatment B."
)
ABSTRACT_HASH = sha256(ABSTRACT.encode("utf-8")).hexdigest()


def make_source() -> EvidenceSourceSnapshot:
    return EvidenceSourceSnapshot(
        pmid="99900001",
        title="Synthetic randomized AML trial",
        abstract_text=ABSTRACT,
        abstract_sha256=ABSTRACT_HASH,
        source_verified=True,
        publication_types=["Randomized Controlled Trial"],
    )


def make_candidate(scenario: str) -> EvidenceClaimCandidate:
    kwargs = dict(
        claim_id="CLAIM-001",
        claim_text="Treatment A was associated with a higher complete-remission proportion than Treatment B in the reported study population.",
        claim_type=EvidenceClaimType.EFFICACY,
        pmid="99900001",
        abstract_sha256=ABSTRACT_HASH,
        source_excerpt="Complete remission occurred in 48% with Treatment A and 31% with Treatment B.",
        study_design="randomized trial",
        population="120 adults with relapsed AML",
        intervention="Treatment A",
        comparator="Treatment B",
        endpoints=["complete remission"],
        numeric_results=["48% vs 31%"],
        applicability="Relevant to a relapsed AML treatment question in this synthetic validation fixture.",
        direction=EvidenceDirection.SUPPORTS,
        human_verified=True,
    )

    if scenario == "Rejected non-exact source excerpt":
        kwargs["source_excerpt"] = "Complete remission was 48 percent versus 31 percent."
    elif scenario == "Unverified human review missing":
        kwargs["human_verified"] = False
    elif scenario == "Partially verified missing quantitative result":
        kwargs["numeric_results"] = []
    elif scenario == "Conflicting evidence preserved":
        kwargs["direction"] = EvidenceDirection.CONTRADICTS

    return EvidenceClaimCandidate(**kwargs)


scenario = st.selectbox(
    "Synthetic verification scenario",
    [
        "Fully verified exact claim",
        "Rejected non-exact source excerpt",
        "Unverified human review missing",
        "Partially verified missing quantitative result",
        "Conflicting evidence preserved",
    ],
)

source = make_source()
candidate = make_candidate(scenario)

left, right = st.columns([1, 1])
with left:
    st.markdown("### Frozen source snapshot")
    st.write(f"**PMID:** {source.pmid}")
    st.write(f"**Title:** {source.title}")
    st.write(f"**Abstract SHA-256:** `{source.abstract_sha256}`")
    st.text_area("Synthetic abstract", source.abstract_text, height=160, disabled=True)

with right:
    st.markdown("### Candidate claim")
    st.write(f"**Claim:** {candidate.claim_text}")
    st.write(f"**Direction:** {candidate.direction.value}")
    st.write(f"**Human verified:** {'YES' if candidate.human_verified else 'NO'}")
    st.write(f"**Study design:** {candidate.study_design or 'Missing'}")
    st.write(f"**Population:** {candidate.population or 'Missing'}")
    st.write(f"**Endpoints:** {', '.join(candidate.endpoints) or 'Missing'}")
    st.write(f"**Numeric results:** {', '.join(candidate.numeric_results) or 'Missing'}")
    st.code(candidate.source_excerpt)

if st.button("Run Evidence Verifier", type="primary"):
    st.session_state["evidence_verifier_report"] = verify_evidence_claims([candidate], [source])

report = st.session_state.get("evidence_verifier_report")
if report is not None:
    st.divider()
    st.markdown("### Verification result")
    claim = report.claims[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Claim status", claim.status.value.replace("_", " ").title())
    c2.metric("Verified", report.verified_count)
    c3.metric("Rejected", report.rejected_count)
    c4.metric("Can influence synthesis", "YES" if claim.can_influence_synthesis else "NO")

    if claim.status.value == "verified":
        st.success("Exact provenance, source integrity, structured evidence fields, and human attestation passed the v1 gate.")
    elif claim.status.value == "rejected":
        st.error("The claim failed a hard source/provenance verification requirement and cannot propagate.")
    elif claim.status.value == "unverified":
        st.error("The claim is not verified and cannot propagate as evidence.")
    elif claim.status.value == "conflicting":
        st.warning("Contradictory evidence is preserved explicitly for downstream synthesis; it is not silently resolved.")
    else:
        st.warning("The claim is only partially verified. Limitations must remain attached downstream.")

    for finding in claim.findings:
        if finding.severity == "error":
            st.error(f"{finding.code.value}: {finding.message}")
        else:
            st.warning(f"{finding.code.value}: {finding.message}")

    st.markdown("### Safety boundary")
    st.write(
        "Evidence Verifier v1 checks exact source provenance, frozen-source integrity, required structured study fields, human attestation, and explicit contradiction state. "
        "It does not infer causality, replace full-text critical appraisal, or convert one study into a treatment recommendation."
    )

    with st.expander("Typed EvidenceVerifierReport"):
        st.json(report.model_dump(mode="json"))
