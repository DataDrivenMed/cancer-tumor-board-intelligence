from __future__ import annotations

from html import escape
from typing import Iterable

import streamlit as st


APP_CSS = r"""
<style>
:root {
  --bg: #f7f7f4;
  --surface: #f2f1ed;
  --surface-2: #e6e5e0;
  --text: #26251e;
  --muted: #6b6b6b;
  --border: rgba(38, 37, 30, .10);
  --border-strong: rgba(38, 37, 30, .20);
  --accent: #c08532;
  --accent-dark: #9a6a28;
  --accent-soft: rgba(192, 133, 50, .12);
  --success: #1f8a65;
  --success-soft: rgba(31, 138, 101, .12);
  --error: #cf2d56;
  --error-soft: rgba(207, 45, 86, .10);
  --warning: #c08532;
  --warning-soft: rgba(192, 133, 50, .12);
  --shadow: 0 1px 3px rgba(0,0,0,.05);
  --radius: 4px;
}

html, body, [class*="css"] { font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
.stApp { background: var(--bg); color: var(--text); }
.block-container { max-width: 1480px; padding-top: 2rem; padding-bottom: 5rem; }
[data-testid="stHeader"] { background: rgba(247,247,244,.90); backdrop-filter: blur(10px); border-bottom: 1px solid var(--border); }
[data-testid="stSidebar"] { background: var(--surface); border-right: 1px solid var(--border); }

h1, h2, h3 { color: var(--text); font-weight: 500; letter-spacing: -0.02em; }
h1 { font-size: clamp(2.2rem, 5vw, 3.6rem) !important; line-height: 1.04 !important; }
h2 { font-size: 1.7rem !important; line-height: 1.15 !important; }
h3 { font-size: 1.05rem !important; line-height: 1.35 !important; }
p, li { line-height: 1.55; }
small, .stCaption, [data-testid="stCaptionContainer"] { color: var(--muted) !important; }

.stButton > button, .stFormSubmitButton > button {
  border-radius: 999px !important; border: 1px solid var(--text) !important;
  background: var(--text) !important; color: var(--bg) !important;
  padding: .62rem 1.05rem !important; font-weight: 500 !important;
  box-shadow: none !important; transition: all .14s ease;
}
.stButton > button:hover, .stFormSubmitButton > button:hover { opacity: .90; transform: translateY(-1px); }
.stButton > button:focus-visible, .stFormSubmitButton > button:focus-visible { outline: 2px solid var(--text) !important; outline-offset: 3px !important; }

[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea, [data-testid="stFileUploader"] section {
  background: #fff !important; border: 1px solid var(--border-strong) !important; border-radius: var(--radius) !important;
}
[data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus { border-color: var(--accent) !important; box-shadow: 0 0 0 2px var(--accent-soft) !important; }

[data-testid="stMetric"] { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 14px 16px; box-shadow: var(--shadow); }
[data-testid="stMetricLabel"] { color: var(--muted); font-size: .78rem; text-transform: uppercase; letter-spacing: .06em; }
[data-testid="stMetricValue"] { color: var(--text); font-weight: 520; }

[data-baseweb="tab-list"] { gap: 4px; background: var(--surface); padding: 4px; border-radius: 8px; border: 1px solid var(--border); }
[data-baseweb="tab"] { border-radius: 4px !important; padding: 8px 14px !important; }
[data-baseweb="tab"][aria-selected="true"] { background: #fff !important; box-shadow: var(--shadow); }
[data-baseweb="tab-highlight"] { display:none; }

[data-testid="stExpander"] { background: var(--surface); border: 1px solid var(--border) !important; border-radius: var(--radius) !important; }
[data-testid="stAlert"] { border-radius: var(--radius) !important; box-shadow: none !important; }
hr { border-color: var(--border) !important; }
code, pre { font-family: "IBM Plex Mono", "SFMono-Regular", Consolas, monospace !important; }

.ctb-eyebrow { font-size: .72rem; letter-spacing: .10em; text-transform: uppercase; color: var(--accent-dark); font-weight: 700; }
.ctb-hero { padding: 42px 0 28px 0; border-bottom: 1px solid var(--border); margin-bottom: 22px; }
.ctb-hero h1 { max-width: 980px; margin: 8px 0 14px 0; }
.ctb-hero p { max-width: 920px; color: var(--muted); font-size: 1.06rem; margin: 0; }
.ctb-badge { display:inline-flex; align-items:center; gap:6px; padding:6px 9px; border-radius:999px; border:1px solid var(--border-strong); font-size:.72rem; margin-right:6px; background:#fff; }
.ctb-dot { width:7px; height:7px; border-radius:999px; background:var(--success); display:inline-block; }
.ctb-dot.warn { background:var(--warning); }
.ctb-dot.error { background:var(--error); }

.ctb-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 18px; box-shadow: var(--shadow); height:100%; }
.ctb-card.white { background:#fff; }
.ctb-card.accent { background:var(--accent-soft); border-color:rgba(192,133,50,.28); }
.ctb-card h3 { margin: 0 0 7px 0; }
.ctb-card p { color: var(--muted); margin: 0; }
.ctb-kicker { font-size:.72rem; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); margin-bottom:8px; }
.ctb-number { font-size:2rem; letter-spacing:-.04em; font-weight:520; margin-bottom:4px; }

.ctb-step { display:grid; grid-template-columns: 46px 1fr; gap:12px; align-items:start; padding:16px 0; border-top:1px solid var(--border); }
.ctb-step-index { width:36px; height:36px; border-radius:999px; display:flex; align-items:center; justify-content:center; background:var(--text); color:var(--bg); font-size:.78rem; font-weight:700; }
.ctb-step-title { font-weight:650; margin-bottom:3px; }
.ctb-step-copy { color:var(--muted); font-size:.92rem; }

.arch-stage { position:relative; background:#fff; border:1px solid var(--border); border-radius:8px; padding:20px; margin:12px 0; box-shadow:var(--shadow); }
.arch-stage::before { content:""; position:absolute; left:-1px; top:18px; bottom:18px; width:3px; background:var(--accent); border-radius:3px; }
.arch-title { display:flex; align-items:center; gap:10px; margin-bottom:10px; }
.arch-num { width:28px; height:28px; border-radius:999px; background:var(--text); color:var(--bg); display:flex; align-items:center; justify-content:center; font-size:.74rem; font-weight:700; }
.arch-name { font-size:1rem; font-weight:700; }
.arch-purpose { color:var(--muted); margin-bottom:12px; }
.arch-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px; }
.arch-node { background:var(--surface); border:1px solid var(--border); border-radius:4px; padding:12px; }
.arch-node b { font-size:.82rem; display:block; margin-bottom:4px; }
.arch-node span { color:var(--muted); font-size:.77rem; line-height:1.4; display:block; }
.arch-connector { width:1px; height:20px; background:var(--border-strong); margin:0 auto; }
.arch-guardrail { background:var(--error-soft); border:1px solid rgba(207,45,86,.20); border-radius:4px; padding:10px 12px; margin-top:10px; font-size:.78rem; }
.arch-outcome { background:var(--success-soft); border:1px solid rgba(31,138,101,.22); border-radius:4px; padding:10px 12px; margin-top:10px; font-size:.78rem; }

.ctb-strip { display:flex; flex-wrap:wrap; gap:8px; margin:10px 0 18px 0; }
.ctb-chip { padding:6px 9px; background:#fff; border:1px solid var(--border); border-radius:999px; font-size:.75rem; color:var(--text); }
.ctb-section-head { display:flex; justify-content:space-between; gap:16px; align-items:flex-end; margin:28px 0 10px 0; }
.ctb-section-head p { color:var(--muted); margin:0; max-width:720px; font-size:.9rem; }
.ctb-divider-label { color:var(--muted); font-size:.72rem; text-transform:uppercase; letter-spacing:.08em; margin:24px 0 6px 0; }
.ctb-status-ok { color:var(--success); font-weight:700; }
.ctb-status-warn { color:var(--accent-dark); font-weight:700; }
.ctb-status-block { color:var(--error); font-weight:700; }

@media (max-width: 900px) { .arch-grid { grid-template-columns:1fr; } .ctb-hero { padding-top:24px; } }
</style>
"""


