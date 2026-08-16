from __future__ import annotations

import time
from html import escape
from typing import Any

import streamlit as st


NODES: list[dict[str, Any]] = [
    {
        "id": "intake",
        "number": "01",
        "title": "Case intake / source documents",
        "type": "case",
        "purpose": "Collect the de-identified source narrative or document set that will anchor the tumor-board case.",
        "inputs": "De-identified narrative, PDF, DOCX, TXT, or provenance-bearing synthetic fixture.",
        "action": "Preserve the source as the reference frame for extraction and provenance checks.",
        "output": "Source document package for structured extraction.",
        "safety": "No patient fact is treated as true simply because it appears in an uploaded file.",
        "why": "Every downstream claim needs a traceable source context.",
    },
    {
        "id": "extraction",
        "number": "02",
        "title": "Extraction Agent",
        "type": "case",
        "purpose": "Convert unstructured oncology material into a canonical structured case.",
        "inputs": "Source text plus the governed case schema.",
        "action": "Extract diagnosis, disease state, stage when explicitly represented, treatment history, molecular findings, performance status, and the tumor-board question with provenance anchors.",
        "output": "Canonical CancerTumorBoardCase plus raw extraction/audit package.",
        "safety": "Explicit missingness is preserved. Stage is never derived from TNM, imaging, or model memory when it is not explicitly represented.",
        "why": "Specialist agents need one consistent case state rather than independently re-reading the chart.",
    },
    {
        "id": "confirmation",
        "number": "03",
        "title": "Case Confirmation Gate",
        "type": "gate",
        "purpose": "Require a human check that the structured representation matches the source material.",
        "inputs": "Structured case plus source-traced extraction package.",
        "action": "Clinician confirms only facts already carrying verified source provenance.",
        "output": "Human-reviewed represented case or correction request.",
        "safety": "Confirmation does not validate diagnosis accuracy, treatment correctness, or model-inferred facts.",
        "why": "The workflow should not reason on a misrepresented case.",
    },
    {
        "id": "correction",
        "number": "04",
        "title": "Case Correction Gate",
        "type": "gate",
        "purpose": "Return representation errors to correction before specialist reasoning.",
        "inputs": "Clinician correction or detected representation conflict.",
        "action": "Refresh the canonical case and re-run integrity checks.",
        "output": "Corrected structured case.",
        "safety": "Downstream specialist work remains blocked until the corrected case passes the required gates.",
        "why": "Prevents error propagation into multiple specialist agents.",
    },
    {
        "id": "integrity",
        "number": "05",
        "title": "Case Integrity Agent",
        "type": "case",
        "purpose": "Validate deterministic completeness, consistency, provenance, and clinical plausibility rules before routing.",
        "inputs": "Canonical case and semantic-integrity findings.",
        "action": "Check contradictions, malformed facts, unsupported confirmed assertions, recommendation-blocking conflicts, and routing safety.",
        "output": "Integrity report with disposition, findings, and safe-to-route flag.",
        "safety": "A recommendation-blocking integrity failure produces abstention rather than specialist synthesis.",
        "why": "This is the first formal fail-closed gate after representation.",
    },
    {
        "id": "missing",
        "number": "06",
        "title": "Missing Information Agent",
        "type": "safety",
        "purpose": "Identify what is absent, pending, conflicting, or required for the represented question.",
        "inputs": "Canonical case, disease program, question type, and existing conflicts.",
        "action": "Classify missing information by severity and whether it blocks recommendation synthesis.",
        "output": "Missing-information report with items, severity, and recommended next information.",
        "safety": "Missing or conflicting information remains visible and can force clarification or abstention.",
        "why": "Tumor-board reasoning is often defined as much by what is not known as by what is known.",
    },
    {
        "id": "clarification",
        "number": "07",
        "title": "Clarification Gate",
        "type": "gate",
        "purpose": "Decide whether the case can proceed or needs additional human information.",
        "inputs": "Integrity findings and missing-information report.",
        "action": "Branch to clarification when recommendation-blocking information is unresolved; otherwise permit routing.",
        "output": "Clarification required or case ready for routing.",
        "safety": "The system does not silently fill gaps from model memory.",
        "why": "Makes conditional branching explicit rather than hidden inside a prompt.",
    },
    {
        "id": "apply",
        "number": "08",
        "title": "Apply Clarification",
        "type": "gate",
        "purpose": "Integrate verified clarification back into the shared case state.",
        "inputs": "Clinician-supplied clarification and its source/provenance context.",
        "action": "Update the canonical representation and re-run integrity and missingness checks.",
        "output": "Refreshed case state.",
        "safety": "Clarification must be represented explicitly; it is not inferred.",
        "why": "All agents should see the same corrected state.",
    },
    {
        "id": "router",
        "number": "09",
        "title": "Clinical Router",
        "type": "case",
        "purpose": "Route the case to the governed oncology program and specialist channels relevant to the represented question.",
        "inputs": "Confirmed diagnosis, age where relevant, disease program, tumor-board question, and routing metadata.",
        "action": "Deterministically assign the oncology program and activate the required specialist evidence channels.",
        "output": "Disease/question-specific specialist route.",
        "safety": "Routing support does not imply disease-specific clinical validation or treatment correctness.",
        "why": "Specialists should run because the case requires them, not because one generic prompt happened to mention a concept.",
    },
    {
        "id": "guideline",
        "number": "10A",
        "title": "Guideline Agent",
        "type": "evidence",
        "purpose": "Match governed disease-specific guidance to the represented case context.",
        "inputs": "Confirmed case facts plus admitted guideline evidence package.",
        "action": "Apply explicit disease, state, stage, and other represented criteria to governed recommendations.",
        "output": "Matched guidance, source metadata, status, and limitations.",
        "safety": "No formal guideline claim is created when a governed disease-specific evidence package is absent. Stage-dependent guidance requires confirmed, human-verified, source-verified stage.",
        "why": "Separates guideline logic from literature, molecular, and safety reasoning.",
    },
    {
        "id": "molecular",
        "number": "10B",
        "title": "Molecular Interpretation Agent",
        "type": "evidence",
        "purpose": "Interpret only governed molecular evidence relevant to the represented alteration and disease context.",
        "inputs": "Human-reviewed molecular finding plus approved molecular evidence store/candidates.",
        "action": "Match disease, alteration, therapy context, and evidence statement without promoting gene identity alone to actionability.",
        "output": "Molecular evidence report with actionability boundaries and provenance.",
        "safety": "Model knowledge and mechanistic plausibility cannot establish clinical actionability.",
        "why": "Molecular oncology requires tight provenance and context matching.",
    },
    {
        "id": "literature",
        "number": "10C",
        "title": "Literature Agent",
        "type": "evidence",
        "purpose": "Retrieve current literature through the configured bounded source adapter.",
        "inputs": "Represented disease/question concepts and configured PubMed client.",
        "action": "Retrieve and summarize source records relevant to the structured query.",
        "output": "Literature report with retrieval trace, records, summary, and limitations.",
        "safety": "PubMed retrieval does not by itself establish evidence applicability or recommendation support.",
        "why": "Keeps current literature distinct from formal consensus guidance.",
    },
    {
        "id": "translational",
        "number": "10D",
        "title": "Translational Biology Agent",
        "type": "evidence",
        "purpose": "Surface mechanistic and translational biology that may help explain the case.",
        "inputs": "Represented molecular/disease concepts and governed translational evidence store.",
        "action": "Link mechanistic evidence to the represented biology while preserving its epistemic category.",
        "output": "Translational evidence report.",
        "safety": "Translational evidence is never promoted to treatment actionability without separate clinical evidence.",
        "why": "Useful biological explanation should not be confused with clinical recommendation evidence.",
    },
    {
        "id": "trials",
        "number": "10E",
        "title": "Clinical Trials Agent",
        "type": "evidence",
        "purpose": "Retrieve and screen current ClinicalTrials.gov records against bounded case concepts.",
        "inputs": "Diagnosis, molecular terms where represented, age, and configured ClinicalTrials.gov API client.",
        "action": "Screen active recruitment, disease context, and explicit age bounds; retain unresolved eligibility domains.",
        "output": "Possible trial matches, retrieval trace, matched concepts, unresolved eligibility, and source URLs.",
        "safety": "TRIAL MATCH IS NOT TRIAL ELIGIBILITY. Site status, full criteria, prior therapy, labs, washouts, and investigator confirmation remain unresolved unless explicitly reviewed.",
        "why": "Faculty can see why a trial surfaced without the system pretending eligibility is known.",
    },
    {
        "id": "safety",
        "number": "10F",
        "title": "Safety Agent",
        "type": "evidence",
        "purpose": "Evaluate bounded safety-source evidence for represented or guideline-candidate therapies.",
        "inputs": "Represented therapy context and locally approved safety-source records.",
        "action": "Surface label warnings, contraindication/source context, and relevant limitations.",
        "output": "Safety report with provenance and support boundaries.",
        "safety": "FDA label retrieval is source evidence, not a patient-specific dosing, contraindication, or treatment directive.",
        "why": "Separates treatment efficacy reasoning from safety evidence.",
    },
    {
        "id": "join",
        "number": "11",
        "title": "Join Specialists",
        "type": "challenge",
        "purpose": "Collect structured outputs from independently operating specialist channels.",
        "inputs": "Guideline, molecular, literature, translational, trials, and safety reports that were actually routed/reached.",
        "action": "Preserve statuses, provenance, limitations, and unavailable channels without flattening them into one answer.",
        "output": "Joined specialist evidence state for challenge review.",
        "safety": "A missing specialist output is preserved as missing/unavailable rather than reconstructed from memory.",
        "why": "Consensus should know exactly which channels contributed and which did not.",
    },
    {
        "id": "redteam",
        "number": "12",
        "title": "Clinical Red Team",
        "type": "challenge",
        "purpose": "Independently challenge evidence sufficiency, assumptions, conflicts, and recommendation logic before consensus.",
        "inputs": "Joined specialist outputs, case state, integrity and missingness reports.",
        "action": "Identify recommendation-blocking and nonblocking weaknesses, unsupported leaps, source gaps, and conflicts.",
        "output": "Challenge findings with severity and effect on recommendation.",
        "safety": "Blocking challenge findings prevent recommendation synthesis or force conditional/abstention states.",
        "why": "The system has an explicit adversarial review step rather than asking the same model to self-approve its answer.",
    },
    {
        "id": "consensus",
        "number": "13",
        "title": "Consensus Engine",
        "type": "challenge",
        "purpose": "Synthesize specialist evidence only after integrity, missingness, and challenge controls are satisfied.",
        "inputs": "Specialist reports plus Challenge Review findings.",
        "action": "Resolve supported agreements/conflicts, determine decision state, preserve uncertainty, and identify discussion priorities.",
        "output": "Consensus report and final decision state.",
        "safety": "If evidence is inadequate or blocking issues remain, consensus abstains or remains conditional rather than forcing a recommendation.",
        "why": "Consensus is a governed synthesis layer, not a majority vote or confidence score.",
    },
    {
        "id": "brief",
        "number": "14",
        "title": "Tumor Board Brief",
        "type": "output",
        "purpose": "Translate governed workflow state into a readable, auditable tumor-board intelligence brief.",
        "inputs": "Final decision, consensus, specialist outputs, missingness, Challenge Review, and source references.",
        "action": "Present patient snapshot, management strategy or abstention, evidence, uncertainty, what could change the decision, and limitations.",
        "output": "Structured TumorBoardIntelligenceBrief.",
        "safety": "Presentation cannot create new clinical claims that are absent from the governed workflow state.",
        "why": "Faculty receive a concise decision-support artifact without losing provenance or uncertainty.",
    },
    {
        "id": "outputs",
        "number": "15",
        "title": "PDF / Structured Outputs",
        "type": "output",
        "purpose": "Export the governed brief in faculty-readable and audit-oriented formats.",
        "inputs": "Tumor Board Brief and structured workflow result.",
        "action": "Generate PDF presentation and structured JSON/audit output.",
        "output": "Readable report plus machine-readable audit package.",
        "safety": "Export is a presentation transformation and cannot create new treatment claims.",
        "why": "Supports tumor-board review, research evaluation, and reproducible audit.",
    },
]


