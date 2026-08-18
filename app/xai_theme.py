from __future__ import annotations

import streamlit as st


def inject_xai_theme() -> None:
    """Signal design system — the single authoritative theme for every page.

    Deep-indigo canvas, violet + mint accents. Safe-fallback styling only:
    no gradient-clipped text, no backdrop-blur, no glow shadows — everything
    here renders identically across Streamlit versions. Premium comes from
    contrast, spacing rhythm, one restrained accent, crisp bordered cards,
    hover-lift, and a mint 'verified' system that carries auditability.

    This file is the whole look. It re-themes the existing component classes
    (ov-*, fx-*, ws-*, arch-*, tb-*) so the page files barely need to change.
    """
    st.markdown(
        r'''
<style>
:root{
  --bg:#0f1120; --bg2:#0c0e1a; --panel:#181b30; --panel2:#141729; --panelhi:#1d2138;
  --line:#282c47; --line2:#20233a; --linehi:#343a5e;
  --ink:#f4f5fb; --body:#b7bad2; --muted:#818599; --faint:#5f6379;
  --violet:#7c7bff; --violet2:#9d6bff; --violet-ink:#c9c8ff;
  --mint:#54e0c8; --mint-dim:#3bbfa8;
  --warn:#ffc54d; --danger:#ff6f7d; --verified:#54e0c8;
  --mono:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  --x-canvas:#0f1120; --x-canvas-soft:#141729; --x-card:#181b30; --x-card2:#141729;
  --x-mid:#282c47; --x-hair:#282c47; --x-hair-soft:#20233a; --x-hair-strong:#343a5e;
  --x-ink:#f4f5fb; --x-body:#b7bad2; --x-muted:#818599; --x-muted-soft:#5f6379;
  --x-primary:#7c7bff; --x-primary-active:#9d6bff;
  --x-thinking:#7c7bff; --x-grep:#54e0c8; --x-read:#7c7bff; --x-edit:#9d6bff; --x-done:#54e0c8;
  --x-green:#54e0c8; --x-danger:#ff6f7d; --x-amber:#ffc54d;
  --r:14px; --rlg:18px; --rsm:9px;
}
html,body,[class*=css]{font-family:Inter,system-ui,"Helvetica Neue",Helvetica,Arial,sans-serif!important}
.stApp{background:var(--bg)!important;color:var(--ink)!important}
[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:var(--bg)!important}
[data-testid="stHeader"]{background:rgba(15,17,32,.92)!important;border-bottom:1px solid var(--line)!important}
.block-container{max-width:1200px!important;padding-top:1.1rem!important;padding-bottom:4.5rem!important}
h1,h2,h3,h4,h5,h6{color:var(--ink)!important;font-weight:600!important;letter-spacing:-.02em!important}
p,li{color:var(--body)}
hr{border-color:var(--line)!important}
code,pre,.stCode,[data-testid="stCodeBlock"]{font-family:var(--mono)!important;background:var(--panel2)!important;color:var(--mint)!important}

.stButton>button,.stDownloadButton>button,[data-testid="stFormSubmitButton"] button,[data-testid="stPageLink-NavLink"]{
  border-radius:11px!important;border:1px solid var(--line)!important;background:var(--panel)!important;color:var(--ink)!important;
  box-shadow:none!important;font-size:14px!important;font-weight:600!important;min-height:42px!important;padding:.62rem 1.1rem!important;
  transition:background .15s ease,border-color .15s ease,color .15s ease!important}
.stButton>button:hover,.stDownloadButton>button:hover,[data-testid="stPageLink-NavLink"]:hover{
  background:var(--panelhi)!important;border-color:var(--violet)!important;color:#fff!important;transform:none!important}
.stButton>button[kind="primary"],[data-testid="stFormSubmitButton"] button[kind="primary"]{
  background:var(--violet)!important;color:#fff!important;border-color:var(--violet)!important}
.stButton>button[kind="primary"]:hover,[data-testid="stFormSubmitButton"] button[kind="primary"]:hover{
  background:var(--violet2)!important;border-color:var(--violet2)!important;color:#fff!important}
[data-testid="stPageLink-NavLink"][aria-disabled="true"]{background:var(--panelhi)!important;border-color:var(--violet)!important;color:var(--violet-ink)!important;opacity:1!important}

.stTextInput input,.stTextArea textarea,.stNumberInput input,.stSelectbox [data-baseweb="select"]>div,[data-testid="stFileUploader"] section{
  background:var(--panel2)!important;color:var(--ink)!important;border:1px solid var(--line)!important;border-radius:9px!important;box-shadow:none!important}
.stTextInput input,.stTextArea textarea,.stNumberInput input{font-size:15px!important}
.stTextInput input:focus,.stTextArea textarea:focus,.stNumberInput input:focus{
  border-color:var(--violet)!important;box-shadow:0 0 0 2px rgba(124,123,255,.18)!important}
.stTextInput input::placeholder,.stTextArea textarea::placeholder{color:var(--faint)!important}
.stTextInput label,.stTextArea label,.stSelectbox label,.stNumberInput label,.stFileUploader label{color:var(--body)!important;font-weight:500!important;font-size:14px!important}
[data-baseweb="popover"],[data-baseweb="menu"],ul[role="listbox"]{background:var(--panel)!important;color:var(--ink)!important}
[data-baseweb="select"] span{color:var(--ink)!important}
[data-testid="stExpander"]{background:var(--panel)!important;border:1px solid var(--line)!important;border-radius:12px!important;box-shadow:none!important}
[data-testid="stExpander"] summary,[data-testid="stExpander"] summary p{color:var(--ink)!important;font-size:14.5px!important}
.stTabs [data-baseweb="tab-list"]{border-bottom:1px solid var(--line)!important;gap:4px!important;background:transparent!important}
.stTabs [data-baseweb="tab"]{color:var(--muted)!important;font-weight:600!important;font-size:13.5px!important;padding:.65rem .9rem!important}
.stTabs [aria-selected="true"]{color:var(--mint)!important}
.stTabs [data-baseweb="tab-highlight"]{background:var(--mint)!important}
[data-testid="stAlert"]{background:var(--panel)!important;border:1px solid var(--line)!important;color:var(--body)!important;border-radius:12px!important;box-shadow:none!important}
[data-testid="stAlert"] p{color:var(--body)!important}
[data-testid="stMetric"]{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
[data-testid="stMetricLabel"]{color:var(--muted)!important}[data-testid="stMetricValue"]{color:var(--ink)!important}
[data-testid="stDataFrame"]{border:1px solid var(--line)!important;border-radius:12px!important;overflow:hidden}
[data-testid="stCaptionContainer"]{color:var(--muted)!important;font-size:13px!important}
[data-testid="stChatInput"] textarea{background:var(--panel2)!important;color:var(--ink)!important;border:1px solid var(--line)!important}

.fx-kicker,.ws-eye,.eyebrow,.ov-kicker,.ov-label,.arch-hero .eyebrow,.sect-label,.fx-lbl,.fl,.decision-label,.dv-eyebrow{
  font-family:var(--mono)!important;text-transform:uppercase!important;letter-spacing:.13em!important;color:var(--muted)!important;font-weight:600!important;font-size:11px!important}

.fx-hero h1,.ov-hero h1,.arch-hero h1,.ws-hero h1,.hero h2,.arch-hero h2{
  color:var(--ink)!important;font-weight:600!important;letter-spacing:-.7px!important}
.fx-hero p,.ov-lede,.ov-sub,.arch-sub,.hero p,.arch-hero .lead{color:var(--body)!important}
.fx-section,.ov-section,.arch-section,.ws-section,.fx-panel-title,.sect-h{color:var(--ink)!important;font-weight:600!important}

.fx-card,.ov-card,.fx-node,.ov-node,.fx-status,.fx-program,.ws-card,.fact,.decision,.reason,
.fx-decision-banner,.fx-answer,.arch-handoff,.arch-principle,.arch-compare>div,.ov-step,.ov-agent-item,
.ov-safeguard,.ov-preview,.channel,.agent,.card,.prog,.principle,.comp{
  background:var(--panel)!important;border:1px solid var(--line)!important;color:var(--ink)!important;box-shadow:none!important;border-radius:var(--r)!important}
.fx-card p,.ov-card p,.fx-node span,.ws-copy,.fx-status span,.fx-program span,.card-c,.agent-d,.reason div{color:var(--body)!important}
.ws-card.soft,.fx-card.soft,.soft{background:var(--panel2)!important}
.fx-icon,.ov-step-num,.step-num{color:var(--violet)!important}

.fx-thirty,.fx-core,.decision{background:var(--panelhi)!important;border:1px solid var(--line)!important;border-left:3px solid var(--violet)!important;color:var(--ink)!important;border-radius:var(--rlg)!important}
.fx-thirty .fx-val,.fx-core h2,.fx-core strong,.fx-thirty-title,.decision-title,.d-title{color:var(--ink)!important}
.fx-thirty .fx-lbl,.fx-core p,.fx-thirty-sub,.d-label{color:var(--mint)!important}
.fx-thirty-cell,.fx-agent{background:var(--panel)!important;border:1px solid var(--line2)!important;border-radius:12px!important}

.fx-val,.fv,.fx-thirty .fx-val{color:var(--ink)!important;font-weight:600!important}
.source{color:var(--mint)!important;font-weight:600!important;font-size:12px!important}

.chip,.fx-source-chip,.ov-badge,.fx-synthetic{border-radius:999px!important;font-weight:600!important;font-family:var(--mono)!important;font-size:10.5px!important;text-transform:uppercase!important;letter-spacing:.05em!important}
.chip.ok,.ok{background:rgba(84,224,200,.1)!important;color:var(--mint)!important;border:1px solid rgba(84,224,200,.25)!important}
.chip.warn,.warn{background:rgba(255,197,77,.1)!important;color:var(--warn)!important;border:1px solid rgba(255,197,77,.25)!important}
.chip.bad,.bad{background:rgba(255,111,125,.1)!important;color:var(--danger)!important;border:1px solid rgba(255,111,125,.25)!important}
.chip.neutral,.neutral,.chip.off{background:var(--panel2)!important;color:var(--muted)!important;border:1px solid var(--line2)!important}

.fx-missing,.ws-alert{background:rgba(255,197,77,.07)!important;border:1px solid rgba(255,197,77,.28)!important;color:var(--warn)!important;border-radius:var(--r)!important}
.fx-missing strong,.fx-missing p{color:var(--warn)!important}
.fx-challenge{background:var(--panelhi)!important;border:1px solid var(--line)!important;color:var(--ink)!important;border-radius:var(--r)!important}
.fx-challenge .fx-panel-title,.fx-challenge p{color:var(--ink)!important}
.ws-call,.fx-chat-note,.arch-callout,.callout{background:var(--panel2)!important;border:1px solid var(--line2)!important;color:var(--body)!important;border-radius:var(--r)!important}

.ws-nav{border:1px solid var(--line2)!important;border-radius:var(--r)!important;background:var(--panel2)!important;min-height:auto!important;padding:12px 14px!important}
.ws-nav .ws-num{color:var(--muted)!important;font-family:var(--mono)!important;font-weight:700!important}
.ws-nav .ws-label{color:var(--body)!important;font-weight:600!important}
.ws-nav.active{border-color:var(--violet)!important;background:var(--panelhi)!important}
.ws-nav.active .ws-label{color:#fff!important}.ws-nav.active .ws-num{color:var(--violet)!important}
.ws-nav.done{border-color:rgba(84,224,200,.28)!important}
.ws-nav.done .ws-num{color:var(--mint)!important}.ws-nav.done .ws-label{color:var(--ink)!important}

.tb-chat-shell,.tb-answer{background:var(--panel)!important;border:1px solid var(--line)!important;border-radius:var(--r)!important}
.tb-chat-head{background:var(--panel2)!important;color:var(--ink)!important;border:1px solid var(--line)!important;border-radius:12px!important}
.tb-chat-head strong{color:var(--ink)!important;font-size:16px!important}.tb-chat-head span{color:var(--muted)!important;font-size:12px!important}
.tb-chat-note{background:var(--panel2)!important;border:1px solid var(--line2)!important;color:var(--muted)!important;border-radius:9px!important}
.tb-chat-note strong{color:var(--violet-ink)!important}
.tb-user{color:var(--ink)!important}.tb-status{color:var(--muted)!important;font-family:var(--mono)!important}
.tb-answer-text{color:var(--body)!important;font-size:13.5px!important}
.tb-block-title{color:var(--muted)!important;font-family:var(--mono)!important}
.tb-chip{background:var(--panel2)!important;color:var(--body)!important;border:1px solid var(--line2)!important}
.tb-limit{background:rgba(255,197,77,.07)!important;border:1px solid rgba(255,197,77,.28)!important;color:var(--warn)!important}
.tb-change{color:var(--body)!important}
[data-testid="stChatInput"]{background:var(--bg)!important;border-top:1px solid var(--line)!important}

[data-testid="stSidebar"]{background:var(--bg2)!important;border-right:1px solid var(--line)!important;min-width:270px!important;max-width:270px!important}
[data-testid="stSidebarNav"]{display:none!important}
[data-testid="stSidebarContent"]{padding:17px 15px 22px!important}
.fx-side-brand{display:flex;align-items:center;gap:10px;padding:4px 3px 15px;border-bottom:1px solid var(--line);margin-bottom:14px;flex-wrap:wrap}
.fx-side-mark{width:34px;height:34px;border-radius:9px;background:var(--violet);display:grid;place-items:center;color:#fff;font:800 10px/1 var(--mono)}
.fx-side-name{font-size:15px;color:var(--ink);font-weight:600}.fx-side-sub{font-size:12px;color:var(--muted);margin-top:2px}
.fx-side-label{font:600 10px/14px var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--muted);margin:16px 3px 7px}
.fx-side-case{border:1px solid var(--line);background:var(--panel);border-radius:12px;padding:13px;margin-bottom:6px}
.fx-side-case strong{display:block;color:var(--ink);font-size:14px;font-weight:600;margin-top:6px}
.fx-side-case span{display:block;color:var(--body);font-size:12.5px;margin-top:4px}.fx-side-case small{display:block;color:var(--muted);font-size:11.5px;margin-top:7px}
.fx-side-live{font:600 10px/12px var(--mono);text-transform:uppercase;color:var(--mint)}.fx-side-idle{font:600 10px/12px var(--mono);text-transform:uppercase;color:var(--muted)}
.fx-side-system{border:1px solid var(--line);background:var(--panel);border-radius:12px;padding:12px}
.fx-side-system div{display:flex;align-items:center;gap:7px;margin:4px 0}.fx-side-system i{width:7px;height:7px;border-radius:50%;background:var(--mint);display:block}.fx-side-system i.amber{background:var(--warn)}
.fx-side-system strong{font-size:12px;color:var(--ink);font-weight:600}.fx-side-system span{display:block;color:var(--muted);font-size:11.5px;margin:6px 0 9px}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]{justify-content:flex-start!important;border-color:transparent!important;background:transparent!important;min-height:40px!important;padding:.48rem .62rem!important;margin:2px 0!important;color:var(--body)!important;font-size:14px!important}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover{background:var(--panel)!important;border-color:var(--line)!important;color:var(--ink)!important}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-disabled="true"]{background:var(--panelhi)!important;border-color:var(--violet)!important;color:var(--violet-ink)!important}
[data-testid="collapsedControl"]{display:none!important}

/* ---------- top nav tabs (override old pastel per-href colors; Signal premium) ---------- */
/* These beat faculty_ui's hardcoded pastels regardless of load order. */
.block-container [data-testid="stPageLink-NavLink"],
.block-container [data-testid="stPageLink-NavLink"][href*="Clinical_Workspace"],
.block-container [data-testid="stPageLink-NavLink"][href*="Workspace"],
.block-container [data-testid="stPageLink-NavLink"][href*="Validation"],
.block-container [data-testid="stPageLink-NavLink"][href*="Architecture"],
.block-container [data-testid="stPageLink-NavLink"][href*="About"],
.block-container [data-testid="stPageLink-NavLink"][href*="main"]{
  background:var(--panel)!important;border:1px solid var(--line)!important;color:var(--body)!important;
  border-radius:11px!important;font-weight:600!important;font-size:14px!important;letter-spacing:-.005em!important;
  min-height:44px!important;transition:background .15s ease,border-color .15s ease,color .15s ease!important}
.block-container [data-testid="stPageLink-NavLink"]:hover{
  background:var(--panelhi)!important;border-color:var(--violet)!important;color:#fff!important}
/* active tab: mint underline accent + brighter text, unmistakable on dark */
.block-container [data-testid="stPageLink-NavLink"][aria-disabled="true"]{
  background:var(--panelhi)!important;border-color:var(--mint)!important;color:#fff!important;
  box-shadow:inset 0 -2px 0 0 var(--mint)!important;opacity:1!important}

/* sidebar nav links keep their own quieter treatment (defined above), unaffected here */

.fx-footer,.footer{border-top:1px solid var(--line)!important;color:var(--muted)!important;margin-top:34px;padding:16px 0}
.fx-footer{display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap;font-size:12px!important}

.verified{display:inline-flex;align-items:center;gap:5px;font:600 10px/1 var(--mono);color:var(--mint);text-transform:uppercase;letter-spacing:.05em}
.verified.review-needed{color:var(--warn)}

/* ---------- catch-all: panels that were LIGHT or intentionally-dark in the
   old themes and now render wrong on the Signal canvas. Force dark bg + readable
   text so nothing is ever pale-on-pale or white-on-white. High specificity via
   .stApp prefix so these win over leftover !important pastels. ---------- */
.stApp .ov-clinician,.stApp .ov-agents,.stApp .ov-assistant-intro,.stApp .ov-preview,
.stApp .ov-step,.stApp .ov-card,.stApp .arch-node-card,.stApp .arch-callout,
.stApp .fx-chat-head,.stApp .fx-answer,.stApp .fx-thirty,.stApp .fx-core{
  background:var(--panel)!important;border:1px solid var(--line)!important;border-radius:var(--r)!important}
/* the two "feature" dark panels lift a shade and keep the violet edge */
.stApp .ov-clinician,.stApp .fx-thirty,.stApp .fx-core{
  background:var(--panelhi)!important;border-left:3px solid var(--violet)!important}
/* force ALL descendant text in these panels to readable Signal colors */
.stApp .ov-clinician *,.stApp .ov-agents *,.stApp .ov-assistant-intro *,.stApp .ov-preview *,
.stApp .ov-step *,.stApp .ov-card *,.stApp .arch-node-card *,.stApp .arch-callout *,
.stApp .ov-clinician-item *,.stApp .ov-agent-item *{
  color:var(--body)!important}
.stApp .ov-clinician h3,.stApp .ov-clinician-item strong,.stApp .ov-agents h3,
.stApp .ov-card h3,.stApp .ov-step strong,.stApp .ov-assistant-intro h3,
.stApp .ov-preview strong,.stApp .arch-node-card strong{color:var(--ink)!important;font-weight:600!important}
/* inner sub-cells (grids inside feature panels) get a slightly deeper fill for separation */
.stApp .ov-clinician-item,.stApp .ov-agent-item,.stApp .ov-preview-cell{
  background:var(--panel)!important;border:1px solid var(--line2)!important;border-radius:10px!important}
/* eyebrow/label text inside these stays muted-mono, not body */
.stApp .ov-clinician .ov-kicker,.stApp .ov-card .ov-label,.stApp .ov-agents .ov-kicker,
.stApp .ov-preview-cell span{color:var(--muted)!important}

@media(max-width:1024px){
  .block-container{max-width:100%!important;padding-left:1rem!important;padding-right:1rem!important}
  [data-testid="stSidebar"]{min-width:240px!important;max-width:240px!important}
}
</style>
'''
        ,
        unsafe_allow_html=True,
    )
