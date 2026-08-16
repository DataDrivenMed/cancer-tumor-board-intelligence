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
from services.runtime_agents import configure_workflow_runtime


st.set_page_config(
    page_title="Tumor Board Intelligence",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
:root{
 --page:#f6f8fb;--surface:#fff;--surface2:#f0f4f8;--ink:#0b1220;--ink2:#293548;
 --muted:#687386;--line:#dbe3ed;--navy:#163b67;--blue:#2f6bff;--blueSoft:#edf3ff;
 --ok:#16775a;--okBg:#eaf7f1;--warn:#956400;--warnBg:#fff6df;--bad:#b42318;--badBg:#fff0ee;
 --shadow:0 8px 28px rgba(15,23,42,.055);--r:12px;
}
html,body,[class*=css]{font-family:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;}
.stApp{background:radial-gradient(circle at 90% 0%,rgba(47,107,255,.045),transparent 30rem),var(--page);color:var(--ink);}
[data-testid="stSidebar"],[data-testid="collapsedControl"]{display:none!important;}
[data-testid="stHeader"]{background:transparent;}
.block-container{max-width:1320px;padding:1.1rem 1.8rem 4rem;}
.ws-top{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line);padding:0 0 14px;margin-bottom:0;}
.ws-brand{display:flex;gap:10px;align-items:center}.ws-mark{width:30px;height:30px;border-radius:8px;background:linear-gradient(145deg,var(--navy),#0b2747);color:#fff;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800}.ws-name{font-size:16px;font-weight:700;letter-spacing:-.025em}.ws-sub{font-size:10px;color:var(--muted);margin-top:2px}.ws-ready{font-size:11px;color:var(--muted)}
.ws-nav{min-height:61px;padding:11px 8px 9px;border-bottom:2px solid transparent}.ws-nav.active{border-bottom-color:var(--blue)}.ws-nav.done{border-bottom-color:rgba(22,119,90,.42)}.ws-num{font-size:9px;font-weight:750;letter-spacing:.1em;color:#8994a5}.ws-label{font-size:12px;font-weight:600;color:var(--ink2);margin-top:4px}.ws-nav.active .ws-label{font-weight:750;color:var(--ink)}
.ws-hero{padding:30px 0 22px;max-width:860px}.ws-eye{font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--blue);font-weight:800;margin-bottom:9px}.ws-hero h1{font-size:38px;line-height:1.08;letter-spacing:-1.05px;font-weight:550;margin:0;color:var(--ink)}.ws-hero p{font-size:14px;line-height:1.55;color:var(--muted);max-width:760px;margin:11px 0 0}
.ws-card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:15px;box-shadow:0 1px 2px rgba(15,23,42,.025);margin-bottom:10px}.ws-card.raised{box-shadow:var(--shadow)}.ws-card.soft{background:var(--surface2);box-shadow:none}.ws-title{font-size:14px;font-weight:700;letter-spacing:-.1px}.ws-copy{font-size:11px;line-height:1.5;color:var(--muted);margin-top:4px}.ws-section{font-size:19px;font-weight:700;letter-spacing:-.35px;margin:9px 0 4px}.ws-section-sub{font-size:11px;color:var(--muted);margin-bottom:11px}
.ws-call{background:var(--blueSoft);border:1px solid #d8e4ff;border-radius:var(--r);padding:11px 13px;font-size:11px;line-height:1.5;color:#405475;margin-bottom:16px}
.facts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:5px 0 12px}.fact{background:#fff;border:1px solid var(--line);border-radius:var(--r);padding:12px 13px;min-height:73px}.fl{font-size:9px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);font-weight:750}.fv{font-size:14px;line-height:1.3;font-weight:650;margin-top:6px}.source{font-size:9px;color:var(--ok);margin-top:5px;font-weight:650}
.chip{display:inline-flex;padding:4px 8px;border-radius:999px;font-size:9px;font-weight:750;margin:2px 4px 2px 0}.ok{background:var(--okBg);color:var(--ok)}.warn{background:var(--warnBg);color:var(--warn)}.bad{background:var(--badBg);color:var(--bad)}.neutral{background:#edf1f6;color:#5d6878}
.decision{background:#fff;border:1px solid var(--line);border-radius:16px;padding:18px;box-shadow:var(--shadow);margin-bottom:11px}.decision-label{font-size:9px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);font-weight:800}.decision-title{font-size:24px;line-height:1.14;font-weight:700;letter-spacing:-.5px;margin:7px 0 8px}.reason{padding:11px 12px;border-radius:10px;background:#fff;border:1px solid var(--line);margin:7px 0}.reason strong{font-size:11px}.reason div{font-size:10px;color:var(--muted);margin-top:3px;line-height:1.45}
.stButton>button,.stDownloadButton>button,[data-testid=stFormSubmitButton] button{min-height:40px;border-radius:8px!important;border:1px solid #cbd5e1!important;background:#fff!important;color:var(--ink2)!important;font-size:12px!important;font-weight:650!important;box-shadow:none!important}.stButton>button[kind=primary],[data-testid=stFormSubmitButton] button[kind=primary]{background:var(--navy)!important;border-color:var(--navy)!important;color:#fff!important}.stButton>button:hover,.stDownloadButton>button:hover{border-color:#9eacc0!important;background:#f8fafc!important}
.stTextInput input,.stTextArea textarea,.stSelectbox [data-baseweb=select]>div,.stNumberInput input,[data-testid=stFileUploader] section{border-radius:8px!important;border-color:var(--line)!important;background:#fff!important;box-shadow:none!important}.stTextInput label,.stTextArea label,.stSelectbox label,.stNumberInput label{font-size:11px!important;color:var(--ink2)!important}.stTabs [data-baseweb=tab-list]{gap:3px;border-bottom:1px solid var(--line)}.stTabs [data-baseweb=tab]{font-size:11px;padding:9px 11px}[data-testid=stExpander]{border:1px solid var(--line)!important;border-radius:10px!important;background:#fff!important}
@media(max-width:850px){.block-container{padding-left:14px;padding-right:14px}.facts{grid-template-columns:repeat(2,1fr)}.ws-hero h1{font-size:32px}}@media(max-width:560px){.facts{grid-template-columns:1fr}.ws-ready{display:none}}
</style>
""",
    unsafe_allow_html=True,
)


STATUS_LABELS = {
    "pass": "Passed", "ready": "Ready", "block": "Cannot proceed", "blocked": "Cannot proceed",
    "source_unavailable": "Source not available", "verification_failed": "Verification failed",
    "completed": "Completed", "completed_with_limitations": "Completed with limitations",
    "no_evidence_found": "No verified match", "escalate_human": "Clinician review required",
    "abstain": "No recommendation issued", "clear": "Clear", "conditional": "Conditional",
}


def val(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def txt(value: Any) -> str:
    if value is None:
        return "Not available"
    if hasattr(value, "value"):
        value = value.value
    return str(value)


def human(value: Any) -> str:
    raw = txt(value)
    return STATUS_LABELS.get(raw.lower(), raw.replace("_", " ").title())


def tone(value: Any) -> str:
    raw = txt(value).lower()
    if raw in {"pass", "ready", "completed", "clear"}: return "ok"
    if raw in {"block", "blocked", "verification_failed", "tool_failure"}: return "bad"
    if raw in {"source_unavailable", "completed_with_limitations", "escalate_human", "abstain", "conditional"}: return "warn"
    return "neutral"


def chip(value: Any) -> str:
    return f'<span class="chip {tone(value)}">{escape(human(value))}</span>'


def secret(name: str, default: str | None = None) -> str | None:
    try:
        value = st.secrets[name]
        if value is not None:
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)


def sync_runtime_env() -> None:
    for name in [
        "PUBMED_EMAIL", "NCBI_API_KEY", "ENABLE_LIVE_PUBMED", "ENABLE_LIVE_CLINICALTRIALS",
        "GUIDELINE_EVIDENCE_JSON", "GUIDELINE_EVIDENCE_PATH", "MOLECULAR_EVIDENCE_JSON",
        "MOLECULAR_EVIDENCE_PATH", "SAFETY_EVIDENCE_JSON", "SAFETY_EVIDENCE_PATH",
        "TRANSLATIONAL_EVIDENCE_JSON", "TRANSLATIONAL_EVIDENCE_PATH",
    ]:
        value = secret(name)
        if value:
            os.environ[name] = value


def topbar() -> None:
    st.markdown('<div class="ws-top"><div class="ws-brand"><div class="ws-mark">TB</div><div><div class="ws-name">Tumor Board Intelligence</div><div class="ws-sub">Evidence-grounded clinical decision-support workspace</div></div></div><div class="ws-ready">Research decision support · de-identified or synthetic data only</div></div>', unsafe_allow_html=True)


def nav(stage: str) -> None:
    items = [("intake","Case intake"),("review","Review"),("analysis","Analysis"),("brief","Decision brief")]
    current = [x[0] for x in items].index(stage)
    cols = st.columns(4, gap="small")
    for i, (key, label) in enumerate(items):
        cls = " done" if i < current else (" active" if i == current else "")
        with cols[i]:
            st.markdown(f'<div class="ws-nav{cls}"><div class="ws-num">0{i+1}</div><div class="ws-label">{label}</div></div>', unsafe_allow_html=True)


def hero(eye: str, title: str, copy: str) -> None:
    st.markdown(f'<div class="ws-hero"><div class="ws-eye">{escape(eye)}</div><h1>{escape(title)}</h1><p>{escape(copy)}</p></div>', unsafe_allow_html=True)


def source_ok(fact: Any) -> bool:
    prov = val(fact, "provenance", []) or []
    return any(bool(val(p, "source_verified", False)) for p in prov)


def fact(label: str, value: Any, verified: bool | None = None) -> str:
    source = ""
    if verified is True: source = '<div class="source">Verified source trace</div>'
    elif verified is False: source = '<div class="source" style="color:#956400">Source review required</div>'
    return f'<div class="fact"><div class="fl">{escape(label)}</div><div class="fv">{escape(txt(value))}</div>{source}</div>'


def case_summary(case: CancerTumorBoardCase) -> None:
    mol = case.molecular_findings[0] if case.molecular_findings else None
    mol_text = "Not documented"
    mol_verified = None
    if mol:
        mol_text = " ".join(x for x in [mol.gene, mol.alteration_type] if x)
        if mol.variant_allele_frequency is not None:
            mol_text += f" · VAF {mol.variant_allele_frequency*100:.0f}%"
        mol_verified = source_ok(mol)
    st.markdown(
        '<div class="facts">'
        + fact("Diagnosis", case.diagnosis.value, source_ok(case.diagnosis))
        + fact("Disease state", case.disease_state.value, source_ok(case.disease_state))
        + fact("Molecular", mol_text, mol_verified)
        + fact("Age", case.age)
        + fact("Sex", case.sex)
        + fact("ECOG", case.performance_status.value if case.performance_status else None, source_ok(case.performance_status) if case.performance_status else None)
        + '</div>', unsafe_allow_html=True)
    tx = case.treatments[-1] if case.treatments else None
    c1, c2 = st.columns(2, gap="small")
    with c1:
        st.markdown(f'<div class="ws-card soft"><div class="ws-title">Most recent represented treatment</div><div class="ws-copy">{escape(tx.regimen if tx else "Not documented")}</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="ws-card soft"><div class="ws-title">Tumor board question</div><div class="ws-copy">{escape(case.clinical_question.question)}</div></div>', unsafe_allow_html=True)


def load_synthetic() -> CancerTumorBoardCase:
    payload = json.loads((PROJECT_ROOT / "synthetic_cases" / "syn_aml_001.json").read_text(encoding="utf-8"))
    return CancerTumorBoardCase.model_validate(payload)


def reset() -> None:
    for key in ["stage","case","raw_extraction","result","extraction_package","runtime_status"]:
        st.session_state.pop(key, None)
    st.rerun()


for key, default in {"stage":"intake","case":None,"raw_extraction":None,"result":None,"extraction_package":None,"runtime_status":None}.items():
    if key not in st.session_state: st.session_state[key] = default

sync_runtime_env()
# Configure on every Streamlit rerun so deployment secrets set before execution are honored.
st.session_state.runtime_status = configure_workflow_runtime()

topbar(); nav(st.session_state.stage)

if st.session_state.stage == "intake":
    hero("Case intake", "Build a decision-ready tumor board case.", "Start from a provenance-bearing synthetic case, a de-identified narrative, or an uploaded document. Structured review always precedes analysis.")
    st.markdown('<div class="ws-call">Patient facts are not treated as clinical truth merely because an AI extracted them. Source provenance, deterministic integrity checks, clinician confirmation, evidence verification, challenge review, and abstention remain separate controls.</div>', unsafe_allow_html=True)
    left, right = st.columns([2.15,.85], gap="large")
    with left:
        tabs = st.tabs(["Paste narrative", "Upload document"])
        with tabs[0]:
            narrative = st.text_area("De-identified case narrative", height=210, placeholder="Paste a de-identified tumor-board summary...")
            if st.button("Extract and review", type="primary", use_container_width=True, key="extract_text"):
                token = secret("MODEL_AUTH_TOKEN") or secret("HF_TOKEN")
                model = secret("MODEL_NAME", "openai/gpt-oss-120b:fireworks-ai") or "openai/gpt-oss-120b:fireworks-ai"
                if not token: st.error("Model access is not configured. Add MODEL_AUTH_TOKEN in the deployment secret store.")
                elif not narrative.strip(): st.warning("Add a case narrative first.")
                else:
                    try:
                        package = extract_case_v25(document=parse_text(narrative), api_key=token, model=model, case_id="CASE-INTAKE-001")
                        st.session_state.case = package.case; st.session_state.raw_extraction = package.raw_extraction; st.session_state.extraction_package = package; st.session_state.stage = "review"; st.rerun()
                    except (ModelGatewayError, Exception) as exc:
                        st.error(f"Extraction could not complete safely: {exc}")
        with tabs[1]:
            upload = st.file_uploader("De-identified PDF, DOCX, TXT, or Markdown", type=["pdf","docx","txt","md"])
            if st.button("Parse, extract, and review", type="primary", use_container_width=True, key="extract_upload"):
                token = secret("MODEL_AUTH_TOKEN") or secret("HF_TOKEN")
                model = secret("MODEL_NAME", "openai/gpt-oss-120b:fireworks-ai") or "openai/gpt-oss-120b:fireworks-ai"
                if not token: st.error("Model access is not configured. Add MODEL_AUTH_TOKEN in the deployment secret store.")
                elif upload is None: st.warning("Choose a de-identified document first.")
                else:
                    try:
                        package = extract_case_v25(document=parse_upload(upload), api_key=token, model=model, case_id="CASE-UPLOAD-001")
                        st.session_state.case = package.case; st.session_state.raw_extraction = package.raw_extraction; st.session_state.extraction_package = package; st.session_state.stage = "review"; st.rerun()
                    except Exception as exc:
                        st.error(f"Document processing could not complete safely: {exc}")
    with right:
        st.markdown('<div class="ws-section">Quick validation</div><div class="ws-section-sub">Run the full workflow with a synthetic AML fixture that carries verified synthetic source traces.</div>', unsafe_allow_html=True)
        st.markdown('<div class="ws-card raised"><div class="ws-title">Synthetic relapsed AML</div><div class="ws-copy">68-year-old · ECOG 1 · FLT3-ITD · prior therapy represented</div><div style="margin-top:8px"><span class="chip neutral">Synthetic</span><span class="chip ok">Provenance attached</span></div></div>', unsafe_allow_html=True)
        if st.button("Load synthetic case", type="primary", use_container_width=True):
            st.session_state.case = load_synthetic(); st.session_state.raw_extraction = None; st.session_state.stage = "review"; st.rerun()
        with st.expander("Evidence readiness"):
            for name, status in st.session_state.runtime_status.items():
                ready = bool(status.get("ready", status.get("loaded", False)))
                st.markdown(f"**{name.replace('_',' ').title()}**  \\n{('Ready' if ready else 'Not configured / unavailable')}")
            st.caption("No API keys or secret values are displayed here.")

elif st.session_state.stage == "review":
    case = st.session_state.case
    if case is None: reset()
    hero("Clinical review", "Verify the structured case before analysis.", "Confirm only if this structured representation matches the available source information. Analysis remains downstream of this human review.")
    case_summary(case)
    if st.session_state.extraction_package is not None:
        p = st.session_state.extraction_package
        st.markdown(f'<div class="ws-call">Extraction provenance: {p.provenance_verified}/{p.provenance_total} verified anchors. Diagnostic certainty: {escape(str(p.diagnostic_certainty))}. Any extraction warning remains available in the audit output.</div>', unsafe_allow_html=True)
    st.markdown('<div class="ws-card"><div class="ws-title">Ready for confirmation</div><div class="ws-copy">Confirming this case does not validate a diagnosis or treatment. It only confirms that the structured case accurately represents the available information.</div></div>', unsafe_allow_html=True)
    b1,b2 = st.columns([.8,1.2], gap="small")
    with b1:
        if st.button("Return to intake", use_container_width=True): reset()
    with b2:
        if st.button("Confirm and analyze", type="primary", use_container_width=True):
            st.session_state.stage="analysis"; st.rerun()

elif st.session_state.stage == "analysis":
    hero("Analysis", "Assembling and challenging the evidence stack.", "Case integrity, information completeness, specialist evidence channels, challenge review, consensus gates, and the final presentation layer remain distinct.")
    with st.spinner("Running deterministic gates and configured evidence channels..."):
        try:
            st.session_state.result = run_workflow(st.session_state.case, raw_extraction=st.session_state.raw_extraction)
            st.session_state.stage = "brief"; st.rerun()
        except Exception as exc:
            st.error(f"The workflow stopped safely because analysis could not complete: {exc}")
            if st.button("Return to case review"): st.session_state.stage="review"; st.rerun()

else:
    result = st.session_state.result or {}
    final = result.get("final_decision"); consensus = result.get("consensus_report"); integrity = result.get("case_integrity_report"); missing = result.get("missing_information_report"); red = result.get("red_team_report")
    decision = val(final,"decision_state",val(consensus,"decision_state","abstain"))
    hero("Decision brief", "A structured view of the decision state and supporting evidence.", "Evidence availability, challenge findings, consensus, uncertainty, and abstention are made visible rather than compressed into a single answer.")
    l,r = st.columns([.92,1.58], gap="large")
    with l:
        st.markdown(f'<div class="decision"><div class="decision-label">Decision state</div><div class="decision-title">{escape(human(decision))}</div>{chip(val(consensus,"status",decision))}<div class="ws-copy" style="margin-top:8px">{escape(txt(val(consensus,"summary",val(final,"abstention_reason","Decision-support state generated from current evidence."))))}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ws-card"><div class="ws-title">Case quality</div><div style="margin-top:6px">{chip(val(integrity,"disposition","not available"))}</div><div class="ws-copy">Critical findings: {escape(txt(val(integrity,"critical_count",0)))}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="ws-card"><div class="ws-title">Information completeness</div><div style="margin-top:6px">{chip(val(missing,"disposition","not available"))}</div><div class="ws-copy">{escape(txt(val(missing,"summary","No summary available")))}</div></div>', unsafe_allow_html=True)
        if red:
            st.markdown(f'<div class="ws-card"><div class="ws-title">Challenge review</div><div style="margin-top:6px">{chip(val(red,"status",val(red,"disposition")))}</div><div class="ws-copy">Blocking findings: {escape(txt(val(red,"blocking_count",0)))}</div></div>', unsafe_allow_html=True)
    with r:
        st.markdown('<div class="ws-section">Evidence availability</div><div class="ws-section-sub">Channel status is shown independently from clinical recommendation status.</div>', unsafe_allow_html=True)
        outputs = result.get("specialist_outputs", {}) or {}
        labels = [("guideline","Guidelines"),("molecular","Molecular evidence"),("literature","Current literature"),("clinical_trials","Clinical trials"),("safety","Safety evidence"),("translational","Translational evidence")]
        for key,label in labels:
            obj = outputs.get(key)
            status = val(obj,"status","not selected") if obj else "not selected"
            summary = val(obj,"summary","This evidence channel did not produce an output for the current route.") if obj else "This evidence channel did not produce an output for the current route."
            st.markdown(f'<div class="ws-card"><div style="display:flex;justify-content:space-between;gap:12px"><div><div class="ws-title">{label}</div><div class="ws-copy">{escape(txt(summary))}</div></div><div>{chip(status)}</div></div></div>', unsafe_allow_html=True)
    tabs=st.tabs(["Decision brief","Challenge review","Evidence","Case QA","Audit"])
    with tabs[0]:
        brief=result.get("tumor_board_brief")
        if brief:
            st.markdown(f'<div class="ws-section">Tumor board intelligence brief</div><div class="ws-section-sub">{escape(txt(val(brief,"summary","")))}</div>', unsafe_allow_html=True)
            for section in val(brief,"sections",[]) or []:
                with st.expander(txt(val(section,"title","Section")), expanded=txt(val(section,"section_id","")) in {"management_strategy","what_changes_recommendation"}):
                    for item in val(section,"items",[]) or []:
                        st.markdown(f"**{txt(val(item,'label',''))}**  \\n{txt(val(item,'value',''))}")
                        limits=val(item,"limitations",[]) or []
                        if limits: st.caption(" · ".join(txt(x) for x in limits))
        else: st.info("No structured brief is available for this workflow state.")
    with tabs[1]:
        if not red: st.info("Challenge review was not reached because an earlier safety gate stopped the workflow.")
        else:
            findings=val(red,"findings",[]) or []
            blocking=[f for f in findings if bool(val(f,"recommendation_blocking",False))]
            other=[f for f in findings if not bool(val(f,"recommendation_blocking",False))]
            st.markdown('<div class="ws-section">Recommendation-blocking findings</div>', unsafe_allow_html=True)
            if not blocking: st.success("No recommendation-blocking challenge findings remain.")
            for f in blocking:
                issue=txt(val(f,"issue","Evidence boundary requires review")); effect=txt(val(f,"effect_on_recommendation","Recommendation synthesis cannot proceed."))
                issue=issue.replace("Specialist 'guideline'", "Required guideline evidence").replace("Specialist 'molecular'", "Required molecular evidence").replace("Specialist 'safety'", "Required safety evidence")
                st.markdown(f'<div class="reason"><strong>{escape(issue)}</strong><div>{escape(effect)}</div></div>', unsafe_allow_html=True)
            if other:
                st.markdown('<div class="ws-section">Nonblocking limitations</div>', unsafe_allow_html=True)
                for f in other: st.markdown(f'<div class="reason"><strong>{escape(txt(val(f,"issue","Limitation")))}</strong><div>{escape(txt(val(f,"effect_on_recommendation","")))}</div></div>', unsafe_allow_html=True)
    with tabs[2]:
        for key,label in labels:
            obj=outputs.get(key)
            if obj:
                st.markdown(f"### {label}"); st.markdown(chip(val(obj,"status","not available")),unsafe_allow_html=True); st.write(val(obj,"summary",""))
                with st.expander("Structured details"): st.json(obj.model_dump(mode="json") if hasattr(obj,"model_dump") else obj)
    with tabs[3]:
        st.markdown("### Case integrity"); st.markdown(chip(val(integrity,"disposition","not available")),unsafe_allow_html=True)
        if integrity: st.write(f"Checks passed: {val(integrity,'checks_passed',0)} / {val(integrity,'checks_run',0)} · Critical: {val(integrity,'critical_count',0)}")
        st.markdown("### Missing information"); st.markdown(chip(val(missing,"disposition","not available")),unsafe_allow_html=True); st.write(val(missing,"summary",""))
    with tabs[4]:
        st.caption("Reasoning chain-of-thought is not stored or displayed. This audit view contains structured state, source status, and workflow events only.")
        with st.expander("Evidence runtime configuration"):
            st.json(st.session_state.runtime_status)
        with st.expander("Audit events"):
            events=result.get("audit_events",[]) or []
            st.json([e.model_dump(mode="json") if hasattr(e,"model_dump") else e for e in events])
    st.markdown("<br>",unsafe_allow_html=True)
    x1,x2=st.columns([.8,1.2],gap="small")
    with x1:
        if st.button("Start new case",use_container_width=True): reset()
    with x2:
        serial={k:(v.model_dump(mode="json") if hasattr(v,"model_dump") else v) for k,v in result.items()}
        st.download_button("Download structured result",data=json.dumps(serial,indent=2,default=str),file_name="tumor_board_result.json",mime="application/json",use_container_width=True)
    st.caption("Clinical trial matching does not establish eligibility. This research system is decision support, not an autonomous treatment directive, and has not been clinically validated for patient care.")
