# Clinical Router v1.0.0

## Purpose

The Clinical Router is a deterministic orchestration component that decides which bounded specialist agents should receive a case after upstream safety gates have passed.

It does **not** infer patient facts, retrieve clinical evidence, rank treatments, determine trial eligibility, or generate a recommendation.

## Position in the pipeline

`v2.5 qualified extraction -> Semantic Integrity -> Case Integrity / Data QA -> Missing Information Agent -> Clinical Router -> specialist agents`

The frozen v2.5 extraction implementation and its qualification evidence are not modified by this component.

## Preconditions

The router assumes that:

- deterministic semantic-integrity validation has passed;
- Case Integrity / Data QA has permitted specialist routing;
- the Missing Information Agent has not identified a routing-blocking information gap.

If those preconditions are not met, the workflow abstains before the router is called.

## Typed output

`RoutingDecision` includes:

- router version;
- clinical question type;
- one or more detected question domains;
- deterministic case-complexity class;
- selected specialist agents;
- omitted specialist agents;
- required versus conditional agents;
- concise routing rationale;
- routing warnings;
- parallel-execution flag;
- human-review flag;
- explicit safe-to-execute flag.

## Specialist domains

The current bounded registry contains:

- Guideline Agent
- Molecular Interpretation Agent
- Translational Biology Agent
- Literature Agent
- Clinical Trials Agent
- Safety Agent

## Routing rules v1.0.0

1. Safety review is mandatory for every clinical tumor-board route.
2. Management and guideline-focused questions route to Guideline and Literature.
3. Treatment-oriented questions also make Clinical Trials conditionally relevant.
4. Represented molecular findings or explicit molecular questions route to Molecular Interpretation.
5. Explicit mechanistic/translational questions require Translational Biology.
6. Molecular treatment/trial context makes Translational Biology conditionally relevant.
7. Pure safety questions intentionally omit unrelated specialist agents.
8. Agent ordering is fixed and deterministic.
9. Complexity is based on represented treatment burden, molecular complexity, source conflicts, number of question domains, transplant/cellular therapy history, toxicity history, and relapsed/refractory/progressive disease state.

## Complexity classes

- `routine`
- `intermediate`
- `complex`
- `high_complexity`

Complexity changes orchestration metadata. It does not itself imply that a recommendation is clinically difficult or unsafe.

## Safety invariants

- Routing occurs only after upstream integrity and missing-information gates permit propagation.
- The router never fills missing information.
- The router never changes the canonical case.
- Agent agreement is not treated as truth.
- Selection of an agent is not a clinical recommendation.
- Selection of the Clinical Trials Agent is not a claim of trial availability or eligibility.
- Selection of the Molecular or Translational agents is not a claim of clinical actionability.
- A deterministic route can be reproduced from the same canonical case.

## Validation status

This component has automated routing regression tests. Passing software tests demonstrates deterministic implementation behavior against the specified synthetic cases. It is not clinical validation and does not establish optimal routing for every malignancy, clinical question, or institution.