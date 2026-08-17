from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from app.chat_ui import render_governed_chat
from app.faculty_ui import faculty_css, research_footer, top_navigation


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


def _case_snapshot(case: Any) -> dict[str, str]:
    diagnosis = _txt(_val(getattr(case, "diagnosis", None), "value", None))
    disease_state = _txt(_val(getattr(case, "disease_state", None), "value", None))
    case_id = _txt(getattr(case, "case_id", None), "Current case")
    mols = getattr(case, "molecular_findings", []) or []
    molecular = "Not documented"
    if mols:
        first = mols[0]
        molecular = " ".join(
            x
            for x in [
                _txt(getattr(first, "gene", None), ""),
                _txt(getattr(first, "alteration_type", None), ""),
            ]
            if x
        ).strip() or "Documented"
    return {
        "diagnosis": diagnosis,
        "disease_state": disease_state,
        "case_id": case_id,
        "molecular": molecular,
    }


def _result_snapshot(result: dict[str, Any]) -> dict[str, str]:
    outputs = result.get("specialist_outputs", {}) or {}
    final = result.get("final_decision")
    consensus = result.get("consensus_report")
    red = result.get("red_team_report")
    missing = result.get("missing_information_report")
    decision = _txt(
        _val(final, "decision_state", _val(consensus, "decision_state", "Not available"))
    ).replace("_", " ").title()
    return {
        "decision": decision,
        "specialists": str(sum(1 for value in outputs.values() if value is not None)),
        "red_team": _txt(_val(red, "status", _val(red, "disposition", "Not reached"))).replace("_", " ").title(),
        "missing": _txt(_val(missing, "summary", "No missing-information summary is available.")),
    }


