from __future__ import annotations

import streamlit as st

from app.ui import apply_design_system, architecture_stage, connector, hero, badge


st.set_page_config(page_title="Architecture Anatomy | Tumor Board Intelligence", page_icon="◉", layout="wide")
apply_design_system()

hero(
    "Anatomy of an evidence-grounded tumor-board intelligence system",
    "A detailed view of how a case moves from source material to a bounded, auditable decision-support brief. The architecture is intentionally layered so that extraction, evidence retrieval, verification, challenge, and consensus remain separate responsibilities.",
    eyebrow="System Anatomy · Research v1.0",
)

st.markdown(
    badge("36/36 frozen whole-system qualification", "ok")
    + badge("0 observed safety-stop violations", "ok")
    + badge("Decision support only", "warn"),
    unsafe_allow_html=True,
)

st.markdown("## Executive view")
st.write(
    "The system is designed around a simple principle: no single model response is allowed to become a clinical recommendation. "
    "Instead, the platform builds a structured case, verifies what it knows, identifies what it does not know, routes the question to bounded specialist services, challenges the outputs, and only then permits a management candidate to appear when the evidence contract allows it."
)

architecture_stage(
    "01",
    "Source truth and case construction",
    "Convert narrative or document-based tumor-board material into a structured case without losing the relationship to the original source.",
    [
        ("Case ingestion", "Synthetic or fully de-identified narrative, PDF, DOCX, TXT, or structured case input."),
        ("Structured extraction", "The extraction layer identifies diagnosis, disease state, treatment history, pathology, molecular findings, performance status, and the clinical question."),
        ("Field-level provenance", "Every decision-relevant extracted fact can retain source-document, segment, and exact-excerpt references."),
    ],
    guardrail="No source means no patient fact. Unsupported model text is not accepted as canonical clinical data.",
    outcome="Canonical CancerTumorBoardCase with observed, derived, interpreted, missing, and conflicting information represented explicitly.",
)
connector()

architecture_stage(
    "02",
    "Deterministic integrity gates",
    "Before specialist reasoning begins, the system checks whether the structured representation itself is safe enough to route downstream.",
    [
        ("Semantic Integrity", "Detects unsafe transformations such as pending being converted to negative, unsupported disease-state assertions, and known semantic integrity failures."),
        ("Case Integrity / Data QA", "Checks provenance, schema consistency, diagnosis certainty, unresolved high-impact conflicts, duplicate treatment episodes, and temporal contradictions."),
        ("Missing Information", "Classifies missing decision-relevant information and determines whether a case is READY, CONDITIONAL, or BLOCKED."),
    ],
    guardrail="Critical conflict, failed provenance, or recommendation-blocking missing information prevents downstream recommendation synthesis.",
    outcome="A structurally qualified case or an explicit abstention with the reason for stopping.",
)
connector()

architecture_stage(
    "03",
    "Clinical routing",
    "Determine which evidence channels are relevant to the clinical question rather than sending every case through an undifferentiated prompt.",
    [
        ("Question classification", "Classifies treatment-management, diagnosis/workup, molecular-management, safety, trial, and related question domains."),
        ("Complexity assessment", "Assigns routine, intermediate, complex, or high-complexity routing states."),
        ("Specialist selection", "Selects required and conditional specialist agents while preserving a stable, auditable route."),
    ],
    guardrail="Routing determines which bounded services may act. It does not create a clinical conclusion.",
    outcome="Typed RoutingDecision specifying required, conditional, selected, and omitted specialist agents.",
)
connector()

architecture_stage(
    "04",
    "Parallel specialist evidence channels",
    "Each specialist answers a narrower question under its own evidence and claim rules. These channels are deliberately separated because mechanism, guideline support, trial matching, and safety are not interchangeable forms of evidence.",
    [
        ("Guideline Agent", "Matches the represented case to verified formal or consensus guidelines. Authoritative summaries remain explicitly distinct from formal guideline recommendations."),
        ("Literature Agent", "Performs bounded PubMed retrieval and records canonical publication identifiers without converting retrieval into a treatment recommendation."),
        ("Molecular Interpretation", "Separates variant identity, disease context, prognostic significance, resistance evidence, and clinical actionability."),
        ("Translational Biology", "Surfaces mechanistic, human translational, in-vivo, in-vitro, and hypothesis-level evidence without promoting biological plausibility into clinical actionability."),
        ("Clinical Trials", "Searches current ClinicalTrials.gov records and surfaces possible matches while leaving individual eligibility unresolved."),
        ("Safety Agent", "Matches verified safety evidence and can block recommendation synthesis when a relevant contraindication or unresolved monitoring requirement is represented."),
    ],
    guardrail="Gene match is not variant match. Mechanism is not actionability. Trial match is not eligibility. No verified source means no evidence claim.",
    outcome="Separate structured specialist reports with explicit claim gates, evidence references, limitations, and failure states.",
)
connector()

