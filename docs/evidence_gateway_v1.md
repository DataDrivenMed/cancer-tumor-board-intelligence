# Evidence Gateway / Source Ingestion v1.0.0

## Purpose

The Evidence Gateway is the deterministic trust boundary between external evidence material and specialist agents. It verifies whether a source package is authorized, frozen, traceable, and excerpt-grounded before any content is allowed to enter the Guideline Agent evidence store.

It does not summarize evidence, infer recommendations, classify a source by reputation, or decide that a treatment is appropriate.

## Pipeline position

`qualified case -> integrity gates -> router -> Evidence Gateway -> verified specialist evidence store -> Guideline Agent`

The Guideline Agent can only propagate recommendation records that the Evidence Gateway has admitted.

## Core invariants

1. No verified source -> no evidence claim.
2. No authorized license/use status -> source rejected.
3. Source text is normalized and frozen by SHA-256.
4. Manifest digest must exactly match the supplied source text.
5. Every recommendation record must reference the same source_id as the manifest.
6. Every recommendation requires an exact source excerpt that occurs verbatim in the supplied source text.
7. Every recommendation requires a source locator.
8. Source manifest and recommendation record both require explicit human verification.
9. Synthetic evidence is rejected in production mode.
10. A rejected recommendation never propagates to the specialist evidence store.
11. A rejected source contributes no source and no recommendation records.

## Source package

An `EvidenceIngestionPackage` contains:

- `EvidenceSourceManifest`
- the source text used for verification and hashing
- zero or more `EvidenceRecommendationRecord` objects
- optional package metadata

The source manifest records source type, organization, jurisdiction, canonical URL, version/date metadata, license/authorization status, expected SHA-256 digest, and human verification status.

## Output

`EvidenceIngestionResult` is one of:

- `accepted`
- `accepted_with_limitations`
- `rejected`

The result records accepted and rejected recommendation IDs, verification findings, the observed content hash, whether the source itself verified, and whether it may enter the Guideline Agent store.

## Public and licensed sources

The gateway is intentionally source-neutral. Public sources, licensed guidelines, and institution-authorized material can all use the same ingestion contract. Licensed full-text material should not be committed to the public repository. It should be supplied at runtime from an authorized storage location and only the minimum required metadata/audit record should persist in public code.

## NCI PDQ handling

NCI PDQ health-professional summaries are appropriate as `authoritative_evidence_summary`, not `formal_guideline`, because NCI explicitly states that PDQ treatment summaries are evidence-based clinician resources but do not provide formal health-care guidelines or recommendations. Any PDQ text used by the platform must still pass the same source, excerpt, date, and reuse-policy checks.

## Current limitation

v1.0.0 verifies already curated source packages. It does not yet fetch external URLs, monitor source updates, automatically detect changed versions, or extract recommendation records from raw guideline documents. Those functions belong to later source adapters and update-monitoring services.

Passing the automated tests demonstrates enforcement of these software invariants on synthetic fixtures. It is not clinical validation of any external evidence source.