# Safety Agent v1.0.0

## Purpose

The Safety Agent is a deterministic, evidence-bounded specialist that matches represented therapies and patient-context triggers to pre-verified safety evidence records.

## Core invariants

- NO VERIFIED SAFETY SOURCE -> NO SAFETY CLAIM
- THERAPY MATCH != CONTRAINDICATION
- CONDITIONAL CONTRAINDICATION REQUIRES THE REPRESENTED PATIENT TRIGGER
- MISSING MONITORING DATA != NORMAL MONITORING DATA
- NO MATCH != SAFE
- SAFETY FINDING != TREATMENT RECOMMENDATION

## Inputs

- Canonical `CancerTumorBoardCase`
- `SafetyEvidenceStore` containing independently verified evidence records

## Outputs

`SafetyReport` with:

- matched evidence records;
- exact source title, locator, and excerpt;
- safety issue and severity;
- matched therapy terms;
- matched patient trigger terms;
- required monitoring parameters;
- unresolved parameters;
- contraindication status;
- recommendation-blocking status;
- explicit limitations.

## Matching

A record can match only when:

1. source verification and human verification are true;
2. synthetic evidence is not being used in production mode;
3. represented therapy terms match the evidence record;
4. disease context matches when the record is disease-specific;
5. patient trigger terms match when the safety statement is conditional.

## Blocking behavior

A matched contraindication is recommendation-blocking. A high- or critical-severity record with required parameters that are not represented as confirmed is also recommendation-blocking pending resolution and human review.

## Production boundary

The production evidence store is intentionally empty until authorized, versioned, independently verified safety sources are ingested. The agent will not use model memory to infer contraindications, interactions, toxicities, monitoring requirements, or dose changes.

## Limitations

Version 1 is a deterministic evidence matcher, not a prescribing engine. It does not replace current prescribing information, pharmacy review, drug-interaction checking, renal/hepatic dose assessment, organ-function review, or clinician judgment. It has not undergone prospective clinical validation.
