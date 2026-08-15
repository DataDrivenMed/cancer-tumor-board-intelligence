# Literature Agent v1.0.0 Contract

## Purpose

Retrieve candidate biomedical literature from PubMed for a bounded hematologic-malignancy tumor-board question while preserving a strict separation between **literature discovery** and **clinical evidence claims**.

## Position in the workflow

`canonical case -> integrity gates -> missing-information gate -> Clinical Router -> Literature Agent -> future Evidence Verifier -> Red Team / Consensus`

## Allowed inputs

- Confirmed structured diagnosis
- Structured disease state
- Molecular gene symbols already represented in the canonical case
- Clinical-question type/family

The free-text clinical question is **not transmitted verbatim** to PubMed. It is used only to classify the search family. This reduces the chance of sending narrative identifiers to an external service.

## External source

PubMed via NCBI Entrez E-utilities:

- ESearch for PMIDs
- One batched EFetch request for PubMed XML

The client includes `tool` and `email` parameters on requests. An NCBI API key is optional and should be kept in secrets, never committed to the repository.

## Outputs

Typed `LiteratureReport` with:

- exact PubMed query
- bounded query terms
- returned PMIDs
- normalized bibliographic metadata
- DOI and PMCID when represented by PubMed
- publication types
- abstract availability
- abstract SHA-256
- a short inspection excerpt when available
- warnings and limitations

## Critical claim boundary

Version 1 **cannot support a literature claim**. `can_support_literature_claim` is always `false`.

Retrieval alone must never be translated into statements such as:

- treatment X improves survival
- treatment Y is superior
- a molecular alteration is clinically actionable
- a study applies to this patient
- the retrieved papers represent the totality of evidence

Those require a separate Evidence Verifier that checks study design, population, endpoints, numerical results, risk of bias, applicability, contradictory evidence, and exact claim-level provenance.

## Failure behavior

- No configured PubMed client -> `source_unavailable`
- No records -> `no_evidence_found`, with explicit warning that no-result retrieval is not proof of absence of evidence
- ESearch/EFetch/parsing error -> `tool_failure`
- Outside hematologic malignancy domain -> `abstain_domain`

No failure state may emit a clinical claim.

## Determinism and auditability

Given the same canonical case and returned PubMed payloads, query generation and XML normalization are deterministic. Search results themselves may change as PubMed is updated, so the exact query, PMIDs, and retrieved metadata are preserved in the report.

## Production safety

The main workflow uses a production-safe unconfigured Literature Agent by default. Live PubMed access is explicitly enabled through the dedicated validation page by providing an NCBI contact email. This prevents CI and ordinary workflow execution from silently making network calls.