def render_final_overview() -> None:
    faculty_css()
    top_navigation("overview")

    st.markdown(
        """
<style>
:root{
  --ov-bg:#0a0a0a;--ov-panel:#111214;--ov-panel2:#151619;--ov-line:#292c31;
  --ov-ink:#f7f7f5;--ov-body:#c7c9ce;--ov-muted:#7f838b;--ov-green:#35b88a;
  --ov-blue:#3c8dde;--ov-rose:#d8587e;--ov-amber:#ca8514;--ov-teal:#239783;--ov-plum:#8d62c5;
}
.block-container{max-width:1780px!important;padding:1rem 1.3rem 3rem!important}
.ov-rail-title{font:500 10px/14px "Geist Mono","IBM Plex Mono",monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--ov-muted);margin:2px 0 9px}
.ov-rail-card{background:var(--ov-panel);border:1px solid var(--ov-line);border-radius:12px;padding:15px;margin-bottom:11px}
.ov-case-status{display:flex;justify-content:space-between;gap:8px;align-items:center;margin-bottom:12px}.ov-case-status b{font-size:11px;color:var(--ov-body);font-weight:500}.ov-live{display:inline-flex;align-items:center;gap:6px;font-size:10px;color:#9ce0c4}.ov-live:before{content:"";width:7px;height:7px;border-radius:999px;background:var(--ov-green);box-shadow:0 0 0 3px rgba(53,184,138,.10)}
.ov-case-name{font-size:22px;line-height:1.08;color:var(--ov-ink);letter-spacing:-.035em;margin-bottom:7px}.ov-case-meta{font-size:11px;color:var(--ov-muted);line-height:1.5}.ov-rail-copy{font-size:12px;line-height:1.55;color:var(--ov-body);margin:0}
.ov-status-line{display:flex;gap:9px;align-items:flex-start;padding:7px 0;border-bottom:1px solid #202226}.ov-status-line:last-child{border-bottom:0}.ov-status-dot{width:7px;height:7px;border-radius:50%;background:var(--ov-green);margin-top:5px;flex:none}.ov-status-line strong{font-size:11px;color:var(--ov-ink);font-weight:500;display:block}.ov-status-line span{font-size:10px;color:var(--ov-muted);display:block;margin-top:2px;line-height:1.4}
.ov-hero{padding:26px 0 22px;border-bottom:1px solid var(--ov-line);margin-bottom:18px}.ov-kicker{font:500 10px/14px "Geist Mono","IBM Plex Mono",monospace;letter-spacing:.14em;text-transform:uppercase;color:var(--ov-body);margin-bottom:10px}.ov-hero h1{font-size:58px!important;line-height:.98!important;letter-spacing:-2.25px!important;color:var(--ov-ink)!important;margin:0!important;font-weight:400!important}.ov-lede{font-size:15px;line-height:1.6;color:var(--ov-body);max-width:880px;margin-top:15px}.ov-badges{display:flex;gap:7px;flex-wrap:wrap;margin-top:15px}.ov-badge{display:inline-flex;padding:5px 9px;border-radius:999px;border:1px solid rgba(255,255,255,.22);font-size:10px;color:var(--ov-body)}
.ov-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;margin:0 0 18px}.ov-metric{background:var(--ov-panel);border:1px solid var(--ov-line);border-radius:11px;padding:14px;min-height:101px}.ov-metric .label{font:500 9px/13px "Geist Mono",monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--ov-muted)}.ov-metric .value{font-size:25px;color:var(--ov-ink);letter-spacing:-.6px;margin-top:9px}.ov-metric .note{font-size:10px;line-height:1.4;color:var(--ov-muted);margin-top:5px}
.ov-panel{background:var(--ov-panel);border:1px solid var(--ov-line);border-radius:12px;padding:16px;margin-bottom:12px}.ov-panel-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;margin-bottom:13px}.ov-panel-head h2{font-size:20px!important;letter-spacing:-.4px!important;margin:0!important;color:var(--ov-ink)!important}.ov-panel-head p{font-size:10px;line-height:1.45;color:var(--ov-muted);margin:4px 0 0}.ov-mini-label{font:500 9px/13px "Geist Mono",monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--ov-muted)}
.ov-flow{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:7px;align-items:stretch}.ov-node{position:relative;background:var(--ov-panel2);border:1px solid var(--ov-line);border-radius:10px;padding:11px;min-height:92px}.ov-node:after{content:"→";position:absolute;right:-10px;top:37px;color:#62666e;z-index:3}.ov-node:last-child:after{display:none}.ov-node .num{font:500 9px/12px "Geist Mono",monospace;color:var(--ov-muted);margin-bottom:10px}.ov-node strong{font-size:11px;line-height:1.35;color:var(--ov-ink);font-weight:500;display:block}.ov-node.blue{border-top:2px solid var(--ov-blue)}.ov-node.rose{border-top:2px solid var(--ov-rose)}.ov-node.amber{border-top:2px solid var(--ov-amber)}.ov-node.teal{border-top:2px solid var(--ov-teal)}.ov-node.plum{border-top:2px solid var(--ov-plum)}
.ov-lower{display:grid;grid-template-columns:1fr 1fr;gap:10px}.ov-summary-row{padding:9px 0;border-bottom:1px solid #22252a}.ov-summary-row:last-child{border-bottom:0}.ov-summary-row span{display:block;font:500 9px/12px "Geist Mono",monospace;text-transform:uppercase;letter-spacing:.08em;color:var(--ov-muted)}.ov-summary-row strong{display:block;font-size:13px;line-height:1.4;color:var(--ov-ink);font-weight:500;margin-top:4px}.ov-evidence-row{display:flex;justify-content:space-between;gap:9px;padding:10px 0;border-bottom:1px solid #22252a;align-items:center}.ov-evidence-row:last-child{border-bottom:0}.ov-evidence-row span{font-size:11px;color:var(--ov-body)}.ov-count{min-width:30px;text-align:center;border-radius:999px;border:1px solid #34373d;padding:3px 7px;font-size:9px;color:var(--ov-ink)}
.ov-assistant{background:var(--ov-panel);border:1px solid var(--ov-line);border-radius:12px;padding:14px;position:sticky;top:68px}.ov-assistant h3{font-size:21px!important;margin:0!important;color:var(--ov-ink)!important;font-weight:400!important}.ov-assistant-sub{font-size:11px;line-height:1.5;color:var(--ov-muted);margin:5px 0 12px}.ov-empty{background:#0f1012;border:1px solid #23262a;border-radius:10px;padding:12px;font-size:11px;line-height:1.55;color:var(--ov-body)}
[data-testid="stPageLink-NavLink"]{border-radius:999px!important;font-size:11px!important;min-height:36px!important;padding:.4rem .72rem!important}
@media(max-width:1180px){.ov-flow{grid-template-columns:repeat(3,1fr)}.ov-node:nth-child(3):after,.ov-node:last-child:after{display:none}.ov-metrics{grid-template-columns:repeat(2,1fr)}}
@media(max-width:900px){.ov-hero h1{font-size:44px!important}.ov-lower{grid-template-columns:1fr}.ov-flow{grid-template-columns:repeat(2,1fr)}.ov-node:after{display:none}}
</style>
""",
        unsafe_allow_html=True,
    )

    case = st.session_state.get("case")
    result = st.session_state.get("result") or {}
    case_snapshot = _case_snapshot(case) if case is not None else None
    result_snapshot = _result_snapshot(result) if result else None

    left, center, right = st.columns([0.78, 2.35, 1.02], gap="large")

    with left:
        st.markdown('<div class="ov-rail-title">Current case</div>', unsafe_allow_html=True)
        if case_snapshot:
            st.markdown(
                '<div class="ov-rail-card"><div class="ov-case-status"><b>CASE IN SESSION</b><span class="ov-live">Active</span></div>'
                f'<div class="ov-case-name">{escape(case_snapshot["diagnosis"])}</div>'
                f'<div class="ov-case-meta">{escape(case_snapshot["disease_state"])}<br>{escape(case_snapshot["case_id"])}</div></div>',
                unsafe_allow_html=True,
            )
            st.page_link("pages/00_Clinical_Workspace.py", label="View case workspace", use_container_width=True)
        else:
            st.markdown(
                '<div class="ov-rail-card"><div class="ov-case-status"><b>NO ACTIVE CASE</b></div>'
                '<p class="ov-rail-copy">Start in the clinical workspace or load the synthetic demonstration case. Nothing is inferred on this screen before a governed case exists.</p></div>',
                unsafe_allow_html=True,
            )
            st.page_link("pages/00_Clinical_Workspace.py", label="Start a case", use_container_width=True)

        st.markdown('<div class="ov-rail-title" style="margin-top:18px">Workspace</div>', unsafe_allow_html=True)
        st.page_link("pages/00_Clinical_Workspace.py", label="Clinical workspace", use_container_width=True)
        st.page_link("pages/03_Architecture.py", label="Architecture", use_container_width=True)
        st.page_link("pages/01_Validation.py", label="Validation", use_container_width=True)
        st.page_link("pages/02_About.py", label="Scientific scope", use_container_width=True)

        st.markdown('<div class="ov-rail-title" style="margin-top:18px">System status</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="ov-rail-card">'
            '<div class="ov-status-line"><div class="ov-status-dot"></div><div><strong>Research workspace</strong><span>Available for governed demonstration and faculty evaluation.</span></div></div>'
            '<div class="ov-status-line"><div class="ov-status-dot"></div><div><strong>Common-core qualification</strong><span>Synthetic architecture qualification passed.</span></div></div>'
            '<div class="ov-status-line"><div class="ov-status-dot" style="background:#ca8514"></div><div><strong>Clinical release</strong><span>Not established. Disease-specific clinical validation remains separate.</span></div></div>'
            '</div>',
            unsafe_allow_html=True,
        )

    with center:
        st.markdown(
            '<div class="ov-hero"><div class="ov-kicker">Governed multi-agent oncology intelligence</div>'
            '<h1>Pan-Oncology<br>Tumor Board Intelligence</h1>'
            '<div class="ov-lede">A multidisciplinary cancer-review workspace that keeps case representation, evidence retrieval, missingness, challenge, consensus, and final presentation visibly separate.</div>'
            '<div class="ov-badges"><span class="ov-badge">Pan-oncology</span><span class="ov-badge">Bounded evidence</span><span class="ov-badge">Clinical Red Team</span><span class="ov-badge">Human review</span><span class="ov-badge">Auditable outputs</span></div></div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="ov-metrics">'
            '<div class="ov-metric"><div class="label">Oncology programs</div><div class="value">14</div><div class="note">Registered disease programs</div></div>'
            '<div class="ov-metric"><div class="label">Specialist evidence agents</div><div class="value">6</div><div class="note">Guideline · Molecular · Literature · Translational · Trials · Safety</div></div>'
            '<div class="ov-metric"><div class="label">Common-core qualification</div><div class="value">Passed</div><div class="note">Synthetic software and architecture gate</div></div>'
            '<div class="ov-metric"><div class="label">Clinical release</div><div class="value">Research</div><div class="note">Disease-specific clinical validation remains future work</div></div>'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div class="ov-panel"><div class="ov-panel-head"><div><h2>Multi-agent architecture</h2><p>Compact workflow orientation. The Architecture page retains the complete interactive handoff map.</p></div><div class="ov-mini-label">Fail closed by design</div></div>'
            '<div class="ov-flow">'
            '<div class="ov-node blue"><div class="num">01-02</div><strong>Case intake<br>+ extraction</strong></div>'
            '<div class="ov-node rose"><div class="num">03-04</div><strong>Confirmation<br>+ correction</strong></div>'
            '<div class="ov-node amber"><div class="num">05-08</div><strong>Integrity<br>+ missingness</strong></div>'
            '<div class="ov-node blue"><div class="num">09</div><strong>Clinical<br>router</strong></div>'
            '<div class="ov-node teal"><div class="num">10A-10F</div><strong>Specialist<br>agents</strong></div>'
            '<div class="ov-node plum"><div class="num">11-15</div><strong>Join · Red Team<br>consensus · brief</strong></div>'
            '</div></div>',
            unsafe_allow_html=True,
        )
        st.page_link("pages/03_Architecture.py", label="Open full interactive architecture", use_container_width=True)

        if case_snapshot:
            specialist_count = result_snapshot["specialists"] if result_snapshot else "0"
            decision = result_snapshot["decision"] if result_snapshot else "Analysis not yet completed"
            challenge = result_snapshot["red_team"] if result_snapshot else "Not reached"
            missing = result_snapshot["missing"] if result_snapshot else "Run the governed workflow to classify decision-critical missing information."
            st.markdown(
                '<div class="ov-lower">'
                '<div class="ov-panel"><div class="ov-panel-head"><div><h2>30-second Tumor Board View</h2><p>Current represented case only.</p></div></div>'
                f'<div class="ov-summary-row"><span>Diagnosis</span><strong>{escape(case_snapshot["diagnosis"])}</strong></div>'
                f'<div class="ov-summary-row"><span>Disease state</span><strong>{escape(case_snapshot["disease_state"])}</strong></div>'
                f'<div class="ov-summary-row"><span>Molecular</span><strong>{escape(case_snapshot["molecular"])}</strong></div>'
                f'<div class="ov-summary-row"><span>Decision state</span><strong>{escape(decision)}</strong></div>'
                '</div>'
                '<div class="ov-panel"><div class="ov-panel-head"><div><h2>Governed analysis state</h2><p>These statuses are kept separate rather than collapsed into one score.</p></div></div>'
                f'<div class="ov-evidence-row"><span>Specialist outputs present</span><div class="ov-count">{escape(specialist_count)}</div></div>'
                f'<div class="ov-evidence-row"><span>Challenge review</span><div class="ov-count">{escape(challenge)}</div></div>'
                f'<div class="ov-summary-row"><span>Missing information</span><strong>{escape(missing)}</strong></div>'
                '</div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="ov-lower">'
                '<div class="ov-panel"><div class="ov-panel-head"><div><h2>30-second Tumor Board View</h2><p>Populates from the active governed case.</p></div></div><div class="ov-empty">No case has been loaded in this session. The overview intentionally remains empty rather than displaying demonstration values as if they were current patient facts.</div></div>'
                '<div class="ov-panel"><div class="ov-panel-head"><div><h2>Evidence state</h2><p>Channel-level evidence appears after case review and analysis.</p></div></div><div class="ov-empty">Guideline, molecular, literature, clinical-trial, safety, and translational outputs remain independently labeled once the workflow reaches them.</div></div>'
                '</div>',
                unsafe_allow_html=True,
            )

    with right:
        st.markdown('<div class="ov-assistant"><h3>Ask Tumor Board</h3><div class="ov-assistant-sub">Governed follow-up questions stay bounded to the structured case and available evidence.</div></div>', unsafe_allow_html=True)
        if case is not None and result:
            render_governed_chat(result, case, key_prefix="overview")
        elif case is not None:
            st.markdown(
                '<div class="ov-empty">A case is active, but governed analysis has not produced a result yet. Complete evidence review and analysis before asking the assistant to synthesize specialist outputs.</div>',
                unsafe_allow_html=True,
            )
            st.page_link("pages/00_Clinical_Workspace.py", label="Continue case analysis", use_container_width=True)
        else:
            st.markdown(
                '<div class="ov-empty">The assistant is disabled until a governed case exists. This prevents a general-purpose chat surface from appearing to provide oncology recommendations outside the case workflow.</div>',
                unsafe_allow_html=True,
            )
            st.page_link("pages/00_Clinical_Workspace.py", label="Open clinical workspace", use_container_width=True)

    research_footer()
