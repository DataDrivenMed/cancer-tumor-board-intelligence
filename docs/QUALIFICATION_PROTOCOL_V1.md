# Extraction Qualification Protocol v1.0

## Purpose

This protocol freezes the current 10-case synthetic extraction qualification suite before formal repeatability testing. It is a development-quality reproducibility protocol, not clinical validation.

## Frozen configuration

- Qualification Suite: 1.0.0
- Qualification Protocol: 1.0.0
- Extraction Prompt: 1.0.0
- Scoring: 1.0.0
- Semantic Integrity: 1.0.0
- Normalization: 1.0.0
- Model configuration: held constant within a study
- Reasoning effort: held constant within a study
- Repeatability target: 5 complete independent runs
- Cases per run: 10
- Total planned case executions: 50

The application computes a SHA-256 suite fingerprint from all gold-case definitions and the implementation files that define extraction, scoring, normalization, conflict consistency, and semantic integrity. Runs with a different fingerprint cannot be mixed into the same repeatability study.

## Counted run

A run enters the repeatability denominator only when all 10 frozen cases complete and produce qualification scores. Endpoint, provider, or tool failures that prevent a case from producing a score result in an incomplete trial. The incomplete trial is not counted as a model qualification failure and is not added to the 5-run denominator.

## Strict per-case repeatability PASS

A case execution passes the formal repeatability protocol only when all of the following are true:

1. The existing extraction core gate passes.
2. Every scored core metric equals 100%:
   - field accuracy
   - provenance verification
   - missing-information recall
   - conflict detection
   - molecular accuracy
   - treatment coverage
   - treatment order accuracy
3. Semantic integrity passes with no error or critical finding.
4. Prohibited assertions equal zero.
5. Unsupported-provenance assertion rate equals zero.

This strict definition is intentionally stronger than relying on the development core-gate threshold alone.

## Study-level target

The pre-specified v1.0 target is:

- 5/5 complete runs
- 50/50 strict overall case PASS
- 100% exact provenance across all counted provenance anchors
- 100% for every core metric across all 50 case executions
- zero prohibited assertions
- zero unsupported-provenance assertions
- no case-level instability hidden by aggregate averages

A single failed case execution remains visible in the study record even if aggregate means remain high.

## Persistence and auditability

Each counted run stores:

- timestamp
- model name
- reasoning effort
- protocol versions
- suite fingerprint
- case-level scores
- raw structured extraction diagnostics
- provenance totals and verification counts
- semantic-integrity results
- strict overall qualification status

The Repeatability Qualification page accumulates runs and exports:

- complete study JSON
- case-level CSV

Streamlit Community Cloud runtime storage may be ephemeral. The downloaded study JSON is therefore the durable study record and should be saved after every completed trial.

## Interpretation

Passing this protocol supports reproducibility of the frozen synthetic development extraction benchmark. It does not establish clinical validity, generalization to real-world records, performance on unseen cases, treatment-recommendation safety, regulatory readiness, or authorization for autonomous clinical decision-making.

The next phase after repeatability is a separately created held-out challenge set that was not used to tune the extraction system.
