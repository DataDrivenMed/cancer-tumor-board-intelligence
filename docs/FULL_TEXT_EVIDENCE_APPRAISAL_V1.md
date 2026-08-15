# Full-Text Evidence Appraisal v1.0.0

## Purpose

Full-Text Evidence Appraisal v1 is the verification layer between abstract-level evidence verification and later tumor-board synthesis. It verifies that a human-authored appraisal is complete, internally consistent, and exactly traceable to a frozen full-text source snapshot.

## Inputs

- Frozen full-text source with PMID, title, source type, verification status, and SHA-256.
- Human-authored structured PICO.
- Endpoint records with exact source excerpts.
- Effect estimates with exact source excerpts.
- Structured risk-of-bias assessment.
- Structured applicability assessment.
- Optional linked claim IDs from Evidence Verifier v1.

## Deterministic invariants

1. Frozen full-text SHA-256 must match the supplied source text.
2. Candidate PMID must equal source PMID.
3. Source and appraisal must be explicitly human verified.
4. PICO source excerpts must occur exactly in the frozen full text.
5. Endpoint source excerpts must occur exactly in the frozen full text.
6. Effect-estimate source excerpts must occur exactly in the frozen full text.
7. Risk-of-bias promotion requires human verification and a non-unclear overall judgement.
8. Applicability promotion requires human verification and a non-unclear judgement.
9. Linked evidence claims are promoted to full-text verified only when all core gates, risk-of-bias, and applicability gates pass.
10. A verified full-text appraisal is evidence qualification, not a patient-specific recommendation.

## Statuses

- `VERIFIED`: source integrity, exact provenance, PICO/endpoints, risk of bias, and applicability gates all pass.
- `PARTIALLY_VERIFIED`: exact core evidence passes but risk-of-bias and/or applicability review is incomplete.
- `UNVERIFIED`: core appraisal is incomplete without a hard source-integrity failure.
- `REJECTED`: source hash, PMID, exact-source-span, or required human-review integrity fails.

## Safety boundary

The service does not autonomously infer PICO, effect size, risk of bias, applicability, or clinical meaning. Those are reviewed structured assertions. The deterministic layer verifies traceability and gating only.

The initial Streamlit page uses synthetic text only. It does not ingest copyrighted full-text articles into the public repository.

## Validation targets

Regression tests cover:

- fully verified promotion;
- SHA-256 mismatch rejection;
- non-exact PICO rejection;
- non-exact effect-size rejection;
- incomplete risk-of-bias review;
- unclear applicability;
- PMID mismatch;
- deterministic repeatability.
