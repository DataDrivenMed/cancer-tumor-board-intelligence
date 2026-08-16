# Pan-Oncology Common-Core Qualification Record

## Qualification identity

- Product: Tumor Board Intelligence
- Scope: common pan-oncology software architecture
- Registered tumor-board programs: 14
- Matrix scenarios per program: 15
- Matrix executions: 210
- Dedicated pan-oncology test executions in CI: 261
- Full repository regression tests in CI: 555
- Qualification build: `b62217a3bc65321193195d782a593e093139d406`
- GitHub Actions workflow: `Pan-Oncology Qualification`
- Workflow run: `31964312857`
- Result: PASS
- Date: 2026-08-16

## What passed

The corrected final pan-oncology qualification build completed with **261 passed** dedicated tests. The same build then completed the full repository regression suite with **555 passed** tests.

The dedicated gate includes:

- the 210-execution, 14-program x 15-scenario common-core matrix
- pan-oncology program registry and routing tests
- pediatric cross-program routing tests
- stage missing-information gate tests
- explicit exact-source stage extraction tests
- stage-dependent guidance prerequisite tests, including wrong-stage rejection

During final qualification, a stage-matching defect was detected before release: generic token matching allowed `stage II` to match `stage III`. The matcher was corrected to use exact canonical stage-label comparison, and the complete qualification gate was rerun successfully on the build recorded above.

## Common-core matrix scenarios

Each registered tumor-board program is exercised against the same 15 controlled synthetic scenarios:

1. routine management
2. localized disease with explicit stage
3. metastatic management
4. progressive disease with represented prior therapy
5. multi-line treatment history
6. represented molecular finding
7. clinical-trial question
8. safety-specific question
9. guideline-alignment question
10. pending performance status
11. conflicting explicit stage
12. high-severity unresolved case conflict
13. pending diagnosis
14. empty evidence channels
15. unregistered-program reassignment guard

## Qualification claims supported by this record

This record supports the following software claims for the shared pan-oncology core:

- all 14 registered programs enter the common architecture without disease-domain abstention
- deterministic tumor-board reassignment works from the represented diagnosis
- age-aware pediatric tie-breaking works for overlapping pediatric and organ-specific diagnoses tested in the suite
- safety is retained as a required routed specialist for ordinary clinical routes
- safety-only questions do not invoke unrelated specialists
- molecular and trial questions route to the corresponding bounded specialists
- missing or conflicting decision-critical information can prevent specialist routing
- conflicting explicit stage is represented as a blocking information gap
- pending explicit stage is surfaced without globally assuming stage is required for every oncology question
- an absent stage is not invented
- stage-dependent guidance requires a source-verified and clinician-confirmed explicit stage
- stage-dependent guidance rejects a different represented stage
- empty evidence stores fail closed
- empty evidence stores do not create guideline, molecular-actionability, translational-actionability, literature, trial-match, or safety claims
- unregistered disease-program metadata can be deterministically corrected from a registered represented diagnosis
- the pan-oncology expansion remains compatible with the complete existing regression suite on this build

## Claims this record does not support

This qualification does **not** establish:

- disease-specific treatment correctness
- completeness of disease-specific biomarker rules
- correctness of all staging systems
- patient-specific drug appropriateness
- trial eligibility
- clinical outcome benefit
- clinical validation
- regulatory clearance or authorization
- institutional approval for routine patient-care use

Those claims require the disease-specific and clinical validation process in `docs/PAN_ONCOLOGY_VALIDATION_PROTOCOL.md`.

## Validation state after this record

All 14 disease programs remain labeled `architecture_ready` rather than `clinically_validated_silent` or `clinical_release`.

The reason is deliberate: the shared core has passed formal automated common-core qualification, but disease-specific management correctness still requires independently governed evidence packages and disease-appropriate expert reference-standard validation.