HANDOFFS = [
    ("Case intake", "Extraction Agent", "Source package available", "De-identified source content is available for structured extraction."),
    ("Extraction Agent", "Case Confirmation Gate", "Provenance-bearing case produced", "Structured fields and provenance anchors are available for human review."),
    ("Case Confirmation Gate", "Case Correction Gate", "Conflict / representation error", "Clinician identifies a mismatch or correction is required."),
    ("Case Confirmation Gate", "Case Integrity Agent", "Represented case confirmed", "Only source-traced facts are marked human-reviewed."),
    ("Case Correction Gate", "Case Integrity Agent", "Case corrected", "The refreshed case becomes the single shared state."),
    ("Case Integrity Agent", "Missing Information Agent", "Safe enough to inspect completeness", "Deterministic integrity checks do not identify a blocking structural failure."),
    ("Missing Information Agent", "Clarification Gate", "Missingness classified", "The system distinguishes blocking, nonblocking, pending, and conflicting information."),
    ("Clarification Gate", "Apply Clarification", "Clarification required", "Blocking information must be supplied or resolved by a human before routing."),
    ("Clarification Gate", "Clinical Router", "Case ready for routing", "Required pre-routing gates are satisfied."),
    ("Clinical Router", "Specialist agents", "Disease + question route", "Only the relevant bounded evidence channels are activated."),
    ("Specialist agents", "Join Specialists", "Structured specialist outputs", "Statuses, evidence, provenance, limitations, and unavailable channels are preserved."),
    ("Join Specialists", "Clinical Red Team", "Evidence stack assembled", "Independent challenge occurs before consensus."),
    ("Clinical Red Team", "Consensus Engine", "No unresolved blocking challenge", "Blocking findings must be absent/resolved; otherwise the workflow abstains or remains conditional."),
    ("Consensus Engine", "Tumor Board Brief", "Consensus permitted", "The final decision state and limitations are representable without unsupported assertions."),
    ("Tumor Board Brief", "PDF / Structured Outputs", "Governed brief rendered", "Export transforms presentation only; it cannot create new clinical claims."),
]


