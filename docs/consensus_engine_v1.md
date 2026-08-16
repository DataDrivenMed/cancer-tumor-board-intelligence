# Consensus Engine v1.0.0

## Purpose

The Consensus Engine is the deterministic evidence-integration layer that runs after specialist agents and the Clinical Red Team. It does not use majority vote, model intuition, or hidden chain-of-thought. It converts only explicitly permitted, verified evidence into bounded tumor-board decision support.

## Core invariants

- AGENT AGREEMENT != TRUTH.
- RED TEAM BLOCK -> ABSTAIN.
- SAFETY BLOCK -> ABSTAIN.
- NO VERIFIED FORMAL/CONSENSUS GUIDELINE ANCHOR -> NO MANAGEMENT CANDIDATE.
- AUTHORITATIVE EVIDENCE SUMMARY != FORMAL GUIDELINE.
- MOLECULAR ACTIONABILITY != AUTOMATIC TREATMENT RECOMMENDATION.
- TRANSLATIONAL EVIDENCE != CLINICAL ACTIONABILITY.
- TRIAL MATCH != TREATMENT RECOMMENDATION OR ELIGIBILITY.
- BOUNDED NO-RESULT != NEGATIVE EVIDENCE.

## Inputs

1. Canonical `CancerTumorBoardCase`.
2. Frozen `RoutingDecision`.
3. Specialist outputs.
4. Frozen `ClinicalRedTeamReport`.

## Decision policy

v1 is intentionally conservative. Explicit management candidates may originate only from verified formal or consensus guideline matches whose source excerpt and recommendation text are both present.

Other specialist channels can constrain, contextualize, challenge, or block those candidates, but cannot independently create a management recommendation:

- Molecular: may support bounded clinical actionability claims but does not automatically prescribe therapy.
- Translational: mechanistic/preclinical/human-translational context only.
- Clinical trials: possible match only, never eligibility or recommendation.
- Literature: retrieval/appraisal context does not create an unverified management recommendation.
- Safety: may constrain or block.

## Output states

### PREFERRED_CONDITIONAL

Exactly one verified formal/consensus guideline candidate is available. It is presented as conditional decision support, never as an autonomous directive.

### MULTIPLE_REASONABLE_OPTIONS

More than one verified formal/consensus guideline candidate is available. v1 does not rank by vote. Options remain visible for tumor-board adjudication.

### ABSTAIN

Used whenever:

- Clinical Red Team is blocked;
- required evidence channels are unavailable;
- no verified formal/consensus guideline management anchor exists;
- a recommendation-blocking safety condition remains unresolved.

## Evidence-channel ledger

Each selected specialist is classified as supportive, limiting, unavailable, non-decisional, or not selected. This makes the evidence stack auditable and prevents silent omission of weak or unavailable channels.

## Strength ceiling

Consensus v1 never emits `high` decision-support strength and never emits `strongly_supported`. The maximum is `moderate` because whole-system clinical validation has not been performed.

## Determinism

No LLM is called. Candidate generation, gating, evidence-channel classification, and abstention are deterministic from typed specialist outputs and Red Team state.

## Validation boundary

Passing software tests does not establish clinical correctness, safety, efficacy, or real-world generalizability. A frozen end-to-end adversarial qualification study is still required before this research prototype can be characterized as a qualified integrated system.
