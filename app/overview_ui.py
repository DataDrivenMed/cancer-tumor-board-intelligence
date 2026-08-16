from __future__ import annotations

import streamlit as st

from app.architecture_ui import architecture_css
from app.faculty_ui import faculty_css, research_footer, top_navigation


def render_final_overview() -> None:
    faculty_css(); architecture_css(); top_navigation("overview")
    st.markdown(
        """
<style>
.ov-hero{padding:38px 0 20px;border-bottom:1px solid #e4e7ec;margin-bottom:18px}.ov-hero h1{font-size:58px;line-height:1.0;letter-spacing:-1.8px;color:#102a43;margin:0;font-weight:720}.ov-author{font-size:16px;color:#285e9e;font-weight:720;margin-top:10px}.ov-lede{font-size:18px;line-height:1.62;color:#5e6f82;max-width:980px;margin-top:17px}.ov-badges{display:flex;flex-wrap:wrap;gap:7px;margin-top:16px}.ov-badge{display:inline-flex;padding:6px 10px;border-radius:999px;border:1px solid #d6e2ec;background:#fff;font-size:11px;font-weight:750;color:#40566b}.ov-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:16px 0 26px}.ov-card{border:1px solid #dfe6ed;background:#fff;border-radius:15px;padding:17px;box-shadow:0 2px 4px rgba(16,42,67,.025)}.ov-card .num{font-size:10px;font-weight:850;color:#285e9e;letter-spacing:.1em}.ov-card h3{font-size:17px;color:#173b5e;margin:7px 0}.ov-card p{font-size:13px;color:#66778a;line-height:1.55;margin:0}.ov-section{font-size:29px;letter-spacing:-.6px;color:#102a43;font-weight:760;margin:30px 0 5px}.ov-sub{font-size:14px;color:#65768a;line-height:1.55;max-width:920px;margin-bottom:13px}.ov-arch{display:grid;grid-template-columns:1fr 34px 1fr 34px 1.35fr 34px 1fr 34px 1fr;gap:7px;align-items:center;border:1px solid #dbe4ec;border-radius:17px;padding:17px;background:linear-gradient(180deg,#fff,#fbfcfe)}.ov-node{border:1px solid #cbd8e4;border-radius:12px;padding:13px;min-height:100px;background:#fff}.ov-node strong{display:block;font-size:14px;color:#173b5e}.ov-node span{font-size:12px;line-height:1.45;color:#69798b;display:block;margin-top:4px}.ov-node.spec{border-top:4px solid #18856c}.ov-node.challenge{border-top:4px solid #6c4aa4}.ov-node.output{border-top:4px solid #173f67}.ov-arrow{text-align:center;color:#8394a6;font-size:18px}.ov-safety{border-left:5px solid #9a6700;background:#fffaf0;border-radius:12px;padding:13px 15px;margin-top:13px;font-size:13px;color:#685126;line-height:1.5}
@media(max-width:950px){.ov-grid{grid-template-columns:repeat(2,1fr)}.ov-arch{grid-template-columns:1fr}.ov-arrow{transform:rotate(90deg)}}@media(max-width:600px){.ov-grid{grid-template-columns:1fr}.ov-hero h1{font-size:41px}}
</style>
""",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="ov-hero"><h1>Pan-Oncology Tumor Board Intelligence</h1><div class="ov-author">Ram Paragi · rparag@lsuhsc.edu</div><div class="ov-lede">A governed multi-agent research decision-support platform for multidisciplinary cancer review. It structures the case, detects missingness and conflicts, routes bounded evidence specialists, challenges the evidence stack before consensus, and produces an auditable tumor-board brief while preserving abstention and uncertainty.</div><div class="ov-badges"><span class="ov-badge">Pan-oncology architecture</span><span class="ov-badge">Case provenance</span><span class="ov-badge">Bounded evidence</span><span class="ov-badge">Clinical Red Team</span><span class="ov-badge">Human review</span><span class="ov-badge">Auditable outputs</span></div></div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ov-grid"><div class="ov-card"><div class="num">01</div><h3>Structure the case</h3><p>Extract diagnosis, disease state, explicit stage, treatment history, molecular findings, performance status, and the tumor-board question with provenance.</p></div><div class="ov-card"><div class="num">02</div><h3>Gate before reasoning</h3><p>Human confirmation, deterministic integrity, missing-information, conflict, and clarification gates determine whether specialist reasoning may proceed.</p></div><div class="ov-card"><div class="num">03</div><h3>Route specialist agents</h3><p>Guideline, molecular, literature, translational, clinical-trial, and safety agents work through bounded evidence channels with independent failure states.</p></div><div class="ov-card"><div class="num">04</div><h3>Challenge then synthesize</h3><p>Specialist outputs are joined, challenged by a Clinical Red Team, and only then moved to consensus, abstention, and the final tumor-board brief.</p></div></div>', unsafe_allow_html=True)

    st.markdown('<div class="ov-section">The architecture at a glance</div><div class="ov-sub">This compact view shows the orchestration concept. Open the Architecture page for the complete node-by-node system, handoff criteria, external evidence sources, and interactive Agent Explorer.</div>', unsafe_allow_html=True)
    st.markdown('<div class="ov-arch"><div class="ov-node"><strong>Case representation</strong><span>Intake → extraction → human confirmation → integrity → missingness</span></div><div class="ov-arrow">→</div><div class="ov-node"><strong>Routing + gates</strong><span>Correction / clarification loops → disease + question routing</span></div><div class="ov-arrow">→</div><div class="ov-node spec"><strong>Parallel specialist agents</strong><span>Guideline · Molecular · Literature · Translational · Trials · Safety</span></div><div class="ov-arrow">→</div><div class="ov-node challenge"><strong>Challenge + consensus</strong><span>Join specialists → Clinical Red Team → consensus / abstention</span></div><div class="ov-arrow">→</div><div class="ov-node output"><strong>Auditable brief</strong><span>Tumor Board Brief → PDF + structured audit output</span></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="ov-safety"><strong>Why this matters:</strong> the system does not ask one model to read a case, retrieve evidence, decide what is missing, judge its own assumptions, and recommend care in one opaque step. Those responsibilities are separated, handed off explicitly, challenged, and allowed to fail closed.</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1,1,2], gap="small")
    with c1:
        st.page_link("pages/00_Clinical_Workspace.py", label="Enter Tumor Board Workspace", use_container_width=True)
    with c2:
        st.page_link("pages/03_Architecture.py", label="Explore Full Architecture", use_container_width=True)

    st.markdown('<div class="ov-section">What makes the system agentic?</div><div class="ov-sub">Routed execution, a shared structured case state, parallel specialist roles, governed tool use, conditional branching, human review points, adversarial challenge before consensus, and explicit abstention when evidence is inadequate.</div>', unsafe_allow_html=True)
    st.markdown('<div class="ov-grid"><div class="ov-card"><h3>Shared structured state</h3><p>Every specialist receives the same canonical case rather than independently reinterpreting the source chart.</p></div><div class="ov-card"><h3>Purpose-built roles</h3><p>Each agent has a specific task, allowed evidence, output schema, safety limits, and handoff criteria.</p></div><div class="ov-card"><h3>Conditional execution</h3><p>Integrity failures, missingness, clarification, unavailable evidence, and Red Team findings change or stop the workflow.</p></div><div class="ov-card"><h3>Transparent synthesis</h3><p>The final answer retains what supported it, what did not, what remains uncertain, and what could change the decision.</p></div></div>', unsafe_allow_html=True)

    st.markdown('<div class="ov-section">Faculty evaluation boundary</div><div class="ov-sub">The pan-oncology common-core architecture has passed its synthetic qualification gate. Disease-specific software qualification and clinical validation remain separate future phases. The platform is intended for research, demonstration, workflow evaluation, and controlled faculty review rather than autonomous patient-care use.</div>', unsafe_allow_html=True)
    research_footer()