def architecture_css() -> None:
    st.markdown(
        """
<style>
.arch-hero{padding:24px 0 12px}.arch-hero h1{font-size:42px;line-height:1.05;letter-spacing:-1px;margin:0;color:#102a43}.arch-hero p{font-size:16px;color:#5f6f82;max-width:980px;line-height:1.6;margin-top:10px}
.arch-callout{border:1px solid #b9d1ea;background:#f4f9ff;border-radius:12px;padding:12px 14px;font-size:13px;color:#294d70;margin:8px 0 18px}
.arch-flow{border:1px solid #d9e1ea;border-radius:18px;background:#fff;padding:18px;box-shadow:0 10px 26px rgba(16,42,67,.05);margin:10px 0 20px}.arch-row{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;align-items:stretch}.arch-row.six{grid-template-columns:repeat(6,minmax(0,1fr))}.arch-node{border:1px solid #bfd0df;border-top:4px solid #316a9b;border-radius:12px;padding:11px;background:#fbfdff;min-height:104px}.arch-node.gate{border-top-color:#b84d86;background:#fffafd}.arch-node.evidence{border-top-color:#18856c;background:#f8fdfb}.arch-node.challenge{border-top-color:#6c4aa4;background:#fbf9ff}.arch-node.output{border-top-color:#173f67;background:#f8fbff}.arch-node.safety{border-top-color:#b67a00;background:#fffdf6}.arch-num{font-size:10px;font-weight:800;color:#728197;letter-spacing:.08em}.arch-node strong{display:block;font-size:14px;color:#142f49;margin-top:4px;line-height:1.25}.arch-node span{display:block;font-size:11px;line-height:1.45;color:#65768a;margin-top:5px}.arch-arrow{text-align:center;font-size:18px;color:#7b8da1;padding:8px 0}.arch-edge{font-size:11px;color:#425a70;text-align:center;padding:4px 8px 9px}.arch-edge b{color:#183b56}.arch-sources{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:8px;margin-top:10px}.arch-source{border:1px dashed #aebbc7;border-radius:10px;padding:9px;background:#f7f8fa;font-size:10px;color:#566474;text-align:center}.arch-legend{display:flex;flex-wrap:wrap;gap:8px 14px;margin:12px 0 4px;font-size:10px;color:#64748b}.arch-dot{width:10px;height:10px;border-radius:3px;display:inline-block;margin-right:5px}.arch-section{font-size:26px;font-weight:760;color:#102a43;margin:28px 0 5px}.arch-sub{font-size:14px;color:#65768a;line-height:1.55;max-width:980px;margin-bottom:12px}.arch-handoffs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.arch-handoff{border:1px solid #dce4ec;border-radius:12px;background:#fff;padding:12px}.arch-handoff strong{font-size:13px;color:#173b5e}.arch-handoff .criteria{font-size:11px;font-weight:700;color:#8a5c00;margin:4px 0}.arch-handoff p{font-size:11px;color:#64748b;line-height:1.45;margin:0}.arch-compare{display:grid;grid-template-columns:1fr 1fr;gap:12px}.arch-compare>div{border:1px solid #dce4ec;border-radius:14px;padding:15px;background:#fff}.arch-compare h3{font-size:16px;margin:0 0 6px}.arch-compare p{font-size:12px;line-height:1.5;color:#637286}.arch-single{border-left:5px solid #b42318!important}.arch-multi{border-left:5px solid #18856c!important}.arch-principles{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.arch-principle{border:1px solid #dce4ec;border-radius:12px;padding:12px;background:#fff}.arch-principle strong{font-size:13px;color:#173b5e}.arch-principle p{font-size:11px;color:#66768a;line-height:1.45;margin:5px 0 0}
@media(max-width:950px){.arch-row,.arch-row.six,.arch-sources{grid-template-columns:repeat(2,1fr)}.arch-handoffs,.arch-compare,.arch-principles{grid-template-columns:1fr 1fr}}@media(max-width:620px){.arch-row,.arch-row.six,.arch-sources,.arch-handoffs,.arch-compare,.arch-principles{grid-template-columns:1fr}.arch-hero h1{font-size:34px}}
</style>
""",
        unsafe_allow_html=True,
    )


