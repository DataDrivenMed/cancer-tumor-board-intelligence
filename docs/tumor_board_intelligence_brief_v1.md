# Tumor Board Intelligence Brief v1.0.0

## Purpose

The Tumor Board Intelligence Brief is the deterministic final presentation layer for the research prototype. It converts the canonical case, bounded specialist outputs, Clinical Red Team report, and Consensus Engine report into a structured tumor-board-facing brief.

It is not an autonomous clinical reasoning agent and does not create new clinical claims.

## Core invariants

- CANONICAL FACTS ONLY -> PATIENT SNAPSHOT.
- CONSENSUS AUTHORIZATION ONLY -> MANAGEMENT STRATEGY.
- CONSENSUS ABSTAIN -> MANAGEMENT STRATEGY WITHHELD.
- RED TEAM CHALLENGE -> PRESERVED.
- MISSING / PENDING / CONFLICTING DATA -> PRESERVED, NOT INFERRED.
- TRIAL MATCH != TRIAL ELIGIBILITY.
- TRANSLATIONAL SIGNAL != CLINICAL ACTIONABILITY.
- NO NEW CLAIMS CREATED BY THE RENDERER.
- NO CHAIN-OF-THOUGHT STORAGE OR DISPLAY.

## Sections

The v1 brief contains:

1. Patient Snapshot
2. Prior Treatment Timeline
3. Pathology
4. Molecular Profile
5. Current Clinical Question
6. Decision-Critical Information
7. Guideline Analysis
8. Relevant Current Evidence
9. Molecular / Translational Interpretation
10. Clinical Trial Options
11. Management Strategy and Alternatives
12. Contraindications / Safety
13. Red-Team Challenge
14. Agent Disagreements / Evidence Boundaries
15. Uncertainty
16. What Could Change the Recommendation
17. Evidence Sources / Audit Trace

## Provenance

Canonical facts carry their source document and source-segment references into the brief when available. Evidence-derived items retain source-record identifiers already emitted by specialist agents or the Consensus Engine. The brief does not invent a citation, trial identifier, guideline record, molecular evidence record, or patient fact.

## Management-strategy gate

The renderer may display a management candidate only when `ConsensusReport.safe_to_render_decision_support == True` and the candidate is present in `ConsensusReport.candidates`.

If consensus abstains, the management-strategy section explicitly displays `WITHHELD` together with the abstention reason.

The renderer does not re-rank candidates, vote across agents, or promote molecular, translational, literature, or trial signals into a treatment recommendation.

## Safety and disagreement preservation

Recommendation-blocking Red Team findings, recommendation-blocking missing information, safety limitations, bounded no-result states, and non-decisional evidence channels remain visible. They are not silently averaged away.

## Audit boundary

The final audit section records source-trace count, specialist statuses, Red Team disposition, and Consensus decision state. It does not store or expose private chain-of-thought.

## Validation boundary

Tumor Board Intelligence Brief v1.0.0 is software-level deterministic rendering validation only. It is not prospective clinical validation and does not establish real-world clinical safety, efficacy, or generalizability.

The next stage is a frozen end-to-end adversarial qualification study of the complete research prototype.
