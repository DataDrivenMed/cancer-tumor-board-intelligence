# Pan-Oncology Pathway Validation Protocol

## Purpose

This protocol governs expansion of Tumor Board Intelligence from the initial AML pathway to a pan-oncology platform. It separates software qualification from clinical validation and prevents an architecturally supported disease program from being represented as clinically validated before disease-specific evidence and expert review are complete.

## Scope

Registered tumor-board programs:

1. Hematologic malignancies
2. Breast oncology
3. Thoracic oncology
4. Gastrointestinal oncology
5. Genitourinary oncology
6. Gynecologic oncology
7. Head and neck oncology
8. Neuro-oncology
9. Melanoma and cutaneous oncology
10. Sarcoma and bone oncology
11. Endocrine and neuroendocrine oncology
12. Ophthalmic oncology
13. Pediatric oncology
14. Rare cancers and carcinoma of unknown primary

The registry is an operational grouping layer. Individual diagnoses remain represented in the canonical case and all evidence matching remains disease specific.

## Validation states

Each disease pathway must carry one of four states:

- `architecture_ready`: the program can enter the common workflow and all agents fail closed when evidence is absent.
- `software_qualified`: deterministic and adversarial synthetic cases pass the pathway software gate.
- `clinically_validated_silent`: retrospective or prospective-silent cases have been reviewed against an independent expert reference standard and meet the prespecified clinical performance gate.
- `clinical_release`: institutional governance has approved use for the stated intended purpose and setting.

No state may be inferred from another. In particular, software qualification is not clinical validation.

## Common software qualification gate

Every registered program must pass all of the following before `software_qualified`:

1. 100% exact provenance verification for confirmed extracted assertions in the qualification set.
2. Zero unsupported-provenance confirmed assertions.
3. Zero prohibited assertions.
4. 100% recall of prespecified critical missing-information items.
5. 100% detection of prespecified critical source conflicts.
6. Correct treatment chronology and line-of-therapy ordering when represented.
7. Correct disease-program and tumor-board assignment for all qualification cases.
8. No specialist agent may issue a claim from an empty, unverified, expired, synthetic-only, or disease-mismatched evidence store.
9. Molecular actionability must require disease- and alteration-matched verified evidence.
10. Guideline claims must require a current verified formal/consensus source and all structured prerequisites.
11. Trial matching must remain distinct from eligibility determination.
12. Safety non-match must never be interpreted as absence of risk.
13. Translational evidence must never be upgraded into clinical actionability.
14. Red Team safety-stop conditions must block recommendation propagation.
15. Consensus abstention must withhold management recommendations.
16. Repeated adversarial cases must be deterministic across at least three repeated executions.

A provisional development target is 10/10 core cases per disease family plus at least 5 adversarial cases per disease family, all passing the full gate. Higher-risk pathways should use larger suites.

## Disease-specific qualification matrix

Each program must include cases spanning, where clinically relevant:

- newly diagnosed / localized disease
- locally advanced disease
- recurrent / relapsed disease
- metastatic / progressive disease
- treatment-naive and previously treated states
- biomarker-positive and biomarker-negative states
- pending or conflicting biomarker states
- major treatment contraindication or safety constraint
- incomplete staging or missing decision-critical information
- clinically plausible but unsupported therapy temptation
- trial-relevant case with unresolved eligibility

Disease-specific required fields must be declared in a versioned pathway specification rather than hard-coded globally.

## Evidence-source qualification

For each disease program, maintain a versioned evidence manifest containing:

- source organization
- source type
- disease scope
- version/publication date
- access date
- authorization/license status
- machine-use restrictions
- source locator
- verification status
- structured recommendation or evidence record identifiers
- review/expiry date when applicable

Restricted material must not be ingested when its terms prohibit AI/model/tool processing. Evidence packages must fail closed if verification or authorization is absent.

## Clinical validation design

Clinical validation begins only after software qualification.

### Reference standard

Use an independent multidisciplinary expert panel appropriate to the disease program. The panel reviews the source case and contemporaneous evidence independently of the product output. Disagreements are adjudicated using a prespecified process.

### Suggested study phases

1. Retrospective validation using de-identified historical tumor-board cases.
2. Prospective-silent validation in which the product runs in parallel but does not influence care.
3. Human-factors/usability evaluation with intended clinician users.
4. Institutional release review for the defined intended purpose.

### Core clinical endpoints

At minimum measure:

- factual case-representation accuracy
- critical missing-information recall
- conflict detection sensitivity
- evidence-source correctness
- evidence-to-case applicability accuracy
- unsupported recommendation rate
- unsafe recommendation rate
- appropriate abstention rate
- expert concordance for management-option framing
- trial-match precision, kept separate from eligibility
- time-to-review and clinician correction burden

Safety-critical errors must be reported separately rather than averaged into an overall score.

## Release rule

A disease program may be displayed as `architecture_ready` once it enters the registry and passes architecture regression testing. It must not be labeled clinically validated until its disease-specific clinical validation package is complete.

The product UI and faculty-facing documentation must disclose the validation state for each disease program.

## Regulatory framing

The intended-use statement, degree of automation, clinician ability to independently review the basis of recommendations, and whether the software is used for time-critical decisions affect regulatory classification. Regulatory status must therefore be assessed separately from software qualification and clinical validation.

## Change control

Any change to extraction, disease classification, evidence adapters, recommendation logic, safety logic, consensus logic, or a disease-specific evidence package triggers impact assessment. Material changes require requalification of the affected pathway before its prior validation label is reused.
