# Challenge Validation v2

## Purpose

Challenge Validation v2 follows the completed Extraction Qualification Suite v1.0 repeatability study. It does not alter or replace the v1 evidence. Its purpose is to test whether the unchanged extraction system generalizes beyond the ten development qualification cases and whether the residual omission failures observed during repeated inference recur under targeted stress.

This is a research qualification protocol using synthetic cases only. It is not clinical validation and does not authorize autonomous clinical use.

## Frozen configuration

Before the first v2 inference call, freeze:

- challenge cases and their gold expectations
- extraction implementation and prompt/schema
- scoring logic
- semantic-integrity rules
- extraction normalization
- conflict-consistency rules
- model/provider configuration
- reasoning effort

The application computes a SHA-256 challenge fingerprint over the challenge case definitions, protocol, and extraction-validation implementation. Results with different fingerprints must not be combined.

## Validation streams

### Phase A: Targeted failure-mode challenge

Ten single-pass synthetic cases target risks identified in v1 and closely related safety concerns:

- treatment-history omission
- current versus historical malignancy separation
- longitudinal therapy ordering
- planned versus administered therapy
- medication temporality
- repeated regimen components
- unresolved stage conflict
- pending molecular results

This stream is run once. Do not rerun failed cases inside the same study and do not modify the cases after observing outputs.

### Phase B: Unseen synthetic generalization

Ten single-pass synthetic cases broaden the disease mix beyond the original development suite, including colorectal, breast, melanoma, lung, ovarian, pancreatic, renal, prostate, CNS, and carcinoma-of-unknown-primary scenarios.

The purpose is generalization testing, not disease-specific clinical decision validation. This stream is run once.

### Phase C: Repeated stochastic subset

Six difficult cases are selected before execution and repeated three times under the unchanged configuration. The subset intentionally emphasizes omission-prone, distractor-prone, temporality, repeated-component, sparse-documentation, and abstention scenarios.

Total repeated-subset executions: 18.

## Planned sample

- Phase A: 10 case executions
- Phase B: 10 case executions
- Phase C: 6 cases × 3 repeats = 18 case executions
- Total: 38 case executions

These 38 executions are not equivalent to 38 independent patients. Phase C contains deliberate repeated observations.

## Strict execution-level PASS

An execution passes only when:

1. the ordinary extraction core gate passes;
2. every scored core metric equals 100%;
3. semantic integrity passes;
4. prohibited assertions equal zero; and
5. unsupported-provenance assertion rate equals zero.

Exact provenance verification is tracked independently at the study level.

## Pre-specified research classification

### GREEN

- 100% strict overall pass across all completed executions;
- 100% exact provenance verification;
- zero prohibited assertions; and
- zero unsupported-provenance assertions.

### AMBER

- at least 95% strict overall pass;
- 100% exact provenance verification;
- zero prohibited assertions;
- zero unsupported-provenance assertions; and
- no repeated-subset case fails more than once.

### RED

Any of the following:

- strict overall pass rate below 95%;
- any provenance verification failure;
- any prohibited assertion;
- any unsupported-provenance assertion; or
- the same repeated-subset case fails more than once.

These categories are research workflow classifications only. GREEN does not imply clinical deployment safety.

## Failure handling

Do not modify the frozen system in response to a Phase A, B, or C failure while the study is in progress. Preserve the output and classify the failure after the study or after a protocol-defined stop condition. If a genuine implementation defect requires correction, close the current v2 study, version the change, generate a new fingerprint, and begin a new study.

Endpoint/quota/tool failures do not enter the scientific denominator because no complete scored stream was produced. They should be retained separately as operational reliability events.

## Required exports

After every completed stream or repeated-subset run, download the JSON study archive. The JSON is the durable record and contains protocol metadata, fingerprint, scores, structured extraction, provenance diagnostics, semantic results, and run history. CSV export is supplementary.

## Interpretation

The study is designed to separate three questions:

1. Can the system handle the failure modes exposed by v1?
2. Does it generalize to new synthetic oncology cases without tuning?
3. Does the same difficult case remain stable under repeated inference?

It does not establish population-level clinical accuracy, prospective clinical utility, patient outcome benefit, regulatory fitness, or autonomous decision-making safety.
