from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.extraction_v25 import extract_case_v25
from app.ui import apply_design_system, badge
from orchestration.workflow import run_workflow
from schemas.case import CancerTumorBoardCase
from services.document_parser import parse_text, parse_upload
from services.model_gateway import ModelGatewayError

st.set_page_config(
    page_title="Mission Control | Tumor Board Intelligence",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_design_system()

st.markdown(
    """
<style>
[data-testid="stSidebar"] {display:none;}
[data-testid="collapsedControl"] {display:none;}
.block-container {max-width: 1540px; padding: 1.1rem 1.2rem 3rem 1.2rem;}
.mc-topbar {display:flex; justify-content:space-between; align-items:center; padding:4px 2px 14px 2px; border-bottom:1px solid rgba(38,37,30,.12); margin-bottom:10px;}
.mc-brand {font-weight:650; letter-spacing:-.02em; font-size:1.0rem;}
.mc-sub {color:#6b6b6b; font-size:.75rem;}
.mc-column {min-height:78vh; padding:8px 14px 18px 14px;}
.mc-border {border-right:1px solid rgba(38,37,30,.12);}
.mc-label {font-size:.69rem; text-transform:uppercase; letter-spacing:.10em; color:#8a877e; font-weight:700; margin:12px 0 8px 0;}
.mc-title {font-size:1.02rem; font-weight:650; letter-spacing:-.02em; margin-bottom:4px;}
.mc-copy {font-size:.80rem; line-height:1.45; color:#77746b;}
.mc-row {display:flex; gap:8px; align-items:flex-start; padding:8px 0; border-bottom:1px solid rgba(38,37,30,.08);}
.mc-dot {width:7px; height:7px; border-radius:50%; background:#b9b7b0; margin-top:6px; flex:0 0 auto;}
.mc-dot.ok {background:#1f8a65;}
.mc-dot.warn {background:#c08532;}
.mc-dot.block {background:#cf2d56;}
.mc-row-title {font-size:.78rem; font-weight:600; color:#26251e;}
.mc-row-copy {font-size:.72rem; color:#77746b; line-height:1.35;}
.mc-card {background:#f2f1ed; border:1px solid rgba(38,37,30,.10); border-radius:5px; padding:12px; margin:8px 0; box-shadow:0 1px 3px rgba(0,0,0,.04);}
.mc-card.white {background:#fff;}
.mc-card.accent {background:rgba(192,133,50,.10); border-color:rgba(192,133,50,.25);}
.mc-big {font-size:1.65rem; line-height:1.05; letter-spacing:-.04em; font-weight:540; margin:2px 0 6px 0;}
.mc-chip {display:inline-flex; margin:2px 4px 2px 0; padding:4px 7px; border:1px solid rgba(38,37,30,.12); border-radius:999px; background:white; font-size:.66rem;}
.mc-section {margin:14px 0 7px 0; font-size:.74rem; font-weight:700; letter-spacing:.03em; color:#26251e;}
.mc-line {height:1px; background:rgba(38,37,30,.10); margin:10px 0;}
.mc-muted {color:#77746b; font-size:.72rem; line-height:1.45;}
.mc-status {display:inline-flex; align-items:center; gap:6px; font-size:.67rem; font-weight:650; padding:4px 7px; border-radius:999px; background:#fff; border:1px solid rgba(38,37,30,.12);}
.mc-mini-window {background:white; border:1px solid rgba(38,37,30,.12); border-radius:5px; padding:10px; min-height:120px;}
.mc-brief-head {padding:2px 0 12px 0; border-bottom:1px solid rgba(38,37,30,.10); margin-bottom:10px;}
.mc-brief-title {font-size:1.28rem; letter-spacing:-.03em; font-weight:560; line-height:1.1;}
@media (max-width: 980px) {.mc-border{border-right:none; border-bottom:1px solid rgba(38,37,30,.12);} .mc-column{min-height:auto;}}
</style>
""",
    unsafe_allow_html=True,
)


def get_secret(name: str, default: str | None = None) -> str | None:
    try:
        return st.secrets[name]
    except Exception:
        return default


def value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def text(v: Any) -> str:
    if v is None:
        return "Not represented"
    if hasattr(v, "value"):
        v = v.value
    return str(v)


def run_case(case: CancerTumorBoardCase, raw_extraction: dict | None = None) -> None:
    st.session_state.reviewed_case = case
    st.session_state.result = run_workflow(case, raw_extraction=raw_extraction)


for key, default in {
    "result": None,
    "extraction_package": None,
    "reviewed_case": None,
    "parsed_document": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

result = st.session_state.result
case = st.session_state.reviewed_case
package = st.session_state.extraction_package

st.markdown(
    '<div class="mc-topbar"><div><div class="mc-brand">Tumor Board Intelligence</div><div class="mc-sub">Clinician Mission Control · Research v1.0</div></div>'
    + '<div>' + badge("36/36 qualified synthetic integration", "ok") + badge("Human review required", "warn") + '</div></div>',
    unsafe_allow_html=True,
)

left, middle, right = st.columns([0.78, 1.02, 1.58], gap="small")

with left:
    st.markdown('<div class="mc-column mc-border">', unsafe_allow_html=True)
    st.markdown('<div class="mc-label">In progress</div>', unsafe_allow_html=True)
    status_title = "No active case"
    status_copy = "Start with the synthetic AML case or add a de-identified narrative."
    status_kind = ""
    if result is not None:
        final = result.get("final_decision")
        status_title = "Analysis complete"
        status_copy = f"Decision state: {text(value(final, 'decision_state', 'unknown')).replace('_',' ')}"
        status_kind = "ok"
    elif package is not None:
        status_title = "Extraction complete"
        status_copy = "Clinician verification is required before downstream analysis."
        status_kind = "warn"
    st.markdown(
        f'<div class="mc-row"><span class="mc-dot {status_kind}"></span><div><div class="mc-row-title">{status_title}</div><div class="mc-row-copy">{status_copy}</div></div></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="mc-label">Mission control</div>', unsafe_allow_html=True)
    workflow = [
        ("Case input", case is not None or package is not None),
        ("Case integrity", bool(result and result.get("case_integrity_report"))),
        ("Evidence channels", bool(result and result.get("specialist_outputs"))),
        ("Clinical Red Team", bool(result and result.get("red_team_report"))),
        ("Consensus", bool(result and result.get("consensus_report"))),
        ("Tumor Board Brief", bool(result and result.get("tumor_board_brief"))),
    ]
    for title, done in workflow:
        dot = "ok" if done else ""
        copy = "Complete" if done else "Waiting"
        st.markdown(f'<div class="mc-row"><span class="mc-dot {dot}"></span><div><div class="mc-row-title">{title}</div><div class="mc-row-copy">{copy}</div></div></div>', unsafe_allow_html=True)

    st.markdown('<div class="mc-label">Questions</div>', unsafe_allow_html=True)
    missing_items = []
    if result and result.get("missing_information_report"):
        missing_items = list(result["missing_information_report"].items or [])
    if missing_items:
        for item in missing_items[:5]:
            block = "block" if item.recommendation_blocking else "warn"
            st.markdown(f'<div class="mc-row"><span class="mc-dot {block}"></span><div><div class="mc-row-title">{item.field}</div><div class="mc-row-copy">{item.reason}</div></div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="mc-muted">No unresolved decision-critical questions are currently surfaced.</div>', unsafe_allow_html=True)

    st.markdown('<div class="mc-label">Quick start</div>', unsafe_allow_html=True)
    if st.button("Run synthetic AML", type="primary", use_container_width=True):
        sample = json.loads((PROJECT_ROOT / "synthetic_cases" / "syn_aml_001.json").read_text(encoding="utf-8"))
        run_case(CancerTumorBoardCase.model_validate(sample))
        st.rerun()

    with st.expander("Add de-identified case"):
        narrative = st.text_area("Case narrative", height=120, placeholder="Paste synthetic or fully de-identified tumor-board text...")
        upload = st.file_uploader("Or upload", type=["pdf", "docx", "txt", "md"], key="mission_upload")
        parsed = None
        if upload:
            try:
                parsed = parse_upload(upload.name, upload.getvalue(), document_id="DOC-UPLOAD")
            except Exception as exc:
                st.error(f"Could not parse file safely: {exc}")
        elif narrative.strip():
            parsed = parse_text(narrative, document_id="DOC-PASTED", filename="pasted_case.txt")

        if parsed is not None:
            model_token = get_secret("MODEL_AUTH_TOKEN") or get_secret("HF_TOKEN")
            model_name = get_secret("MODEL_NAME", "openai/gpt-oss-120b:fireworks-ai") or "openai/gpt-oss-120b:fireworks-ai"
            model_base_url = get_secret("MODEL_BASE_URL")
            if model_base_url:
                os.environ["MODEL_BASE_URL"] = model_base_url
            if not model_token and not model_base_url:
                st.caption("Extraction endpoint is not configured in this deployment.")
            elif st.button("Structure case", use_container_width=True):
                try:
                    with st.spinner("Structuring case and verifying provenance..."):
                        extracted = extract_case_v25(
                            document=parsed,
                            api_key=model_token or "local-no-auth",
                            model=model_name,
                            case_id="EXTRACTED-001",
                        )
                    st.session_state.extraction_package = extracted
                    st.session_state.reviewed_case = extracted.case
                    st.session_state.result = None
                    st.rerun()
                except ModelGatewayError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error(f"Extraction failed safely: {exc}")

    if package is not None and result is None:
        st.markdown('<div class="mc-label">Clinician confirmation</div>', unsafe_allow_html=True)
        st.caption(f"{package.provenance_verified}/{package.provenance_total} provenance anchors verified")
        if package.provenance_failures:
            st.error("Provenance failures remain. Analysis should stay blocked until reviewed.")
        if st.button("Confirm extracted case and analyze", use_container_width=True, type="primary"):
            run_case(package.case, raw_extraction=package.raw_extraction)
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

with middle:
    st.markdown('<div class="mc-column mc-border">', unsafe_allow_html=True)
    st.markdown('<div class="mc-label">Case intelligence</div>', unsafe_allow_html=True)
    if case is None:
        st.markdown('<div class="mc-card"><div class="mc-title">Waiting for a case</div><div class="mc-copy">The structured patient representation will appear here after case input.</div></div>', unsafe_allow_html=True)
    else:
        diagnosis = text(value(case.diagnosis, "value", None))
        disease_state = text(value(case.disease_state, "value", None))
        ecog = text(value(case.performance_status, "value", None)) if case.performance_status else "Not represented"
        st.markdown(f'<div class="mc-card white"><div class="mc-label">Patient snapshot</div><div class="mc-big">{diagnosis}</div><div class="mc-copy">{disease_state} · ECOG {ecog}</div></div>', unsafe_allow_html=True)

        st.markdown('<div class="mc-section">Molecular profile</div>', unsafe_allow_html=True)
        if case.molecular_findings:
            chips = "".join(f'<span class="mc-chip">{m.gene} {m.alteration_type or ""}</span>' for m in case.molecular_findings)
            st.markdown(chips, unsafe_allow_html=True)
        else:
            st.markdown('<div class="mc-muted">No molecular findings represented. This is not equivalent to a negative molecular result.</div>', unsafe_allow_html=True)

        st.markdown('<div class="mc-section">Treatment history</div>', unsafe_allow_html=True)
        if case.treatments:
            for tx in case.treatments[:5]:
                st.markdown(f'<div class="mc-row"><span class="mc-dot ok"></span><div><div class="mc-row-title">{tx.regimen}</div><div class="mc-row-copy">Line {tx.line_of_therapy or "?"} · {tx.best_response or "response not represented"}</div></div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="mc-muted">No treatment episodes represented.</div>', unsafe_allow_html=True)

        st.markdown('<div class="mc-section">Clinical question</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="mc-card accent"><div class="mc-copy">{case.clinical_question.question}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="mc-label">Evidence channels</div>', unsafe_allow_html=True)
    if result and result.get("routing"):
        routing = result["routing"]
        for agent in routing.selected_agents:
            output = result.get("specialist_outputs", {}).get(agent)
            status = text(value(output, "status", "waiting")).replace("_", " ") if output is not None else "waiting"
            dot = "ok" if status in {"completed", "completed with limitations", "no evidence found", "source unavailable"} else "warn"
            st.markdown(f'<div class="mc-row"><span class="mc-dot {dot}"></span><div><div class="mc-row-title">{agent.replace("_", " ").title()}</div><div class="mc-row-copy">{status}</div></div></div>', unsafe_allow_html=True)
    else:
        for agent in ["Guidelines", "Literature", "Molecular", "Translational", "Clinical trials", "Safety"]:
            st.markdown(f'<div class="mc-row"><span class="mc-dot"></span><div><div class="mc-row-title">{agent}</div><div class="mc-row-copy">Waiting</div></div></div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="mc-column">', unsafe_allow_html=True)
    st.markdown('<div class="mc-label">Tumor Board Brief</div>', unsafe_allow_html=True)
    if result is None:
        st.markdown('<div class="mc-card white"><div class="mc-brief-head"><div class="mc-brief-title">Decision-support brief</div><div class="mc-copy">Run or structure a case to populate the board-ready output.</div></div><div class="mc-muted">The brief will show the management discussion, decision-critical gaps, evidence, molecular interpretation, possible trials, safety constraints, Red Team findings, uncertainty, and source traceability.</div></div>', unsafe_allow_html=True)
    else:
        brief = result.get("tumor_board_brief")
        final = result.get("final_decision")
        decision = text(value(final, "decision_state", "unknown")).replace("_", " ").upper()
        strength = text(value(final, "decision_support_strength", "unknown")).upper()
        st.markdown(f'<div class="mc-brief-head"><div class="mc-status">{decision}</div><div class="mc-big">Tumor Board Intelligence Brief</div><div class="mc-copy">Decision-support strength: {strength}</div></div>', unsafe_allow_html=True)

        if brief is None:
            reason = text(value(final, "abstention_reason", "The workflow stopped before a structured brief could be produced."))
            st.error(reason)
        else:
            warnings = list(value(brief, "critical_warnings", []) or [])
            for warning in warnings:
                st.error(warning)
            sections = {value(s, "section_id", ""): s for s in list(value(brief, "sections", []) or [])}
            ordered = [
                "patient_snapshot",
                "clinical_question",
                "decision_critical_information",
                "management_strategy",
                "guideline_analysis",
                "molecular_translational",
                "clinical_trials",
                "safety",
                "red_team",
                "uncertainty",
                "what_changes_recommendation",
            ]
            for sid in ordered:
                section = sections.get(sid)
                if section is None:
                    continue
                title = text(value(section, "title", sid))
                items = list(value(section, "items", []) or [])
                st.markdown(f'<div class="mc-section">{title}</div>', unsafe_allow_html=True)
                note = value(section, "section_note", None)
                if note:
                    st.caption(str(note))
                if not items:
                    st.markdown('<div class="mc-muted">No items represented.</div>', unsafe_allow_html=True)
                for item in items:
                    label = text(value(item, "label", "Item"))
                    item_value = text(value(item, "value", ""))
                    refs = list(value(item, "source_refs", []) or [])
                    ref_text = f'<div class="mc-row-copy">Source: {" · ".join(str(r) for r in refs)}</div>' if refs else ''
                    st.markdown(f'<div class="mc-card white"><div class="mc-row-title">{label}</div><div class="mc-copy">{item_value}</div>{ref_text}</div>', unsafe_allow_html=True)

        red = result.get("red_team_report")
        consensus = result.get("consensus_report")
        st.markdown('<div class="mc-label">Control layer</div>', unsafe_allow_html=True)
        if red:
            disposition = text(red.disposition).upper()
            dot = "block" if disposition == "BLOCKED" else "warn" if disposition == "CHALLENGED" else "ok"
            st.markdown(f'<div class="mc-row"><span class="mc-dot {dot}"></span><div><div class="mc-row-title">Clinical Red Team</div><div class="mc-row-copy">{disposition} · {red.blocking_count} blocking finding(s)</div></div></div>', unsafe_allow_html=True)
        if consensus:
            st.markdown(f'<div class="mc-row"><span class="mc-dot ok"></span><div><div class="mc-row-title">Consensus</div><div class="mc-row-copy">{consensus.decision_state.replace("_", " ").upper()}</div></div></div>', unsafe_allow_html=True)

    st.markdown('<div class="mc-line"></div><div class="mc-muted">Research prototype · Synthetic/de-identified data only · Human multidisciplinary review remains required.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