architecture_stage(
    "05",
    "Evidence verification and appraisal",
    "Evidence records are not trusted merely because they were retrieved. Verification checks identity, source integrity, exact supporting spans, and structured appraisal fields before evidence can be promoted.",
    [
        ("Evidence Gateway", "Checks source authorization, license state, human verification, source hash, exact excerpts, and locators before evidence records enter the evidence stores."),
        ("Evidence Verifier", "Requires exact verified source spans and preserves VERIFIED, PARTIALLY_VERIFIED, CONFLICTING, UNVERIFIED, and REJECTED states."),
        ("Full-text Appraisal", "Structures PICO, endpoints, effect estimates, risk-of-bias review, applicability, and source provenance without creating a new clinical recommendation."),
    ],
    guardrail="No exact verified source span means no verified evidence claim. A retrieved article is not automatically a clinically applicable result.",
    outcome="Verified or explicitly limited evidence atoms suitable for downstream challenge and synthesis.",
)
connector()

architecture_stage(
    "06",
    "Independent Clinical Red Team",
    "Challenge the assembled evidence stack before consensus. The Red Team is intentionally independent of specialist generation and looks for unsafe promotion, missing required channels, conflicts, and recommendation-blocking safety conditions.",
    [
        ("Promotion checks", "Detects translational-to-clinical promotion, trial-match-to-eligibility promotion, unsupported guideline promotion, and internal claim-gate inconsistencies."),
        ("Orchestration checks", "Detects missing required specialist outputs, failed channels, unresolved critical case conflicts, and missing recommendation-blocking information."),
        ("Safety challenge", "Blocks consensus when prespecified recommendation-blocking safety findings remain unresolved."),
    ],
    guardrail="Agent agreement is not truth. A bounded no-result search is not negative evidence. CLEAR means no prespecified deterministic violation was found, not that the case is clinically correct.",
    outcome="CLEAR, CHALLENGED, or BLOCKED ClinicalRedTeamReport with explicit findings and effects on recommendation synthesis.",
)
connector()

architecture_stage(
    "07",
    "Evidence-weighted consensus",
    "Integrate specialist outputs without majority voting. The current conservative v1 contract permits an explicit management candidate only when a verified formal or consensus guideline recommendation anchors it.",
    [
        ("Evidence-channel ledger", "Records each selected channel as supportive, limiting, unavailable, non-decisional, or not selected."),
        ("Candidate construction", "Creates management candidates only from allowed verified recommendation records and preserves conditions, exclusions, source excerpts, and locators."),
        ("Abstention logic", "Withholds recommendation synthesis when required channels fail, Red Team blocks, safety blocks, or no permitted management anchor exists."),
    ],
    guardrail="Consensus is not a vote. Molecular, translational, literature, and trial signals cannot independently manufacture a treatment strategy in v1.",
    outcome="PREFERRED_CONDITIONAL, MULTIPLE_REASONABLE_OPTIONS, or ABSTAIN, with bounded decision-support strength and preserved uncertainty.",
)
connector()

architecture_stage(
    "08",
    "Tumor Board Intelligence Brief",
    "Transform the canonical case and verified downstream reports into a clinician-facing brief without adding new clinical claims.",
    [
        ("Clinical synthesis", "Patient snapshot, treatment timeline, pathology, molecular profile, current question, and decision-critical gaps."),
        ("Evidence view", "Guideline analysis, literature, molecular/translational evidence, trials, safety, source references, and evidence boundaries."),
        ("Decision view", "Consensus-authorized management candidates, alternatives, Red Team challenges, uncertainty, and what could change the recommendation."),
    ],
    guardrail="Consensus abstain means Management Strategy = WITHHELD. The renderer does not re-rank, infer, or generate an unsupported recommendation.",
    outcome="A source-traceable, decision-support-only TumorBoardIntelligenceBrief for human multidisciplinary review.",
)
connector()

