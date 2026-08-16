from __future__ import annotations

import streamlit as st

ARTICLE_URL = "https://datadrivenmed.github.io/resources/ai-agents/"

st.set_page_config(page_title="Agent Anatomy | Tumor Board Intelligence", page_icon="🧭", layout="wide")

st.markdown(
    """
<style>
:root{--bg:#f7f7f4;--surface:#f2f1ed;--text:#26251e;--muted:#77746b;--border:rgba(38,37,30,.11);--accent:#c08532;--accent-dark:#9a6a28;--success:#1f8a65;--error:#cf2d56;}
html,body,[class*="css"]{font-family:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;}
.stApp{background:var(--bg);color:var(--text)}
.block-container{max-width:1480px;padding-top:1.6rem;padding-bottom:4rem}
[data-testid="stHeader"]{background:rgba(247,247,244,.94);border-bottom:1px solid var(--border);backdrop-filter:blur(10px)}
h1,h2,h3{color:var(--text);font-weight:550;letter-spacing:-.025em}h1{font-size:3rem!important;line-height:1.03!important}h2{font-size:1.6rem!important}h3{font-size:1rem!important}
.hero{padding:28px 0 22px;border-bottom:1px solid var(--border);margin-bottom:18px}.eyebrow{font-size:.7rem;letter-spacing:.11em;text-transform:uppercase;color:var(--accent-dark);font-weight:750}.hero h1{max-width:1060px;margin:7px 0 10px}.hero p{max-width:930px;color:var(--muted);font-size:1rem;line-height:1.55;margin:0}
.badge{display:inline-flex;align-items:center;gap:6px;padding:5px 8px;border:1px solid var(--border);border-radius:999px;background:#fff;font-size:.67rem;margin:2px 5px 2px 0}.dot{width:6px;height:6px;border-radius:50%;background:var(--success)}.dot.warn{background:var(--accent)}
.arch-wrap{margin:22px 0 28px}.arch-flow{display:grid;grid-template-columns:1fr 42px 1fr 42px 1.35fr 42px 1fr 42px 1fr;align-items:center;gap:0}.node{background:#fff;border:1px solid var(--border);border-radius:6px;padding:13px;min-height:116px;box-shadow:0 1px 3px rgba(0,0,0,.035)}.node.accent{background:rgba(192,133,50,.09);border-color:rgba(192,133,50,.24)}.node.control{background:#fff6f7;border-color:rgba(207,45,86,.18)}.node.output{background:#f1f8f5;border-color:rgba(31,138,101,.2)}.node-k{font-size:.64rem;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);font-weight:750;margin-bottom:5px}.node-t{font-size:.88rem;font-weight:700;margin-bottom:5px}.node-c{font-size:.69rem;line-height:1.4;color:var(--muted)}.arrow{text-align:center;color:#9b978e;font-size:1.3rem}.branch{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:8px}.mini{background:var(--surface);border:1px solid var(--border);border-radius:5px;padding:8px;font-size:.66rem;line-height:1.35}.mini b{display:block;font-size:.69rem;margin-bottom:2px}.mini span{color:var(--muted)}
.arch-bottom{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-top:9px}.guard{background:#fff;border:1px solid var(--border);border-radius:5px;padding:10px}.guard b{display:block;font-size:.72rem;margin-bottom:3px}.guard span{font-size:.67rem;color:var(--muted);line-height:1.38}
.stage{display:grid;grid-template-columns:54px 1.15fr 1.3fr 1fr;gap:14px;align-items:start;padding:16px 0;border-top:1px solid var(--border)}.stage-num{width:38px;height:38px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:var(--text);color:var(--bg);font-size:.72rem;font-weight:750}.stage h3{margin:1px 0 5px}.stage p{font-size:.78rem;line-height:1.48;color:var(--muted);margin:0}.stage-label{font-size:.64rem;text-transform:uppercase;letter-spacing:.08em;color:#8a877e;font-weight:750;margin-bottom:4px}.rule{padding:8px 9px;background:rgba(192,133,50,.08);border:1px solid rgba(192,133,50,.2);border-radius:4px;font-size:.7rem;line-height:1.38}.out{padding:8px 9px;background:rgba(31,138,101,.07);border:1px solid rgba(31,138,101,.18);border-radius:4px;font-size:.7rem;line-height:1.38}
.inv-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}.inv{background:#fff;border:1px solid var(--border);border-radius:5px;padding:10px 12px}.inv b{font-size:.76rem}.inv span{display:block;color:var(--muted);font-size:.69rem;line-height:1.4;margin-top:3px}.footer-note{font-size:.72rem;color:var(--muted);border-top:1px solid var(--border);padding-top:12px;margin-top:22px}
@media(max-width:1050px){.arch-flow{grid-template-columns:1fr}.arrow{transform:rotate(90deg);padding:3px}.branch,.arch-bottom,.inv-grid{grid-template-columns:1fr}.stage{grid-template-columns:45px 1fr}.stage>div:nth-child(3),.stage>div:nth-child(4){grid-column:2}}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<section class="hero">
  <div class="eyebrow">Agent Anatomy · Research v1.0</div>
  <h1>How an evidence-grounded tumor-board agent system turns source material into a bounded clinical brief</h1>
  <p>This page exposes the architecture behind Tumor Board Intelligence. The system separates case construction, data integrity, evidence retrieval, verification, specialist interpretation, adversarial challenge, consensus, and presentation so that no single model response can silently become a clinical recommendation.</p>
</section>
""",
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns([1,1,4])
with c1:
    st.page_link("00_Mission_Control.py", label="Back to Mission Control", use_container_width=True)
with c2:
    st.link_button("AI Agents in Medicine", ARTICLE_URL, use_container_width=True)

st.markdown(
    '<span class="badge"><span class="dot"></span>36/36 frozen whole-system qualification</span>'
    '<span class="badge"><span class="dot"></span>0 observed safety-stop violations</span>'
    '<span class="badge"><span class="dot warn"></span>Decision support only</span>',
    unsafe_allow_html=True,
)

st.markdown("## Architecture at a glance")
st.caption("The diagram shows the main control path. Specialist agents run as bounded evidence channels rather than as one undifferentiated conversational model.")

st.markdown(
    """
<div class="arch-wrap">
  <div class="arch-flow">
    <div class="node">
      <div class="node-k">01 · Source truth</div><div class="node-t">Case Input</div>
      <div class="node-c">Narrative, PDF, DOCX, structured case, or clinician follow-up information.</div>
    </div>
    <div class="arrow">→</div>
    <div class="node">
      <div class="node-k">02 · Understand</div><div class="node-t">Extraction Agent</div>
      <div class="node-c">Builds the canonical case and preserves field-level provenance.</div>
    </div>
    <div class="arrow">→</div>
    <div class="node accent">
      <div class="node-k">03 · Validate + route</div><div class="node-t">Integrity, Missing Information & Router</div>
      <div class="node-c">Checks whether the represented case is coherent enough to enter specialist analysis.</div>
      <div class="branch">
        <div class="mini"><b>Case Integrity</b><span>Schema, provenance, conflict and temporal checks.</span></div>
        <div class="mini"><b>Missing Information</b><span>Decision-critical gaps and blocking status.</span></div>
        <div class="mini"><b>Clinical Router</b><span>Selects only relevant specialist agents.</span></div>
      </div>
    </div>
    <div class="arrow">→</div>
    <div class="node">
      <div class="node-k">04 · Specialist evidence</div><div class="node-t">Parallel Agent Stack</div>
      <div class="branch">
        <div class="mini"><b>Guideline</b><span>Verified formal/consensus guidance.</span></div>
        <div class="mini"><b>Literature</b><span>Bounded PubMed retrieval.</span></div>
        <div class="mini"><b>Molecular</b><span>Disease + alteration context.</span></div>
        <div class="mini"><b>Translational</b><span>Mechanistic/preclinical evidence.</span></div>
        <div class="mini"><b>Trials</b><span>Possible matches, not eligibility.</span></div>
        <div class="mini"><b>Safety</b><span>Verified safety constraints.</span></div>
      </div>
    </div>
    <div class="arrow">→</div>
    <div class="node control">
      <div class="node-k">05 · Challenge</div><div class="node-t">Verification + Clinical Red Team</div>
      <div class="node-c">Tests source support, claim promotion, missing channels, conflicts and safety blockers before synthesis.</div>
    </div>
  </div>
  <div class="arch-bottom">
    <div class="guard"><b>Evidence Gateway / Verifier</b><span>Retrieved content cannot become a verified claim without the required source contract.</span></div>
    <div class="guard"><b>Clinical Red Team</b><span>Independent deterministic challenge. Agent agreement is not treated as truth.</span></div>
    <div class="guard"><b>Consensus Engine</b><span>Evidence-weighted synthesis, never majority voting. Unsafe or unsupported states abstain.</span></div>
    <div class="guard"><b>Tumor Board Brief</b><span>Presentation transformer only. If consensus abstains, management strategy remains withheld.</span></div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown("## Detailed agent anatomy")

stages = [
    ("01", "Case Source Input", "Establish the source material that the system is allowed to treat as case evidence.", "Accepts synthetic or fully de-identified narrative, PDF, DOCX, TXT/MD, structured case input, or clinician follow-up information. Follow-up text is treated as supplemental source material rather than as a conversational instruction.", "NO SOURCE → NO PATIENT FACT. Unknown, pending, absent-from-record and negative remain distinct states.", "A bounded source document or structured source representation."),
    ("02", "Extraction Agent", "Convert source material into a canonical structured tumor-board case.", "Extracts diagnosis, disease state, performance status, treatments, pathology, molecular findings, clinical question and other represented facts. The v2.5 contract carries provenance anchors for supported facts.", "The model may structure source information, but unsupported text cannot enter the canonical patient state.", "CancerTumorBoardCase plus extraction provenance and verification record."),
    ("03", "Case Integrity / Data QA Agent", "Decide whether the structured representation is internally safe enough to propagate.", "Checks verified provenance, schema consistency, diagnostic certainty, unresolved conflicts, treatment identity and temporal consistency.", "Recommendation-blocking structural defects stop routing rather than being averaged away downstream.", "CaseIntegrityReport with routing permission or explicit stop condition."),
    ("04", "Missing Information Agent", "Identify information gaps that could materially change tumor-board interpretation.", "Classifies gaps by category, priority, requested action and recommendation-blocking status. Questions shown in Mission Control come from this layer.", "Missing information is never silently repaired, inferred or converted into a normal value.", "READY, CONDITIONAL or BLOCKED MissingInformationReport."),
    ("05", "Clinical Router", "Select the specialist evidence channels relevant to the represented clinical question.", "Classifies the question and routes to guideline, literature, molecular, translational, clinical-trial and safety agents as required.", "Routing chooses tools. It does not itself create a treatment conclusion.", "Typed RoutingDecision with selected and omitted specialist channels."),
    ("06", "Guideline Agent", "Determine whether verified guideline material supports a case-relevant management statement.", "Matches the represented disease context to preverified formal or consensus guideline records. Authoritative summaries such as NCI PDQ remain a separate evidence class rather than being mislabeled as formal guidelines.", "NO VERIFIED SOURCE → NO GUIDELINE CLAIM.", "Guideline report with source identity, match type, recommendation text and claim gate."),
    ("07", "Literature Agent + Evidence Verifier", "Retrieve current literature while separating retrieval from verification.", "Performs bounded PubMed search using structured case concepts. Evidence verification requires source identity and exact supporting spans before a literature claim is allowed to influence synthesis.", "RETRIEVED ≠ VERIFIED. A paper found by search is not automatically clinically applicable evidence.", "Structured literature records with verification state and limitations."),
    ("08", "Molecular Interpretation Agent", "Interpret represented molecular findings without promoting gene identity into clinical actionability.", "Matches disease context and alteration identity to preverified molecular evidence. Prognostic, resistance, sensitivity and actionability states remain distinct.", "GENE MATCH ≠ ALTERATION MATCH. MOLECULAR SIGNAL ≠ TREATMENT ELIGIBILITY.", "Molecular interpretation report with bounded clinical-actionability gate."),
    ("09", "Translational Biology Agent", "Provide mechanistic and preclinical context without confusing plausibility with established clinical action.", "Surfaces human translational, in-vivo, in-vitro and hypothesis-level evidence under explicit evidence tiers.", "BIOLOGICAL PLAUSIBILITY ≠ CLINICAL ACTIONABILITY. PRECLINICAL SENSITIVITY ≠ TREATMENT RECOMMENDATION.", "Translational report labeled by evidence tier and context match."),
    ("10", "Clinical Trials Agent", "Surface potentially relevant current studies without determining individual eligibility.", "Searches ClinicalTrials.gov using bounded disease and represented molecular concepts. It preserves disease-context matching and recruitment state.", "TRIAL MATCH ≠ TRIAL ELIGIBILITY.", "Possible trial matches with identifiers, context and explicit eligibility limitation."),
    ("11", "Safety Agent", "Identify source-verified safety constraints that can condition or block synthesis.", "Matches represented therapies and patient triggers to verified safety evidence. Recommendation-blocking findings can stop downstream management rendering.", "NO VERIFIED SAFETY SOURCE → NO SAFETY CLAIM. MISSING MONITORING VALUE ≠ NORMAL VALUE.", "Safety report with supported findings and recommendation-blocking state."),
    ("12", "Clinical Red Team", "Independently challenge the assembled specialist stack before consensus.", "Detects unsupported claim promotion, required specialist failure, unresolved high-impact conflicts, recommendation-blocking missing information, trial-eligibility overreach and safety bypass attempts.", "AGENT AGREEMENT ≠ TRUTH. NO EVIDENCE FOUND ≠ NEGATIVE EVIDENCE.", "CLEAR, CHALLENGED or BLOCKED report with explicit findings."),
    ("13", "Consensus Engine", "Integrate qualified evidence without voting and without inventing strategies from weak channels.", "Builds management candidates only from permitted structured recommendation records and preserves conditions, alternatives, disagreements and uncertainty.", "RED TEAM BLOCK → ABSTAIN. SAFETY BLOCK → ABSTAIN. TRANSLATIONAL/TRIAL-ONLY SIGNALS CANNOT MANUFACTURE A MANAGEMENT RECOMMENDATION.", "Preferred conditional option, multiple reasonable options, or abstention."),
    ("14", "Tumor Board Intelligence Brief", "Present the qualified state in a clinician-readable form without adding new reasoning.", "Renders patient snapshot, clinical question, decision-critical gaps, management discussion, evidence, molecular/translational context, trials, safety, Red Team findings, uncertainty and source trace.", "CONSENSUS ABSTAIN → MANAGEMENT STRATEGY WITHHELD.", "Board-ready, source-traceable decision-support brief."),
    ("15", "Human Tumor Board", "Keep final clinical judgment with the multidisciplinary team.", "Clinicians adjudicate evidence, uncertainty, patient context and alternatives. Future governed studies may compare the platform with board decisions and expert adjudication.", "TUMOR-BOARD DECISION ≠ AUTOMATIC GROUND TRUTH. The platform is not an autonomous treatment system.", "Human-reviewed clinical decision and, in future studies, a governed evaluation record."),
]

for num, name, purpose, does, guardrail, output in stages:
    st.markdown(
        f"""
<div class="stage">
  <div class="stage-num">{num}</div>
  <div><h3>{name}</h3><p>{purpose}</p></div>
  <div><div class="stage-label">What it does</div><p>{does}</p></div>
  <div><div class="stage-label">Guardrail</div><div class="rule">{guardrail}</div><div class="stage-label" style="margin-top:7px">Output</div><div class="out">{output}</div></div>
</div>
""",
        unsafe_allow_html=True,
    )

st.markdown("## Core safety invariants")
st.markdown(
    """
<div class="inv-grid">
  <div class="inv"><b>NO SOURCE → NO PATIENT FACT</b><span>Source truth is separated from interpretation.</span></div>
  <div class="inv"><b>NO VERIFIED EVIDENCE → NO EVIDENCE CLAIM</b><span>Retrieval does not automatically authorize synthesis.</span></div>
  <div class="inv"><b>PENDING ≠ NEGATIVE</b><span>Unresolved states are preserved rather than normalized into certainty.</span></div>
  <div class="inv"><b>BIOLOGICAL PLAUSIBILITY ≠ CLINICAL ACTIONABILITY</b><span>Mechanistic evidence has a different epistemic role from management evidence.</span></div>
  <div class="inv"><b>TRIAL MATCH ≠ TRIAL ELIGIBILITY</b><span>Search overlap cannot determine patient-level inclusion or exclusion.</span></div>
  <div class="inv"><b>AGENT AGREEMENT ≠ TRUTH</b><span>Consensus is evidence-gated, not majority voting.</span></div>
  <div class="inv"><b>CRITICAL CONFLICT → HUMAN REVIEW</b><span>Important contradictions are preserved and escalated.</span></div>
  <div class="inv"><b>FAILED VERIFICATION → DO NOT PROPAGATE CLAIM</b><span>Unsupported content cannot reappear later as if verified.</span></div>
  <div class="inv"><b>LOW INFORMATION → ABSTAIN OR REQUEST MORE INFORMATION</b><span>Stopping is a valid system behavior.</span></div>
  <div class="inv"><b>CONSENSUS ABSTAIN → MANAGEMENT WITHHELD</b><span>The presentation layer cannot bypass the decision gate.</span></div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown("## Why this is a useful companion to an AI-agents-in-healthcare discussion")
st.write(
    "A conceptual discussion of agents becomes more concrete when readers can inspect an implementation that separates tools, evidence classes, verification, adversarial challenge, abstention and human review. This prototype is intended as a worked example of those design principles, not as evidence that agentic clinical systems are ready for autonomous use."
)

st.markdown("## Validation boundary")
st.info(
    "The research prototype completed a frozen controlled synthetic whole-system qualification with 36/36 strict case-execution passes and zero observed safety-stop violations. This is controlled software qualification, not clinical validation, proof of real-world efficacy, or authorization for autonomous clinical use."
)

st.markdown('<div class="footer-note">Tumor Board Intelligence · Research prototype · Synthetic/de-identified data only · Human multidisciplinary review remains required.</div>', unsafe_allow_html=True)
