# NCI PDQ AML Authoritative Evidence Adapter v1.0.0

## Purpose

Connect the public National Cancer Institute Acute Myeloid Leukemia Treatment (PDQ®) Health Professional Version to the Evidence Gateway without allowing it to be misrepresented as a formal clinical guideline.

## Evidence classification

NCI PDQ AML is classified as `authoritative_evidence_summary`.

It must never be promoted to `formal_guideline` or `consensus_guideline`. The NCI page itself states that the health-professional summary is comprehensive, peer-reviewed, and evidence-based, while not providing formal guidelines or recommendations for health-care decisions.

## Trust boundary

The adapter performs only deterministic source operations:

1. Fetch the fixed HTTPS cancer.gov AML PDQ endpoint.
2. Reject redirects outside `https://www.cancer.gov/`.
3. Extract visible text with the Python standard library.
4. Normalize whitespace deterministically.
5. Compute SHA-256 over the normalized source snapshot.
6. Parse the visible NCI updated date when possible.
7. Search for a bounded set of exact candidate evidence statements.
8. Omit any candidate whose exact source text is no longer present.
9. Produce a candidate EvidenceIngestionPackage with all human-verification flags set to false.
10. Require explicit reviewer attestation before the Evidence Gateway can admit the source or statement records.

## Safety invariants

- No source fetch -> no NCI evidence package.
- Wrong origin -> fetch fails.
- No exact source statement -> candidate omitted.
- No human source attestation -> Evidence Gateway rejects the package.
- No human statement attestation -> that statement is rejected.
- Hash mismatch -> source is rejected.
- NCI PDQ -> never a formal guideline claim.
- Source change -> re-review required.
- No patient information is sent to NCI by the adapter.

## Public-repository policy

Only adapter code, metadata, bounded public-source statement fixtures used for validation, and tests are stored in this public repository. No licensed NCCN content, institutional policy content, PHI, credentials, or secrets may be committed.

## Validation

The automated test suite uses a local deterministic fixture and does not depend on network access. It verifies source classification, exact-source behavior, human-attestation gating, partial acceptance, fail-closed handling when upstream text changes, and the invariant that accepted PDQ content cannot support a formal guideline claim.
