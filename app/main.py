from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from schemas.case import CancerTumorBoardCase
from orchestration.workflow import run_workflow
from services.document_parser import extract_text_from_upload


st.set_page_config(
    page_title="Cancer Tumor Board Intelligence",
    page_icon="🧬",
    layout="wide",
)

st.title("Cancer Tumor Board Intelligence")
st.caption("Research prototype • Synthetic/de-identified cases only • No clinical recommendations in this build")
st.warning("Development environment only. Do not enter or upload protected health information (PHI).")

tabs = st.tabs(["Case", "Data Quality", "Routing & Agents", "Tumor Board Brief", "Audit"])

if "result" not in st.session_state:
    st.session_state.result = None

with tabs[0]:
    st.subheader("Case input")
    mode = st.radio(
        "Input method",
        ["Load synthetic example", "Paste canonical JSON", "Upload PDF/DOCX for text preview"],
        horizontal=True,
    )

    case = None

    if mode == "Load synthetic example":
        sample_path = PROJECT_ROOT / "synthetic_cases" / "syn_aml_001.json"
        sample_data = json.loads(sample_path.read_text(encoding="utf-8"))
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Disease", "AML")
        col2.metric("Disease state", "Relapsed")
        col3.metric("Molecular", "FLT3-ITD")
        col4.metric("ECOG", "1")
        with st.expander("View canonical synthetic case"):
            st.code(json.dumps(sample_data, indent=2), language="json")
        if st.button("Run development workflow", type="primary"):
            case = CancerTumorBoardCase.model_validate(sample_data)

    elif mode == "Paste canonical JSON":
        raw = st.text_area("Paste case JSON", height=350)
        if st.button("Validate and analyze", type="primary"):
            try:
                case = CancerTumorBoardCase.model_validate_json(raw)
            except Exception as exc:
                st.error(f"Validation failed: {exc}")

    else:
        uploaded = st.file_uploader("Upload synthetic/de-identified PDF or DOCX", type=["pdf", "docx", "txt", "md"])
        if uploaded:
            try:
                extracted = extract_text_from_upload(uploaded.name, uploaded.getvalue())
                st.text_area("Extracted text preview", value=extracted, height=350)
                st.info(
                    "Document parsing is active. Automatic clinical extraction is intentionally disabled until the provenance-aware extraction agent is validated."
                )
            except Exception as exc:
                st.error(f"Could not parse file: {exc}")

    if case is not None:
        st.session_state.result = run_workflow(case)
        st.success("Workflow completed. Review the remaining tabs.")

result = st.session_state.result

with tabs[1]:
    st.subheader("Data quality")
    if not result:
        st.info("Run a case first.")
    else:
        c = result["case"]
        left, right = st.columns(2)
        with left:
            st.markdown("#### Conflicts")
            if c.conflicts:
                for item in c.conflicts:
                    st.warning(f"{item.severity.upper()}: {item.field} • {item.value_a} vs {item.value_b}")
            else:
                st.success("No stored conflicts.")
        with right:
            st.markdown("#### Missing decision-relevant information")
            if c.missing_items:
                for item in c.missing_items:
                    st.warning(f"{item.importance.upper()}: {item.field} • {item.reason}")
            else:
                st.success("No missing items detected by current structural checks.")
        st.markdown("#### Canonical case")
        st.json(c.model_dump(mode="json"))

with tabs[2]:
    st.subheader("Routing & agent analysis")
    if not result:
        st.info("Run a case first.")
    else:
        routing = result["routing"]
        if routing:
            c1, c2 = st.columns(2)
            c1.metric("Question class", routing.question_type.replace("_", " ").title())
            c2.metric("Complexity", routing.complexity.replace("_", " ").title())
            st.markdown("**Agents selected:** " + " · ".join(a.replace("_", " ").title() for a in routing.selected_agents))
            st.markdown("**Routing rationale:**")
            for r in routing.rationale:
                st.write(f"• {r}")

        st.markdown("### Specialist outputs")
        for agent_id, output in result["specialist_outputs"].items():
            with st.expander(agent_id.replace("_", " ").title(), expanded=False):
                st.write(output.summary)
                for warning in output.warnings:
                    st.warning(warning)
                if output.findings:
                    st.json(output.findings)

with tabs[3]:
    st.subheader("Tumor Board Brief")
    if not result:
        st.info("Run a case first.")
    else:
        final = result["final_decision"]
        st.markdown(f"### Decision state: `{final.decision_state.upper()}`")
        st.markdown(f"**Decision-support strength:** {final.decision_support_strength.upper()}")
        if final.abstention_reason:
            st.error(final.abstention_reason)
        if final.major_uncertainties:
            st.markdown("#### Major uncertainties")
            for u in final.major_uncertainties:
                st.write(f"• {u}")
        st.markdown("#### Board discussion priorities")
        for p in final.discussion_priorities:
            st.write(f"• {p}")
        st.markdown("#### Red-team findings")
        for f in result["red_team_findings"]:
            st.warning(f"{f.severity.upper()} • {f.category}: {f.issue}")
        st.caption("The development build intentionally abstains until validated evidence connectors and model contracts are active.")

with tabs[4]:
    st.subheader("Audit")
    if not result:
        st.info("Run a case first.")
    else:
        st.dataframe(result["audit_events"], use_container_width=True, hide_index=True)
