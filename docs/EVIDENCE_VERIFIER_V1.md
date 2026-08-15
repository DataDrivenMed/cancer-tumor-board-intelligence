# Evidence Verifier v1.0.0

## Purpose

Evidence Verifier v1 is the deterministic claim-level gate between retrieved literature and downstream synthesis.

It is intentionally stricter than retrieval. A PubMed record being retrieved does not make a clinical claim verified.

## Core invariant

**No exact verified source span -> no verified literature claim.**

## Required inputs

Each candidate claim must identify:

- claim ID and claim text;
- claim type;
- PMID;
- frozen abstract SHA-256;
- exact supporting source excerpt;
- study design;
- study population;
- relevant endpoint(s);
- quantitative result(s) when expected for the claim type;
- applicability statement;
- evidence direction;
- explicit human-verification attestation.

The corresponding source snapshot must contain the same PMID, frozen abstract text and hash, and source-verification status.

## Hard failures

The claim is rejected when:

- the PMID was not retrieved;
- the source record is not verified;
- abstract text is unavailable;
- the frozen abstract hash is missing or mismatched;
- the supporting excerpt is absent or is not an exact substring of the frozen source.

A claim remains unverified when required human review or core structured evidence characterization is missing.

## Partial verification

A claim can be marked `PARTIALLY_VERIFIED` when provenance and core verification pass but an important non-source field remains incomplete, such as a missing quantitative result or applicability assessment.

Partial verification must remain visibly qualified downstream.

## Conflicting evidence

Claims explicitly marked as contradictory or mixed are preserved as `CONFLICTING`. The verifier does not suppress them and does not resolve conflicts by simple vote counting.

## What v1 does not establish

Evidence Verifier v1 does not establish:

- causal validity;
- risk of bias;
- guideline status;
- superiority of one therapy;
- patient-specific appropriateness;
- trial eligibility;
- full-text methodological adequacy when the abstract is insufficient;
- clinical recommendation safety.

## Intended next extension

A later verifier layer should add full-text critical appraisal where authorized, structured risk-of-bias assessment, population/intervention/comparator/outcome extraction, effect-size verification, contradictory-study clustering, temporal validity, and explicit applicability scoring before evidence reaches consensus synthesis.