def _node_html(node_id: str) -> str:
    node = next(x for x in NODES if x["id"] == node_id)
    cls = node["type"]
    return (
        f'<div class="arch-node {escape(cls)}"><div class="arch-num">{escape(node["number"])}</div>'
        f'<strong>{escape(node["title"])}</strong><span>{escape(node["purpose"])}</span></div>'
    )


def render_architecture_graph() -> None:
    architecture_css()
    st.markdown(
        '<div class="arch-callout"><strong>Interactive architecture:</strong> The graph below shows the complete orchestration path, handoffs, gates, parallel specialist agents, human review points, Challenge Review, consensus, and outputs. <strong>Click an agent in the Agent Explorer below</strong> to see its purpose, inputs, outputs, safety limits, handoff criteria, and why it matters.</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="arch-flow">', unsafe_allow_html=True)
    st.markdown(
        '<div class="arch-row">'
        + _node_html("intake") + _node_html("extraction") + _node_html("confirmation") + _node_html("integrity") + _node_html("missing")
        + '</div><div class="arch-edge"><b>Source available → provenance-bearing representation → human confirmation → deterministic integrity → explicit missingness</b></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="arch-row">'
        + _node_html("correction") + _node_html("clarification") + _node_html("apply") + _node_html("router") + '<div class="arch-node safety"><div class="arch-num">HUMAN</div><strong>Review points</strong><span>Confirm case representation, supply clarification, and attest candidate evidence before it is promoted into governed stores.</span></div>'
        + '</div><div class="arch-edge"><b>Conflict → correction loop · blocking gap → clarification loop · case-ready → route by disease + question</b></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="arch-row six">'
        + _node_html("guideline") + _node_html("molecular") + _node_html("literature") + _node_html("translational") + _node_html("trials") + _node_html("safety")
        + '</div><div class="arch-edge"><b>Parallel bounded specialist work. Each channel keeps its own source status, evidence, limitations, and abstention state.</b></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="arch-sources"><div class="arch-source">ELN / governed guideline package → Guideline</div><div class="arch-source">CIViC / approved molecular evidence → Molecular</div><div class="arch-source">PubMed → Literature</div><div class="arch-source">Governed translational resources → Translational</div><div class="arch-source">ClinicalTrials.gov → Trials</div><div class="arch-source">openFDA / label evidence → Safety</div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="arch-arrow">↓ specialist outputs + provenance</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="arch-row">'
        + _node_html("join") + _node_html("redteam") + _node_html("consensus") + _node_html("brief") + _node_html("outputs")
        + '</div><div class="arch-edge"><b>Join → independent challenge → consensus only if permitted → auditable brief → presentation/audit outputs</b></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="arch-legend">'
        '<span><i class="arch-dot" style="background:#316a9b"></i>Case representation / routing</span>'
        '<span><i class="arch-dot" style="background:#b84d86"></i>Gates / clarification</span>'
        '<span><i class="arch-dot" style="background:#18856c"></i>Evidence specialists</span>'
        '<span><i class="arch-dot" style="background:#b67a00"></i>Missingness / human review</span>'
        '<span><i class="arch-dot" style="background:#6c4aa4"></i>Challenge / consensus</span>'
        '<span><i class="arch-dot" style="background:#173f67"></i>Final outputs</span>'
        '</div></div>',
        unsafe_allow_html=True,
    )


