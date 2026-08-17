from __future__ import annotations

import streamlit as st

from app.architecture_ui import architecture_css
from app.faculty_ui import faculty_css, research_footer, top_navigation
from app.xai_theme import inject_xai_theme


def render_final_overview() -> None:
    faculty_css(); architecture_css(); inject_xai_theme(); top_navigation("overview")
    st.markdown(
        """
<style>
.ov-shell{padding-top:24px}
.ov-eyebrow{font:400 12px/16px "Geist Mono","IBM Plex Mono",monospace;letter-spacing:1.4px;text-transform:uppercase;color:#7d8187;margin-bottom:12px}
.ov-hero{padding:34px 0 30px;border-bottom:1px solid #212327;margin-bottom:26px}
.ov-hero h1{font-size:68px;line-height:.98;letter-spacing:-2.2px;color:#fff;margin:0;font-weight:400}.ov-author{font-size:14px;color:#dadbdf;margin-top:13px;text-transform:none!important;letter-spacing:0!important;font-family:Inter,system-ui!important}.ov-lede{font-size:18px;line-height:1.55;color:#dadbdf;max-width:960px;margin-top:18px}.ov-badges{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px}.ov-badge{display:inline-flex;padding:7px 12px;border-radius:9999px;border:1px solid rgba(255,255,255,.25);background:transparent;font-size:12px;color:#dadbdf}
.ov-metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:8px 0 28px}.ov-metric{border:1px solid #2a2d31;background:#141414;border-radius:8px;padding:18px 19px;min-height:118px}.ov-metric .label{font:400 11px/15px "Geist Mono","IBM Plex Mono",monospace;letter-spacing:1.15px;text-transform:uppercase;color:#7d8187}.ov-metric .value{font-size:31px;line-height:1.05;color:#fff;margin-top:10px;letter-spacing:-1px}.ov-metric .note{font-size:12px;color:#a7a9ad;margin-top:7px;line-height:1.4}
.ov-section{font-size:38px;line-height:1.05;letter-spacing:-1.2px;color:#fff;font-weight:400;margin:42px 0 8px}.ov-sub{font-size:15px;color:#dadbdf;line-height:1.55;max-width:980px;margin-bottom:15px}.ov-arch{display:grid;grid-template-columns:1fr 24px 1fr 24px 1.3fr 24px 1fr 24px 1fr;gap:8px;align-items:center;border:1px solid #2a2d31;border-radius:8px;padding:20px;background:#0d0d0d}.ov-node{border:1px solid #2a2d31;border-radius:8px;padding:15px;min-height:108px;background:#141414}.ov-node strong{display:block;font-size:15px;color:#fff;font-weight:400}.ov-node span{font-size:12px;line-height:1.45;color:#aeb1b6;display:block;margin-top:7px}.ov-node.spec{border-top:2px solid #239783}.ov-node.challenge{border-top:2px solid #8d62c5}.ov-node.output{border-top:2px solid #3c8dde}.ov-arrow{text-align:center;color:#7d8187;font-size:18px}.ov-safety{border:1px solid #2a2d31;background:#111;border-radius:8px;padding:15px 17px;margin-top:12px;font-size:13px;color:#c9cbd0;line-height:1.55}.ov-safety strong{color:#fff;font-weight:400}
.ov-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:14px 0 26px}.ov-card{border:1px solid #2a2d31;background:#141414;border-radius:8px;padding:18px;box-shadow:none}.ov-card .num{font:400 11px/15px "Geist Mono",monospace;color:#7d8187;letter-spacing:1.2px}.ov-card h3{font-size:19px;color:#fff;margin:10px 0 7px;font-weight:400}.ov-card p{font-size:13px;color:#b9bbc0;line-height:1.55;margin:0}
@media(max-width:950px){.ov-metrics,.ov-grid{grid-template-columns:repeat(2,1fr)}.ov-arch{grid-template-columns:1fr}.ov-arrow{transform:rotate(90deg)}}@media(max-width:600px){.ov-metrics,.ov-grid{grid-template-columns:1fr}.ov-hero h1{font-size:46px;letter-spacing:-1.4px}}
</style>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="ov-shell"><div class="ov-hero"><div class="ov-eyebrow">GOVERNED MULTI-AGENT ONCOLOGY INTELLIGENCE</div><h1>Pan-Oncology Tumor Board Intelligence</h1><div class="ov-author">Ram Paragi · rparag@lsuhsc.edu</div><div class="ov-lede">A governed multi-agent research decision-support platform for multidisciplinary cancer review. The system structures the case, detects missingness and conflicts, routes bounded evidence specialists, challenges the evidence stack before consensus, and produces an auditable tumor-board brief while preserving uncertainty and abstention.</div><div class="ov-badges"><span class="ov-badge">Pan-oncology</span><span class="ov-badge">Bounded evidence</span><span class="ov-badge">Clinical Red Team</span><span class="ov-badge">Human review</span><span class="ov-badge">Auditable outputs</span></div></div></div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="ov-metrics">'
        '<div class="ov-metric"><div class="label">Oncology programs</div><div class="value">14</div><div class="note">Registered pan-oncology disease programs</div></div>'
        '<div class="ov-metric"><div class="label">Specialist evidence agents</div><div class="value">6</div><div class="note">Guideline · Molecular · Literature · Translational · Trials · Safety</div></div>'
        '<div class="ov-metric"><div class="label">Common-core qualification</div><div class="value">Passed</div><div class="note">Synthetic software/architecture qualification gate</div></div>'
        '<div class="ov-metric"><div class="label">Clinical release</div><div class="value">Research</div><div class="note">Disease-specific clinical validation remains future work</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns([1,1,2], gap="small")
    with c1:
        st.page_link("pages/00_Clinical_Workspace.py", label="Enter Workspace", use_container_width=True)
    with c2:
        st.page_link("pages/03_Architecture.py", label="View Architecture", use_container_width=True)

    st.markdown('<div class="ov-section">Multi-agent architecture</div><div class="ov-sub">The system separates representation, gating, specialist evidence work, independent challenge, consensus, and final presentation. Open Architecture for the complete interactive handoff map.</div>', unsafe_allow_html=True)
    st.markdown('<div class="ov-arch"><div class="ov-node"><strong>Case representation</strong><span>Intake → extraction → human confirmation → integrity → missingness</span></div><div class="ov-arrow">→</div><div class="ov-node"><strong>Routing + gates</strong><span>Correction and clarification loops → disease + question routing</span></div><div class="ov-arrow">→</div><div class="ov-node spec"><strong>Parallel specialists</strong><span>Guideline · Molecular · Literature · Translational · Trials · Safety</span></div><div class="ov-arrow">→</div><div class="ov-node challenge"><strong>Challenge + consensus</strong><span>Join specialists → Clinical Red Team → consensus or abstention</span></div><div class="ov-arrow">→</div><div class="ov-node output"><strong>Auditable output</strong><span>Tumor Board Brief → PDF + structured audit output</span></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="ov-safety"><strong>Design principle:</strong> the platform does not ask one model to read a case, retrieve evidence, decide what is missing, judge its own assumptions, and recommend care in one opaque step. Responsibilities are separated, handed off explicitly, challenged, and allowed to fail closed.</div>', unsafe_allow_html=True)

    st.markdown('<div class="ov-section">How the system works</div><div class="ov-sub">A faculty-facing view of the scientific workflow rather than the software implementation.</div>', unsafe_allow_html=True)
    st.markdown('<div class="ov-grid"><div class="ov-card"><div class="num">01 / REPRESENT</div><h3>Structure the case</h3><p>Extract diagnosis, disease state, explicit stage, treatment history, molecular findings, performance status, and the tumor-board question with provenance.</p></div><div class="ov-card"><div class="num">02 / CONTROL</div><h3>Gate before reasoning</h3><p>Human confirmation, deterministic integrity, missing-information, conflict, and clarification gates decide whether specialist reasoning may proceed.</p></div><div class="ov-card"><div class="num">03 / SPECIALIZE</div><h3>Route evidence agents</h3><p>Bounded specialist agents work through distinct evidence channels with independent source status, limitations, and failure states.</p></div><div class="ov-card"><div class="num">04 / CHALLENGE</div><h3>Challenge before synthesis</h3><p>Specialist outputs are joined, challenged by a Clinical Red Team, and only then moved to consensus, abstention, and the final brief.</p></div></div>', unsafe_allow_html=True)

    st.markdown('<div class="ov-section">Faculty evaluation boundary</div><div class="ov-sub">The pan-oncology common-core architecture has passed its synthetic qualification gate. Disease-specific software qualification and clinical validation remain separate future phases. The platform is intended for research, demonstration, workflow evaluation, and controlled faculty review rather than autonomous patient-care use.</div>', unsafe_allow_html=True)
    research_footer()