def apply_design_system() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)


def hero(title: str, subtitle: str, eyebrow: str = "Cancer Tumor Board Intelligence") -> None:
    st.markdown(
        f"""
        <section class="ctb-hero">
          <div class="ctb-eyebrow">{escape(eyebrow)}</div>
          <h1>{escape(title)}</h1>
          <p>{escape(subtitle)}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def badge(label: str, kind: str = "ok") -> str:
    cls = "ctb-dot" if kind == "ok" else f"ctb-dot {'warn' if kind == 'warn' else 'error'}"
    return f'<span class="ctb-badge"><span class="{cls}"></span>{escape(label)}</span>'


def architecture_stage(
    number: str,
    name: str,
    purpose: str,
    nodes: Iterable[tuple[str, str]],
    guardrail: str | None = None,
    outcome: str | None = None,
) -> None:
    node_html = "".join(
        f'<div class="arch-node"><b>{escape(title)}</b><span>{escape(copy)}</span></div>'
        for title, copy in nodes
    )
    extras = ""
    if guardrail:
        extras += f'<div class="arch-guardrail"><b>Guardrail:</b> {escape(guardrail)}</div>'
    if outcome:
        extras += f'<div class="arch-outcome"><b>Output:</b> {escape(outcome)}</div>'
    st.markdown(
        f"""
        <div class="arch-stage">
          <div class="arch-title"><span class="arch-num">{escape(number)}</span><span class="arch-name">{escape(name)}</span></div>
          <div class="arch-purpose">{escape(purpose)}</div>
          <div class="arch-grid">{node_html}</div>
          {extras}
        </div>
        """,
        unsafe_allow_html=True,
    )


def connector() -> None:
    st.markdown('<div class="arch-connector"></div>', unsafe_allow_html=True)