def render_agent_explorer() -> None:
    st.markdown('<div class="arch-section">Agent Explorer</div><div class="arch-sub">Click an agent or gate below. The detail panel explains exactly what enters the node, what it does, what it hands off, what it is prohibited from doing, and why the step exists.</div>', unsafe_allow_html=True)
    labels = [f'{n["number"]} · {n["title"]}' for n in NODES]
    choice = st.selectbox("Select an agent or gate to inspect", labels, index=1)
    node = NODES[labels.index(choice)]
    c1, c2 = st.columns([1.15, .85], gap="large")
    with c1:
        st.markdown(f"### {node['number']} · {node['title']}")
        st.markdown(f"**Purpose**  \n{node['purpose']}")
        st.markdown(f"**Inputs**  \n{node['inputs']}")
        st.markdown(f"**What happens in this node**  \n{node['action']}")
        st.markdown(f"**Output / handoff**  \n{node['output']}")
    with c2:
        st.info(f"Safety boundary\n\n{node['safety']}")
        st.success(f"Why it matters\n\n{node['why']}")


def render_handoffs() -> None:
    st.markdown('<div class="arch-section">Agent-to-agent handoffs and criteria</div><div class="arch-sub">The handoff is part of the safety architecture. A downstream agent receives a structured state only when the upstream criterion is met; otherwise the workflow loops, blocks, or abstains.</div>', unsafe_allow_html=True)
    html = '<div class="arch-handoffs">'
    for src, dst, criteria, meaning in HANDOFFS:
        html += (
            '<div class="arch-handoff">'
            f'<strong>{escape(src)} → {escape(dst)}</strong>'
            f'<div class="criteria">Criterion: {escape(criteria)}</div>'
            f'<p>{escape(meaning)}</p></div>'
        )
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def render_agent_anatomy() -> None:
    st.markdown('<div class="arch-section">Anatomy of an agent</div><div class="arch-sub">An agent is not simply a chatbot persona. Each specialist has a bounded role, governed inputs, allowed tools/evidence, explicit output schema, handoff criteria, and a failure/abstention state.</div>', unsafe_allow_html=True)
    cols = st.columns(6, gap="small")
    anatomy = [
        ("1", "Structured input", "Shared canonical case state and question."),
        ("2", "Bounded role", "One explicit scientific task, not all reasoning at once."),
        ("3", "Governed tools", "Only configured evidence stores or source adapters."),
        ("4", "Structured output", "Status, evidence, provenance, limitations, warnings."),
        ("5", "Safety checks", "Missingness, verification, conflict, and abstention rules."),
        ("6", "Handoff", "Output moves to join/challenge only when criteria are met."),
    ]
    for col, (num, title, text) in zip(cols, anatomy):
        with col:
            st.markdown(f"**{num}. {title}**")
            st.caption(text)


