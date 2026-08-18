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
    stage3 = _row(["join", "redteam", "consensus"], ["evidence stack", "challenge findings"])
    stage4 = _row(["brief", "outputs"], ["governed brief rendered"])

    diagram = (
        '<div class="aw-lane"><div class="aw-lane-head"><strong>Case representation, integrity and routing</strong><span>01 / Before specialist reasoning</span></div>'
        f'<div class="aw-scroll">{stage1}</div><div class="aw-branches"><div class="aw-branch"><b>Correction branch:</b> if clinician review identifies a representation mismatch, the case moves through <b>Case Correction Gate</b> and then returns to integrity review.<br><br>{_node_button("correction")}</div>'
        f'<div class="aw-branch"><b>Clarification branch:</b> when recommendation-blocking information is unresolved, the workflow uses <b>Apply Clarification</b> and rechecks the case before routing.<br><br>{_node_button("apply")}</div></div>'
        '<div class="aw-human"><span class="pill">HUMAN</span><div>Clinician review is explicit at case confirmation/correction and wherever source candidates require local attestation. Human review does not convert unsupported information into clinical truth.</div></div></div>'
        '<div class="aw-lane"><div class="aw-lane-head"><strong>Parallel governed specialist agents</strong><span>02 / Bounded evidence channels</span></div>'
        f'<div class="aw-scroll"><div class="aw-specialists">{specialists}</div></div><div class="aw-human"><span class="pill">EVIDENCE</span><div>Guideline, molecular, literature, translational, clinical-trial, and safety channels remain distinct. Their statuses, provenance, limitations, and unavailable states are preserved for downstream review.</div></div></div>'
        '<div class="aw-lane"><div class="aw-lane-head"><strong>Join, challenge and consensus</strong><span>03 / Challenge before synthesis</span></div>'
        f'<div class="aw-scroll">{stage3}</div><div class="aw-human"><span class="pill">GATE</span><div>Consensus may proceed only after the challenge layer does not leave unresolved recommendation-blocking findings. Otherwise the governed workflow remains conditional or abstains.</div></div></div>'
        '<div class="aw-lane"><div class="aw-lane-head"><strong>Governed outputs and human decision support</strong><span>04 / Presentation, not autonomous care</span></div>'
        f'<div class="aw-scroll">{stage4}</div></div>'
    )

    html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{{--canvas:#f7f7f4;--soft:#fafaf7;--card:#fff;--ink:#26251e;--body:#5a5852;--muted:#807d72;--hair:#e6e5e0;--strong:#cfcdc4;--orange:#f54e00;--thinking:#dfa88f;--grep:#9fc9a2;--read:#9fbbe0;--edit:#c0a8dd;--done:#c08532}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--canvas);color:var(--ink);font-family:Inter,system-ui,"Helvetica Neue",Arial,sans-serif}}.aw{{padding:14px}}
.aw-help{{background:#fff;border:1px solid var(--hair);border-radius:12px;padding:15px 17px;margin-bottom:12px;font-size:14.5px;line-height:1.6;color:var(--body)}}.aw-help b{{color:var(--orange)}}
.aw-tools{{display:flex;justify-content:flex-end;align-items:center;gap:10px;margin:-2px 0 12px}}.aw-tools span{{font-size:13px;color:var(--muted)}}.aw-expand{{border:1px solid var(--strong);background:#fff;color:var(--ink);border-radius:8px;padding:9px 13px;font-size:14px;font-weight:600;cursor:pointer}}.aw-expand:hover{{border-color:var(--ink)}}
.aw-lane{{background:#fff;border:1px solid var(--hair);border-radius:12px;padding:17px;margin-bottom:12px}}.aw-lane-head{{display:flex;justify-content:space-between;gap:12px;align-items:end;border-bottom:1px solid var(--hair);padding-bottom:11px;margin-bottom:14px}}.aw-lane-head strong{{font-size:17px;font-weight:600;line-height:1.3}}.aw-lane-head span{{font:600 11px/1.4 "JetBrains Mono",ui-monospace,monospace;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}}
.aw-row{{display:flex;align-items:stretch;gap:8px;min-width:max-content}}.aw-scroll{{overflow-x:auto;padding-bottom:6px}}.aw-node{{width:220px;min-height:136px;text-align:left;border:1px solid var(--strong);border-radius:10px;padding:14px;background:#fff;color:var(--ink);cursor:pointer;font:inherit;box-shadow:none;transition:border-color .12s ease,transform .12s ease}}.aw-node:hover,.aw-node:focus,.aw-node.pinned{{border-color:var(--ink);outline:none;transform:translateY(-1px)}}
.aw-node.case{{background:#eef3f9;border-top:5px solid var(--read)}}.aw-node.gate{{background:#fff4ef;border-top:5px solid var(--thinking)}}.aw-node.safety{{background:#fff8e7;border-top:5px solid var(--done)}}.aw-node.evidence{{background:#eff7ef;border-top:5px solid var(--grep)}}.aw-node.challenge{{background:#f5eff8;border-top:5px solid var(--edit)}}.aw-node.output{{background:var(--ink);color:var(--canvas);border-color:var(--ink)}}.aw-node.output small,.aw-node.output .aw-num{{color:#d6d2c7}}
.aw-num{{display:block;font:600 11px/1.2 "JetBrains Mono",ui-monospace,monospace;letter-spacing:.08em;color:var(--muted);margin-bottom:10px}}.aw-node strong{{display:block;font-size:15px;line-height:1.35;font-weight:600}}.aw-node small{{display:block;font-size:13px;line-height:1.5;color:var(--body);margin-top:7px}}
.aw-arrow{{width:90px;display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--muted);flex:none}}.aw-arrow span{{font-size:23px}}.aw-arrow small{{font:600 10px/1.4 "JetBrains Mono",ui-monospace,monospace;text-transform:uppercase;text-align:center;letter-spacing:.03em;margin-top:4px;color:var(--muted)}}
.aw-branches{{display:grid;grid-template-columns:1fr 1fr;gap:11px;margin-top:13px}}.aw-branch{{background:var(--soft);border:1px dashed var(--strong);border-radius:10px;padding:13px;font-size:13.5px;line-height:1.55;color:var(--body)}}.aw-branch b{{color:var(--ink)}}.aw-branch .aw-node{{width:100%;min-height:118px;margin-top:4px}}
.aw-specialists{{display:grid;grid-template-columns:repeat(6,minmax(190px,1fr));gap:9px;min-width:1220px}}.aw-specialists .aw-node{{width:auto}}
.aw-human{{display:flex;gap:10px;align-items:flex-start;margin-top:13px;padding:13px 14px;border:1px solid #ead6a6;background:#fff8e7;border-radius:10px}}.aw-human .pill{{flex:none;background:var(--done);color:#fff;border-radius:999px;padding:6px 9px;font:600 10px/1 "JetBrains Mono",monospace;letter-spacing:.05em}}.aw-human div{{font-size:13.5px;line-height:1.55;color:#6f5724}}
.aw-tip{{position:fixed;z-index:99;display:none;width:min(440px,calc(100vw - 28px));background:#26251e;color:#fff;border-radius:12px;padding:17px;pointer-events:none}}.aw-tip.show{{display:block}}.aw-tip .k{{font:600 11px/1.4 "JetBrains Mono",monospace;text-transform:uppercase;letter-spacing:.07em;color:#c8c3b8}}.aw-tip h3{{font-size:19px;line-height:1.3;margin:5px 0 10px;font-weight:500}}.aw-tip p{{font-size:14px;line-height:1.55;color:#e6e2d8;margin:7px 0}}.aw-tip b{{color:#fff}}
.aw-pinned{{display:none;margin-top:13px;border:1px solid var(--hair);border-radius:12px;background:#fff;padding:16px}}.aw-pinned.show{{display:block}}.aw-pinned h3{{margin:2px 0 9px;font-size:19px;font-weight:500}}.aw-pinned p{{font-size:14.5px;line-height:1.6;color:var(--body);margin:7px 0}}.aw-pinned .close{{float:right;border:1px solid var(--strong);background:#fff;border-radius:8px;padding:7px 10px;cursor:pointer;color:var(--ink);font-size:13px}}
.aw-dialog{{width:96vw;max-width:1800px;height:92vh;border:1px solid var(--strong);border-radius:14px;padding:0;background:var(--canvas);color:var(--ink)}}.aw-dialog::backdrop{{background:rgba(38,37,30,.62)}}.aw-dialog-head{{position:sticky;top:0;z-index:4;display:flex;justify-content:space-between;align-items:center;gap:16px;padding:14px 16px;background:rgba(247,247,244,.97);border-bottom:1px solid var(--hair)}}.aw-dialog-head strong{{font-size:18px;font-weight:600}}.aw-dialog-head span{{font-size:13px;color:var(--muted)}}.aw-dialog-close{{border:1px solid var(--strong);background:#fff;border-radius:8px;padding:9px 13px;font-size:14px;font-weight:600;color:var(--ink);cursor:pointer}}.aw-dialog-body{{padding:16px;overflow:auto;height:calc(92vh - 64px)}}.aw-dialog .aw-node{{width:250px;min-height:150px}}.aw-dialog .aw-specialists{{grid-template-columns:repeat(6,minmax(220px,1fr));min-width:1420px}}.aw-dialog .aw-branch .aw-node{{width:100%}}
@media(max-width:760px){{.aw-branches{{grid-template-columns:1fr}}.aw{{padding:8px}}.aw-tools{{align-items:flex-start;flex-direction:column}}.aw-lane-head{{align-items:flex-start;flex-direction:column}}}}
</style></head><body><div class="aw">
<div class="aw-help"><b>How to use this diagram:</b> hover over a node for a quick explanation. Click or tap a node to pin its purpose, inputs, outputs, safety boundary, and handoff logic. For easier reading on a smaller screen, open the larger architecture view.</div>
<div class="aw-tools"><span>Need more space?</span><button class="aw-expand" id="openZoom" type="button">Open larger architecture view</button></div>
<div id="mainDiagram">{diagram}</div>
<div id="pinned" class="aw-pinned"></div><div id="tip" class="aw-tip"></div>
<dialog id="zoomDialog" class="aw-dialog"><div class="aw-dialog-head"><div><strong>Pan-Oncology Tumor Board Intelligence</strong><br><span>Expanded architecture view · scroll horizontally where needed</span></div><button id="closeZoom" class="aw-dialog-close" type="button">Close</button></div><div class="aw-dialog-body">{diagram}</div></dialog>
</div><script>
const DETAILS={details_json};
const tip=document.getElementById('tip');const pinned=document.getElementById('pinned');const dialog=document.getElementById('zoomDialog');let pinnedId=null;
function inner(d,close=false){{return `${{close?'<button class="close" onclick="clearPinned()">Close</button>':''}}<div class="k">${{d.number}} · ${{d.type}}</div><h3>${{d.title}}</h3><p><b>Purpose:</b> ${{d.purpose}}</p><p><b>Inputs:</b> ${{d.inputs}}</p><p><b>Output:</b> ${{d.output}}</p><p><b>Safety boundary:</b> ${{d.safety}}</p><p><b>Why this step exists:</b> ${{d.why}}</p>`}}
function placeTip(e){{const pad=14;const w=440;let x=e.clientX+14,y=e.clientY+14;if(x+w>window.innerWidth-pad)x=e.clientX-w-14;if(y+360>window.innerHeight-pad)y=Math.max(pad,window.innerHeight-374);tip.style.left=Math.max(pad,x)+'px';tip.style.top=Math.max(pad,y)+'px'}}
function clearPinned(){{pinnedId=null;pinned.classList.remove('show');pinned.innerHTML='';document.querySelectorAll('.aw-node').forEach(n=>n.classList.remove('pinned'))}}
function bindNodes(){{document.querySelectorAll('.aw-node').forEach(node=>{{const id=node.dataset.id;const d=DETAILS[id];if(!d||node.dataset.bound==='1')return;node.dataset.bound='1';node.addEventListener('mouseenter',e=>{{if(!pinnedId){{tip.innerHTML=inner(d);tip.classList.add('show');placeTip(e)}}}});node.addEventListener('mousemove',e=>{{if(!pinnedId)placeTip(e)}});node.addEventListener('mouseleave',()=>{{if(!pinnedId)tip.classList.remove('show')}});node.addEventListener('focus',e=>{{if(!pinnedId){{tip.innerHTML=inner(d);tip.classList.add('show');const r=node.getBoundingClientRect();placeTip({{clientX:r.right,clientY:r.top}})}}}});node.addEventListener('blur',()=>{{if(!pinnedId)tip.classList.remove('show')}});node.addEventListener('click',()=>{{document.querySelectorAll('.aw-node').forEach(n=>n.classList.remove('pinned'));node.classList.add('pinned');pinnedId=id;tip.classList.remove('show');pinned.innerHTML=inner(d,true);pinned.classList.add('show');if(!dialog.open)pinned.scrollIntoView({{behavior:'smooth',block:'nearest'}})}})}})}}
bindNodes();document.getElementById('openZoom').addEventListener('click',()=>dialog.showModal());document.getElementById('closeZoom').addEventListener('click',()=>dialog.close());dialog.addEventListener('click',e=>{{if(e.target===dialog)dialog.close()}});document.addEventListener('keydown',e=>{{if(e.key==='Escape'&&dialog.open)dialog.close()}});
</script></body></html>'''
    components.html(html, height=1320, scrolling=True)


def render_architecture_page() -> None:
    faculty_css()
    architecture_css()
    inject_xai_theme()
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
