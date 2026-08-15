from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.missing_information import AGENT_VERSION, run_missing_information
from schemas.case import CancerTumorBoardCase


st.set_page_config(page_title="Missing Information Agent", page_icon="🔎", layout="wide")

st.title("Missing Information Agent")
st.caption(
    "Deterministic pre-routing analysis of unresolved patient information. "
    "Synthetic/de-identified development data only."
)
st.warning("Development environment only. Do not enter or upload protected health information (PHI).")

st.markdown(
    """
This agent does not infer missing patient facts. It reads the canonical case, preserves explicit missing-information records,
adds bounded structural gaps, prioritizes them, and blocks specialist routing only when an unresolved item is explicitly
decision-critical under the current rule set.
"""
)

c1, c2, c3 = st.columns(3)
c1.metric("Agent version", AGENT_VERSION)
c2.metric("Model calls", "0")
c3.metric("Behavior", "Deterministic")

mode = st.radio(
    "Case source",
    ["Built-in ready synthetic case", "Built-in blocked synthetic case", "Paste synthetic/de-identified canonical case JSON"],
)

case: CancerTumorBoardCase | None = None

if mode == "Built-in ready synthetic case":
    sample_path = PROJECT_ROOT / "synthetic_cases" / "syn_aml_001.json"
    payload = json.loads(sample_path.read_text(encoding="utf-8"))
    payload["clinical_question"] = {
        "question_type": "diagnostic_review",
        "question": "Confirm the current diagnostic representation.",
        "urgency": "routine_tumor_board",
    }
    case = CancerTumorBoardCase.model_validate(payload)
    st.info("This case is intended to demonstrate a non-blocking Missing Information Agent result.")

elif mode == "Built-in blocked synthetic case":
    sample_path = PROJECT_ROOT / "synthetic_cases" / "syn_aml_001.json"
    payload = json.loads(sample_path.read_text(encoding="utf-8"))
    payload["disease_state"]["value"] = "Relapsed"
    payload["disease_state"]["status"] = "confirmed"
    payload["treatments"] = []
    payload["clinical_question"] = {
        "question_type": "relapsed_refractory_treatment",
        "question": "What treatment strategies should be considered?",
        "urgency": "routine_tumor_board",
    }
    case = CancerTumorBoardCase.model_validate(payload)
    st.info("This case intentionally removes prior treatment history from a relapsed case and should BLOCK routing.")

else:
    raw = st.text_area(
        "Canonical case JSON",
        height=360,
        placeholder="Paste a synthetic or fully de-identified CancerTumorBoardCase JSON object.",
    )
    if raw.strip():
        try:
            case = CancerTumorBoardCase.model_validate(json.loads(raw))
        except Exception as exc:
            st.error(f"Canonical case validation failed safely: {exc}")

if case is not None:
    with st.expander("Inspect canonical case"):
        st.json(case.model_dump(mode="json"))

    if st.button("Run Missing Information Agent", type="primary"):
        report = run_missing_information(case)
        st.session_state["missing_information_report"] = report

report = st.session_state.get("missing_information_report")
if report is not None:
    st.divider()
    if report.disposition.value == "ready":
        st.success("READY: no unresolved information gaps were identified by the current deterministic rule set.")
    elif report.disposition.value == "conditional":
        st.warning("CONDITIONAL: unresolved information exists, but no current item blocks specialist routing.")
    else:
        st.error("BLOCKED: at least one unresolved information item is decision-critical and blocks specialist routing.")

    a, b, c, d, e = st.columns(5)
    a.metric("Items", len(report.items))
    b.metric("Critical", report.critical_count)
    c.metric("High", report.high_count)
    d.metric("Blocking", report.blocking_count)
    e.metric("Safe to route", "YES" if report.safe_to_route_to_specialists else "NO")

    st.write(report.summary)

    if report.items:
        st.markdown("### Prioritized unresolved information")
        for item in report.items:
            label = f"{item.priority.value.upper()} | {item.field} | {item.category}"
            with st.expander(label, expanded=item.recommendation_blocking):
                st.write(f"Reason: {item.reason}")
                st.write(f"Availability: {item.availability}")
                st.write(f"Action: {item.action.value.replace('_', ' ')}")
                st.write(f"Priority score: {item.priority_score}")
                st.write(f"Recommendation blocking: {'Yes' if item.recommendation_blocking else 'No'}")
                st.write(f"Source: {item.source}")
                if item.field_path:
                    st.write(f"Field path: {item.field_path}")
                if item.source_segment_ids:
                    st.write("Source segments: " + ", ".join(item.source_segment_ids))

    with st.expander("Typed agent report"):
        st.json(report.model_dump(mode="json"))

    st.caption(
        "This component identifies information gaps and routing constraints. It does not determine treatment, "
        "establish trial eligibility, or replace clinician review."
    )
