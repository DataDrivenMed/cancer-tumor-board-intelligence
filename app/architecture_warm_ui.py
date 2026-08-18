from __future__ import annotations

import json
from html import escape
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from app.architecture_ui import (
    NODES,
    architecture_css,
    render_agent_anatomy,
    render_agent_explorer,
    render_handoffs,
    render_play_workflow,
    render_why_agentic,
)
from app.faculty_ui import faculty_css, product_header, research_footer, top_navigation
from app.xai_theme import inject_xai_theme


def _node(node_id: str) -> dict[str, Any]:
    return next(item for item in NODES if item["id"] == node_id)


def _node_card(node_id: str, *, compact: bool = False, emphasis: bool = False) -> str:
    node = _node(node_id)
    classes = ["arch-node-card", escape(node["type"])]
    if compact:
        classes.append("compact")
    if emphasis:
        classes.append("emphasis")
    class_name = " ".join(classes)
    return (
        f'<button type="button" class="{class_name}" data-id="{escape(node["id"])}">'
        f'<span class="node-num">{escape(node["number"])}</span>'
        f'<strong>{escape(node["title"])}</strong>'
        f'<span class="node-purpose">{escape(node["purpose"])}</span>'
        '<span class="node-more">Click for details</span>'
        '</button>'
    )


def _arrow(label: str = "") -> str:
    text = f'<small>{escape(label)}</small>' if label else ""
    return f'<div class="flow-arrow"><span>→</span>{text}</div>'


