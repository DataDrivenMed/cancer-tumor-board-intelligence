# Clinical Red Team v1.0.0

## Purpose

The Clinical Red Team is an independent deterministic challenge layer that runs after specialist agents and before the future Consensus Engine. It is designed to identify unsafe claim promotion, incomplete specialist execution, unresolved recommendation-blocking information, unresolved high-severity case conflicts, and safety-gate failures.

The Red Team does not generate treatment recommendations, diagnose the patient, invent alternatives, or use model memory to supply missing evidence.

## Core invariants

- AGENT AGREEMENT != TRUTH.
- NO EVIDENCE FOUND != NEGATIVE EVIDENCE.
- TRANSLATIONAL EVIDENCE != CLINICAL ACTIONABILITY.
- TRIAL MATCH != TRIAL ELIGIBILITY.
- RECOMMENDATION-BLOCKING SAFETY FINDING -> STOP.
- REQUIRED SPECIALIST FAILURE -> STOP.
- UNRESOLVED HIGH/CRITICAL CASE CONFLICT -> STOP.
- RECOMMENDATION-BLOCKING MISSING INFORMATION -> STOP.

## Inputs

1. Canonical `CancerTumorBoardCase`.
2. Frozen `RoutingDecision`.
3. Specialist outputs from the selected agents.

The agent does not read the original narrative and does not call an LLM or external evidence source.

## Outputs

`ClinicalRedTeamReport` contains:

- disposition: `clear`, `challenged`, or `blocked`;
- typed findings with stable codes and severities;
- recommendation-blocking state;
- human-review requirement;
- challenged specialist IDs;
- `safe_for_consensus` gate.

## Deterministic challenge rules

### Orchestration integrity

A selected specialist with no output is challenged. If the missing specialist is required, consensus is blocked.

Required specialists returning `source_unavailable`, `verification_failed`, `tool_failure`, `schema_error`, `insufficient_input`, `abstain_domain`, or `escalate_human` block consensus.

### Bounded no-result handling

`no_evidence_found` is preserved as a non-blocking challenge. It must never be converted into a claim that an option, hazard, biomarker, or trial does not exist.

### Case-state integrity

Unresolved high or critical canonical conflicts block consensus. Recommendation-blocking missing information also blocks consensus.

### Molecular actionability

An interpretation-level clinical-actionability flag cannot exceed the report-level molecular actionability gate.

### Translational evidence

The Translational Biology Agent is prohibited from independently supporting a clinical-actionability claim.

### Clinical trials

The Clinical Trials Agent is prohibited from converting a trial match into patient-specific eligibility. Any `eligibility_determined=True`, non-null `eligible`, or report-level eligibility-support flag is a critical blocking violation.

### Safety

A recommendation-blocking Safety Agent result is a critical stop. Safety findings without a report-level verified safety-claim gate are challenged as an internal-consistency problem.

### Guideline taxonomy

A guideline-support gate cannot be true when there are zero formal or consensus guideline matches. Authoritative evidence summaries must remain distinct from formal guideline support.

## Dispositions

### CLEAR

No deterministic structural, promotion, conflict, orchestration, or safety-gate violation was found. This does not establish clinical correctness or safety.

### CHALLENGED

One or more non-blocking concerns exist and must remain visible during consensus.

### BLOCKED

At least one recommendation-blocking finding exists. The Consensus Engine must not generate a recommendation state until the issue is resolved or explicitly adjudicated.

## Validation boundary

The v1 Red Team is software-level deterministic validation. It is not prospective clinical validation and is not evidence that the overall platform is clinically safe or effective.

A future whole-system qualification study must test red-team sensitivity against prespecified adversarial cases, claim-promotion attacks, missing-specialist failures, contradiction scenarios, and unsafe consensus attempts.