architecture_stage(
    "09",
    "Human tumor-board adjudication and learning loop",
    "The system stops at decision support. Final clinical judgment remains with the multidisciplinary tumor board, and disagreement is valuable data rather than an error to be automatically overwritten.",
    [
        ("Human adjudication", "Clinicians review the case representation, evidence, alternatives, safety constraints, and unresolved uncertainties."),
        ("Decision capture", "Future governed deployments may capture the board decision and rationale as an outcome, but not automatically as ground truth."),
        ("Evaluation loop", "Retrospective and prospective silent studies can assess concordance, safety, utility, abstention quality, evidence fidelity, and time saved."),
    ],
    guardrail="Tumor-board decision is not automatically ground truth, and the research prototype is not an autonomous treatment system.",
    outcome="Human-reviewed clinical decision plus a future governed evaluation record.",
)

st.markdown("## Why the architecture is intentionally separated")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<div class="ctb-card"><div class="ctb-kicker">Separation of concerns</div><h3>Different evidence has different meaning</h3><p>A formal guideline, a molecular biomarker, a preclinical mechanism, a trial listing, and a safety warning are not equivalent signals. Separate agents keep their epistemic boundaries visible.</p></div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="ctb-card"><div class="ctb-kicker">Auditability</div><h3>Every stage can be inspected</h3><p>The route, source records, verification status, Red Team findings, consensus state, and final rendering can be reviewed independently instead of being buried inside one model response.</p></div>', unsafe_allow_html=True)
with col3:
    st.markdown('<div class="ctb-card"><div class="ctb-kicker">Failure containment</div><h3>Unsafe states fail closed</h3><p>Missing information, failed verification, evidence-source failure, unsafe promotion, and safety blockers are designed to stop or constrain synthesis rather than be averaged away.</p></div>', unsafe_allow_html=True)

st.markdown("## The core safety vocabulary")
st.markdown(
    """
| Invariant | Meaning |
|---|---|
| **NO SOURCE → NO PATIENT FACT** | A model statement cannot become a patient fact without source support. |
| **NO VERIFIED EVIDENCE → NO EVIDENCE CLAIM** | Retrieval alone is insufficient. Evidence must pass the appropriate verification contract. |
| **PENDING ≠ NEGATIVE** | Unknown, pending, absent-from-record, and truly negative are different states. |
| **BIOLOGICAL PLAUSIBILITY ≠ CLINICAL ACTIONABILITY** | Mechanistic evidence cannot independently justify treatment action. |
| **TRIAL MATCH ≠ TRIAL ELIGIBILITY** | Search overlap does not establish that a patient meets inclusion/exclusion criteria. |
| **AGENT AGREEMENT ≠ TRUTH** | Consensus is evidence-gated, not majority voting. |
| **LOW INFORMATION → ABSTAIN OR REQUEST MORE INFORMATION** | The system is allowed to stop. |
| **CRITICAL CONFLICT → HUMAN REVIEW** | Important unresolved contradictions are not silently resolved by the model. |
| **FAILED VERIFICATION → DO NOT PROPAGATE CLAIM** | Failed evidence cannot reappear downstream as if it had been verified. |
| **CONSENSUS ABSTAIN → MANAGEMENT WITHHELD** | The presentation layer cannot circumvent the decision gate. |
"""
)

st.markdown("## Validation boundary")
st.info(
    "The current research prototype completed a frozen controlled synthetic whole-system qualification with 36/36 strict case-execution passes and zero observed safety-stop violations. This is controlled software qualification, not clinical validation, proof of real-world efficacy, or authorization for autonomous clinical use."
)

st.markdown("## How a clinician should experience it")
st.write(
    "The architecture above is intentionally deep, but the clinician-facing workflow should be shallow. A user should normally interact with only four moments: enter the case, verify what the system understood, run the analysis, and review the tumor-board brief. The remaining machinery should be available through Evidence and Audit views when deeper inspection is needed."
)
