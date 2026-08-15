# Extraction Remediation Validation v2.1

## Purpose

Remediation Validation v2.1 is a new, frozen synthetic qualification study created after Challenge Validation v2.0 closed with a RED result. It does not alter, replace, rescore, or erase the v2.0 evidence.

The v2.0 study identified two principal technical weaknesses:

1. intermittent and recurrent omission of explicit current disease state from the canonical `disease_state` field even when metastatic/progression evidence appeared elsewhere in the extraction;
2. intermittent omission of longitudinal treatment episodes, especially intermediate maintenance/consolidation phases.

It also identified evaluation-representation mismatches involving clinically equivalent progression language and uncertain carcinoma-of-unknown-primary wording.

## v2.1 remediation architecture

### Immutable raw model output

The provider response is retained as `raw_model_output` before any deterministic normalization or repair. Normalization is performed on a detached copy.

### Auditable normalization

Every deterministic mutation can generate a normalization event containing:

- rule
- field path
- before value
- after value
- reason
- source segment IDs when applicable
- source excerpt when applicable
- event version

The resulting representation is stored separately as `normalized_extraction`.

### Disease-State Consistency Resolver

The resolver runs only when the primary extraction leaves `disease_state` unresolved. It:

- uses only explicit source text;
- does not overwrite a substantive model disease state;
- abstains when a relevant unresolved conflict exists;
- ignores uncertain and negated state mentions;
- requires state evidence to be locally tied to the current diagnosis or explicit current-context language;
- may label `metastatic` as derived when the source explicitly states metastasis/metastases rather than the adjective metastatic;
- records every repair as an auditable normalization event.

### Treatment Episode Completeness Pass

Treatment-rich narratives can invoke a second bounded extraction pass whose only task is to enumerate treatment episodes chronologically. New episodes are merged only when:

- administration status is explicitly `started`, `completed`, or `stopped`;
- exact source-segment provenance verifies;
- the episode is not already represented in the primary extraction.

Planned, ordered, cancelled, or unknown-status therapy is not added as an administered episode.

### Treatment administration state

The canonical treatment schema now includes:

- `planned`
- `ordered`
- `started`
- `completed`
- `stopped`
- `cancelled`
- `unknown`

### Scoring v2.1

The v2.1 scorer preserves the original strict provenance and safety gates while adding prespecified semantic equivalence for representations such as:

- `radiographic progression` and `progressive`;
- status-aware uncertain diagnosis wording, where entity equivalence is accepted only if structured uncertainty is preserved;
- `resected` as an explicit disease-state representation.

## Frozen remediation suite

The fresh baseline contains 12 cases, R01-R12. These cases were created for v2.1 and are separate from v1 Q-cases and v2.0 T/U-cases.

A six-case repeated subset is prespecified:

- R01
- R02
- R06
- R07
- R10
- R12

Each repeated-subset case is executed three times.

Total planned case executions:

- baseline: 12
- repeated subset: 6 × 3 = 18
- total: 30

Treatment-rich cases may make one additional bounded model request for treatment completeness, so model-request count can exceed case-execution count.

## Acceptance policy

### GREEN

- 30/30 strict overall case passes
- 100% exact provenance
- zero prohibited assertions
- zero unsupported-provenance assertions
- zero semantic-integrity errors
- each repeated case 3/3

### AMBER

- exactly 29/30 strict overall case passes
- 100% exact provenance
- zero prohibited assertions
- zero unsupported-provenance assertions
- zero semantic-integrity errors
- no repeated case fails more than once

### RED

Any of:

- 28/30 or fewer strict passes
- provenance/safety failure
- semantic-integrity error
- any repeated case fails more than once

## Safety stop

A completed run triggers a study safety stop if it contains:

- any provenance verification failure;
- any prohibited assertion;
- any unsupported-provenance assertion;
- any semantic-integrity error.

The UI then locks additional formal study runs.

## Methodological rules

Once the first v2.1 baseline inference starts:

- do not alter the frozen cases;
- do not alter extraction logic;
- do not alter scoring;
- do not alter normalization or semantic-integrity checks;
- do not change model/provider configuration or reasoning effort;
- do not rerun a failed baseline case individually to replace its recorded result.

If a genuine implementation defect is found after the study starts, close the study, change the relevant version/fingerprint, and begin a new remediation study rather than silently continuing.

## Interpretation

This remains a controlled synthetic research qualification study. Even a GREEN result supports advancement to broader held-out and prospective evaluation, not autonomous clinical use or a claim of clinical validation.
