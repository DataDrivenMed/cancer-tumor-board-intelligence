from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.case_integrity import AGENT_VERSION, run_case_integrity
from schemas.case import CancerTumorBoardCase, ClinicalQuestion, Fact, Provenance


st.set_page_config(page_title="Case Integrity / Data QA", page_icon="🛡️", layout="wide")
st.title("Case Integrity / Data QA Agent")
st.caption(
    "Deterministic pre-routing gate over the canonical case. No external retrieval, no treatment recommendation, no hidden chain-of-thought."
)
st.warning("Development environment only. Synthetic or fully de-identified data only. Do not enter PHI.")

st.markdown(
    """
This agent sits **after structured extraction and before specialist-agent routing**. It never changes patient facts. It checks whether the canonical representation is internally coherent and sufficiently trustworthy to propagate downstream.

**Hard rule:** a BLOCK disposition prevents specialist routing. PASS WITH WARNINGS may route, but requires human review.
"""
)


def _demo_case() -> CancerTumorBoardCase:
    def f(field: str, value: str) -> Fact:
        return Fact(
            field=field,
            value=value,
            provenance=[Provenance(
                document_id="SYN-QA-DOC",
                document_type="synthetic",
                source_excerpt=value,
                source_segment_ids=["S0001"],
                source_verified=True,
            )],
        )

    return CancerTumorBoardCase(
        case_id="SYN-QA-PASS-001",
        diagnosis=f("diagnosis", "acute myeloid leukemia"),
        disease_state=f("disease_state", "newly diagnosed"),
        performance_status=f("ECOG", "1"),
        clinical_question=ClinicalQuestion(
            question_type="management",
            question="Synthetic QA demonstration only.",
        ),
    )


source = st.radio(
    "Case source",
    ["Current reviewed case", "Built-in clean synthetic case", "Paste canonical case JSON"],
    horizontal=True,
)

case = None
if source == "Current reviewed case":
    case = st.session_state.get("reviewed_case")
    if case is None:
        st.info("No reviewed case is present in this Streamlit session. Use the built-in clean synthetic case or paste canonical JSON.")
elif source == "Built-in clean synthetic case":
    case = _demo_case()
else:
    raw = st.text_area(
        "Canonical CancerTumorBoardCase JSON",
        height=360,
        placeholder="Paste synthetic or fully de-identified canonical case JSON here.",
    )
    if raw.strip():
        try:
            case = CancerTumorBoardCase.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError) as exc:
            st.error(f"Canonical case validation failed safely: {exc}")

if case is not None:
    st.markdown(f"**Agent version:** `{AGENT_VERSION}`")
    if st.button("Run Case Integrity / Data QA", type="primary"):
        report = run_case_integrity(case)
        st.session_state["case_integrity_report"] = report

report = st.session_state.get("case_integrity_report")
if report is not None:
    st.divider()
    if report.disposition.value == "pass":
        st.success("PASS: canonical case cleared the deterministic integrity gate.")
    elif report.disposition.value == "pass_with_warnings":
        st.warning("PASS WITH WARNINGS: routing may continue, but human review is required.")
    else:
        st.error("BLOCK: specialist-agent routing must not continue until blocking findings are resolved.")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Checks", f"{report.checks_passed}/{report.checks_run}")
    c2.metric("Critical", report.critical_count)
    c3.metric("Major", report.major_count)
    c4.metric("Warnings", report.warning_count)
    c5.metric("Blocking", report.recommendation_blocking_count)

    st.write(f"**Safe to route to specialists:** {'YES' if report.safe_to_route_to_specialists else 'NO'}")
    st.write(f"**Human review required:** {'YES' if report.requires_human_review else 'NO'}")

    st.markdown("### Findings")
    if not report.findings:
        st.success("No integrity findings.")
    else:
        rows = [
            {
                "severity": f.severity.value,
                "code": f.code,
                "category": f.category,
                "field": f.field_path,
                "blocking": f.recommendation_blocking,
                "message": f.message,
                "source_segments": ", ".join(f.source_segment_ids),
            }
            for f in report.findings
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)

    with st.expander("Check-by-check audit"):
        for check in report.check_results:
            st.write(f"{'PASS' if check.passed else 'FINDING'} • {check.check_id} • v{check.check_version}")

    with st.expander("Typed report JSON"):
        st.json(report.model_dump(mode="json"))

    with st.expander("Canonical case inspected"):
        st.json(case.model_dump(mode="json"))