def render_warm_architecture_graph() -> None:
    details_json = json.dumps({node["id"]: node for node in NODES}).replace("</", "<\\/")

    html = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{{--canvas:#f7f7f4;--soft:#fafaf7;--card:#ffffff;--ink:#26251e;--body:#5a5852;--muted:#807d72;--hair:#e6e5e0;--strong:#cfcdc4;--orange:#f54e00;--thinking:#dfa88f;--grep:#9fc9a2;--read:#9fbbe0;--edit:#c0a8dd;--done:#c08532}}
*{{box-sizing:border-box}}
html,body{{margin:0;background:var(--canvas);color:var(--ink);font-family:Inter,system-ui,"Helvetica Neue",Arial,sans-serif;overflow-x:hidden}}
.arch-map{{padding:8px 4px 18px;max-width:1500px;margin:0 auto}}
.read-guide{{display:grid;grid-template-columns:1.15fr .85fr;gap:18px;align-items:center;background:#fff;border:1px solid var(--hair);border-radius:12px;padding:20px 22px;margin-bottom:18px}}
.read-guide h2{{font-size:22px;line-height:1.25;font-weight:500;margin:0 0 7px}}
.read-guide p{{font-size:15px;line-height:1.62;color:var(--body);margin:0}}
.phase-key{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}}
.phase-chip{{border-radius:999px;padding:8px 10px;text-align:center;font:600 10px/1.25 "JetBrains Mono",ui-monospace,monospace;letter-spacing:.06em;text-transform:uppercase;color:var(--ink)}}
.phase-chip.case{{background:#eaf2fb}}.phase-chip.specialist{{background:#eef7ef}}.phase-chip.challenge{{background:#f5eff8}}.phase-chip.output{{background:#f6eee9}}
.phase{{background:#fff;border:1px solid var(--hair);border-radius:14px;padding:22px;margin:0 0 18px}}
.phase-head{{display:flex;justify-content:space-between;gap:18px;align-items:flex-start;padding-bottom:14px;border-bottom:1px solid var(--hair);margin-bottom:18px}}
.phase-head-left{{display:flex;gap:12px;align-items:flex-start}}
.phase-no{{min-width:44px;height:30px;border-radius:999px;display:grid;place-items:center;font:600 10px/1 "JetBrains Mono",monospace;letter-spacing:.08em;background:var(--soft);border:1px solid var(--hair);color:var(--muted)}}
.phase-title strong{{display:block;font-size:21px;line-height:1.3;font-weight:500}}
.phase-title span{{display:block;font-size:14px;line-height:1.55;color:var(--body);margin-top:4px;max-width:820px}}
.phase-rule{{font:600 10px/1.4 "JetBrains Mono",monospace;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);text-align:right;max-width:250px}}
.main-flow{{display:grid;grid-template-columns:1fr 58px 1fr 58px 1fr 58px 1fr;align-items:stretch;gap:6px}}
.secondary-flow{{display:grid;grid-template-columns:1fr 58px 1fr 58px 1fr;align-items:stretch;gap:6px;max-width:930px;margin:0 auto}}
.flow-arrow{{display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--muted);min-width:0}}
.flow-arrow span{{font-size:23px;line-height:1}}
.flow-arrow small{{font:600 9px/1.35 "JetBrains Mono",monospace;text-transform:uppercase;letter-spacing:.03em;text-align:center;color:var(--muted);margin-top:5px}}
.flow-down{{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:8px 0;color:var(--muted)}}
.flow-down span{{font-size:23px;line-height:1}}
.flow-down small{{font:600 9px/1.4 "JetBrains Mono",monospace;text-transform:uppercase;letter-spacing:.04em;margin-top:4px}}
.arch-node-card{{appearance:none;width:100%;min-height:154px;text-align:left;border:1px solid var(--strong);border-radius:11px;padding:15px;background:#fff;color:var(--ink);font:inherit;cursor:pointer;box-shadow:none;transition:border-color .12s ease,transform .12s ease,background .12s ease}}
.arch-node-card:hover,.arch-node-card:focus{{outline:none;border-color:var(--ink);transform:translateY(-1px)}}
.arch-node-card.case{{background:#eef4fb;border-top:5px solid var(--read)}}
.arch-node-card.gate{{background:#fff4ef;border-top:5px solid var(--thinking)}}
.arch-node-card.safety{{background:#fff8e7;border-top:5px solid var(--done)}}
.arch-node-card.evidence{{background:#eff7ef;border-top:5px solid var(--grep)}}
.arch-node-card.challenge{{background:#f5eff8;border-top:5px solid var(--edit)}}
.arch-node-card.output{{background:var(--ink);color:var(--canvas);border-color:var(--ink)}}
.arch-node-card.output .node-num,.arch-node-card.output .node-purpose,.arch-node-card.output .node-more{{color:#d6d2c7}}
.arch-node-card.emphasis{{border-width:2px}}
.node-num{{display:block;font:600 10px/1.25 "JetBrains Mono",monospace;letter-spacing:.08em;color:var(--muted);margin-bottom:10px}}
.arch-node-card strong{{display:block;font-size:16px;line-height:1.35;font-weight:600}}
.node-purpose{{display:block;font-size:13.5px;line-height:1.5;color:var(--body);margin-top:7px}}
.node-more{{display:block;font-size:11px;color:var(--muted);margin-top:10px}}
.branch-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:14px auto 0;max-width:930px}}
.branch-card{{border:1px dashed var(--strong);border-radius:11px;background:var(--soft);padding:13px}}
.branch-card .branch-label{{font:600 10px/1.4 "JetBrains Mono",monospace;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-bottom:8px}}
.branch-card p{{font-size:13px;line-height:1.5;color:var(--body);margin:0 0 10px}}
.branch-card .arch-node-card{{min-height:128px}}
.specialist-intro,.join-note,.human-note{{font-size:14px;line-height:1.58;color:var(--body);background:var(--soft);border:1px solid var(--hair);border-radius:10px;padding:13px 15px;margin-bottom:14px}}
.specialist-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}}
.specialist-grid .arch-node-card{{min-height:170px}}
.converge{{display:flex;align-items:center;justify-content:center;gap:12px;margin:16px 0 2px;color:var(--muted)}}
.converge::before,.converge::after{{content:"";height:1px;background:var(--hair);flex:1}}
.converge span{{font:600 10px/1.4 "JetBrains Mono",monospace;text-transform:uppercase;letter-spacing:.06em}}
.challenge-flow{{display:grid;grid-template-columns:1fr 64px 1fr 64px 1fr;align-items:stretch;gap:6px;max-width:1020px;margin:0 auto}}
.challenge-flow .arch-node-card{{min-height:168px}}
.output-flow{{display:grid;grid-template-columns:1fr 64px 1fr 64px 1fr;align-items:stretch;gap:6px;max-width:1020px;margin:0 auto}}
.clinician-card{{min-height:154px;border:1px solid var(--ink);border-radius:11px;padding:15px;background:#fff;color:var(--ink);display:flex;flex-direction:column;justify-content:center}}
.clinician-card .node-num{{color:var(--orange)}}
.clinician-card strong{{font-size:17px;line-height:1.35}}
.clinician-card span{{font-size:13.5px;line-height:1.5;color:var(--body);margin-top:7px}}
.human-note{{margin-top:14px;margin-bottom:0;background:#fff8e7;border-color:#ead6a6;color:#6f5724}}
.detail-dialog{{width:min(760px,calc(100vw - 28px));max-height:86vh;border:1px solid var(--strong);border-radius:14px;padding:0;background:#fff;color:var(--ink)}}
.detail-dialog::backdrop{{background:rgba(38,37,30,.58)}}
.detail-head{{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;padding:17px 18px;border-bottom:1px solid var(--hair);background:var(--canvas)}}
.detail-head .k{{font:600 10px/1.4 "JetBrains Mono",monospace;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}}
.detail-head h3{{font-size:22px;line-height:1.3;font-weight:500;margin:4px 0 0}}
.detail-close{{border:1px solid var(--strong);background:#fff;color:var(--ink);border-radius:8px;padding:8px 11px;font-size:14px;font-weight:600;cursor:pointer}}
.detail-body{{padding:18px;overflow:auto;max-height:calc(86vh - 82px)}}
.detail-row{{padding:11px 0;border-bottom:1px solid var(--hair)}}.detail-row:last-child{{border-bottom:0}}
.detail-row strong{{display:block;font-size:13px;color:var(--ink);margin-bottom:4px}}
.detail-row span{{display:block;font-size:14.5px;line-height:1.62;color:var(--body)}}
@media(max-width:1080px){{
 .read-guide{{grid-template-columns:1fr}}.main-flow{{grid-template-columns:1fr 38px 1fr}}.main-flow>.flow-arrow:nth-of-type(2),.main-flow>.flow-arrow:nth-of-type(3){{display:none}}
 .main-flow>.arch-node-card:nth-of-type(3),.main-flow>.arch-node-card:nth-of-type(4){{margin-top:10px}}
 .specialist-grid{{grid-template-columns:repeat(2,1fr)}}
 .challenge-flow,.output-flow{{grid-template-columns:1fr 48px 1fr 48px 1fr}}
}}
@media(max-width:760px){{
 .phase{{padding:16px}}.phase-head{{flex-direction:column}}.phase-rule{{text-align:left}}
 .phase-key{{grid-template-columns:1fr 1fr}}
 .main-flow,.secondary-flow,.challenge-flow,.output-flow{{display:flex;flex-direction:column;gap:8px;max-width:none}}
 .flow-arrow{{height:30px}}.flow-arrow span{{transform:rotate(90deg)}}.flow-arrow small{{display:none}}
 .branch-grid,.specialist-grid{{grid-template-columns:1fr}}
 .arch-node-card,.specialist-grid .arch-node-card,.challenge-flow .arch-node-card{{min-height:auto}}
}}
</style>
</head>
<body>
<div class="arch-map">
  <section class="read-guide">
    <div>
      <h2>How to read this architecture</h2>
      <p>A traditional chatbot tries to answer the whole question in one interaction. Tumor Board Intelligence separates the work into bounded stages: first the case is represented and checked, then relevant evidence specialists work independently, their findings are challenged, and only then can a clinician-facing brief be produced.</p>
    </div>
    <div class="phase-key">
      <div class="phase-chip case">Case</div>
      <div class="phase-chip specialist">Specialists</div>
      <div class="phase-chip challenge">Challenge</div>
      <div class="phase-chip output">Tumor Board</div>
    </div>
  </section>

  <section class="phase">
    <div class="phase-head">
      <div class="phase-head-left"><div class="phase-no">01</div><div class="phase-title"><strong>Case understanding and safety</strong><span>The system creates one source-traced case representation, asks clinicians to verify it, and keeps missing or conflicting information visible before specialist reasoning begins.</span></div></div>
      <div class="phase-rule">No specialist reasoning before required case gates</div>
    </div>
    <div class="main-flow">
      {_node_card("intake")}{_arrow("source")}{_node_card("extraction")}{_arrow("structured case")}{_node_card("confirmation")}{_arrow("human reviewed")}{_node_card("integrity")}
    </div>
    <div class="flow-down"><span>↓</span><small>Integrity cleared</small></div>
    <div class="secondary-flow">
      {_node_card("missing")}{_arrow("classified")}{_node_card("clarification")}{_arrow("case ready")}{_node_card("router")}
    </div>
    <div class="branch-grid">
      <div class="branch-card"><div class="branch-label">Correction loop</div><p>If clinician review identifies a representation mismatch, the case is corrected before integrity review continues.</p>{_node_card("correction", compact=True)}</div>
      <div class="branch-card"><div class="branch-label">Clarification loop</div><p>If recommendation-blocking information is unresolved, verified clarification is added and the case is rechecked before routing.</p>{_node_card("apply", compact=True)}</div>
    </div>
  </section>

  <section class="phase">
    <div class="phase-head">
      <div class="phase-head-left"><div class="phase-no">02</div><div class="phase-title"><strong>Parallel specialist agents</strong><span>The Clinical Router sends the same governed case state to the evidence channels relevant to the represented question. Each specialist has a bounded role and returns a structured result.</span></div></div>
      <div class="phase-rule">Independent evidence channels, shared case state</div>
    </div>
    <div class="specialist-intro">The specialists do not vote and they do not independently make the final treatment decision. Their outputs preserve evidence source, availability, limitations, and uncertainty for downstream review.</div>
    <div class="specialist-grid">
      {_node_card("guideline")}{_node_card("molecular")}{_node_card("literature")}
      {_node_card("translational")}{_node_card("trials")}{_node_card("safety")}
    </div>
    <div class="converge"><span>Structured specialist outputs + provenance</span></div>
  </section>

  <section class="phase">
    <div class="phase-head">
      <div class="phase-head-left"><div class="phase-no">03</div><div class="phase-title"><strong>Challenge and consensus</strong><span>Specialist outputs are assembled without flattening their differences. The Clinical Red Team then challenges evidence sufficiency, assumptions, conflicts, and unsupported recommendation logic before consensus is allowed.</span></div></div>
      <div class="phase-rule">Challenge before synthesis</div>
    </div>
    <div class="challenge-flow">
      {_node_card("join")}{_arrow("assembled")}{_node_card("redteam", emphasis=True)}{_arrow("no blocking finding")}{_node_card("consensus")}
    </div>
    <div class="human-note"><strong>Fail-closed behavior:</strong> if evidence remains inadequate or a blocking challenge is unresolved, the workflow can remain conditional or abstain rather than forcing a recommendation.</div>
  </section>

  <section class="phase">
    <div class="phase-head">
      <div class="phase-head-left"><div class="phase-no">04</div><div class="phase-title"><strong>Tumor Board output and human decision support</strong><span>The final layers translate governed workflow state into a readable brief and audit-oriented output. The clinician and multidisciplinary tumor board remain the final decision-makers.</span></div></div>
      <div class="phase-rule">Presentation does not create new clinical claims</div>
    </div>
    <div class="output-flow">
      {_node_card("brief")}{_arrow("render")}{_node_card("outputs")}{_arrow("review")}
      <div class="clinician-card"><span class="node-num">HUMAN</span><strong>Clinician / Multidisciplinary Tumor Board</strong><span>Reviews applicability, uncertainty, patient context, alternatives, and the final management decision.</span></div>
    </div>
  </section>
</div>

<dialog id="detailDialog" class="detail-dialog">
  <div class="detail-head"><div><div id="detailKicker" class="k"></div><h3 id="detailTitle"></h3></div><button id="detailClose" class="detail-close" type="button">Close</button></div>
  <div id="detailBody" class="detail-body"></div>
</dialog>

<script>
const DETAILS={details_json};
const dialog=document.getElementById('detailDialog');
const title=document.getElementById('detailTitle');
const kicker=document.getElementById('detailKicker');
const body=document.getElementById('detailBody');
const closeBtn=document.getElementById('detailClose');
function esc(s){{return String(s??'').replace(/[&<>"']/g,m=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}}[m]))}}
function row(label,value){{return `<div class="detail-row"><strong>${{esc(label)}}</strong><span>${{esc(value)}}</span></div>`}}
function openDetail(id){{const d=DETAILS[id];if(!d)return;kicker.textContent=`${{d.number}} · ${{d.type}}`;title.textContent=d.title;body.innerHTML=row('Purpose',d.purpose)+row('Inputs',d.inputs)+row('What happens in this node',d.action)+row('Output / handoff',d.output)+row('Safety boundary',d.safety)+row('Why this step exists',d.why);if(dialog.showModal)dialog.showModal();else dialog.setAttribute('open','')}}
document.querySelectorAll('.arch-node-card').forEach(node=>node.addEventListener('click',()=>openDetail(node.dataset.id)));
closeBtn.addEventListener('click',()=>dialog.close());
dialog.addEventListener('click',e=>{{if(e.target===dialog)dialog.close()}});
document.addEventListener('keydown',e=>{{if(e.key==='Escape'&&dialog.open)dialog.close()}});
</script>
</body>
</html>'''

    components.html(html, height=2160, scrolling=False)


def render_architecture_page() -> None:
    faculty_css()
    inject_xai_theme()
    architecture_css()
    product_header("Scientific architecture")
    top_navigation("architecture")
    st.markdown(
        '<div class="arch-hero"><div class="eyebrow">Technical view</div><h1>How the tumor-board agents work together</h1>'
        '<p>This page shows the governed workflow as four readable phases. The diagram itself is designed to fit the page without horizontal scrolling. Click any individual agent or gate when you want its complete purpose, inputs, outputs, safety boundary, and handoff logic.</p></div>',
        unsafe_allow_html=True,
    )
    render_warm_architecture_graph()
    render_play_workflow()
    render_agent_explorer()
    render_handoffs()
    render_agent_anatomy()
    render_why_agentic()
    research_footer()
