from __future__ import annotations

import streamlit as st


def inject_xai_theme() -> None:
    st.markdown(
        r'''
<style>
:root{
  --x-canvas:#f7f7f4; --x-canvas-soft:#fafaf7; --x-card:#ffffff; --x-card2:#fafaf7;
  --x-mid:#e6e5e0; --x-hair:#e6e5e0; --x-hair-soft:#efeee8; --x-hair-strong:#cfcdc4;
  --x-ink:#26251e; --x-body:#5a5852; --x-muted:#807d72; --x-muted-soft:#a09c92;
  --x-primary:#f54e00; --x-primary-active:#d04200;
  --x-thinking:#dfa88f; --x-grep:#9fc9a2; --x-read:#9fbbe0; --x-edit:#c0a8dd; --x-done:#c08532;
  --x-green:#1f8a65; --x-danger:#cf2d56; --x-amber:#c08532;
}
html,body,[class*=css]{font-family:Inter,system-ui,"Helvetica Neue",Helvetica,Arial,sans-serif!important}
.stApp{background:var(--x-canvas)!important;color:var(--x-ink)!important}
[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:var(--x-canvas)!important}
[data-testid="stHeader"]{background:rgba(247,247,244,.96)!important;border-bottom:1px solid var(--x-hair)!important;backdrop-filter:blur(10px)}
.block-container{max-width:1440px!important;padding-top:1.15rem!important;padding-bottom:4.5rem!important}
h1,h2,h3,h4,h5,h6,p,label,span,div{font-synthesis:none}
h1,h2,h3{color:var(--x-ink)!important;font-weight:400!important}
p,li{color:var(--x-body)}
hr{border-color:var(--x-hair)!important}
code,pre,.stCode,[data-testid="stCodeBlock"]{font-family:"JetBrains Mono",ui-monospace,SFMono-Regular,Consolas,monospace!important}

/* Streamlit primitives */
.stButton>button,.stDownloadButton>button,[data-testid="stFormSubmitButton"] button,[data-testid="stPageLink-NavLink"]{
  border-radius:8px!important;border:1px solid var(--x-hair-strong)!important;
  background:var(--x-card)!important;color:var(--x-ink)!important;box-shadow:none!important;
  font-size:14px!important;font-weight:500!important;min-height:40px!important;padding:.58rem 1rem!important;
  transition:background .14s ease,border-color .14s ease,color .14s ease!important
}
.stButton>button:hover,.stDownloadButton>button:hover,[data-testid="stPageLink-NavLink"]:hover{
  background:#fff!important;border-color:#aaa79d!important;color:var(--x-ink)!important;transform:none!important;box-shadow:none!important
}
.stButton>button[kind="primary"],[data-testid="stFormSubmitButton"] button[kind="primary"]{
  background:var(--x-primary)!important;color:#fff!important;border-color:var(--x-primary)!important
}
.stButton>button[kind="primary"]:hover,[data-testid="stFormSubmitButton"] button[kind="primary"]:hover{
  background:var(--x-primary-active)!important;border-color:var(--x-primary-active)!important;color:#fff!important
}
[data-testid="stPageLink-NavLink"][aria-disabled="true"]{
  background:var(--x-card)!important;border-color:var(--x-primary)!important;color:var(--x-primary)!important;opacity:1!important;box-shadow:none!important
}

.stTextInput input,.stTextArea textarea,.stNumberInput input,.stSelectbox [data-baseweb="select"]>div,[data-testid="stFileUploader"] section{
  background:var(--x-card)!important;color:var(--x-ink)!important;border:1px solid var(--x-hair-strong)!important;border-radius:8px!important;box-shadow:none!important
}
.stTextInput input:focus,.stTextArea textarea:focus,.stNumberInput input:focus{
  border-color:var(--x-primary)!important;box-shadow:0 0 0 2px rgba(245,78,0,.10)!important
}
.stTextInput input::placeholder,.stTextArea textarea::placeholder{color:var(--x-muted-soft)!important}
.stTextInput label,.stTextArea label,.stSelectbox label,.stNumberInput label,.stFileUploader label{color:var(--x-body)!important;font-weight:500!important}
[data-baseweb="popover"],[data-baseweb="menu"],ul[role="listbox"]{background:#fff!important;color:var(--x-ink)!important}
[data-testid="stExpander"]{background:#fff!important;border:1px solid var(--x-hair)!important;border-radius:12px!important;color:var(--x-ink)!important;box-shadow:none!important}
[data-testid="stExpander"] summary{color:var(--x-ink)!important}
.stTabs [data-baseweb="tab-list"]{border-bottom:1px solid var(--x-hair)!important;gap:8px!important;background:transparent!important}
.stTabs [data-baseweb="tab"]{color:var(--x-muted)!important;font-weight:500!important}
.stTabs [aria-selected="true"]{color:var(--x-primary)!important}
[data-testid="stAlert"]{background:#fff!important;border:1px solid var(--x-hair)!important;color:var(--x-body)!important;border-radius:12px!important;box-shadow:none!important}
[data-testid="stMetric"]{background:#fff;border:1px solid var(--x-hair);border-radius:12px;padding:14px 16px;box-shadow:none!important}
[data-testid="stMetricLabel"]{color:var(--x-muted)!important}
[data-testid="stMetricValue"]{color:var(--x-ink)!important;font-weight:400!important}
[data-testid="stDataFrame"]{border:1px solid var(--x-hair)!important;border-radius:12px!important;overflow:hidden}

/* Product header */
.fx-top,.ws-top{border-bottom:1px solid var(--x-hair)!important;padding-bottom:15px!important}
.fx-mark,.ws-mark{background:var(--x-primary)!important;border:1px solid var(--x-primary)!important;color:#fff!important;border-radius:8px!important}
.fx-product,.ws-name{color:var(--x-ink)!important;font-weight:400!important;letter-spacing:-.035em!important}
.fx-author,.fx-mode,.ws-sub,.ws-ready{color:var(--x-muted)!important}

/* Editorial hierarchy */
.fx-hero,.ov-hero{border-color:var(--x-hair)!important}
.fx-kicker,.ws-eye,.eyebrow,.arch-hero .eyebrow,.ov-kicker,.ov-label{
  font-family:"JetBrains Mono",ui-monospace,SFMono-Regular,Consolas,monospace!important;
  text-transform:uppercase!important;letter-spacing:.10em!important;color:var(--x-muted)!important;font-weight:600!important
}
.fx-hero h1,.ov-hero h1,.arch-hero h1,.ws-hero h1{
  color:var(--x-ink)!important;font-weight:400!important;letter-spacing:-.03em!important
}
.fx-hero p,.ov-lede,.ov-sub,.arch-sub{color:var(--x-body)!important}
.fx-section,.ov-section,.arch-section,.ws-section,.fx-panel-title{color:var(--x-ink)!important;font-weight:400!important}
.ov-badge,.fx-synthetic,.chip,.fx-source-chip{border-radius:9999px!important;background:var(--x-card)!important;border:1px solid var(--x-hair-strong)!important;color:var(--x-body)!important}

/* Every workspace hero doubles as concise user instruction */
.ws-hero{padding:28px 0 18px!important;max-width:980px!important}
.ws-hero p{
  position:relative!important;background:var(--x-card)!important;border:1px solid var(--x-hair)!important;
  border-radius:12px!important;padding:34px 16px 14px!important;color:var(--x-body)!important;max-width:900px!important
}
.ws-hero p::before{
  content:"WHAT TO DO HERE";position:absolute;top:12px;left:16px;
  font:600 10px/1.2 "JetBrains Mono",ui-monospace,monospace;letter-spacing:.10em;color:var(--x-primary)
}

/* Cards */
.fx-card,.ov-card,.fx-node,.ov-node,.fx-status,.fx-program,.ws-card,.fact,.decision,.reason,.fx-decision-banner,.fx-answer,.arch-handoff,.arch-principle,.arch-compare>div{
  background:var(--x-card)!important;border:1px solid var(--x-hair)!important;color:var(--x-ink)!important;box-shadow:none!important;border-radius:12px!important
}
.fx-card h3,.ov-card h3,.fx-node strong,.ov-node strong,.fx-status strong,.fx-program strong,.ws-title,.fv,.decision-title,.reason strong,.fx-answer b{color:var(--x-ink)!important}
.fx-card p,.ov-card p,.fx-node span,.ov-node span,.fx-status span,.fx-program span,.ws-copy,.reason div,.evidence-meta,.evidence-text,.fx-answer p{color:var(--x-body)!important}
.fx-icon{background:var(--x-canvas-soft)!important;border:1px solid var(--x-hair)!important;color:var(--x-primary)!important}
.fx-method,.ov-arch,.arch-flow{background:var(--x-card)!important;border:1px solid var(--x-hair)!important;box-shadow:none!important;border-radius:12px!important}
.fx-core,.fx-thirty{background:var(--x-ink)!important;border:1px solid var(--x-ink)!important;box-shadow:none!important;border-radius:12px!important;color:var(--x-canvas)!important}
.fx-core h2,.fx-core strong,.fx-thirty-title,.fx-thirty .fx-val{color:var(--x-canvas)!important}
.fx-core p,.fx-core span,.fx-thirty-sub,.fx-thirty .fx-lbl{color:#d6d3ca!important}
.fx-thirty-cell,.fx-agent{background:rgba(255,255,255,.07)!important;border:1px solid rgba(255,255,255,.15)!important;border-radius:8px!important}
.fx-challenge{background:#fff9f4!important;border:1px solid #f0c7b2!important;color:var(--x-ink)!important;border-radius:12px!important;box-shadow:none!important}
.fx-challenge .fx-panel-title,.fx-challenge p{color:var(--x-ink)!important}
.fx-missing,.ws-alert{background:#fff8e7!important;border:1px solid #ead6a6!important;color:#6f5724!important;border-radius:12px!important}
.ws-call,.fx-chat-note{background:#fff!important;border:1px solid var(--x-hair)!important;color:var(--x-body)!important;border-radius:12px!important}
.fx-context{background:#fff!important;border:1px solid var(--x-hair)!important;box-shadow:none!important;border-radius:12px!important}
.fx-lbl,.fl,.decision-label{font-family:"JetBrains Mono",ui-monospace,monospace!important;color:var(--x-muted)!important;font-weight:600!important;letter-spacing:.08em!important}
.fx-val,.fv{color:var(--x-ink)!important}
.source{color:var(--x-green)!important}

/* Workspace workflow as an in-product agent timeline */
.ws-nav{border:1px solid var(--x-hair)!important;border-radius:9999px!important;min-height:auto!important;padding:9px 13px!important;background:#fff!important}
.ws-nav.active{border-color:var(--x-ink)!important;color:var(--x-ink)!important}
.ws-nav.done{border-color:#8daf91!important;background:#eff7ef!important}
.ws-num{font-family:"JetBrains Mono",ui-monospace,monospace!important;color:var(--x-muted)!important;font-weight:600!important}
.ws-label{color:var(--x-body)!important;font-weight:500!important}
.ws-nav.active .ws-label{color:var(--x-ink)!important;font-weight:600!important}

/* Functional semantic states stay separate from timeline colors */
.ok{background:#edf8f4!important;color:var(--x-green)!important;border:1px solid #b8dfd0!important}
.warn{background:#fff8e7!important;color:#84631c!important;border:1px solid #ead6a6!important}
.bad{background:#fff1f4!important;color:var(--x-danger)!important;border:1px solid #efc2cd!important}
.neutral{background:#f0efeb!important;color:#6d6a62!important;border:1px solid var(--x-hair)!important}

/* Architecture outer page */
.arch-callout{background:#fff!important;border:1px solid var(--x-hair)!important;color:var(--x-body)!important;border-radius:12px!important}
.arch-handoff .criteria{color:#8b6727!important}
.arch-handoff strong,.arch-principle strong{color:var(--x-ink)!important;font-weight:600!important}
.arch-handoff p,.arch-principle p{color:var(--x-body)!important}
.arch-single{border-left-color:var(--x-thinking)!important}.arch-multi{border-left-color:var(--x-grep)!important}

/* Footer */
.fx-footer,.footer{border-color:var(--x-hair)!important;color:var(--x-muted)!important}

/* Persistent product rail */
[data-testid="stSidebar"]{display:block!important;background:var(--x-canvas-soft)!important;border-right:1px solid var(--x-hair)!important;min-width:248px!important;max-width:248px!important}
[data-testid="stSidebarNav"]{display:none!important}
[data-testid="stSidebarContent"]{padding:15px 13px 20px!important}
[data-testid="collapsedControl"]{display:none!important}
.fx-side-brand{display:flex;align-items:center;gap:10px;padding:4px 3px 16px;border-bottom:1px solid var(--x-hair);margin-bottom:15px}
.fx-side-mark{width:32px;height:32px;border-radius:8px;background:var(--x-primary);display:grid;place-items:center;color:#fff;font:600 9px/1 "JetBrains Mono",monospace}
.fx-side-name{font-size:15px;color:var(--x-ink);letter-spacing:-.02em;font-weight:500}.fx-side-sub{font-size:10px;color:var(--x-muted);margin-top:2px}
.fx-side-label{font:600 9px/13px "JetBrains Mono",monospace;letter-spacing:.10em;text-transform:uppercase;color:var(--x-muted);margin:18px 3px 7px}
.fx-side-case{border:1px solid var(--x-hair);background:#fff;border-radius:12px;padding:12px;margin-bottom:6px}.fx-side-case strong{display:block;color:var(--x-ink);font-size:14px;font-weight:600;line-height:1.3;margin-top:6px}.fx-side-case span{display:block;color:var(--x-body);font-size:10px;line-height:1.45;margin-top:3px}.fx-side-case small{display:block;color:var(--x-muted);font-size:9px;margin-top:7px}
.fx-side-live,.fx-side-idle{font:600 8px/11px "JetBrains Mono",monospace;text-transform:uppercase;letter-spacing:.08em}.fx-side-live{color:var(--x-green)}.fx-side-idle{color:var(--x-muted)}
.fx-side-system,.fx-side-help{border:1px solid var(--x-hair);background:#fff;border-radius:12px;padding:11px}.fx-side-system div{display:flex;align-items:center;gap:7px;margin:3px 0}.fx-side-system i{width:7px;height:7px;border-radius:50%;background:var(--x-green);display:block}.fx-side-system i.amber{background:var(--x-amber)}.fx-side-system strong{font-size:9px;color:var(--x-ink);font-weight:600}.fx-side-system span{display:block;color:var(--x-muted);font-size:8px;line-height:1.4;margin:5px 0 8px}
.fx-side-help strong{display:block;color:var(--x-primary);font:600 9px/13px "JetBrains Mono",monospace;text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px}.fx-side-help span{display:block;color:var(--x-body);font-size:10px;line-height:1.5}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]{justify-content:flex-start!important;border-radius:8px!important;border-color:transparent!important;min-height:34px!important;padding:.38rem .55rem!important;margin:2px 0!important;color:var(--x-body)!important;background:transparent!important}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover{background:#fff!important;border-color:var(--x-hair)!important;color:var(--x-ink)!important}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-disabled="true"]{background:#fff!important;border-color:var(--x-primary)!important;color:var(--x-primary)!important}

/* top navigation stays quiet */
.block-container > div [data-testid="stPageLink-NavLink"]{box-shadow:none!important}

/* reduce visual chrome */
[data-testid="stVerticalBlockBorderWrapper"]{border-color:var(--x-hair)!important}

@media(max-width:1024px){
 .block-container{max-width:100%!important;padding-left:1rem!important;padding-right:1rem!important}
 .fx-product,.ws-name{font-size:22px!important}
 .ov-hero h1,.fx-hero h1{font-size:50px!important}
}
@media(max-width:700px){
 [data-testid="stSidebar"]{min-width:220px!important;max-width:220px!important}
 .ov-hero h1,.fx-hero h1,.ws-hero h1{font-size:34px!important}
 .ws-hero p{padding-top:34px!important}
}
</style>
''',
        unsafe_allow_html=True,
    )
