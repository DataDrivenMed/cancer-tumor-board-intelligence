from __future__ import annotations

import csv
import io
from html import escape
from typing import Any

import streamlit as st

from app.xai_theme import inject_xai_theme

from services.oncology_programs import PROGRAM_BY_ID, PROGRAMS
from services.pathway_validation import get_pathway_validation_status


def _val(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _txt(value: Any, default: str = "Not available") -> str:
    if value is None:
        return default
    if hasattr(value, "value"):
        value = value.value
    text = str(value).strip()
    return text or default


def faculty_css() -> None:
    st.markdown(
        """
<style>
:root{
 --fx-ink:#101828;--fx-ink2:#344054;--fx-muted:#667085;--fx-line:#e4e7ec;
 --fx-navy:#17324d;--fx-blue:#285e9e;--fx-blue-soft:#eef5fb;--fx-cyan:#eaf7fa;
 --fx-green:#15715d;--fx-green-soft:#ecf8f3;--fx-amber:#9a6700;--fx-amber-soft:#fff7e6;
 --fx-red:#b42318;--fx-red-soft:#fff1f0;--fx-violet:#6941c6;--fx-violet-soft:#f4f0ff;
 --fx-slate:#eef1f5;--fx-white:#fff;--fx-shadow:0 12px 34px rgba(16,24,40,.07);
}
.fx-top{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:8px 0 14px;border-bottom:1px solid var(--fx-line);margin-bottom:10px}
.fx-brand{display:flex;align-items:center;gap:12px}.fx-mark{width:38px;height:38px;border:1px solid #315471;border-radius:10px;background:linear-gradient(150deg,#1f405e,#10283e);display:grid;place-items:center;color:#fff;font-size:11px;font-weight:800;letter-spacing:.08em}
.fx-product{font-size:32px;font-weight:760;color:var(--fx-ink);letter-spacing:-.02em}.fx-author{font-size:14px;color:var(--fx-muted);margin-top:2px}.fx-mode{font-size:12px;color:var(--fx-muted);text-align:right}
.fx-hero{padding:44px 0 28px;max-width:1020px}.fx-kicker{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.12em;color:var(--fx-blue);margin-bottom:12px}.fx-hero h1{font-size:48px;line-height:1.03;letter-spacing:-1.5px;color:var(--fx-ink);margin:0;font-weight:650}.fx-hero p{font-size:17px;line-height:1.6;color:var(--fx-muted);max-width:840px;margin:16px 0 0}
.fx-section{font-size:27px;font-weight:730;letter-spacing:-.6px;color:var(--fx-ink);margin:30px 0 5px}.fx-sub{font-size:13px;line-height:1.55;color:var(--fx-muted);margin-bottom:16px;max-width:880px}
.fx-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:14px 0 24px}.fx-card{background:#fff;border:1px solid var(--fx-line);border-radius:14px;padding:17px;box-shadow:0 1px 2px rgba(16,24,40,.03)}.fx-card h3{font-size:16px;margin:8px 0 6px;color:var(--fx-ink)}.fx-card p{font-size:13px;line-height:1.55;color:var(--fx-muted);margin:0}.fx-icon{width:32px;height:32px;border-radius:8px;background:var(--fx-blue-soft);color:var(--fx-blue);display:grid;place-items:center;font-size:10px;font-weight:850;border:1px solid #dbe9f6}
.fx-method{display:grid;grid-template-columns:1fr 34px 1fr 34px 1fr 34px 1fr;align-items:center;gap:8px;background:linear-gradient(180deg,#fff,#fbfcfe);border:1px solid var(--fx-line);border-radius:18px;padding:20px;box-shadow:var(--fx-shadow);margin:14px 0 24px}.fx-node{min-height:112px;border-radius:14px;padding:15px;background:#fff;border:1px solid var(--fx-line)}.fx-node strong{display:block;font-size:15px;color:var(--fx-ink);margin-bottom:5px}.fx-node span{font-size:12px;line-height:1.45;color:var(--fx-muted)}.fx-arrow{text-align:center;color:#98a2b3;font-size:19px}
.fx-core{background:linear-gradient(150deg,#15344e,#0e2437);color:#fff;border-radius:18px;padding:22px}.fx-core .fx-kicker{color:#a8d4f3}.fx-core h2{font-size:25px;margin:0 0 8px}.fx-core p{font-size:12px;line-height:1.6;color:#d7e2ea;margin:0}.fx-agent-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:14px}.fx-agent{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);border-radius:12px;padding:13px}.fx-agent strong{font-size:12px;display:block}.fx-agent span{font-size:10px;color:#cdd9e2;line-height:1.45;display:block;margin-top:4px}
.fx-context{display:grid;grid-template-columns:1.1fr .9fr .9fr 1fr 2fr;gap:8px;border:1px solid var(--fx-line);background:#fff;border-radius:12px;padding:9px 10px;margin:8px 0 14px;box-shadow:0 1px 2px rgba(16,24,40,.03)}.fx-context div{min-width:0}.fx-lbl{font-size:10px;text-transform:uppercase;letter-spacing:.09em;color:var(--fx-muted);font-weight:800}.fx-val{font-size:13px;color:var(--fx-ink);font-weight:650;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.fx-question .fx-val{white-space:normal}
.fx-synthetic{display:inline-flex;align-items:center;gap:5px;padding:5px 9px;border-radius:999px;background:var(--fx-violet-soft);color:var(--fx-violet);font-size:11px;font-weight:800;border:1px solid #e4dcff;margin-bottom:8px}
.fx-thirty{background:linear-gradient(140deg,#102b43,#193f60);color:#fff;border-radius:18px;padding:20px 22px;box-shadow:var(--fx-shadow);margin:8px 0 18px}.fx-thirty-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}.fx-thirty-title{font-size:21px;font-weight:750}.fx-thirty-sub{font-size:12px;color:#bdd1df;margin-top:3px}.fx-thirty-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;margin-top:15px}.fx-thirty-cell{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.11);border-radius:11px;padding:11px}.fx-thirty-cell .fx-lbl{color:#a9c2d4}.fx-thirty-cell .fx-val{color:#fff;white-space:normal;font-size:14px}
.fx-decision-banner{background:#fff;border:1px solid var(--fx-line);border-left:5px solid var(--fx-blue);border-radius:14px;padding:18px 20px;box-shadow:var(--fx-shadow);margin:10px 0 14px}.fx-decision-banner h2{font-size:26px;letter-spacing:-.5px;margin:4px 0}.fx-decision-banner p{font-size:14px;color:var(--fx-muted);line-height:1.5;margin:4px 0 0}
.fx-panel-title{font-size:21px;font-weight:760;color:var(--fx-ink);margin:16px 0 4px}.fx-panel-sub{font-size:13px;color:var(--fx-muted);margin-bottom:10px}
.fx-challenge{background:linear-gradient(145deg,#2a3140,#1e2530);color:#fff;border-radius:15px;padding:17px;margin:10px 0}.fx-challenge .fx-panel-title{color:#fff;margin:0 0 5px}.fx-challenge p{color:#cbd5df;font-size:13px;line-height:1.5;margin:0}
.fx-missing{background:var(--fx-amber-soft);border:1px solid #f2d58d;border-radius:14px;padding:15px}.fx-missing strong{font-size:15px;color:#6f4d00}.fx-missing p{font-size:13px;color:#7a5b15;line-height:1.5;margin:5px 0 0}
.fx-chat-head{background:linear-gradient(145deg,#215f78,#18475c);color:#fff;border-radius:15px 15px 9px 9px;padding:16px 17px;margin-top:8px}.fx-chat-head strong{font-size:17px;display:block}.fx-chat-head span{font-size:10px;color:#d4edf5;line-height:1.45;display:block;margin-top:4px}.fx-chat-note{background:var(--fx-cyan);border:1px solid #c8e8ef;border-radius:10px;padding:9px 10px;color:#315c68;font-size:10px;line-height:1.45;margin:6px 0 10px}.fx-answer{background:#fff;border:1px solid #dce8ed;border-radius:12px;padding:12px 13px;margin:8px 0}.fx-answer b{font-size:11px;color:var(--fx-ink)}.fx-answer p{font-size:11px;color:var(--fx-ink2);line-height:1.55;margin:5px 0}.fx-source-chip{display:inline-flex;padding:3px 7px;border-radius:999px;background:#edf4f7;color:#3d6875;font-size:8px;font-weight:750;margin:3px 3px 0 0}
.fx-status-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:14px 0}.fx-status{border:1px solid var(--fx-line);border-radius:12px;padding:13px;background:#fff}.fx-status strong{font-size:14px;display:block}.fx-status span{font-size:12px;color:var(--fx-muted);display:block;margin-top:4px}
.fx-program-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:12px}.fx-program{border:1px solid var(--fx-line);border-radius:12px;padding:13px;background:#fff}.fx-program strong{font-size:14px;color:var(--fx-ink)}.fx-program span{display:block;font-size:11px;color:var(--fx-muted);margin-top:4px}
.fx-footer{border-top:1px solid var(--fx-line);margin-top:34px;padding:14px 0 4px;font-size:11px;color:var(--fx-muted);display:flex;justify-content:space-between;gap:14px}
[data-testid="stExpander"] summary p::after{content:"  ·  View details";font-size:11px;color:#7c8798;font-weight:600}
[data-testid="stExpander"] summary{cursor:pointer}
@media(max-width:950px){.fx-grid,.fx-thirty-grid{grid-template-columns:repeat(2,1fr)}.fx-agent-grid,.fx-program-grid{grid-template-columns:repeat(2,1fr)}.fx-context{grid-template-columns:repeat(2,1fr)}.fx-question{grid-column:1/-1}.fx-method{grid-template-columns:1fr}.fx-arrow{transform:rotate(90deg)}}
@media(max-width:600px){.fx-grid,.fx-thirty-grid,.fx-agent-grid,.fx-program-grid{grid-template-columns:1fr}.fx-hero h1{font-size:37px}.fx-context{grid-template-columns:1fr}.fx-footer{display:block}.fx-footer div+div{margin-top:5px}}

[data-testid="stPageLink-NavLink"]{border:1px solid #d8e2ec!important;border-radius:10px!important;padding:.58rem .75rem!important;font-size:13px!important;font-weight:750!important;transition:all .15s ease;background:#f4f8fc!important;color:#23415d!important}
[data-testid="stPageLink-NavLink"]:hover{transform:translateY(-1px);box-shadow:0 4px 10px rgba(16,42,67,.06)}
[data-testid="stPageLink-NavLink"][href*="Clinical_Workspace"]{background:#181b30!important;border-color:#282c47!important;color:#b7bad2!important}
[data-testid="stPageLink-NavLink"][href*="Validation"]{background:#181b30!important;border-color:#282c47!important;color:#b7bad2!important}
[data-testid="stPageLink-NavLink"][href*="Architecture"]{background:#181b30!important;border-color:#282c47!important;color:#b7bad2!important}
[data-testid="stPageLink-NavLink"][href*="About"]{background:#181b30!important;border-color:#282c47!important;color:#b7bad2!important}
[data-testid="stPageLink-NavLink"][aria-disabled="true"]{box-shadow:inset 0 0 0 2px currentColor!important;opacity:1!important}

</style>
""",
        unsafe_allow_html=True,
    )


def product_header(mode: str = "Faculty evaluation") -> None:
    st.markdown(
        '<div class="fx-top"><div class="fx-brand"><div class="fx-mark">TB</div><div>'
        '<div class="fx-product">Pan-Oncology Tumor Board Intelligence</div>'
        '<div class="fx-author">Ram Paragi · rparag@lsuhsc.edu</div></div></div>'
        f'<div class="fx-mode">{escape(mode)}<br>Research decision support</div></div>',
        unsafe_allow_html=True,
    )


def top_navigation(active: str) -> None:
    inject_xai_theme()
    links = [
        ("main.py", "Overview", "overview"),
        ("pages/00_Clinical_Workspace.py", "Workspace", "workspace"),
        ("pages/01_Validation.py", "Validation", "validation"),
        ("pages/03_Architecture.py", "Architecture", "architecture"),
        ("pages/02_About.py", "About", "about"),
    ]

    with st.sidebar:
        st.markdown(
            '<div class="fx-side-brand"><div class="fx-side-mark">TB</div><div><div class="fx-side-name">Pan-Oncology</div><div class="fx-side-sub">Tumor Board Intelligence</div></div></div>',
            unsafe_allow_html=True,
        )
        case = st.session_state.get("case")
        if case is not None:
            diagnosis = _txt(_val(getattr(case, "diagnosis", None), "value", None))
            disease_state = _txt(_val(getattr(case, "disease_state", None), "value", None))
            case_id = _txt(getattr(case, "case_id", None), "Current case")
            st.markdown(
                '<div class="fx-side-label">Current case</div><div class="fx-side-case"><div class="fx-side-live">Active</div>'
                f'<strong>{escape(diagnosis)}</strong><span>{escape(disease_state)}</span><small>{escape(case_id)}</small></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="fx-side-label">Current case</div><div class="fx-side-case"><div class="fx-side-idle">No active case</div><span>Open the workspace to begin a governed case.</span></div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div class="fx-side-label">Navigate</div>', unsafe_allow_html=True)
        for page, label, key in links:
            st.page_link(page, label=label, use_container_width=True, disabled=active == key)

        st.markdown(
            '<div class="fx-side-label">System</div><div class="fx-side-system"><div><i></i><strong>Research mode</strong></div><span>De-identified or synthetic data only</span><div><i class="amber"></i><strong>Clinical release not established</strong></div></div>',
            unsafe_allow_html=True,
        )

    cols = st.columns([1, 1, 1, 1, 1, 2], gap="small")
    for col, (page, label, key) in zip(cols[:5], links):
        with col:
            st.page_link(page, label=label, use_container_width=True, disabled=active == key)

def research_footer() -> None:
    st.markdown(
        '<div class="fx-footer"><div>Research decision support · de-identified or synthetic data only</div>'
        '<div>Not clinically validated for unrestricted patient-care use</div></div>',
        unsafe_allow_html=True,
    )


def render_case_context(case: Any) -> None:
    program = PROGRAM_BY_ID.get(getattr(case, "disease_program", None))
    validation = get_pathway_validation_status(getattr(case, "disease_program", ""))
    stage = _txt(_val(getattr(case, "stage", None), "value", None))
    mol = getattr(case, "molecular_findings", []) or []
    molecular = "Not documented"
    if mol:
        first = mol[0]
        molecular = " ".join(x for x in [_txt(getattr(first, "gene", None), ""), _txt(getattr(first, "alteration_type", None), "")] if x).strip() or "Documented"
    question = _txt(_val(getattr(case, "clinical_question", None), "question", None))
    synthetic = str(getattr(case, "case_type", "")).lower() == "synthetic" or str(getattr(case, "case_id", "")).startswith("SYN-")
    if synthetic:
        st.markdown('<div class="fx-synthetic">Synthetic demonstration case</div>', unsafe_allow_html=True)
    html = '<div class="fx-context">'
    items = [
        ("Tumor board", program.display_name if program else _txt(getattr(case, "disease_program", None))),
        ("Diagnosis", _txt(_val(getattr(case, "diagnosis", None), "value", None))),
        ("Stage", stage),
        ("Validation", _txt(getattr(validation, "label", None))),
    ]
    for label, value in items:
        html += f'<div><div class="fx-lbl">{escape(label)}</div><div class="fx-val">{escape(value)}</div></div>'
    html += f'<div class="fx-question"><div class="fx-lbl">Tumor board question</div><div class="fx-val">{escape(question)}</div></div></div>'
    st.markdown(html, unsafe_allow_html=True)


def _evidence_strength(result: dict[str, Any]) -> str:
    outputs = result.get("specialist_outputs", {}) or {}
    if not outputs:
        return "Insufficient"
    statuses = [str(_val(v, "status", "")).lower() for v in outputs.values() if v is not None]
    positive = sum(s in {"completed", "clear", "ready", "pass", "completed_with_limitations"} for s in statuses)
    negative = sum(s in {"source_unavailable", "no_evidence_found", "verification_failed", "tool_failure"} for s in statuses)
    if positive >= 4 and negative == 0:
        return "Strong"
    if positive >= 3:
        return "Moderate"
    if positive >= 1:
        return "Limited"
    return "Insufficient"


def _brief_item(result: dict[str, Any], *needles: str) -> str:
    brief = result.get("tumor_board_brief")
    for section in _val(brief, "sections", []) or []:
        sid = _txt(_val(section, "section_id", ""), "").lower()
        title = _txt(_val(section, "title", ""), "").lower()
        if any(n.lower() in sid or n.lower() in title for n in needles):
            items = _val(section, "items", []) or []
            if items:
                return _txt(_val(items[0], "value", None))
    return "Not available from the current governed brief"


def render_thirty_second_view(result: dict[str, Any], case: Any) -> None:
    final = result.get("final_decision")
    consensus = result.get("consensus_report")
    decision = _txt(_val(final, "decision_state", _val(consensus, "decision_state", "abstain")))
    mols = getattr(case, "molecular_findings", []) or []
    mol_text = "Not documented"
    if mols:
        mol_text = "; ".join(" ".join(x for x in [_txt(getattr(m, "gene", None), ""), _txt(getattr(m, "alteration_type", None), "")] if x).strip() for m in mols[:3])
    cells = [
        ("Diagnosis", _txt(_val(getattr(case, "diagnosis", None), "value", None))),
        ("Disease state / stage", f"{_txt(_val(getattr(case, 'disease_state', None), 'value', None))} · {_txt(_val(getattr(case, 'stage', None), 'value', None))}"),
        ("Key molecular findings", mol_text),
        ("Decision state", decision.replace("_", " ").title()),
        ("Primary strategy", _brief_item(result, "management_strategy", "management strategy")),
        ("Biggest uncertainty", _brief_item(result, "uncertainty", "missing", "what changes")),
        ("Evidence strength", _evidence_strength(result)),
        ("Tumor board question", _txt(_val(getattr(case, "clinical_question", None), "question", None))),
    ]
    html = '<div class="fx-thirty"><div class="fx-thirty-head"><div><div class="fx-thirty-title">30-second Tumor Board View</div><div class="fx-thirty-sub">Rapid orientation before deeper evidence review</div></div></div><div class="fx-thirty-grid">'
    for label, value in cells:
        html += f'<div class="fx-thirty-cell"><div class="fx-lbl">{escape(label)}</div><div class="fx-val">{escape(value)}</div></div>'
    html += '</div></div>'
    st.markdown(html, unsafe_allow_html=True)


def render_treatment_timeline(case: Any) -> None:
    treatments = getattr(case, "treatments", []) or []
    st.markdown('<div class="fx-panel-title">Treatment history</div><div class="fx-panel-sub">Represented treatment sequence. Expand source details where available.</div>', unsafe_allow_html=True)
    if not treatments:
        st.info("No treatment history is represented in the current case.")
        return
    cols = st.columns(min(len(treatments), 4), gap="small") if len(treatments) <= 4 else None
    if cols:
        for col, tx in zip(cols, treatments):
            with col:
                st.markdown(f"**{escape(_txt(getattr(tx, 'regimen', None)))}**")
                st.caption(_txt(getattr(tx, "response", None), "Response not documented"))
    else:
        for i, tx in enumerate(treatments, 1):
            st.markdown(f"**{i}. {_txt(getattr(tx, 'regimen', None))}** · {_txt(getattr(tx, 'response', None), 'Response not documented')}")


def render_molecular_table(case: Any) -> None:
    molecular = getattr(case, "molecular_findings", []) or []
    st.markdown('<div class="fx-panel-title">Molecular findings</div><div class="fx-panel-sub">Structured alterations represented in the case. Source verification remains distinct from actionability.</div>', unsafe_allow_html=True)
    if not molecular:
        st.info("No molecular findings are represented.")
        return
    rows = []
    for item in molecular:
        rows.append({
            "Gene": _txt(getattr(item, "gene", None)),
            "Alteration": _txt(getattr(item, "alteration_type", None)),
            "VAF": f"{getattr(item, 'variant_allele_frequency')*100:.1f}%" if getattr(item, "variant_allele_frequency", None) is not None else "Not available",
            "Human verified": "Yes" if bool(getattr(item, "human_verified", False)) else "No",
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _sources_for_result(result: dict[str, Any]) -> list[str]:
    sources: list[str] = []
    outputs = result.get("specialist_outputs", {}) or {}
    for key, obj in outputs.items():
        if obj is None:
            continue
        status = _txt(_val(obj, "status", ""), "")
        if status:
            sources.append(f"{key.replace('_', ' ').title()}: {status.replace('_', ' ')}")
    return sources[:6]


def answer_case_question(question: str, result: dict[str, Any], case: Any) -> tuple[str, list[str], str]:
    q = " ".join(question.lower().split())
    brief = result.get("tumor_board_brief")
    sources = _sources_for_result(result)
    if any(k in q for k in ["summar", "30 second", "overview"]):
        answer = _txt(_val(brief, "summary", None), "The current governed brief does not contain a summary.")
        return answer, sources, "Case-grounded answer"
    if any(k in q for k in ["missing", "incomplete", "need to know"]):
        missing = result.get("missing_information_report")
        return _txt(_val(missing, "summary", None), "No missing-information summary is available."), ["Missing Information Agent"], "Case-grounded answer"
    if any(k in q for k in ["why", "recommend", "decision", "rationale"]):
        consensus = result.get("consensus_report")
        final = result.get("final_decision")
        answer = _txt(_val(consensus, "summary", _val(final, "abstention_reason", None)), "No governed decision rationale is available.")
        return answer, sources + ["Consensus / final decision"], "Evidence-backed" if sources else "Evidence incomplete"
    if any(k in q for k in ["change", "would alter", "what could"]):
        return _brief_item(result, "what_changes_recommendation", "what changes", "uncertainty"), ["Tumor board brief"], "Case-grounded answer"
    if any(k in q for k in ["trial", "clinical trial"]):
        obj = (result.get("specialist_outputs", {}) or {}).get("clinical_trials")
        return _txt(_val(obj, "summary", None), "No governed clinical-trial output is available for this case."), ["Clinical Trials Agent"], "Evidence-backed" if obj else "Evidence incomplete"
    if any(k in q for k in ["safety", "tox", "contraind", "adverse"]):
        obj = (result.get("specialist_outputs", {}) or {}).get("safety")
        return _txt(_val(obj, "summary", None), "No governed safety output is available for this case."), ["Safety Agent"], "Evidence-backed" if obj else "Evidence incomplete"
    if any(k in q for k in ["molecular", "mutation", "gene", "flt3", "variant"]):
        obj = (result.get("specialist_outputs", {}) or {}).get("molecular")
        return _txt(_val(obj, "summary", None), "No governed molecular output is available for this case."), ["Molecular Interpretation Agent"], "Evidence-backed" if obj else "Evidence incomplete"
    if any(k in q for k in ["challenge", "red team", "concern", "weakness"]):
        red = result.get("red_team_report")
        findings = _val(red, "findings", []) or []
        if findings:
            text = "; ".join(_txt(_val(f, "issue", None)) for f in findings[:4])
        else:
            text = _txt(_val(red, "summary", None), "No challenge-review finding is available.")
        return text, ["Challenge Review"], "Case-grounded answer"
    return "I cannot answer that from the current structured case and approved evidence without introducing information outside the governed record. Rephrase toward the case, evidence, missing information, challenge review, safety, trials, or decision rationale.", [], "Unable to answer from current case evidence"


def render_case_chat(result: dict[str, Any], case: Any, key_prefix: str = "brief") -> None:
    st.markdown('<div class="fx-chat-head"><strong>Ask Tumor Board</strong><span>Answers are limited to the structured case and approved evidence. This panel does not create a parallel treatment recommendation from unrestricted model memory.</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="fx-chat-note">Source chips identify the governed channel used. If the current record cannot support an answer, the panel abstains.</div>', unsafe_allow_html=True)
    hist_key = f"{key_prefix}_tb_chat"
    if hist_key not in st.session_state:
        st.session_state[hist_key] = []
    prompts = ["Summarize for tumor board", "What is missing?", "Why this decision?", "What could change the decision?", "Show molecular evidence", "Relevant trials"]
    if not st.session_state[hist_key]:
        cols = st.columns(2, gap="small")
        for i, prompt in enumerate(prompts):
            with cols[i % 2]:
                if st.button(prompt, key=f"{key_prefix}_prompt_{i}", use_container_width=True):
                    answer, sources, status = answer_case_question(prompt, result, case)
                    st.session_state[hist_key].append((prompt, answer, sources, status))
                    st.rerun()
    for question, answer, sources, status in st.session_state[hist_key][-5:]:
        st.markdown(f"**You:** {escape(question)}")
        chips = "".join(f'<span class="fx-source-chip">{escape(src)}</span>' for src in sources)
        st.markdown(f'<div class="fx-answer"><b>{escape(status)}</b><p>{escape(answer)}</p>{chips}</div>', unsafe_allow_html=True)
    question = st.chat_input("Ask about this case and its approved evidence", key=f"{key_prefix}_chat_input")
    if question:
        answer, sources, status = answer_case_question(question, result, case)
        st.session_state[hist_key].append((question, answer, sources, status))
        st.rerun()


def render_feedback() -> None:
    st.markdown('<div class="fx-panel-title">Faculty evaluation</div><div class="fx-panel-sub">Optional structured feedback for research and usability evaluation.</div>', unsafe_allow_html=True)
    with st.form("faculty_feedback"):
        usefulness = st.select_slider("Clinical usefulness", options=["Very low", "Low", "Moderate", "High", "Very high"], value="Moderate")
        evidence = st.select_slider("Evidence completeness", options=["Very low", "Low", "Moderate", "High", "Very high"], value="Moderate")
        clarity = st.select_slider("Clarity of reasoning", options=["Very low", "Low", "Moderate", "High", "Very high"], value="Moderate")
        missing = st.select_slider("Missing-information handling", options=["Very low", "Low", "Moderate", "High", "Very high"], value="Moderate")
        usability = st.select_slider("Usability", options=["Very low", "Low", "Moderate", "High", "Very high"], value="Moderate")
        trust = st.select_slider("Overall trust", options=["Very low", "Low", "Moderate", "High", "Very high"], value="Moderate")
        comments = st.text_area("Optional comments")
        submitted = st.form_submit_button("Add feedback to downloadable evaluation file", use_container_width=True)
    if submitted:
        st.session_state.setdefault("faculty_feedback_rows", []).append({"clinical_usefulness": usefulness, "evidence_completeness": evidence, "clarity_of_reasoning": clarity, "missing_information_handling": missing, "usability": usability, "overall_trust": trust, "comments": comments})
        st.success("Feedback added to this session's evaluation file.")
    rows = st.session_state.get("faculty_feedback_rows", [])
    if rows:
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)
        st.download_button("Download faculty feedback CSV", data=output.getvalue(), file_name="tumor_board_faculty_feedback.csv", mime="text/csv", use_container_width=True)


def render_overview() -> None:
    faculty_css(); product_header(); top_navigation("overview")
    st.markdown('<div class="fx-hero"><div class="fx-kicker">Scientific architecture for multidisciplinary cancer review</div><h1>Evidence-grounded intelligence for the tumor board.</h1><p>A pan-oncology research platform that structures complex cases, retrieves bounded evidence, makes missingness and conflict explicit, challenges recommendation logic, and produces an auditable decision brief without collapsing uncertainty into a single opaque answer.</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="fx-grid"><div class="fx-card"><div class="fx-icon">01</div><h3>Structure the case</h3><p>Represent diagnosis, disease state, stage, treatment history, molecular findings, performance status, and the clinical question with provenance.</p></div><div class="fx-card"><div class="fx-icon">02</div><h3>Commission evidence</h3><p>Route the represented question through bounded guideline, molecular, safety, literature, trial, and translational channels.</p></div><div class="fx-card"><div class="fx-icon">03</div><h3>Challenge before synthesis</h3><p>Keep missing-information, integrity, conflict, Red Team challenge, and abstention controls separate from specialist evidence generation.</p></div><div class="fx-card"><div class="fx-icon">04</div><h3>Produce an auditable brief</h3><p>Surface decision state, evidence strength, uncertainty, what could change the decision, source traceability, and limitations.</p></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="fx-section">How the scientific workflow works</div><div class="fx-sub">The architecture separates representation, evidence, challenge, consensus, and presentation so that one layer cannot silently substitute for another.</div>', unsafe_allow_html=True)
    st.markdown('<div class="fx-method"><div class="fx-node"><strong>1. Case representation</strong><span>Source-traced extraction and clinician review create the structured case. Missing facts remain missing.</span></div><div class="fx-arrow">→</div><div class="fx-node"><strong>2. Specialist evidence</strong><span>Guideline, molecular, literature, trial, safety, and translational channels operate within their governed evidence boundaries.</span></div><div class="fx-arrow">→</div><div class="fx-node"><strong>3. Challenge + consensus</strong><span>Integrity checks, missingness, conflict detection, Red Team review, and consensus gates test whether synthesis is supportable.</span></div><div class="fx-arrow">→</div><div class="fx-node"><strong>4. Tumor board brief</strong><span>Decision state, rationale, evidence availability, uncertainty, abstention, and source references become a readable brief.</span></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="fx-core"><div class="fx-kicker">Anatomy of the agent system</div><h2>One case at the center. Specialist agents around it. Challenge and consensus downstream.</h2><p>The system is intentionally modular: specialist channels contribute bounded outputs, while independent controls determine whether those outputs can support a decision state.</p><div class="fx-agent-grid"><div class="fx-agent"><strong>Case integrity + missingness</strong><span>Checks provenance, contradictions, unresolved facts, and decision-critical gaps.</span></div><div class="fx-agent"><strong>Guideline + molecular</strong><span>Tests governed guidance applicability and approved molecular evidence without inferring actionability from gene identity alone.</span></div><div class="fx-agent"><strong>Literature + trials</strong><span>Surfaces current evidence and trial matches while keeping retrieval distinct from applicability and eligibility.</span></div><div class="fx-agent"><strong>Safety + translational</strong><span>Separates label/source evidence and mechanistic context from patient-specific treatment direction.</span></div><div class="fx-agent"><strong>Challenge Review</strong><span>Actively looks for unsupported leaps, conflicts, missing prerequisites, and recommendation-blocking weaknesses.</span></div><div class="fx-agent"><strong>Consensus + brief</strong><span>Combines only supportable outputs, preserves disagreement and abstention, and generates the final auditable presentation layer.</span></div></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="fx-section">Scientific safeguards</div><div class="fx-sub">These are design constraints, not decorative disclaimers.</div>', unsafe_allow_html=True)
    st.markdown('<div class="fx-status-grid"><div class="fx-status"><strong>Provenance first</strong><span>Confirmed extracted assertions require source traceability.</span></div><div class="fx-status"><strong>Human verification stays explicit</strong><span>Retrieval does not silently become clinician-verified evidence.</span></div><div class="fx-status"><strong>Missingness remains visible</strong><span>The system does not fill decision-critical gaps from model memory.</span></div><div class="fx-status"><strong>Conflict detection</strong><span>Contradictory represented facts can block recommendation synthesis.</span></div><div class="fx-status"><strong>Abstention is a valid output</strong><span>Unsupported scenarios remain unsupported rather than being forced into a recommendation.</span></div><div class="fx-status"><strong>Challenge before consensus</strong><span>Red Team review tests the evidence boundary before the final brief is presented.</span></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="fx-section">Why this matters for tumor boards</div><div class="fx-sub">The intended value is not to replace multidisciplinary judgment. It is to make the information architecture around that judgment more explicit, reviewable, and auditable.</div>', unsafe_allow_html=True)
    cols = st.columns([1.2,1,1], gap="small")
    with cols[0]: st.page_link("pages/00_Clinical_Workspace.py", label="Enter Tumor Board Workspace", use_container_width=True)
    with cols[1]: st.page_link("pages/01_Validation.py", label="Review validation status", use_container_width=True)
    with cols[2]: st.page_link("pages/02_About.py", label="Read scientific scope", use_container_width=True)
    research_footer()


def render_validation_page() -> None:
    faculty_css(); product_header("Validation and qualification"); top_navigation("validation")
    st.markdown('<div class="fx-hero"><div class="fx-kicker">Validation boundary</div><h1>Qualified software architecture is not the same as clinical validation.</h1><p>The platform separates common-core software qualification, disease-specific software qualification, retrospective and prospective clinical validation, and governed clinical release.</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="fx-status-grid"><div class="fx-status"><strong>Common-core software qualification</strong><span>Pan-oncology routing, provenance, stage gating, fail-closed behavior, and common workflow controls have a frozen synthetic qualification record.</span></div><div class="fx-status"><strong>Disease-specific clinical validation</strong><span>Requires independent reference-standard review and remains a separate research phase.</span></div><div class="fx-status"><strong>Clinical release</strong><span>Not established. The current platform is for research decision support and faculty evaluation.</span></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="fx-section">Current oncology program scope</div><div class="fx-sub">Registration means the architecture can route and represent the disease family. It does not imply disease-specific treatment correctness.</div>', unsafe_allow_html=True)
    html = '<div class="fx-program-grid">'
    for program in PROGRAMS:
        status = get_pathway_validation_status(program.program_id)
        html += f'<div class="fx-program"><strong>{escape(program.display_name)}</strong><span>{escape(_txt(getattr(status, "label", None)))}</span></div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)
    research_footer()


def render_about_page() -> None:
    faculty_css(); product_header("Scientific scope"); top_navigation("about")
    st.markdown('<div class="fx-hero"><div class="fx-kicker">Scientific scope</div><h1>Designed for transparent decision support, not autonomous oncology care.</h1><p>The system is built around a simple principle: a tumor-board tool should make evidence boundaries, missing information, disagreement, and abstention easier to see rather than hiding them behind fluent output.</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="fx-section">What the platform does</div>', unsafe_allow_html=True)
    st.markdown('<div class="fx-grid"><div class="fx-card"><h3>Represents</h3><p>Structures the case and keeps source provenance attached to represented facts.</p></div><div class="fx-card"><h3>Retrieves</h3><p>Brings bounded external evidence into distinct specialist channels.</p></div><div class="fx-card"><h3>Challenges</h3><p>Uses missingness, conflict, safety gates, and Red Team review before synthesis.</p></div><div class="fx-card"><h3>Communicates</h3><p>Creates a tumor-board brief and PDF with decision state, evidence, uncertainty, and limitations.</p></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="fx-section">What the platform does not claim</div><div class="fx-sub">It does not establish clinical validation, trial eligibility, unrestricted disease-specific treatment correctness, or autonomous patient-care authority.</div>', unsafe_allow_html=True)
    st.markdown('<div class="fx-section">Author</div><div class="fx-sub"><strong>Ram Paragi</strong><br>rparag@lsuhsc.edu</div>', unsafe_allow_html=True)
    research_footer()