def render_why_agentic() -> None:
    st.markdown('<div class="arch-section">Why agents instead of one prompt?</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="arch-compare"><div class="arch-single"><h3>Single-model pattern</h3><p><strong>Case → one prompt → opaque answer</strong></p><p>Representation, retrieval, interpretation, safety checking, and recommendation synthesis can become entangled. Failure location and provenance are harder to see.</p></div><div class="arch-multi"><h3>Governed multi-agent pattern</h3><p><strong>Case → integrity + routing → specialists → challenge → consensus → auditable brief</strong></p><p>Roles are separated, handoffs are explicit, sources remain attributable, independent failures remain visible, and the workflow can abstain before unsupported synthesis.</p></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="arch-section">What makes this agentic?</div>', unsafe_allow_html=True)
    principles = [
        ("Routed execution", "Disease program and clinical question determine which specialists run."),
        ("Shared state", "Agents operate on one canonical structured case rather than reinterpreting the chart independently."),
        ("Parallel specialists", "Guideline, molecular, literature, translational, trials, and safety channels can work independently."),
        ("Governed tool use", "Evidence retrieval is bounded to configured stores/adapters and retains source status."),
        ("Conditional branching", "Integrity, missingness, clarification, challenge, and abstention change the path."),
        ("Human review", "Case representation and candidate evidence require explicit human review at defined points."),
        ("Challenge before consensus", "The Clinical Red Team tests assumptions and evidence sufficiency before synthesis."),
        ("Auditable output", "The final brief preserves evidence, uncertainty, limitations, and source traceability."),
    ]
    html = '<div class="arch-principles">'
    for title, text in principles:
        html += f'<div class="arch-principle"><strong>{escape(title)}</strong><p>{escape(text)}</p></div>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def render_play_workflow() -> None:
    st.markdown('<div class="arch-section">Play the workflow</div><div class="arch-sub">Use this short walk-through to see the order in which the governed system moves from source material to final brief. It is a presentation aid, not a live execution of a patient case.</div>', unsafe_allow_html=True)
    steps = [
        "1. Source intake",
        "2. Structured extraction + provenance",
        "3. Human case confirmation / correction",
        "4. Case integrity gate",
        "5. Missing-information + clarification gate",
        "6. Disease/question routing",
        "7. Parallel specialist evidence agents",
        "8. Human evidence attestation where required",
        "9. Join specialist outputs",
        "10. Clinical Red Team challenge",
        "11. Consensus / abstention decision",
        "12. Tumor Board Brief + PDF/audit outputs",
    ]
    if st.button("Play workflow", type="primary"):
        slot = st.empty()
        progress = st.progress(0)
        for i, step in enumerate(steps, 1):
            slot.info(step)
            progress.progress(int(i / len(steps) * 100))
            time.sleep(0.16)
        slot.success("Workflow complete: final output remains clinician-facing research decision support.")


def render_architecture_page() -> None:
    from app.faculty_ui import faculty_css, product_header, research_footer, top_navigation

    faculty_css(); architecture_css(); product_header("Scientific architecture"); top_navigation("architecture")
    st.markdown('<div class="arch-hero"><h1>Pan-Oncology Tumor Board Intelligence</h1><p><strong>Ram Paragi · rparag@lsuhsc.edu</strong></p><p>Complete scientific architecture of the governed multi-agent tumor-board workflow, including handoffs, routing criteria, parallel evidence channels, human review points, Challenge Review, consensus, abstention, and auditable output.</p></div>', unsafe_allow_html=True)
    render_architecture_graph()
    render_play_workflow()
    render_agent_explorer()
    render_handoffs()
    render_agent_anatomy()
    render_why_agentic()
    research_footer()
