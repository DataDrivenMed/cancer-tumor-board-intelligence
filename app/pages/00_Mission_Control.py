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
from orchestration.workflow import run_workflow
from schemas.case import CancerTumorBoardCase
from services.document_parser import parse_text, parse_upload
from services.model_gateway import ModelGatewayError

ARTICLE_URL = "https://datadrivenmed.github.io/resources/ai-agents/"

st.set_page_config(
    page_title="Tumor Board Intelligence",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
:root {
  --bg:#f7f7f4; --surface:#f2f1ed; --surface2:#ebeae5; --text:#26251e;
  --muted:#77746b; --border:rgba(38,37,30,.11); --accent:#c08532;
  --accent-dark:#9a6a28; --success:#1f8a65; --error:#cf2d56; --warning:#c08532;
}
html,body,[class*="css"]{font-family:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;}
.stApp{background:var(--bg);color:var(--text);}
[data-testid="stSidebar"],[data-testid="collapsedControl"]{display:none;}
[data-testid="stHeader"]{background:rgba(247,247,244,.94);border-bottom:1px solid var(--border);backdrop-filter:blur(10px);}
.block-container{max-width:1560px;padding:1rem 1.15rem 3rem 1.15rem;}
h1,h2,h3{color:var(--text);font-weight:550;letter-spacing:-.025em;}
p{line-height:1.5;}
.mc-topbar{display:flex;justify-content:space-between;gap:18px;align-items:center;padding:5px 2px 14px;border-bottom:1px solid var(--border);margin-bottom:7px;}
.mc-brand{font-size:1.02rem;font-weight:700;letter-spacing:-.025em;}
.mc-sub{font-size:.73rem;color:var(--muted);margin-top:2px;}
.mc-top-actions{display:flex;gap:7px;align-items:center;flex-wrap:wrap;justify-content:flex-end;}
.mc-pill{display:inline-flex;align-items:center;gap:6px;padding:5px 8px;border-radius:999px;border:1px solid var(--border);background:#fff;font-size:.66rem;color:var(--text);}
.mc-pill .dot{width:6px;height:6px;border-radius:50%;background:var(--success);}.mc-pill.warn .dot{background:var(--warning);}
.mc-column{min-height:82vh;padding:7px 15px 20px;}.mc-border{border-right:1px solid var(--border);}
.mc-label{font-size:.67rem;text-transform:uppercase;letter-spacing:.11em;color:#8a877e;font-weight:750;margin:13px 0 7px;}
.mc-row{display:flex;gap:8px;align-items:flex-start;padding:7px 0;border-bottom:1px solid rgba(38,37,30,.075);}
.mc-dot{width:7px;height:7px;border-radius:50%;background:#b9b7b0;margin-top:5px;flex:0 0 auto;}
.mc-dot.ok{background:var(--success)}.mc-dot.warn{background:var(--warning)}.mc-dot.block{background:var(--error)}
.mc-row-title{font-size:.76rem;font-weight:650;color:var(--text);}.mc-row-copy{font-size:.70rem;color:var(--muted);line-height:1.35;margin-top:1px;}
.mc-card{background:var(--surface);border:1px solid var(--border);border-radius:5px;padding:11px;margin:7px 0;box-shadow:0 1px 3px rgba(0,0,0,.035);}
.mc-card.white{background:#fff}.mc-card.accent{background:rgba(192,133,50,.09);border-color:rgba(192,133,50,.23)}
.mc-big{font-size:1.58rem;line-height:1.05;letter-spacing:-.04em;font-weight:560;margin:2px 0 6px;}
.mc-copy{font-size:.78rem;line-height:1.46;color:var(--muted);}.mc-muted{font-size:.70rem;line-height:1.45;color:var(--muted);}
.mc-section{margin:13px 0 6px;font-size:.72rem;font-weight:750;letter-spacing:.02em;color:var(--text);}
.mc-chip{display:inline-flex;margin:2px 4px 2px 0;padding:4px 7px;border:1px solid var(--border);border-radius:999px;background:#fff;font-size:.64rem;}
.mc-brief-head{padding:2px 0 10px;border-bottom:1px solid var(--border);margin-bottom:7px;}.mc-status{display:inline-flex;padding:4px 7px;border-radius:999px;border:1px solid var(--border);background:#fff;font-size:.64rem;font-weight:700;margin-bottom:7px;}
.mc-question-detail{background:#fff;border:1px solid var(--border);border-radius:5px;padding:10px;margin:7px 0 9px;}
.mc-question-title{font-size:.76rem;font-weight:700}.mc-question-copy{font-size:.70rem;color:var(--muted);line-height:1.4;margin-top:4px;}
.mc-footer{margin-top:12px;padding-top:10px;border-top:1px solid var(--border);font-size:.67rem;color:var(--muted);}
.stButton>button,.stFormSubmitButton>button{border-radius:999px!important;border:1px solid var(--text)!important;background:var(--text)!important;color:var(--bg)!important;font-weight:550!important;box-shadow:none!important;}
.stButton>button:hover,.stFormSubmitButton>button:hover{opacity:.9;}
[data-testid="stTextArea"] textarea,[data-testid="stFileUploader"] section{background:#fff!important;border:1px solid rgba(38,37,30,.18)!important;border-radius:5px!important;}
[data-testid="stExpander"]{background:transparent;border:1px solid var(--border)!important;border-radius:5px!important;}
[data-testid="stAlert"]{border-radius:5px!important;box-shadow:none!important;}
@media(max-width:980px){.mc-border{border-right:none;border-bottom:1px solid var(--border)}.mc-column{min-height:auto}.mc-topbar{align-items:flex-start;flex-direction:column}}
</style>
""",
    unsafe_allow_html=True,
)


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


def secret(name: str, default: str | None = None) -> str | None:
    try:
        return st.secrets[name]
    except Exception:
        return default


def model_config() -> tuple[str | None, str, str | None]:
    token = secret("MODEL_AUTH_TOKEN") or secret("HF_TOKEN")
    model = secret("MODEL_NAME", "openai/gpt-oss-120b:fireworks-ai") or "openai/gpt-oss-120b:fireworks-ai"
    base_url = secret("MODEL_BASE_URL")
    if base_url:
        os.environ["MODEL_BASE_URL"] = base_url
    return token, model, base_url


def run_case(case: CancerTumorBoardCase, raw_extraction: dict | None = None) -> None:
    st.session_state.reviewed_case = case
    st.session_state.result = run_workflow(case, raw_extraction=raw_extraction)


def agent_state(agent_id: str, result: dict | None, package: Any) -> tuple[str, str]:
    if agent_id == "extraction":
        return (("ok", "Complete") if package is not None or st.session_state.reviewed_case is not None else ("", "Waiting"))
    if result is None:
        return "", "Waiting"
    structural = {
        "case_integrity": result.get("case_integrity_report"),
        "missing_information": result.get("missing_information_report"),
        "clinical_router": result.get("routing"),
        "clinical_red_team": result.get("red_team_report"),
        "consensus": result.get("consensus_report"),
    }
    if agent_id in structural:
        obj = structural[agent_id]
        if obj is None:
            return "warn", "Stopped before this stage"
        label = text(value(obj, "disposition", "Complete")).replace("_", " ").title()
        kind = "block" if label.lower() in {"blocked", "red"} else "ok"
        return kind, label
    output = result.get("specialist_outputs", {}).get(agent_id)
    if output is None:
        routing = result.get("routing")
        if routing and agent_id not in routing.selected_agents:
            return "", "Not selected"
        return "warn", "No output"
    status = text(value(output, "status", "completed")).replace("_", " ")
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
    '<div class="mc-topbar"><div><div class="mc-brand">Tumor Board Intelligence</div>'
    '<div class="mc-sub">Evidence-grounded, agentic decision support for multidisciplinary cancer case review · Research v1.0</div></div>'
    '<div class="mc-top-actions"><span class="mc-pill"><span class="dot"></span>36/36 frozen qualification</span>'
    '<span class="mc-pill warn"><span class="dot"></span>Human review required</span></div></div>',
    unsafe_allow_html=True,
)

nav1, nav2, nav3 = st.columns([1, 1, 5])
with nav1:
    st.page_link("pages/00_Architecture_Anatomy.py", label="Agent Anatomy", use_container_width=True)
with nav2:
    st.link_button("AI Agents in Medicine", ARTICLE_URL, use_container_width=True)

left, middle, right = st.columns([0.84, 1.02, 1.60], gap="small")

with left:
    st.markdown('<div class="mc-column mc-border">', unsafe_allow_html=True)
    st.markdown('<div class="mc-label">In progress</div>', unsafe_allow_html=True)
    if result is not None:
        final = result.get("final_decision")
        st.markdown(
            f'<div class="mc-row"><span class="mc-dot ok"></span><div><div class="mc-row-title">Analysis complete</div>'
            f'<div class="mc-row-copy">Decision state: {safe(value(final,"decision_state","unknown")).replace("_"," ")}</div></div></div>',
            unsafe_allow_html=True,
        )
    elif package is not None:
        st.markdown('<div class="mc-row"><span class="mc-dot warn"></span><div><div class="mc-row-title">Extraction complete</div><div class="mc-row-copy">Review and confirm the structured case before downstream analysis.</div></div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="mc-row"><span class="mc-dot"></span><div><div class="mc-row-title">No active case</div><div class="mc-row-copy">Run the synthetic AML example or add a de-identified case.</div></div></div>', unsafe_allow_html=True)

    st.markdown('<div class="mc-label">Agents</div>', unsafe_allow_html=True)
    agents = [
        ("extraction", "Extraction Agent", "Builds the provenance-aware case"),
        ("case_integrity", "Case Integrity / Data QA", "Checks structure, provenance, conflicts"),
        ("missing_information", "Missing Information Agent", "Surfaces decision-critical gaps"),
        ("clinical_router", "Clinical Router", "Selects relevant specialist channels"),
        ("guideline", "Guideline Agent", "Verified guideline context"),
        ("literature", "Literature Agent", "Bounded PubMed evidence retrieval"),
        ("molecular", "Molecular Interpretation", "Disease + alteration context"),
        ("translational", "Translational Biology", "Mechanistic and preclinical evidence"),
        ("clinical_trials", "Clinical Trials Agent", "Trial matching, not eligibility"),
        ("safety", "Safety Agent", "Verified safety constraints"),
        ("clinical_red_team", "Clinical Red Team", "Independent challenge layer"),
        ("consensus", "Consensus Engine", "Evidence-weighted, non-voting synthesis"),
    ]
    for agent_id, label, description in agents:
        dot, status = agent_state(agent_id, result, package)
        st.markdown(
            f'<div class="mc-row"><span class="mc-dot {dot}"></span><div><div class="mc-row-title">{escape(label)}</div>'
            f'<div class="mc-row-copy">{escape(description)} · {escape(status)}</div></div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="mc-label">Questions</div>', unsafe_allow_html=True)
    missing_items = []
    if result and result.get("missing_information_report"):
        missing_items = list(result["missing_information_report"].items or [])
    if missing_items:
        for item in missing_items[:6]:
            prefix = "BLOCKING" if item.recommendation_blocking else item.priority.value.upper()
            if st.button(f"{prefix} · {item.field}", key=f"q_{item.item_id}", use_container_width=True):
                st.session_state.selected_question_id = item.item_id
                st.rerun()
    else:
        st.markdown('<div class="mc-muted">No unresolved decision-critical questions are currently surfaced.</div>', unsafe_allow_html=True)

    selected = None
    if st.session_state.selected_question_id and missing_items:
        selected = next((x for x in missing_items if x.item_id == st.session_state.selected_question_id), None)
    if selected is not None:
        st.markdown(
            f'<div class="mc-question-detail"><div class="mc-question-title">{safe(selected.field)}</div>'
            f'<div class="mc-question-copy">{safe(selected.reason)}</div></div>',
            unsafe_allow_html=True,
        )
        st.caption(
            f"Priority: {selected.priority.value.upper()} · Raised by: Missing Information Agent · "
            f"Action: {selected.action.value.replace('_',' ').title()} · Recommendation blocking: {'Yes' if selected.recommendation_blocking else 'No'}"
        )

    st.markdown('<div class="mc-label">Follow-up case information</div>', unsafe_allow_html=True)
    st.caption("Add new case facts or clarifications. This is not a free-form treatment chat. New text becomes supplemental source material and must pass extraction, provenance, integrity, and clinician review again.")
    with st.form("followup_form", clear_on_submit=True):
        clarification = st.text_area(
            "Add de-identified follow-up information",
            height=92,
            placeholder=(f"Add information to address: {selected.field}" if selected is not None else "Example: Bone marrow biopsy from 8/10 showed 42% blasts..."),
        )
        submitted = st.form_submit_button("Incorporate into case", use_container_width=True)
    if submitted:
        if not clarification.strip():
            st.warning("Enter follow-up information first.")
        elif st.session_state.parsed_document is None:
            st.warning("The structured AML quick-start case has no source narrative to safely merge with free text. Use 'Add a de-identified case' below when testing interactive clarification.")
        else:
            token, model, base_url = model_config()
            if not token and not base_url:
                st.warning("The extraction endpoint is not configured for this deployment.")
            else:
                combined = st.session_state.parsed_document.full_text + "\n\nCLINICIAN FOLLOW-UP INFORMATION:\n" + clarification.strip()
                reparsed = parse_text(combined, document_id="DOC-UPDATED", filename="updated_case.txt")
                try:
                    with st.spinner("Re-structuring case and re-verifying provenance..."):
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
        st.session_state.selected_question_id = None
        run_case(CancerTumorBoardCase.model_validate(sample))
        st.rerun()

    with st.expander("Add a de-identified case"):
        narrative = st.text_area("Case narrative", height=120, placeholder="Paste synthetic or fully de-identified tumor-board text...")
        upload = st.file_uploader("Or upload PDF / DOCX / TXT / MD", type=["pdf", "docx", "txt", "md"], key="mission_upload")
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
                    with st.spinner("Structuring case and verifying exact source provenance..."):
                        extracted = extract_case_v25(document=parsed, api_key=token or "local-no-auth", model=model, case_id="EXTRACTED-001")
                    st.session_state.parsed_document = parsed
                    st.session_state.extraction_package = extracted
                    st.session_state.reviewed_case = extracted.case
                    st.session_state.result = None
                    st.session_state.selected_question_id = None
                    st.rerun()
                except ModelGatewayError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error(f"Extraction failed safely: {exc}")

    if package is not None and result is None:
        st.markdown('<div class="mc-label">Clinician confirmation</div>', unsafe_allow_html=True)
        st.caption(f"Exact provenance: {package.provenance_verified}/{package.provenance_total} anchors verified")
        if package.provenance_failures:
            st.error("One or more provenance anchors failed. Analysis should remain blocked until reviewed.")
        if st.button("Confirm structured case and analyze", type="primary", use_container_width=True):
            run_case(package.case, raw_extraction=package.raw_extraction)
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

with middle:
    st.markdown('<div class="mc-column mc-border">', unsafe_allow_html=True)
    st.markdown('<div class="mc-label">Case Intelligence</div>', unsafe_allow_html=True)
    if case is None:
        st.markdown('<div class="mc-card"><div class="mc-row-title">Waiting for a case</div><div class="mc-copy">The structured patient representation will appear here after case input.</div></div>', unsafe_allow_html=True)
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
            st.markdown('<div class="mc-muted">No molecular findings represented. Absence from the case is not a negative result.</div>', unsafe_allow_html=True)

        st.markdown('<div class="mc-section">Treatment history</div>', unsafe_allow_html=True)
        if case.treatments:
            for tx in case.treatments[:6]:
                st.markdown(
                    f'<div class="mc-row"><span class="mc-dot ok"></span><div><div class="mc-row-title">{escape(tx.regimen)}</div>'
                    f'<div class="mc-row-copy">Line {escape(str(tx.line_of_therapy or "?"))} · {escape(tx.best_response or "response not represented")}</div></div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown('<div class="mc-muted">No treatment episodes represented.</div>', unsafe_allow_html=True)

        st.markdown('<div class="mc-section">Clinical question</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="mc-card accent"><div class="mc-copy">{escape(case.clinical_question.question)}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="mc-label">Evidence channels</div>', unsafe_allow_html=True)
    if result and result.get("routing"):
        routing = result["routing"]
        for agent_id in routing.selected_agents:
            output = result.get("specialist_outputs", {}).get(agent_id)
            status = text(value(output, "status", "waiting")).replace("_", " ") if output is not None else "waiting"
            kind = "ok" if status in {"completed", "completed with limitations", "no evidence found", "source unavailable"} else "warn"
            st.markdown(
                f'<div class="mc-row"><span class="mc-dot {kind}"></span><div><div class="mc-row-title">{escape(agent_id.replace("_"," ").title())}</div>'
                f'<div class="mc-row-copy">{escape(status.title())}</div></div></div>', unsafe_allow_html=True)
    else:
        for label in ["Guideline", "Literature", "Molecular", "Translational", "Clinical Trials", "Safety"]:
            st.markdown(f'<div class="mc-row"><span class="mc-dot"></span><div><div class="mc-row-title">{label}</div><div class="mc-row-copy">Waiting</div></div></div>', unsafe_allow_html=True)

    if st.session_state.clarification_history:
        st.markdown('<div class="mc-label">Follow-up sources</div>', unsafe_allow_html=True)
        for idx, item in enumerate(st.session_state.clarification_history[-3:], start=1):
            st.markdown(f'<div class="mc-card white"><div class="mc-row-title">Supplement {idx}</div><div class="mc-copy">{escape(item)}</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="mc-column">', unsafe_allow_html=True)
    st.markdown('<div class="mc-label">Tumor Board Brief</div>', unsafe_allow_html=True)
    if result is None:
        st.markdown('<div class="mc-card white"><div class="mc-big">Decision-support brief</div><div class="mc-copy">Run or structure a case to populate the board-ready output. This pane is intentionally the largest because the brief, not the machinery, is the clinician-facing product.</div></div>', unsafe_allow_html=True)
    else:
        brief = result.get("tumor_board_brief")
        final = result.get("final_decision")
        decision = safe(value(final, "decision_state", "unknown")).replace("_", " ").upper()
        strength = safe(value(final, "decision_support_strength", "unknown")).upper()
        st.markdown(f'<div class="mc-brief-head"><div class="mc-status">{decision}</div><div class="mc-big">Tumor Board Intelligence Brief</div><div class="mc-copy">Decision-support strength: {strength}</div></div>', unsafe_allow_html=True)

        if brief is None:
            reason = safe(value(final, "abstention_reason", "Workflow stopped before a structured brief could be produced."))
            st.error(reason)
        else:
            for warning in list(value(brief, "critical_warnings", []) or []):
                st.error(warning)
            sections = {value(s, "section_id", ""): s for s in list(value(brief, "sections", []) or [])}
            ordered = [
                "patient_snapshot", "clinical_question", "decision_critical_information", "management_strategy",
                "guideline_analysis", "molecular_translational", "clinical_trials", "safety", "red_team",
                "uncertainty", "what_changes_recommendation",
            ]
            for sid in ordered:
                section = sections.get(sid)
                if section is None:
                    continue
                st.markdown(f'<div class="mc-section">{safe(value(section,"title",sid))}</div>', unsafe_allow_html=True)
                note = value(section, "section_note", None)
                if note:
                    st.caption(str(note))
                items = list(value(section, "items", []) or [])
                if not items:
                    st.markdown('<div class="mc-muted">No items represented.</div>', unsafe_allow_html=True)
                for item in items:
                    label = safe(value(item, "label", "Item"))
                    item_value = safe(value(item, "value", ""))
                    refs = list(value(item, "source_refs", []) or [])
                    ref_html = f'<div class="mc-row-copy">Source trace: {escape(" · ".join(str(r) for r in refs))}</div>' if refs else ""
                    st.markdown(f'<div class="mc-card white"><div class="mc-row-title">{label}</div><div class="mc-copy">{item_value}</div>{ref_html}</div>', unsafe_allow_html=True)

        red = result.get("red_team_report")
        consensus = result.get("consensus_report")
        st.markdown('<div class="mc-label">Control layer</div>', unsafe_allow_html=True)
        if red:
            disposition = text(red.disposition).upper()
            kind = "block" if disposition == "BLOCKED" else "warn" if disposition == "CHALLENGED" else "ok"
            st.markdown(f'<div class="mc-row"><span class="mc-dot {kind}"></span><div><div class="mc-row-title">Clinical Red Team</div><div class="mc-row-copy">{escape(disposition)} · {red.blocking_count} blocking finding(s)</div></div></div>', unsafe_allow_html=True)
        if consensus:
            st.markdown(f'<div class="mc-row"><span class="mc-dot ok"></span><div><div class="mc-row-title">Consensus Engine</div><div class="mc-row-copy">{escape(consensus.decision_state.replace("_"," ").upper())}</div></div></div>', unsafe_allow_html=True)

    st.markdown('<div class="mc-footer">Research prototype · Synthetic/de-identified data only · Controlled software qualification does not establish clinical validation or autonomous clinical safety · Human multidisciplinary review remains required.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
