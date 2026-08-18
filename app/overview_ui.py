from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from app.chat_ui import render_governed_chat
from app.faculty_ui import faculty_css, research_footer, top_navigation
from app.xai_theme import inject_xai_theme

PRODUCT_NAME = "Pan-Oncology Tumor Board Intelligence"


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
    question = _txt(_val(getattr(case, "clinical_question", None), "question", None))
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
        "question": question,
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
    inject_xai_theme()
    top_navigation("overview")

    st.markdown(
        """
<style>
.ov-shell{max-width:1200px;margin:0 auto}
.ov-hero{padding:58px 0 48px;border-bottom:1px solid var(--x-hair)}
.ov-kicker{font-size:11px;margin-bottom:14px}.ov-hero h1{font-size:68px!important;line-height:1.03!important;letter-spacing:-2.0px!important;margin:0!important;max-width:980px}.ov-lede{font-size:18px;line-height:1.55;color:var(--x-body);max-width:860px;margin:20px 0 0}.ov-hero-note{font-size:13px;line-height:1.55;color:var(--x-muted);max-width:820px;margin-top:12px}
.ov-section{font-size:36px!important;line-height:1.15!important;letter-spacing:-.72px!important;margin:0 0 10px!important}.ov-sub{font-size:15px;line-height:1.6;color:var(--x-body);max-width:840px;margin:0 0 22px}.ov-band{padding:70px 0;border-bottom:1px solid var(--x-hair)}
.ov-grid2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.ov-grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.ov-grid5{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}
.ov-card{background:#fff;border:1px solid var(--x-hair);border-radius:12px;padding:22px}.ov-card h3{font-size:18px!important;line-height:1.35!important;font-weight:600!important;margin:0 0 8px!important}.ov-card p{font-size:14px;line-height:1.55;color:var(--x-body);margin:0}.ov-card .ov-label{font-size:10px;margin-bottom:12px;color:var(--x-muted)}
.ov-agents{background:#fff;border:1px solid var(--x-hair);border-radius:12px;padding:24px;display:grid;grid-template-columns:.92fr 1.08fr;gap:28px;align-items:start}.ov-agents h3{font-size:26px!important;line-height:1.25!important;letter-spacing:-.32px!important;margin:0 0 10px!important}.ov-agents p{font-size:15px;line-height:1.6;color:var(--x-body);margin:0}.ov-agent-list{display:grid;grid-template-columns:1fr 1fr;gap:8px}.ov-agent-item{background:var(--x-canvas-soft);border:1px solid var(--x-hair-soft);border-radius:8px;padding:11px}.ov-agent-item strong{font-size:12px;color:var(--x-ink);display:block}.ov-agent-item span{font-size:11px;line-height:1.45;color:var(--x-muted);display:block;margin-top:3px}
.ov-timeline{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:18px 0 6px}.ov-pill{display:inline-flex;align-items:center;justify-content:center;padding:6px 11px;border-radius:9999px;color:var(--x-ink);font:600 10px/1.2 "JetBrains Mono",ui-monospace,monospace;text-transform:uppercase;letter-spacing:.08em}.thinking{background:var(--x-thinking)}.grep{background:var(--x-grep)}.read{background:var(--x-read)}.edit{background:var(--x-edit)}.done{background:var(--x-done);color:#fff}.ov-arrow{color:var(--x-muted);font-size:14px}
.ov-step{background:#fff;border:1px solid var(--x-hair);border-radius:12px;padding:18px;min-height:160px}.ov-step-num{font:600 10px/1.2 "JetBrains Mono",monospace;color:var(--x-primary);letter-spacing:.08em;margin-bottom:16px}.ov-step strong{font-size:16px;color:var(--x-ink);display:block}.ov-step span{font-size:12px;line-height:1.5;color:var(--x-body);display:block;margin-top:7px}
.ov-clinician{background:var(--x-ink);border-radius:12px;padding:25px;color:var(--x-canvas)}.ov-clinician h3{color:var(--x-canvas)!important;font-size:26px!important;margin:0 0 9px!important}.ov-clinician p{color:#d8d5cc;font-size:14px;line-height:1.6;margin:0}.ov-clinician-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:18px}.ov-clinician-item{border:1px solid rgba(255,255,255,.16);border-radius:8px;padding:12px}.ov-clinician-item strong{color:#fff;display:block;font-size:12px}.ov-clinician-item span{color:#c8c5bc;font-size:10px;line-height:1.45;display:block;margin-top:4px}
.ov-safeguard{display:flex;gap:12px;align-items:flex-start;padding:15px 0;border-bottom:1px solid var(--x-hair)}.ov-safeguard:last-child{border-bottom:0}.ov-safeguard-index{width:26px;height:26px;flex:none;border-radius:9999px;background:var(--x-canvas-soft);border:1px solid var(--x-hair);display:grid;place-items:center;font:600 9px/1 "JetBrains Mono",monospace;color:var(--x-muted)}.ov-safeguard strong{font-size:14px;color:var(--x-ink);display:block}.ov-safeguard span{font-size:12px;line-height:1.5;color:var(--x-body);display:block;margin-top:3px}
.ov-preview{background:#fff;border:1px solid var(--x-hair);border-radius:12px;overflow:hidden}.ov-preview-head{padding:16px 18px;border-bottom:1px solid var(--x-hair);display:flex;justify-content:space-between;gap:12px;align-items:center}.ov-preview-head strong{font-size:15px;color:var(--x-ink)}.ov-preview-head span{font-size:10px;color:var(--x-muted)}.ov-preview-grid{display:grid;grid-template-columns:repeat(2,1fr)}.ov-preview-cell{padding:16px 18px;border-bottom:1px solid var(--x-hair-soft)}.ov-preview-cell:nth-child(odd){border-right:1px solid var(--x-hair-soft)}.ov-preview-cell span{display:block;font:600 9px/1.3 "JetBrains Mono",monospace;text-transform:uppercase;letter-spacing:.07em;color:var(--x-muted)}.ov-preview-cell strong{display:block;font-size:14px;line-height:1.4;color:var(--x-ink);margin-top:6px;font-weight:500}.ov-empty{padding:18px;font-size:13px;line-height:1.6;color:var(--x-body);background:var(--x-canvas-soft)}
.ov-assistant-wrap{position:sticky;top:78px}.ov-assistant-intro{background:#fff;border:1px solid var(--x-hair);border-radius:12px;padding:18px;margin-bottom:10px}.ov-assistant-intro h3{font-size:22px!important;margin:0!important}.ov-assistant-intro p{font-size:12px;line-height:1.55;color:var(--x-body);margin:7px 0 0}.ov-assistant-state{margin-top:10px;padding:10px;border-radius:8px;background:var(--x-canvas-soft);border:1px solid var(--x-hair-soft);font-size:11px;line-height:1.5;color:var(--x-muted)}
.ov-cta{padding:64px 0 20px;text-align:center}.ov-cta h2{font-size:36px!important;letter-spacing:-.72px!important;margin:0 0 10px!important}.ov-cta p{font-size:14px;color:var(--x-body);margin:0 auto 18px;max-width:720px}
@media(max-width:1050px){.ov-grid5{grid-template-columns:repeat(2,1fr)}.ov-grid3{grid-template-columns:1fr}.ov-agents{grid-template-columns:1fr}.ov-clinician-grid{grid-template-columns:1fr}.ov-hero h1{font-size:54px!important}}
@media(max-width:700px){.ov-grid2,.ov-preview-grid,.ov-agent-list,.ov-grid5{grid-template-columns:1fr}.ov-preview-cell:nth-child(odd){border-right:0}.ov-hero{padding-top:34px}.ov-hero h1{font-size:38px!important}.ov-band{padding:48px 0}}
</style>
""",
        unsafe_allow_html=True,
    )

    case = st.session_state.get("case")
    result = st.session_state.get("result") or {}
    case_snapshot = _case_snapshot(case) if case is not None else None
    result_snapshot = _result_snapshot(result) if result else None

    main, assistant = st.columns([2.5, 1.0], gap="large")

    with main:
        st.markdown(
            '<div class="ov-shell"><section class="ov-hero">'
            '<div class="ov-kicker">Multidisciplinary cancer decision support</div>'
            '<h1>Bring the case, the evidence, and the challenge into one reviewable workflow.</h1>'
            '<div class="ov-lede">Pan-Oncology Tumor Board Intelligence is a research decision-support workspace designed to help a multidisciplinary tumor board structure a complex case, identify what is missing, review distinct evidence channels, challenge the emerging synthesis, and prepare an auditable brief for discussion.</div>'
            '<div class="ov-hero-note">It does not replace the tumor board, make autonomous treatment decisions, or turn an AI response into clinical truth. The goal is to make the information around multidisciplinary judgment easier to review.</div>'
            '</section></div>',
            unsafe_allow_html=True,
        )

        cta1, cta2, cta3 = st.columns([1.1, 1.35, 1.2], gap="small")
        with cta1:
            st.page_link("pages/00_Clinical_Workspace.py", label="Start a new case", use_container_width=True)
        with cta2:
            st.page_link("pages/00_Clinical_Workspace.py", label="Try the synthetic demonstration", use_container_width=True)
        with cta3:
            st.page_link("pages/03_Architecture.py", label="See how the agents work", use_container_width=True)

        st.markdown(
            '<section class="ov-band"><div class="ov-kicker">Why this may help</div><h2 class="ov-section">Tumor boards already integrate many kinds of expertise. The software should do the same without hiding the boundaries.</h2>'
            '<p class="ov-sub">The platform is organized around common tumor-board friction points: information scattered across the case, decision-critical gaps, different evidence types being mixed together, current literature and trial retrieval, and the need to see what could weaken or change a proposed management direction.</p>'
            '<div class="ov-grid3">'
            '<div class="ov-card"><div class="ov-label">Before discussion</div><h3>Structure the case</h3><p>Bring diagnosis, disease state, stage when explicitly represented, treatment history, molecular findings, performance status, and the clinical question into one source-traced case view.</p></div>'
            '<div class="ov-card"><div class="ov-label">During review</div><h3>Keep evidence channels distinct</h3><p>Guidelines, molecular evidence, literature, clinical trials, safety, and translational biology remain separately labeled so one source type does not silently substitute for another.</p></div>'
            '<div class="ov-card"><div class="ov-label">Before synthesis</div><h3>Challenge what looks persuasive</h3><p>Missing information, conflicts, unsupported leaps, and recommendation-blocking weaknesses are surfaced before the system presents a consensus state.</p></div>'
            '</div></section>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<section class="ov-band"><div class="ov-kicker">New concept: AI agents</div><div class="ov-agents"><div><h3>What is an AI agent in this system?</h3><p>Instead of asking one AI model to do everything, the tumor-board task is divided into specialized agents with defined jobs. One agent may check whether the represented case is internally consistent. Another identifies missing information. Others review a bounded evidence channel. A separate challenge step looks for weaknesses before consensus. The agents share the governed case state, but they do not independently make the final clinical decision.</p>'
            '<div class="ov-timeline"><span class="ov-pill thinking">Case</span><span class="ov-arrow">→</span><span class="ov-pill grep">Verify</span><span class="ov-arrow">→</span><span class="ov-pill read">Evidence</span><span class="ov-arrow">→</span><span class="ov-pill edit">Specialists</span><span class="ov-arrow">→</span><span class="ov-pill thinking">Challenge</span><span class="ov-arrow">→</span><span class="ov-pill done">Consensus</span></div></div>'
            '<div class="ov-agent-list">'
            '<div class="ov-agent-item"><strong>Case integrity</strong><span>Checks the represented case before reasoning proceeds.</span></div>'
            '<div class="ov-agent-item"><strong>Missing information</strong><span>Identifies absent, pending, or conflicting facts that may matter.</span></div>'
            '<div class="ov-agent-item"><strong>Evidence specialists</strong><span>Review governed guideline, molecular, literature, trial, safety, and translational channels.</span></div>'
            '<div class="ov-agent-item"><strong>Clinical Red Team</strong><span>Challenges assumptions, evidence sufficiency, and unsupported recommendation logic.</span></div>'
            '<div class="ov-agent-item"><strong>Consensus engine</strong><span>Synthesizes only after required gates and challenge review are satisfied.</span></div>'
            '<div class="ov-agent-item"><strong>Tumor board brief</strong><span>Presents the governed result without inventing new clinical claims.</span></div>'
            '</div></div></section>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<section class="ov-band"><div class="ov-kicker">How to use the application</div><h2 class="ov-section">Five steps from case intake to tumor-board brief.</h2><p class="ov-sub">Every stage of the workspace also includes a short “What to do here” instruction. You do not need to understand the technical architecture to use the workflow.</p>'
            '<div class="ov-grid5">'
            '<div class="ov-step"><div class="ov-step-num">01</div><strong>Add the case</strong><span>Use the synthetic demonstration, paste a de-identified narrative, or upload a supported de-identified document.</span></div>'
            '<div class="ov-step"><div class="ov-step-num">02</div><strong>Review what was captured</strong><span>Confirm that the structured case matches the source. Correct representation errors before continuing.</span></div>'
            '<div class="ov-step"><div class="ov-step-num">03</div><strong>Review evidence</strong><span>Inspect the retrieved bounded source candidates and attest only records you have actually reviewed.</span></div>'
            '<div class="ov-step"><div class="ov-step-num">04</div><strong>Run agent analysis</strong><span>The governed workflow checks integrity, missingness, specialist evidence, challenge findings, and consensus.</span></div>'
            '<div class="ov-step"><div class="ov-step-num">05</div><strong>Discuss the brief</strong><span>Review decision state, evidence, missing information, uncertainty, challenge findings, and what could change the conclusion.</span></div>'
            '</div></section>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<section class="ov-band"><div class="ov-clinician"><h3>What remains with the clinicians?</h3><p>The system is designed to organize and challenge information around multidisciplinary judgment. Clinical interpretation, patient-specific applicability, final recommendations, communication with the patient, and treatment decisions remain with the treating clinicians and tumor board.</p>'
            '<div class="ov-clinician-grid"><div class="ov-clinician-item"><strong>Verify the represented case</strong><span>The team decides whether the structured case accurately reflects the source record.</span></div><div class="ov-clinician-item"><strong>Judge applicability</strong><span>Retrieved evidence is not automatically applicable to the individual patient.</span></div><div class="ov-clinician-item"><strong>Make the clinical decision</strong><span>The brief supports discussion. It does not replace multidisciplinary judgment.</span></div></div></div></section>',
            unsafe_allow_html=True,
        )

        st.markdown('<section class="ov-band"><div class="ov-kicker">Current workspace preview</div><h2 class="ov-section">A readable snapshot before deeper review.</h2><p class="ov-sub">When a case is active, this area reflects the governed session state. When no case is loaded, it stays empty rather than showing demonstration data as if it were current clinical information.</p>', unsafe_allow_html=True)
        if case_snapshot:
            decision = result_snapshot["decision"] if result_snapshot else "Analysis not yet completed"
            missing = result_snapshot["missing"] if result_snapshot else "Run the governed workflow to classify decision-critical missing information."
            st.markdown(
                '<div class="ov-preview"><div class="ov-preview-head"><strong>Current case</strong><span>Session data</span></div><div class="ov-preview-grid">'
                f'<div class="ov-preview-cell"><span>Diagnosis</span><strong>{escape(case_snapshot["diagnosis"])}</strong></div>'
                f'<div class="ov-preview-cell"><span>Disease state</span><strong>{escape(case_snapshot["disease_state"])}</strong></div>'
                f'<div class="ov-preview-cell"><span>Molecular</span><strong>{escape(case_snapshot["molecular"])}</strong></div>'
                f'<div class="ov-preview-cell"><span>Decision state</span><strong>{escape(decision)}</strong></div>'
                f'<div class="ov-preview-cell"><span>Tumor board question</span><strong>{escape(case_snapshot["question"])}</strong></div>'
                f'<div class="ov-preview-cell"><span>Missing information</span><strong>{escape(missing)}</strong></div>'
                '</div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown('<div class="ov-preview"><div class="ov-empty">No active case. Open the Clinical Workspace to start a new case or use the synthetic demonstration to learn the workflow.</div></div>', unsafe_allow_html=True)
        st.markdown('</section>', unsafe_allow_html=True)

        st.markdown(
            '<section class="ov-band"><div class="ov-kicker">Scientific safeguards</div><h2 class="ov-section">The guardrails are part of the product, not a disclaimer at the end.</h2>'
            '<div class="ov-safeguard"><div class="ov-safeguard-index">01</div><div><strong>Source-grounded representation</strong><span>Confirmed extracted assertions require traceable source context.</span></div></div>'
            '<div class="ov-safeguard"><div class="ov-safeguard-index">02</div><div><strong>Missing information stays missing</strong><span>The system does not silently fill decision-critical gaps from model memory.</span></div></div>'
            '<div class="ov-safeguard"><div class="ov-safeguard-index">03</div><div><strong>Evidence channels remain distinct</strong><span>Guideline, molecular, literature, trial, safety, and translational evidence retain their own status and limitations.</span></div></div>'
            '<div class="ov-safeguard"><div class="ov-safeguard-index">04</div><div><strong>Challenge before consensus</strong><span>An explicit adversarial review step looks for conflicts, unsupported leaps, and recommendation-blocking weaknesses.</span></div></div>'
            '<div class="ov-safeguard"><div class="ov-safeguard-index">05</div><div><strong>Abstention is a valid output</strong><span>If the evidence or represented case cannot support synthesis, the system can stop rather than force a recommendation.</span></div></div>'
            '<div class="ov-safeguard"><div class="ov-safeguard-index">06</div><div><strong>Clinician judgment remains central</strong><span>The output is a decision-support artifact for multidisciplinary review, not autonomous oncology care.</span></div></div>'
            '</section>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<section class="ov-cta"><div class="ov-kicker">Explore further</div><h2>Use the workspace first. Open the architecture when you want the technical detail.</h2><p>The architecture page preserves the full interactive agent map, handoffs, safety boundaries, and click/hover explanations. Validation remains a separate question from software qualification.</p></section>',
            unsafe_allow_html=True,
        )
        a1, a2, a3 = st.columns(3, gap="small")
        with a1:
            st.page_link("pages/00_Clinical_Workspace.py", label="Enter Clinical Workspace", use_container_width=True)
        with a2:
            st.page_link("pages/03_Architecture.py", label="Explore Agent Architecture", use_container_width=True)
        with a3:
            st.page_link("pages/01_Validation.py", label="Review Validation Status", use_container_width=True)

    with assistant:
        st.markdown('<div class="ov-assistant-wrap"><div class="ov-assistant-intro"><div class="ov-kicker">Case-grounded assistant</div><h3>Ask Tumor Board</h3><p>This panel is intentionally not a general oncology chatbot. It becomes useful only when there is a governed case and analysis result to query.</p>', unsafe_allow_html=True)
        if case is not None and result:
            st.markdown('<div class="ov-assistant-state"><strong>Ready.</strong> Ask about the represented case, evidence, missing information, challenge findings, trials, safety, rationale, or what could change the decision.</div></div></div>', unsafe_allow_html=True)
            render_governed_chat(result, case, key_prefix="overview")
        elif case is not None:
            st.markdown('<div class="ov-assistant-state"><strong>Case loaded, analysis not complete.</strong> Continue through evidence review and agent analysis before using this panel for synthesis.</div></div></div>', unsafe_allow_html=True)
            st.page_link("pages/00_Clinical_Workspace.py", label="Continue the case", use_container_width=True)
        else:
            st.markdown('<div class="ov-assistant-state"><strong>Not active yet.</strong> Start a case or open the synthetic demonstration first. This prevents the assistant from appearing to answer outside the governed tumor-board workflow.</div></div></div>', unsafe_allow_html=True)
            st.page_link("pages/00_Clinical_Workspace.py", label="Open Clinical Workspace", use_container_width=True)

    research_footer()
