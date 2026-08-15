# Missing Information Agent v1.0.0

## Purpose

The Missing Information Agent is a deterministic pre-routing component that identifies unresolved information in the canonical tumor-board case, prioritizes those gaps, and distinguishes between non-blocking uncertainty and information that must be resolved before specialist-agent reasoning.

It does **not** invent missing facts, retrieve external evidence, diagnose the patient, rank treatments, or determine clinical trial eligibility.

## Position in the pipeline

`v2.5 qualified extraction -> structural quality enrichment -> Case Integrity / Data QA -> Missing Information Agent -> router -> specialist agents`

The frozen v2.5 extraction implementation and its qualification evidence are not modified by this component.

## Inputs

- One validated `CancerTumorBoardCase`
- Existing canonical missing-information items
- Canonical diagnosis, disease state, performance status, molecular findings, treatments, conflicts, and clinical question

## Typed output

`MissingInformationReport` contains:

- disposition: `ready`, `conditional`, or `blocked`
- prioritized unresolved information items
- deterministic category and action
- priority level and numeric priority score
- recommendation-blocking flag
- field path and source-segment references when applicable
- critical/high/moderate/low counts
- `requires_human_review`
- `safe_to_route_to_specialists`

## Deterministic rules v1.0.0

1. Preserve canonical `missing_items` and normalize them into the agent output.
2. Unconfirmed diagnosis creates a critical, recommendation-blocking diagnostic-confirmation gap.
3. Unresolved disease state creates a high-priority non-blocking gap.
4. Missing or unresolved performance status creates a high-priority non-blocking gap.
5. Relapsed, refractory, or progressive disease with no treatment history creates a critical, recommendation-blocking gap.
6. Treatment- or trial-oriented hematologic malignancy questions with no molecular/cytogenetic findings create a moderate review item, not an automatic treatment recommendation block.
7. Unresolved source conflicts are converted into explicit conflict-resolution actions; high/critical conflicts block routing.
8. Equivalent items are deduplicated deterministically, retaining the highest-priority and most conservative representation.

## Routing policy

- `READY`: no unresolved gaps identified by the current rule set; routing allowed.
- `CONDITIONAL`: unresolved information exists, but no item currently blocks specialist routing; human review required.
- `BLOCKED`: one or more decision-critical gaps remain unresolved; specialist routing prohibited and workflow abstains.

## Safety invariants

- Missing information is represented explicitly, never silently filled.
- Pending is not treated as negative.
- No external clinical inference is used to manufacture patient facts.
- Relapsed/refractory/progressive disease cannot be reasoned over without represented prior treatment history.
- An unconfirmed diagnosis cannot proceed as if diagnostic confirmation were complete.
- A deterministic missingness rule may request information; it may not assert what the missing result will be.
- The agent stores concise rule-based reasons, not hidden chain-of-thought.

## Validation status

This component has automated unit tests and workflow-gating regression tests. Passing those tests demonstrates implementation behavior against the specified synthetic cases. It is not clinical validation and does not establish completeness of all information requirements for every hematologic malignancy or real-world tumor-board case.
