# Pan-Oncology Tumor Board Intelligence: Product Status

## What the product is

Tumor Board Intelligence is a pan-oncology research decision-support platform. It is not a one-case AML application. The same governed workflow now accepts and routes cases across 14 oncology tumor-board programs while preserving disease-specific diagnosis, provenance, evidence boundaries, missingness, conflicts, safety review, Red Team challenge, consensus gates, abstention, and auditability.

## Registered tumor-board programs

| Program | Product architecture | Disease-specific management evidence bundled in public product | Current validation state |
|---|---|---|---|
| Hematologic malignancies | Supported | Narrow ELN 2022 AML pathway plus governed deployment packages | Architecture ready |
| Breast oncology | Supported | Governed package required for formal/consensus guideline claims | Architecture ready |
| Thoracic oncology | Supported | Governed package required for formal/consensus guideline claims | Architecture ready |
| Gastrointestinal oncology | Supported | Governed package required for formal/consensus guideline claims | Architecture ready |
| Genitourinary oncology | Supported | Governed package required for formal/consensus guideline claims | Architecture ready |
| Gynecologic oncology | Supported | Governed package required for formal/consensus guideline claims | Architecture ready |
| Head and neck oncology | Supported | Governed package required for formal/consensus guideline claims | Architecture ready |
| Neuro-oncology | Supported | Governed package required for formal/consensus guideline claims | Architecture ready |
| Melanoma and cutaneous oncology | Supported | Governed package required for formal/consensus guideline claims | Architecture ready |
| Sarcoma and bone oncology | Supported | Governed package required for formal/consensus guideline claims | Architecture ready |
| Endocrine and neuroendocrine oncology | Supported | Governed package required for formal/consensus guideline claims | Architecture ready |
| Ophthalmic oncology | Supported | Governed package required for formal/consensus guideline claims | Architecture ready |
| Pediatric oncology | Supported | Governed package required for formal/consensus guideline claims | Architecture ready |
| Rare cancers and unknown primary | Supported | Governed package required for formal/consensus guideline claims | Architecture ready |

## What is shared across all programs

Every registered program uses the same common safety architecture:

1. Provenance-aware case extraction.
2. Deterministic tumor-board program assignment from the represented diagnosis, with an age-aware pediatric tie-breaker for overlapping programs.
3. First-class diagnosis, disease state, explicit stage, performance status, pathology, molecular findings, imaging, laboratory data, prior therapy, toxicities, comorbidities, and current medications.
4. Exact-source stage extraction only. TNM or imaging is not automatically converted into a stage.
5. Missing-information and conflict gates before specialist analysis.
6. Bounded specialist routing for guidance, molecular evidence, literature, trials, translational evidence, and safety.
7. CIViC molecular evidence discovery.
8. FDA labeling safety discovery through openFDA.
9. PubMed discovery when configured.
10. ClinicalTrials.gov discovery when configured.
11. Explicit human evidence attestation where required.
12. Clinical Red Team challenge before consensus.
13. Evidence-weighted consensus without agent voting.
14. Abstention when required evidence is unavailable or verification fails.
15. Structured tumor-board decision brief and audit trace.

## What “pan-oncology” does not mean

Pan-oncology architecture does not mean that one generic recommendation engine invents treatment guidance for every cancer. Disease-specific management claims remain fail-closed. If a current, verified, authorized formal or consensus guidance package is not available for the represented disease and question, the Consensus Engine withholds a management recommendation rather than using model memory or agent agreement.

This is intentional. A broad tumor-board platform should be able to represent, route, retrieve, challenge, and abstain across oncology without pretending that architecture coverage equals disease-specific evidence coverage.

## Software qualification status

The repository contains three relevant validation layers:

- Historical frozen extraction remediation qualification for the earlier extraction architecture.
- Historical frozen whole-system qualification for the earlier controlled AML-centered post-extraction architecture.
- Current pan-oncology common-core qualification covering all 14 registered tumor-board programs.

The current pan-oncology CI gate includes a 210-execution common-core matrix, 15 synthetic scenarios across each of 14 programs, plus dedicated program-routing and exact-stage regression tests, followed by the complete repository regression suite.

The common-core matrix tests platform mechanics such as routing, fail-closed evidence behavior, missing-information handling, stage conflict handling, domain boundaries, treatment-history handling, molecular routing, trial routing, safety routing, and unregistered-program reassignment. It does not establish disease-specific treatment correctness.

## Clinical validation status

No pan-oncology pathway should currently be described as clinically validated solely because the software tests pass. Clinical validation requires an independent disease-appropriate expert reference standard using retrospective and/or prospective-silent cases, prespecified endpoints, safety-critical error analysis, adjudication, human-factors evaluation, and institutional governance.

The required process is defined in `docs/PAN_ONCOLOGY_VALIDATION_PROTOCOL.md`.

## Appropriate faculty use now

The current build is appropriate for:

- faculty demonstration
- tumor-board workflow evaluation
- research and usability evaluation
- review of evidence-grounding and safety architecture
- controlled de-identified or synthetic case testing
- development of disease-specific governed evidence packages
- planning retrospective expert validation

It should not be represented as autonomous clinical decision-making software or as clinically validated across all cancers.
