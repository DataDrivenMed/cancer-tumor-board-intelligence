"""
Agentic Workspace (Phase 1 — skeleton only).

A NEW page beside the existing Clinical Workspace. Does nothing yet except
render the Midnight look, a left progress rail, an empty stream, and a
composer. No pipeline logic — that arrives in later phases. The existing
workspace (00_Clinical_Workspace.py) is untouched.
"""
from __future__ import annotations

import streamlit as st

from app.xai_theme import inject_xai_theme

st.set_page_config(
    page_title="Agentic Workspace · Tumor Board Intelligence",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Single source of truth for the Midnight look.
inject_xai_theme()

# Phase-1-only structural CSS for the stream + rail. (Colors come from the theme.)
st.markdown(
    """
<style>
.ag-stream{display:flex;flex-direction:column;gap:13px;padding:6px 0 20px;max-width:820px}
.ag-turn{display:flex;gap:12px}
.ag-av{width:29px;height:29px;flex:none;border-radius:8px;display:grid;place-items:center;font:700 10px/1 var(--mono);margin-top:2px}
.ag-av.agent{background:var(--panelhi);border:1px solid var(--line);color:var(--accent2)}
.ag-av.user{background:var(--accent);color:#231a13}
.ag-who{font:600 11px/1 var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-bottom:6px}
.ag-bubble{flex:1;min-width:0}
.ag-text{font-size:14px;color:var(--body);line-height:1.58}
.ag-empty{border:1px dashed var(--line);border-radius:14px;padding:26px;text-align:center;color:var(--muted);font-size:13px;max-width:820px}
.ag-prog{display:flex;flex-direction:column;gap:2px}
.ag-pstep{display:flex;gap:10px;align-items:center;padding:9px;border-radius:8px;font-size:13px}
.ag-pstep .pn{width:21px;height:21px;flex:none;border-radius:6px;display:grid;place-items:center;font:700 9px/1 var(--mono);background:var(--panel);border:1px solid var(--line);color:var(--muted)}
.ag-pstep .pl{color:var(--muted);font-weight:500}
.ag-pstep.done .pn{background:rgba(108,194,160,.14);border-color:var(--mint);color:var(--mint)}
.ag-pstep.done .pl{color:var(--body)}
.ag-pstep.active{background:var(--panelhi)}
.ag-pstep.active .pn{background:var(--accent);border-color:var(--accent);color:#231a13}
.ag-pstep.active .pl{color:#fff;font-weight:600}
.ag-rail-label{font:600 10px/1 var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin:4px 3px 9px}
.ag-rail-note{font-size:10.5px;color:var(--faint);line-height:1.5;margin-top:9px;padding:0 3px}
</style>
""",
    unsafe_allow_html=True,
)

# ---- session bootstrap (Phase 1 keeps it minimal) ----
if "ag_stage" not in st.session_state:
    st.session_state.ag_stage = "intake"  # intake -> review -> evidence -> analysis -> brief

STAGES = [
    ("intake", "Case intake"),
    ("review", "Review"),
    ("evidence", "Evidence"),
    ("analysis", "Analysis"),
    ("brief", "Decision brief"),
]


def _rail() -> None:
    """Left progress rail: passive, shows where the agent is. Not clickable."""
    current = st.session_state.ag_stage
    order = [s for s, _ in STAGES]
    ci = order.index(current) if current in order else 0
    with st.sidebar:
        st.markdown(
            '<div class="fx-side-brand"><div class="fx-side-mark">TB</div>'
            '<div><div class="fx-side-name">Tumor Board</div>'
            '<div class="fx-side-sub">Agentic workup</div></div></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="ag-rail-label">This workup</div>', unsafe_allow_html=True)
        rows = []
        for i, (_key, label) in enumerate(STAGES):
            cls = "ag-pstep"
            num = str(i + 1)
            if i < ci:
                cls += " done"; num = "\u2713"
            elif i == ci:
                cls += " active"
            rows.append(
                f'<div class="{cls}"><span class="pn">{num}</span>'
                f'<span class="pl">{label}</span></div>'
            )
        st.markdown('<div class="ag-prog">' + "".join(rows) + "</div>", unsafe_allow_html=True)
        st.markdown(
            '<div class="ag-rail-note">The agent moves through these. '
            'You act only at the guardrails.</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="ag-rail-label" style="margin-top:18px">Reference</div>', unsafe_allow_html=True)
        st.page_link("app/pages/03_Architecture.py", label="Architecture", use_container_width=True)
        st.page_link("app/pages/01_Validation.py", label="Validation & scope", use_container_width=True)
        st.page_link("app/pages/02_About.py", label="About", use_container_width=True)


def _stream() -> None:
    """The center conversation surface. Phase 1: one greeting + empty state."""
    st.markdown(
        '<div class="ag-stream">'
        '<div class="ag-turn"><div class="ag-av agent">TB</div>'
        '<div class="ag-bubble"><div class="ag-who">Tumor Board Agent</div>'
        '<div class="ag-text">This is the new agentic workspace (build in progress). '
        'When it is finished, I will run the full tumor-board workup here and pause '
        'only when I need your judgment.</div></div></div>'
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="ag-empty">Stream will appear here. '
        'Phase 1 is the skeleton only \u2014 no case runs yet.</div>',
        unsafe_allow_html=True,
    )


def _composer() -> None:
    st.markdown("<br>", unsafe_allow_html=True)
    st.chat_input("Reply, ask a follow-up, or start a new case\u2026 (inactive in Phase 1)")


_rail()
_stream()
_composer()
