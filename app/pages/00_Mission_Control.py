from __future__ import annotations

import json
import os
import sys
from html import escape
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
    page_title="Tumor Board Intelligence",
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
.block-container {max-width: 1540px; padding: 1rem 1.1rem 3rem 1.1rem;}
.mc-topbar {display:flex; justify-content:space-between; align-items:center; padding:4px 2px 12px 2px; border-bottom:1px solid rgba(38,37,30,.12); margin-bottom:6px;}
.mc-brand {font-weight:650; letter-spacing:-.02em; font-size:1rem;}
.mc-sub {color:#6b6b6b; font-size:.74rem;}
.mc-column {min-height:82vh; padding:8px 14px 18px 14px;}
.mc-border {border-right:1px solid rgba(38,37,30,.12);}
.mc-label {font-size:.68rem; text-transform:uppercase; letter-spacing:.10em; color:#8a877e; font-weight:700; margin:12px 0 7px 0;}
.mc-title {font-size:1rem; font-weight:650; letter-spacing:-.02em; margin-bottom:4px;}
.mc-copy {font-size:.79rem; line-height:1.45; color:#77746b;}
.mc-row {display:flex; gap:8px; align-items:flex-start; padding:7px 0; border-bottom:1px solid rgba(38,37,30,.08);}
.mc-dot {width:7px; height:7px; border-radius:50%; background:#b9b7b0; margin-top:6px; flex:0 0 auto;}
.mc-dot.ok {background:#1f8a65;}.mc-dot.warn {background:#c08532;}.mc-dot.block {background:#cf2d56;}
.mc-row-title {font-size:.77rem; font-weight:600; color:#26251e;}
.mc-row-copy {font-size:.71rem; color:#77746b; line-height:1.35;}
.mc-card {background:#f2f1ed; border:1px solid rgba(38,37,30,.10); border-radius:5px; padding:11px; margin:7px 0; box-shadow:0 1px 3px rgba(0,0,0,.04);}
.mc-card.white {background:#fff;}.mc-card.accent {background:rgba(192,133,50,.10); border-color:rgba(192,133,50,.25);}
.mc-big {font-size:1.6rem; line-height:1.05; letter-spacing:-.04em; font-weight:540; margin:2px 0 6px 0;}
.mc-chip {display:inline-flex; margin:2px 4px 2px 0; padding:4px 7px; border:1px solid rgba(38,37,30,.12); border-radius:999px; background:white; font-size:.65rem;}
.mc-section {margin:13px 0 6px 0; font-size:.73rem; font-weight:700; letter-spacing:.03em; color:#26251e;}
.mc-line {height:1px; background:rgba(38,37,30,.10); margin:10px 0;}
.mc-muted {color:#77746b; font-size:.71rem; line-height:1.45;}
.mc-status {display:inline-flex; align-items:center; gap:6px; font-size:.66rem; font-weight:650; padding:4px 7px; border-radius:999px; background:#fff; border:1px solid rgba(38,37,30,.12);}
.mc-brief-head {padding:2px 0 10px 0; border-bottom:1px solid rgba(38,37,30,.10); margin-bottom:8px;}
.mc-question {background:#fff; border:1px solid rgba(38,37,30,.12); border-radius:5px; padding:10px; margin:7px 0;}
.mc-question-title {font-size:.77rem; font-weight:650; color:#26251e;}
.mc-question-copy {font-size:.70rem; color:#77746b; margin-top:3px; line-height:1.35;}
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


def safe(v: Any) -> str:
    return escape(text(v))


def run_case(case: CancerTumorBoardCase, raw_extraction: dict | None = None) -> None:
    st.session_state.reviewed_case = case
    st.session_state.result = run_workflow(case, raw_extraction=raw_extraction)


def model_config() -> tuple[str | None, str, str | None]:
    token = get_secret("MODEL_AUTH_TOKEN") or get_secret("HF_TOKEN")
    model = get_secret("MODEL_NAME", "openai/gpt-oss-120b:fireworks-ai") or "openai/gpt-oss-120b:fireworks-ai"
    base_url = get_secret("MODEL_BASE_URL")
    if base_url:
        os.environ["MODEL_BASE_URL"] = base_url
    return token, model, base_url


def agent_state(agent_id: str, result: dict | None, package: Any) -> tuple[str, str]:
    if agent_id == "extraction":
        return ("ok", "Complete") if package is not None or st.session_state.reviewed_case is not None else ("", "Waiting")
    if result is None:
        return "", "Waiting"
    mapping = {
        "case_integrity": result.get("case_integrity_report"),
        "missing_information": result.get("missing_information_report"),
        "clinical_router": result.get("routing"),
        "clinical_red_team": result.get("red_team_report"),
        "consensus": result.get("consensus_report"),
    }
    if agent_id in mapping:
        obj = mapping[agent_id]
        if obj is None:
            return "warn", "Stopped before this stage"
        return "ok", text(value(obj, "disposition", "Complete")).replace("_", " ").title()
    output = result.get("specialist_outputs", {}).get(agent_id)
    if output is None:
        routing = result.get("routing")
        if routing and agent_id not in routing.selected_agents:
            return "", "Not selected"
        return "warn", "No output"
    status = text(value(output, "status", "complete")).replace("_", " ")
    kind = "ok" if status in {"completed", "completed with limitations", "no evidence found", "source unavailable"} else "warn"
    return kind, status.title()


for key, default in {
    "result": None,
    "extraction_package": None,
    "reviewed_case": None,
    "parsed_document": None,
    "selected_question_id": None,
    "clarification_history": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

result = st.session_state.result
case = st.session_state.reviewed_case
package = st.session_state.extraction_package

st.markdown(
    '<div class="mc-topbar"><div><div class="mc-brand">Tumor Board Intelligence</div><div class="mc-sub">Clinician workspace · Research v1.0</div></div>'
    + '<div>' + badge("36/36 qualified synthetic integration", "ok") + badge("Human review required", "warn") + '</div></div>',
    unsafe_allow_html=True,
)

left, middle, right = st.columns([0.82, 1.02, 1.56], gap="small")

with left:
    st.markdown('<div class="mc-column mc-border">', unsafe_allow_html=True)
    st.markdown('<div class="mc-label">In progress</div>', unsafe_allow_html=True)
    if result is not None:
        final = result.get("final_decision")
        st.markdown(f'<div class="mc-row"><span class="mc-dot ok"></span><div><div class="mc-row-title">Analysis complete</div><div class="mc-row-copy">Decision state: {safe(value(final, "decision_state", "unknown")).replace("_", " ")}</div></div></div>', unsafe_allow_html=True)
    elif package is not None:
        st.markdown('<div class="mc-row"><span class="mc-dot warn"></span><div><div class="mc-row-title">Extraction complete</div><div class="mc-row-copy">Clinician confirmation is required before analysis.</div></div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="mc-row"><span class="mc-dot"></span><div><div class="mc-row-title">No active case</div><div class="mc-row-copy">Start with the synthetic AML case or add a de-identified narrative.</div></div></div>', unsafe_allow_html=True)

    st.markdown('<div class="mc-label">Agents</div>', unsafe_allow_html=True)
    agents = [
        ("extraction", "Extraction Agent"),
        ("case_integrity", "Case Integrity / Data QA Agent"),
        ("missing_information", "Missing Information Agent"),
        ("clinical_router", "Clinical Router"),
        ("guideline", "Guideline Agent"),
        ("literature", "Literature Agent"),
        ("molecular", "Molecular Interpretation Agent"),
        ("translational", "Translational Biology Agent"),
        ("clinical_trials", "Clinical Trials Agent"),
        ("safety", "Safety Agent"),
        ("clinical_red_team", "Clinical Red Team"),
        ("consensus", "Consensus Engine"),
    ]
    for agent_id, label in agents:
        dot, status = agent_state(agent_id, result, package)
        st.markdown(f'<div class="mc-row"><span class="mc-dot {dot}"></span><div><div class="mc-row-title">{label}</div><div class="mc-row-copy">{safe(status)}</div></div></div>', unsafe_allow_html=True)

    st.markdown('<div class="mc-label">Questions</div>', unsafe_allow_html=True)
    missing_items = []
    if result and result.get("missing_information_report"):
        missing_items = list(result["missing_information_report"].items or [])
    if missing_items:
        for item in missing_items[:5]:
            prefix = "BLOCKING" if item.recommendation_blocking else item.priority.value.upper()
            if st.button(f"{prefix} · {item.field}", key=f"question_{item.item_id}", use_container_width=True):
                st.session_state.selected_question_id = item.item_id
                st.rerun()
    else:
        st.markdown('<div class="mc-muted">No unresolved decision-critical questions are currently surfaced.</div>', unsafe_allow_html=True)

    selected = None
    if st.session_state.selected_question_id and missing_items:
        selected = next((x for x in missing_items if x.item_id == st.session_state.selected_question_id), None)
    if selected is not None:
        st.markdown('<div class="mc-question">', unsafe_allow_html=True)
        st.markdown(f'<div class="mc-question-title">{safe(selected.field)}</div><div class="mc-question-copy">{safe(selected.reason)}</div>', unsafe_allow_html=True)
        st.caption(f"Priority: {selected.priority.value.upper()} · Action: {selected.action.value.replace('_',' ').title()} · Blocking: {'Yes' if selected.recommendation_blocking else 'No'}")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="mc-label">Add case information</div>', unsafe_allow_html=True)
    st.caption("This is not an open-ended treatment chat. New text is treated as supplemental case data and must pass extraction, provenance, integrity, and human review again.")
    with st.form("clarification_form", clear_on_submit=True):
        clarification = st.text_area(
            "Follow-up information",
            height=90,
            placeholder=(f"Add information about: {selected.field}" if selected is not None else "Add new de-identified clinical information...")
        )
        submitted = st.form_submit_button("Add and re-check case", use_container_width=True)
    if submitted:
        if not clarification.strip():
            st.warning("Enter follow-up information first.")
        elif st.session_state.parsed_document is None:
            st.warning("The structured AML demo has no source narrative to safely merge with free-text follow-up. Use Add de-identified case below to test interactive clarification.")
        else:
            token, model, base_url = model_config()
            if not token and not base_url:
                st.warning("The extraction endpoint is not configured for this deployment.")
            else:
                original = st.session_state.parsed_document.full_text
                combined = original + "\n\nCLINICIAN FOLLOW-UP INFORMATION:\n" + clarification.strip()
                reparsed = parse_text(combined, document_id="DOC-UPDATED", filename="updated_case.txt")
                try:
                    with st.spinner("Re-structuring the case and re-verifying provenance..."):
                        extracted = extract_case_v25(
                            document=reparsed,
                            api_key=token or "local-no-auth",
                            model=model,
                            case_id=text(value(case, "case_id", "EXTRACTED-001")),
                        )
                    st.session_state.parsed_document = reparsed
                    st.session_state.extraction_package = extracted
                    st.session_state.reviewed_case = extracted.case
                    st.session_state.result = None
                    st.session_state.clarification_history.append(clarification.strip())
                    st.session_state.selected_question_id = None
                    st.success("Follow-up information was added as a new source. Review and confirm the updated extraction before analysis.")
                    st.rerun()
                except ModelGatewayError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error(f"Follow-up processing failed safely: {exc}")

    st.markdown('<div class="mc-label">Quick start</div>', unsafe_allow_html=True)
    if st.button("Run synthetic AML", type="primary", use_container_width=True):
        sample = json.loads((PROJECT_ROOT / "synthetic_cases" / "syn_aml_001.json").read_text(encoding="utf-8"))
        st.session_state.parsed_document = None
        st.session_state.extraction_package = None
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
            token, model, base_url = model_config()
            if not token and not base_url:
                st.caption("Extraction endpoint is not configured in this deployment.")
            elif st.button("Structure case", use_container_width=True):
                try:
                    with st.spinner("Structuring case and verifying provenance..."):
                        extracted = extract_case_v25(document=parsed, api_key=token or "local-no-auth", model=model, case_id="EXTRACTED-001")
                    st.session_state.parsed_document = parsed
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
            st.error("Provenance failures remain. Analysis stays blocked until reviewed.")
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
        diagnosis = safe(value(case.diagnosis, "value", None))
        disease_state = safe(value(case.disease_state, "value", None))
        ecog = safe(value(case.performance_status, "value", None)) if case.performance_status else "Not represented"
        st.markdown(f'<div class="mc-card white"><div class="mc-label">Patient snapshot</div><div class="mc-big">{diagnosis}</div><div class="mc-copy">{disease_state} · ECOG {ecog}</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="mc-section">Molecular profile</div>', unsafe_allow_html=True)
        if case.molecular_findings:
            chips = "".join(f'<span class="mc-chip">{escape(m.gene)} {escape(m.alteration_type or "")}</span>' for m in case.molecular_findings)
            st.markdown(chips, unsafe_allow_html=True)
        else:
            st.markdown('<div class="mc-muted">No molecular findings represented. This is not equivalent to a negative molecular result.</div>', unsafe_allow_html=True)
        st.markdown('<div class="mc-section">Treatment history</div>', unsafe_allow_html=True)
        if case.treatments:
            for tx in case.treatments[:5]:
                st.markdown(f'<div class="mc-row"><span class="mc-dot ok"></span><div><div class="mc-row-title">{escape(tx.regimen)}</div><div class="mc-row-copy">Line {escape(str(tx.line_of_therapy or "?"))} · {escape(tx.best_response or "response not represented")}</div></div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="mc-muted">No treatment episodes represented.</div>', unsafe_allow_html=True)
        st.markdown('<div class="mc-section">Clinical question</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="mc-card accent"><div class="mc-copy">{escape(case.clinical_question.question)}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="mc-label">Selected evidence agents</div>', unsafe_allow_html=True)
    if result and result.get("routing"):
        routing = result["routing"]
        for agent in routing.selected_agents:
            output = result.get("specialist_outputs", {}).get(agent)
            status = text(value(output, "status", "waiting")).replace("_", " ") if output is not None else "waiting"
            dot = "ok" if status in {"completed", "completed with limitations", "no evidence found", "source unavailable"} else "warn"
            st.markdown(f'<div class="mc-row"><span class="mc-dot {dot}"></span><div><div class="mc-row-title">{escape(agent.replace("_", " ").title())}</div><div class="mc-row-copy">{escape(status.title())}</div></div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="mc-muted">Evidence agents are selected after the case passes integrity and missing-information gates.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="mc-column">', unsafe_allow_html=True)
    st.markdown('<div class="mc-label">Tumor Board Brief</div>', unsafe_allow_html=True)
    if result is None:
        st.markdown('<div class="mc-card white"><div class="mc-title">Decision-support brief</div><div class="mc-copy">Run or confirm a case to populate the board-ready output.</div></div>', unsafe_allow_html=True)
    else:
        brief = result.get("tumor_board_brief")
        final = result.get("final_decision")
        decision = safe(value(final, "decision_state", "unknown")).replace("_", " ").upper()
        strength = safe(value(final, "decision_support_strength", "unknown")).upper()
        st.markdown(f'<div class="mc-brief-head"><span class="mc-status">{decision}</span><div class="mc-big">Tumor Board Intelligence Brief</div><div class="mc-copy">Decision-support strength: {strength}</div></div>', unsafe_allow_html=True)
        if brief is None:
            reason = safe(value(final, "abstention_reason", "The workflow stopped before a structured brief could be produced."))
            st.error(reason)
        else:
            for warning in list(value(brief, "critical_warnings", []) or []):
                st.error(str(warning))
            sections = {value(s, "section_id", ""): s for s in list(value(brief, "sections", []) or [])}
            ordered = ["patient_snapshot", "clinical_question", "decision_critical_information", "management_strategy", "guideline_analysis", "molecular_translational", "clinical_trials", "safety", "red_team", "uncertainty", "what_changes_recommendation"]
            for sid in ordered:
                section = sections.get(sid)
                if section is None:
                    continue
                st.markdown(f'<div class="mc-section">{safe(value(section, "title", sid))}</div>', unsafe_allow_html=True)
                note = value(section, "section_note", None)
                if note:
                    st.caption(str(note))
                items = list(value(section, "items", []) or [])
                if not items:
                    st.markdown('<div class="mc-muted">No items represented.</div>', unsafe_allow_html=True)
                for item in items:
                    refs = list(value(item, "source_refs", []) or [])
                    ref_text = f'<div class="mc-row-copy">Source: {escape(" · ".join(str(r) for r in refs))}</div>' if refs else ''
                    st.markdown(f'<div class="mc-card white"><div class="mc-row-title">{safe(value(item, "label", "Item"))}</div><div class="mc-copy">{safe(value(item, "value", ""))}</div>{ref_text}</div>', unsafe_allow_html=True)
        red = result.get("red_team_report")
        consensus = result.get("consensus_report")
        st.markdown('<div class="mc-label">Control layer</div>', unsafe_allow_html=True)
        if red:
            disposition = text(red.disposition).upper()
            dot = "block" if disposition == "BLOCKED" else "warn" if disposition == "CHALLENGED" else "ok"
            st.markdown(f'<div class="mc-row"><span class="mc-dot {dot}"></span><div><div class="mc-row-title">Clinical Red Team</div><div class="mc-row-copy">{escape(disposition)} · {red.blocking_count} blocking finding(s)</div></div></div>', unsafe_allow_html=True)
        if consensus:
            st.markdown(f'<div class="mc-row"><span class="mc-dot ok"></span><div><div class="mc-row-title">Consensus Engine</div><div class="mc-row-copy">{escape(consensus.decision_state.replace("_", " ").upper())}</div></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="mc-line"></div><div class="mc-muted">Research prototype · Synthetic/de-identified data only · Human multidisciplinary review remains required.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
