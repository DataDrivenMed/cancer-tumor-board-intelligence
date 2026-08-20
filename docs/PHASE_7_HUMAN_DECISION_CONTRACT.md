# Phase 7: Human decision contract

Phase 7 adds a stateless endpoint for recording the handoff from governed system synthesis to human judgment:

```text
POST /api/v1/decisions/record
```

The endpoint was introduced with API contract `0.4.0` and remains available in the Phase 8 `0.5.0` contract.

## Request layers

### System decision

`system_decision` is the exact structured decision supplied by the completed workflow. The service includes it unchanged in the receipt. It is not edited by clinician or board fields.

### Clinician judgment

`clinician_judgment.position` accepts:

- `agree`
- `partially_agree`
- `disagree`
- `insufficient_context`

Clinician attestation is always required. Any position other than `agree` also requires at least one governed reason code and a written rationale.

Reason codes are:

- `clinical_context_not_represented`
- `evidence_interpretation_differs`
- `patient_preference`
- `institutional_practice`
- `safety_concern`
- `other`

### Board decision

`board_decision.status` is either `pending` or `recorded`. A pending decision is valid without outcome text or attestation. A recorded decision requires:

- an outcome category
- board decision text
- a written rationale
- board attestation

## Response receipt

The response contains:

- request and workflow request identifiers
- API version and research-use boundary
- a SHA-256 `decision_record_id` over the canonical three-layer package
- the preserved system decision
- the validated clinician judgment
- the board decision or explicit pending state
- structured human decision events
- `persisted: false`

`persisted: false` is intentional. Phase 7 validates and hands back a receipt without adding process-wide state. Durable versions, later amendments, and new-information reruns belong to Phase 8.

## Safety properties

- Only synthetic or fully de-identified research cases are accepted.
- Pydantic rejects missing required attestations and explanations.
- The endpoint does not create treatment recommendations.
- The endpoint does not change the prior workflow result.
- No process-wide decision registry is introduced.
