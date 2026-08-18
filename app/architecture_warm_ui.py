from __future__ import annotations

import json
from html import escape
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from app.architecture_ui import (
    HANDOFFS,
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


def _node_button(node_id: str) -> str:
    node = _node(node_id)
    return (
        f'<button class="aw-node {escape(node["type"])}" data-id="{escape(node["id"])}">'
        f'<span class="aw-num">{escape(node["number"])}</span>'
        f'<strong>{escape(node["title"])}</strong>'
        f'<small>{escape(node["purpose"])}</small>'
        '</button>'
    )


def _arrow(label: str = "") -> str:
    label_html = f'<small>{escape(label)}</small>' if label else ""
    return f'<div class="aw-arrow"><span>→</span>{label_html}</div>'


def _row(node_ids: list[str], labels: list[str] | None = None) -> str:
    pieces: list[str] = []
    labels = labels or []
    for idx, node_id in enumerate(node_ids):
        pieces.append(_node_button(node_id))
        if idx < len(node_ids) - 1:
            pieces.append(_arrow(labels[idx] if idx < len(labels) else ""))
    return '<div class="aw-row">' + ''.join(pieces) + '</div>'


def render_warm_architecture_graph() -> None:
    details = {node["id"]: node for node in NODES}
    details_json = json.dumps(details).replace("</", "<\\/")

    stage1 = _row(
        ["intake", "extraction", "confirmation", "integrity", "missing", "clarification", "router"],
        ["source available", "structured case", "human confirmation", "integrity passed", "missingness classified", "case ready"],
    )
    specialists = ''.join(_node_button(node_id) for node_id in ["guideline", "molecular", "literature", "translational", "trials", "safety"])
    stage3 = _row(["join", "redteam", "consensus", "brief"], ["evidence stack", "challenge findings", "consensus permitted"])
    stage4 = _row(["brief", "outputs"], ["governed brief rendered"])

    html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{{--canvas:#f7f7f4;--soft:#fafaf7;--card:#fff;--ink:#26251e;--body:#5a5852;--muted:#807d72;--hair:#e6e5e0;--strong:#cfcdc4;--orange:#f54e00;--thinking:#dfa88f;--grep:#9fc9a2;--read:#9fbbe0;--edit:#c0a8dd;--done:#c08532}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--canvas);color:var(--ink);font-family:Inter,system-ui,"Helvetica Neue",Arial,sans-serif}}.aw{{padding:14px}}
.aw-help{{background:#fff;border:1px solid var(--hair);border-radius:12px;padding:13px 15px;margin-bottom:12px;font-size:12px;line-height:1.55;color:var(--body)}}.aw-help b{{color:var(--orange)}}
.aw-lane{{background:#fff;border:1px solid var(--hair);border-radius:12px;padding:16px;margin-bottom:12px}}.aw-lane-head{{display:flex;justify-content:space-between;gap:12px;align-items:end;border-bottom:1px solid var(--hair);padding-bottom:10px;margin-bottom:13px}}.aw-lane-head strong{{font-size:15px;font-weight:600}}.aw-lane-head span{{font:600 9px/1.3 "JetBrains Mono",ui-monospace,monospace;letter-spacing:.10em;text-transform:uppercase;color:var(--muted)}}
.aw-row{{display:flex;align-items:stretch;gap:7px;min-width:max-content}}.aw-scroll{{overflow-x:auto;padding-bottom:4px}}.aw-node{{width:190px;min-height:112px;text-align:left;border:1px solid var(--strong);border-radius:10px;padding:12px;background:#fff;color:var(--ink);cursor:pointer;font:inherit;box-shadow:none;transition:border-color .12s ease,transform .12s ease}}.aw-node:hover,.aw-node:focus,.aw-node.pinned{{border-color:var(--ink);outline:none;transform:translateY(-1px)}}
.aw-node.case{{background:#eef3f9;border-top:5px solid var(--read)}}.aw-node.gate{{background:#fff4ef;border-top:5px solid var(--thinking)}}.aw-node.safety{{background:#fff8e7;border-top:5px solid var(--done)}}.aw-node.evidence{{background:#eff7ef;border-top:5px solid var(--grep)}}.aw-node.challenge{{background:#f5eff8;border-top:5px solid var(--edit)}}.aw-node.output{{background:var(--ink);color:var(--canvas);border-color:var(--ink)}}.aw-node.output small,.aw-node.output .aw-num{{color:#d6d2c7}}
.aw-num{{display:block;font:600 9px/1.2 "JetBrains Mono",ui-monospace,monospace;letter-spacing:.09em;color:var(--muted);margin-bottom:9px}}.aw-node strong{{display:block;font-size:13px;line-height:1.3;font-weight:600}}.aw-node small{{display:block;font-size:10px;line-height:1.45;color:var(--body);margin-top:6px}}
.aw-arrow{{width:82px;display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--muted);flex:none}}.aw-arrow span{{font-size:20px}}.aw-arrow small{{font:600 8px/1.3 "JetBrains Mono",ui-monospace,monospace;text-transform:uppercase;text-align:center;letter-spacing:.04em;margin-top:4px;color:var(--muted)}}
.aw-branches{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px}}.aw-branch{{background:var(--soft);border:1px dashed var(--strong);border-radius:10px;padding:11px;font-size:11px;line-height:1.5;color:var(--body)}}.aw-branch b{{color:var(--ink)}}
.aw-specialists{{display:grid;grid-template-columns:repeat(6,minmax(150px,1fr));gap:8px;min-width:1020px}}.aw-specialists .aw-node{{width:auto}}
.aw-human{{display:flex;gap:9px;align-items:flex-start;margin-top:12px;padding:11px 12px;border:1px solid #ead6a6;background:#fff8e7;border-radius:10px}}.aw-human .pill{{flex:none;background:var(--done);color:#fff;border-radius:999px;padding:5px 8px;font:600 8px/1 "JetBrains Mono",monospace;letter-spacing:.06em}}.aw-human div{{font-size:11px;line-height:1.5;color:#6f5724}}
.aw-tip{{position:fixed;z-index:99;display:none;width:min(390px,calc(100vw - 28px));background:#26251e;color:#fff;border-radius:12px;padding:15px;pointer-events:none}}.aw-tip.show{{display:block}}.aw-tip .k{{font:600 9px/1.3 "JetBrains Mono",monospace;text-transform:uppercase;letter-spacing:.08em;color:#c8c3b8}}.aw-tip h3{{font-size:16px;line-height:1.25;margin:4px 0 9px;font-weight:500}}.aw-tip p{{font-size:11px;line-height:1.5;color:#e6e2d8;margin:6px 0}}.aw-tip b{{color:#fff}}
.aw-pinned{{display:none;margin-top:12px;border:1px solid var(--hair);border-radius:12px;background:#fff;padding:14px}}.aw-pinned.show{{display:block}}.aw-pinned h3{{margin:2px 0 8px;font-size:17px;font-weight:500}}.aw-pinned p{{font-size:11px;line-height:1.55;color:var(--body);margin:6px 0}}.aw-pinned .close{{float:right;border:1px solid var(--strong);background:#fff;border-radius:8px;padding:6px 9px;cursor:pointer;color:var(--ink)}}
@media(max-width:760px){{.aw-branches{{grid-template-columns:1fr}}.aw{{padding:8px}}}}
</style></head><body><div class="aw">
<div class="aw-help"><b>How to use this diagram:</b> hover over a node for a quick explanation. Click or tap a node to pin its purpose, inputs, outputs, safety boundary, and handoff logic below the diagram.</div>
<div class="aw-lane"><div class="aw-lane-head"><strong>Case representation, integrity and routing</strong><span>01 / Before specialist reasoning</span></div><div class="aw-scroll">{stage1}</div><div class="aw-branches"><div class="aw-branch"><b>Correction branch:</b> if clinician review identifies a representation mismatch, the case moves through <b>Case Correction Gate</b> and then returns to integrity review.<br><br>{_node_button("correction")}</div><div class="aw-branch"><b>Clarification branch:</b> when recommendation-blocking information is unresolved, the workflow uses <b>Apply Clarification</b> and rechecks the case before routing.<br><br>{_node_button("apply")}</div></div><div class="aw-human"><span class="pill">HUMAN</span><div>Clinician review is explicit at case confirmation/correction and wherever source candidates require local attestation. Human review does not convert unsupported information into clinical truth.</div></div></div>
<div class="aw-lane"><div class="aw-lane-head"><strong>Parallel governed specialist agents</strong><span>02 / Bounded evidence channels</span></div><div class="aw-scroll"><div class="aw-specialists">{specialists}</div></div><div class="aw-human"><span class="pill">EVIDENCE</span><div>Guideline, molecular, literature, translational, clinical-trial, and safety channels remain distinct. Their statuses, provenance, limitations, and unavailable states are preserved for downstream review.</div></div></div>
<div class="aw-lane"><div class="aw-lane-head"><strong>Join, challenge and consensus</strong><span>03 / Challenge before synthesis</span></div><div class="aw-scroll">{stage3}</div></div>
<div class="aw-lane"><div class="aw-lane-head"><strong>Governed outputs and human decision support</strong><span>04 / Presentation, not autonomous care</span></div><div class="aw-scroll">{stage4}</div></div>
<div id="pinned" class="aw-pinned"></div><div id="tip" class="aw-tip"></div>
</div><script>
const DETAILS={details_json};
const tip=document.getElementById('tip');const pinned=document.getElementById('pinned');let pinnedId=null;
function inner(d,close=false){{return `${{close?'<button class="close" onclick="clearPinned()">Close</button>':''}}<div class="k">${{d.number}} · ${{d.type}}</div><h3>${{d.title}}</h3><p><b>Purpose:</b> ${{d.purpose}}</p><p><b>Inputs:</b> ${{d.inputs}}</p><p><b>Output:</b> ${{d.output}}</p><p><b>Safety boundary:</b> ${{d.safety}}</p><p><b>Why this step exists:</b> ${{d.why}}</p>`}}
function placeTip(e){{const pad=14;const w=390;let x=e.clientX+14,y=e.clientY+14;if(x+w>window.innerWidth-pad)x=e.clientX-w-14;if(y+300>window.innerHeight-pad)y=Math.max(pad,window.innerHeight-314);tip.style.left=Math.max(pad,x)+'px';tip.style.top=Math.max(pad,y)+'px'}}
function clearPinned(){{pinnedId=null;pinned.classList.remove('show');pinned.innerHTML='';document.querySelectorAll('.aw-node').forEach(n=>n.classList.remove('pinned'))}}
document.querySelectorAll('.aw-node').forEach(node=>{{const id=node.dataset.id;const d=DETAILS[id];if(!d)return;node.addEventListener('mouseenter',e=>{{if(!pinnedId){{tip.innerHTML=inner(d);tip.classList.add('show');placeTip(e)}}}});node.addEventListener('mousemove',e=>{{if(!pinnedId)placeTip(e)}});node.addEventListener('mouseleave',()=>{{if(!pinnedId)tip.classList.remove('show')}});node.addEventListener('focus',e=>{{if(!pinnedId){{tip.innerHTML=inner(d);tip.classList.add('show');const r=node.getBoundingClientRect();placeTip({{clientX:r.right,clientY:r.top}})}}}});node.addEventListener('blur',()=>{{if(!pinnedId)tip.classList.remove('show')}});node.addEventListener('click',()=>{{document.querySelectorAll('.aw-node').forEach(n=>n.classList.remove('pinned'));node.classList.add('pinned');pinnedId=id;tip.classList.remove('show');pinned.innerHTML=inner(d,true);pinned.classList.add('show');pinned.scrollIntoView({{behavior:'smooth',block:'nearest'}})}})}});
</script></body></html>'''
    components.html(html, height=1180, scrolling=True)


def render_architecture_page() -> None:
    faculty_css()
    inject_xai_theme()
    architecture_css()
    product_header("Scientific architecture")
    top_navigation("architecture")
    st.markdown(
        '<div class="arch-hero"><div class="eyebrow">Technical view</div><h1>How the tumor-board agents work together</h1>'
        '<p>This page shows the complete governed multi-agent workflow. If AI agents are new to you, start on the Overview first. Here, each node represents a bounded job, and each handoff represents a condition that must be satisfied before the next part of the workflow proceeds.</p></div>',
        unsafe_allow_html=True,
    )
    render_warm_architecture_graph()
    render_play_workflow()
    render_agent_explorer()
    render_handoffs()
    render_agent_anatomy()
    render_why_agentic()
    research_footer()
