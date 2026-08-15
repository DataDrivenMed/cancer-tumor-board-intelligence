# Translational Biology Agent v1.0.0

## Purpose

Summarize verified mechanistic, human-translational, and preclinical evidence that matches represented molecular findings in the canonical hematologic malignancy case.

## Safety boundary

This agent does **not** establish clinical actionability, treatment efficacy, regulatory indication, or patient-level eligibility. Translational and preclinical evidence remain explicitly distinct from clinical evidence.

Core invariants:

- No verified translational source -> no mechanistic claim.
- Gene match != alteration match.
- Alteration match != disease-context match.
- Mechanistic plausibility != clinical actionability.
- Preclinical sensitivity/resistance != treatment recommendation.
- Translational evidence != trial eligibility.
- Synthetic fixtures cannot enter production mode.

## Evidence tiers

- T1: human translational evidence.
- T2: in vivo preclinical evidence.
- T3: in vitro preclinical evidence.
- Hypothesis only.

The tier describes translational proximity to human disease. It is not a clinical recommendation grade.

## Production behavior

The production evidence store is empty by default. Until independently verified records are loaded through a governed evidence process, the agent returns `source_unavailable` rather than using model memory.

## Validation status

Implementation validation includes unit tests for production fail-safe behavior, synthetic-source blocking, disease and alteration matching, gene-only false matches, disease-context mismatch, preclinical resistance non-actionability, no-findings semantics, and deterministic repeatability.

Passing software tests do not constitute clinical validation or establish real-world safety.
