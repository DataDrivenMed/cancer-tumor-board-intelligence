# Faculty Demonstration Guide

## Tumor Board Intelligence

Tumor Board Intelligence is a pan-oncology research decision-support workspace for structured multidisciplinary cancer case review. The product is designed to help a tumor board organize the patient state, identify missing or conflicting information, retrieve bounded evidence, challenge proposed conclusions, and produce an auditable decision-support brief.

It is not a single AML case demonstration. AML was the first deeply commissioned disease pathway, but the common platform now supports 14 tumor-board programs.

## What to demonstrate

### 1. Start with a de-identified case

Paste a de-identified narrative or upload a supported de-identified document. The extraction layer creates a canonical structured case and preserves source provenance for substantive patient facts.

For a controlled demonstration, the bundled synthetic case can also be used.

### 2. Review the represented patient state

Before evidence analysis, confirm that the structured representation matches the source. The workflow distinguishes observed information from missing, pending, unavailable, and conflicting information.

The canonical case can represent:

- diagnosis
- current disease state
- explicit stage when directly stated in the source
- performance status
- pathology
- molecular findings
- imaging
- laboratory data
- comorbidities
- prior and current treatment
- toxicities
- transplant or cellular therapy
- current medications
- the tumor-board question

The system does not calculate a cancer stage merely because TNM or imaging information is present.

### 3. Observe automatic tumor-board routing

The represented diagnosis is mapped to one of the registered tumor-board programs. The diagnosis itself is not replaced by the program label.

The programs are hematologic, breast, thoracic, gastrointestinal, genitourinary, gynecologic, head and neck, neuro-oncology, melanoma/cutaneous, sarcoma/bone, endocrine/neuroendocrine, ophthalmic, pediatric, and rare/unknown-primary oncology.

### 4. Review missing information and conflicts

The system identifies information gaps before specialist analysis. Decision-blocking gaps stop downstream recommendation synthesis rather than being filled from model knowledge.

Examples include an unresolved diagnosis, a major source conflict, missing prior therapy in a progressive/relapsed case, or conflicting explicit stage statements.

### 5. Review evidence sources

Depending on configuration and the represented case, the product can use:

- disease-specific governed guidance packages
- CIViC for molecular evidence discovery
- FDA labeling through openFDA for safety evidence discovery
- PubMed for literature discovery
- ClinicalTrials.gov for trial discovery
- separately governed translational evidence

Evidence discovery and evidence admission are separate. Retrieval alone does not make a record patient-specific clinical truth.

### 6. Review the safety boundaries

Several product behaviors are intentionally conservative:

- pending does not become negative
- no source does not become a patient fact
- a molecular finding does not become actionable because a gene name is recognized
- trial matching does not become trial eligibility
- absence of a safety match does not mean absence of risk
- translational plausibility does not become clinical actionability
- agent agreement is not treated as truth
- required evidence failure can force abstention

### 7. Run analysis and inspect challenge review

The workflow performs deterministic quality checks, specialist analysis, a Clinical Red Team challenge, and consensus synthesis. The Red Team looks for evidence-promotion errors, missing required channels, unresolved safety conditions, and other structural reasons that a recommendation should not propagate.

### 8. Review the decision brief

The final brief separates:

- represented patient facts
- available evidence
- limitations
- unresolved uncertainties
- challenge findings
- decision-support state
- abstention reasons when applicable
- audit information

For disease programs without an admitted current formal or consensus guidance package, the system can still organize the case and retrieve bounded evidence, but it will withhold an unsupported management recommendation.

## What faculty feedback is most useful

Faculty evaluation should focus on whether the system improves the quality and efficiency of tumor-board preparation without obscuring uncertainty. Useful questions include:

- Is the patient representation faithful to the source?
- Are clinically important missing items easy to see?
- Are conflicts handled appropriately?
- Is the evidence trail transparent enough to verify independently?
- Does the system abstain when it should?
- Are the decision brief and challenge findings useful for multidisciplinary discussion?
- What disease-specific information should be required for that tumor board?
- What evidence sources should be formally commissioned for that program?

## Current validation label

The pan-oncology platform is currently **architecture ready**. The common architecture has automated qualification coverage across all 14 tumor-board programs, including a 210-execution synthetic common-core matrix and full repository regression testing.

This label does not mean clinically validated. Disease-specific clinical validation requires independent expert reference standards and retrospective and/or prospective-silent evaluation under the protocol in `docs/PAN_ONCOLOGY_VALIDATION_PROTOCOL.md`.

## Suggested description to faculty

> Tumor Board Intelligence is a pan-oncology research decision-support platform that structures de-identified cancer cases, preserves provenance and uncertainty, retrieves bounded evidence, identifies missing and conflicting information, performs independent challenge review, and generates an auditable tumor-board brief. The common architecture supports 14 oncology tumor-board programs, while disease-specific evidence and clinical validation are governed separately so the system can abstain rather than generate unsupported recommendations.
