from __future__ import annotations

import streamlit as st


def inject_xai_theme() -> None:
    st.markdown(
        r'''
<style>
:root{
  --x-canvas:#0a0a0a; --x-card:#141414; --x-card2:#191919; --x-mid:#26282c;
  --x-hair:#2a2d31; --x-ink:#ffffff; --x-body:#dadbdf; --x-muted:#7d8187;
  --x-blue:#3c8dde; --x-rose:#d8587e; --x-amber:#ca8514; --x-teal:#239783;
  --x-plum:#8d62c5; --x-danger:#d86a6a; --x-green:#35b88a;
}
html,body,[class*=css]{font-family:Inter,Geist,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif!important}
.stApp{background:var(--x-canvas)!important;color:var(--x-ink)!important}
[data-testid="stAppViewContainer"], [data-testid="stMain"]{background:var(--x-canvas)!important}
[data-testid="stHeader"]{background:rgba(10,10,10,.92)!important;border-bottom:1px solid var(--x-hair)!important}
.block-container{max-width:1500px!important;padding-top:1.1rem!important}
h1,h2,h3,h4,h5,h6,p,label,span,div{font-synthesis:none}
h1,h2,h3{font-weight:400!important;color:var(--x-ink)!important}
p{color:var(--x-body)}
hr{border-color:var(--x-hair)!important}

/* Streamlit primitives */
.stButton>button,.stDownloadButton>button,[data-testid="stFormSubmitButton"] button,[data-testid="stPageLink-NavLink"]{
  border-radius:9999px!important;border:1px solid rgba(255,255,255,.26)!important;
  background:transparent!important;color:#fff!important;box-shadow:none!important;
  font-size:14px!important;font-weight:400!important;min-height:40px!important;padding:.48rem 1rem!important;
  transition:background .15s ease,border-color .15s ease,opacity .15s ease!important
}
.stButton>button:hover,.stDownloadButton>button:hover,[data-testid="stPageLink-NavLink"]:hover{
  background:#1a1c20!important;border-color:rgba(255,255,255,.52)!important;color:#fff!important;transform:none!important;box-shadow:none!important
}
.stButton>button[kind="primary"],[data-testid="stFormSubmitButton"] button[kind="primary"]{
  background:#fff!important;color:#0a0a0a!important;border-color:#fff!important
}
[data-testid="stPageLink-NavLink"][aria-disabled="true"]{background:#1a1c20!important;border-color:rgba(255,255,255,.5)!important;opacity:1!important;box-shadow:none!important}
[data-testid="stPageLink-NavLink"][href*="Clinical_Workspace"],
[data-testid="stPageLink-NavLink"][href*="Validation"],
[data-testid="stPageLink-NavLink"][href*="Architecture"],
[data-testid="stPageLink-NavLink"][href*="About"]{background:transparent!important;color:#fff!important;border-color:rgba(255,255,255,.26)!important}

.stTextInput input,.stTextArea textarea,.stNumberInput input,.stSelectbox [data-baseweb="select"]>div,[data-testid="stFileUploader"] section{
  background:#151619!important;color:#fff!important;border:1px solid var(--x-hair)!important;border-radius:8px!important;box-shadow:none!important
}
.stTextInput input::placeholder,.stTextArea textarea::placeholder{color:var(--x-muted)!important}
.stTextInput label,.stTextArea label,.stSelectbox label,.stNumberInput label,.stFileUploader label{color:var(--x-body)!important;font-weight:400!important}
[data-baseweb="popover"],[data-baseweb="menu"],ul[role="listbox"]{background:#191919!important;color:#fff!important}
[data-testid="stExpander"]{background:#111!important;border:1px solid var(--x-hair)!important;border-radius:8px!important;color:#fff!important}
[data-testid="stExpander"] summary{color:#fff!important}
.stTabs [data-baseweb="tab-list"]{border-bottom:1px solid var(--x-hair)!important;gap:8px!important}
.stTabs [data-baseweb="tab"]{color:var(--x-muted)!important;font-weight:400!important}
.stTabs [aria-selected="true"]{color:#fff!important}
[data-testid="stAlert"]{background:#141414!important;border:1px solid var(--x-hair)!important;color:var(--x-body)!important;border-radius:8px!important}
[data-testid="stMetric"]{background:#141414;border:1px solid var(--x-hair);border-radius:8px;padding:14px 16px}
[data-testid="stMetricLabel"]{color:var(--x-muted)!important}
[data-testid="stMetricValue"]{color:#fff!important;font-weight:400!important}

/* Product header */
.fx-top,.ws-top{border-bottom:1px solid var(--x-hair)!important;padding-bottom:15px!important}
.fx-mark,.ws-mark{background:#0a0a0a!important;border:1px solid rgba(255,255,255,.34)!important;color:#fff!important;border-radius:9999px!important}
.fx-product,.ws-name{color:#fff!important;font-weight:400!important;letter-spacing:-.04em!important}
.fx-author,.fx-mode,.ws-sub,.ws-ready{color:var(--x-muted)!important}

/* Overview / editorial hierarchy */
.fx-hero,.ov-hero{border-color:var(--x-hair)!important}
.fx-kicker,.ws-eye,.eyebrow,.arch-hero .eyebrow,.ov-author{font-family:"Geist Mono","IBM Plex Mono",ui-monospace,monospace!important;text-transform:uppercase!important;letter-spacing:.12em!important;color:var(--x-body)!important;font-weight:400!important}
.fx-hero h1,.ov-hero h1,.arch-hero h1,.ws-hero h1{color:#fff!important;font-weight:400!important;letter-spacing:-.045em!important}
.fx-hero p,.ov-lede,.ov-sub,.arch-sub,.ws-hero p{color:var(--x-body)!important}
.fx-section,.ov-section,.arch-section,.ws-section,.fx-panel-title{color:#fff!important;font-weight:400!important}
.ov-badge,.fx-synthetic,.chip,.fx-source-chip{border-radius:9999px!important;background:transparent!important;border:1px solid rgba(255,255,255,.24)!important;color:var(--x-body)!important}

/* Cards */
.fx-card,.ov-card,.fx-node,.ov-node,.fx-status,.fx-program,.ws-card,.fact,.decision,.reason,.fx-decision-banner,.fx-answer,.arch-handoff,.arch-principle,.arch-compare>div{
  background:var(--x-card)!important;border:1px solid var(--x-hair)!important;color:#fff!important;box-shadow:none!important;border-radius:8px!important
}
.fx-card h3,.ov-card h3,.fx-node strong,.ov-node strong,.fx-status strong,.fx-program strong,.ws-title,.fv,.decision-title,.reason strong,.fx-answer b{color:#fff!important;font-weight:400!important}
.fx-card p,.ov-card p,.fx-node span,.ov-node span,.fx-status span,.fx-program span,.ws-copy,.reason div,.evidence-meta,.evidence-text,.fx-answer p{color:var(--x-body)!important}
.fx-icon{background:#111!important;border:1px solid var(--x-hair)!important}
.fx-method,.ov-arch,.arch-flow{background:#0d0d0d!important;border:1px solid var(--x-hair)!important;box-shadow:none!important;border-radius:8px!important}
.fx-core,.fx-thirty,.fx-challenge{background:#111!important;border:1px solid var(--x-hair)!important;box-shadow:none!important;border-radius:8px!important}
.fx-thirty-cell,.fx-agent{background:#191919!important;border:1px solid var(--x-hair)!important}
.fx-missing,.ws-alert{background:#16130d!important;border-color:#503a14!important;color:#e5c783!important}
.ws-call,.fx-chat-note{background:#101418!important;border-color:#28343d!important;color:#c7d7e1!important}
.fx-context{background:#111!important;border:1px solid var(--x-hair)!important;box-shadow:none!important;border-radius:8px!important}
.fx-lbl,.fl,.decision-label{font-family:"Geist Mono","IBM Plex Mono",ui-monospace,monospace!important;color:var(--x-muted)!important;font-weight:400!important;letter-spacing:.1em!important}
.fx-val,.fv{color:#fff!important}
.source{color:var(--x-green)!important}

/* Chat */
.fx-chat-head{background:#0d0d0d!important;border:1px solid rgba(255,255,255,.28)!important;border-radius:8px!important;color:#fff!important}
.fx-chat-head strong{font-weight:400!important;font-size:22px!important}
.fx-chat-head span{color:var(--x-body)!important;font-size:12px!important}
.fx-answer{padding:15px 16px!important}
.fx-source-chip{font-size:10px!important}

/* Workspace stage nav */
.ws-nav{border:1px solid transparent!important;border-radius:9999px!important;min-height:auto!important;padding:9px 13px!important}
.ws-nav.active{border-color:rgba(255,255,255,.4)!important;background:#18191b!important}
.ws-nav.done{border-color:#245c50!important;background:#0d1714!important}
.ws-num{font-family:"Geist Mono","IBM Plex Mono",ui-monospace,monospace!important;color:var(--x-muted)!important;font-weight:400!important}
.ws-label{color:var(--x-body)!important;font-weight:400!important}
.ws-nav.active .ws-label{color:#fff!important;font-weight:400!important}

/* status color preserved functionally */
.ok{background:#0e201a!important;color:#6fd4ae!important;border:1px solid #244d40!important}
.warn{background:#211a0e!important;color:#dfbd70!important;border:1px solid #54431e!important}
.bad{background:#251111!important;color:#e89797!important;border:1px solid #5d2929!important}
.neutral{background:#17181a!important;color:#aeb2b8!important;border:1px solid #33363a!important}

/* architecture */
.arch-callout{background:#111!important;border:1px solid var(--x-hair)!important;color:var(--x-body)!important}
.arch-handoff .criteria{color:#ddb761!important}
.arch-handoff strong,.arch-principle strong{color:#fff!important;font-weight:400!important}
.arch-handoff p,.arch-principle p{color:var(--x-body)!important}
.arch-single{border-left-color:var(--x-rose)!important}.arch-multi{border-left-color:var(--x-teal)!important}

/* footer */
.fx-footer,.footer{border-color:var(--x-hair)!important;color:var(--x-muted)!important}

/* reduce visual chrome */
[data-testid="stVerticalBlockBorderWrapper"]{border-color:var(--x-hair)!important}

@media(max-width:700px){
 .fx-product,.ws-name{font-size:22px!important}
 .ov-hero h1,.fx-hero h1{font-size:44px!important}
}
</style>
''',
        unsafe_allow_html=True,
    )
