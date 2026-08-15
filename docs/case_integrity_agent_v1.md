# Case Integrity / Data QA Agent v1.0.0

## Purpose

The Case Integrity / Data QA Agent is a deterministic pre-routing safety gate over the canonical `CancerTumorBoardCase`. It evaluates whether the structured representation is internally coherent and sufficiently trustworthy to propagate to downstream specialist agents.

It does **not** retrieve clinical evidence, infer missing patient facts, alter the canonical case, rank treatments, or produce a clinical recommendation.

## Position in the pipeline

`v2.5 qualified extraction -> structural quality enrichment -> Case Integrity / Data QA -> router -> specialist agents`

The v2.5 extraction implementation and its frozen qualification evidence are not modified by this build.

## Inputs

- One validated `CancerTumorBoardCase`
- Existing provenance, conflict, missing-information, molecular, and treatment structures contained in that case

## Typed output

`CaseIntegrityReport` contains:

- disposition: `pass`, `pass_with_warnings`, or `block`
- check counts
- severity counts
- recommendation-blocking count
- deterministic finding codes
- field paths
- source-segment references when applicable
- per-check audit results
- `requires_human_review`
- `safe_to_route_to_specialists`

## Deterministic checks v1.0.0

1. Verified provenance for substantive observed facts, molecular findings, and treatment episodes.
2. Basic schema consistency for confirmed diagnosis/performance fields.
3. Diagnostic-certainty invariant: an unconfirmed diagnosis cannot support a confirmed disease state.
4. Unresolved conflict severity and routing impact.
5. Recommendation-blocking missing information.
6. Duplicate treatment episode identifiers.
7. Treatment temporal consistency, including end-before-start and planned treatment with an end date.

## Routing policy

- `PASS`: specialist routing allowed.
- `PASS_WITH_WARNINGS`: routing allowed, human review required.
- `BLOCK`: specialist routing prohibited; workflow abstains before specialist execution.

A finding is deterministic and reproducible from the same canonical case. The agent stores concise finding messages and evidence references, not hidden chain-of-thought.

## Safety invariants

- No verified provenance -> no propagation of substantive observed claim.
- Unconfirmed diagnosis -> no confirmed disease state.
- Recommendation-blocking unresolved information -> no specialist routing.
- High/critical unresolved source conflict -> no specialist routing.
- Invalid treatment chronology -> no specialist routing.
- The agent never repairs or invents patient facts.

## Validation status

This component has automated unit and workflow-gating regression tests. Passing software tests demonstrates implementation behavior against those specified cases. It is not clinical validation and does not establish safety on real patient charts.
