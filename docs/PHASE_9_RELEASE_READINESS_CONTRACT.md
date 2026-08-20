# Phase 9: Evaluation, security, accessibility, and release readiness

Phase 9 completes the local research-software implementation. The API contract version is `0.6.0`.

This phase does not deploy the service and does not authorize patient care. It makes the difference between those decisions visible in code and in the interface.

## What was added

### Deterministic workflow evaluation

`POST /api/v1/evaluations/workflow` evaluates one workflow package. It checks explicit invariants rather than asking another model to grade the output.

Critical gates cover:

1. research-case boundaries;
2. safe rendering of a primary strategy;
3. coherent abstention;
4. source traces for rendered decision support;
5. evidence attestation;
6. exact separation of system synthesis and human decision;
7. clinician and board attestations;
8. Clinical Red Team completion; and
9. audit lineage for reused specialist outputs.

`release_eligible` means that the submitted package passed these research-software governance checks. It never means clinically correct, clinically validated, or authorized for care.

### Saved-version scorecard

`GET /api/v1/evaluations/summary` evaluates every immutable case version in the configured SQLite store. It reports three primary measures:

| Measure | Definition | Target |
| --- | --- | --- |
| Critical safety-gate adherence | Saved packages with no critical governance failure divided by all evaluated packages | 100% |
| Human-decision separation | Human records that exactly preserve the workflow synthesis divided by records evaluated | 100% |
| Evidence-attestation completeness | Evidence reviews with attestation divided by reviews evaluated | 100% |

The zero-tolerance guardrails are unsafe render violations, decision-lineage violations, and unaudited specialist reuse. Each target is zero.

An empty store returns `baseline_pending`. The API does not invent sample values.

### Release-readiness levels

`GET /api/v1/release/readiness` returns three levels:

1. `local_research` checks the code-level research boundary, fail-closed behavior, request isolation, and deterministic evaluation.
2. `production_research` checks deployment environment, authentication, HTTPS, explicit CORS, trusted hosts, shared rate limiting, monitoring, backups, and durable state configuration.
3. `clinical_release` remains blocked. It requires institutional privacy, security, regulatory review, local validation, prospective or silent evaluation, change control, and accountable clinical governance outside this repository.

## HTTP security controls

The FastAPI boundary now provides:

- trusted-host validation;
- a configurable request-size ceiling;
- explicit CORS origins;
- request identifiers;
- no-store caching;
- content-type sniffing protection;
- frame denial;
- restrictive referrer and permissions policies;
- a restrictive API content security policy; and
- optional HSTS only when HTTPS is explicitly required.

API documentation stays enabled for local development and can be disabled for production.

## Configuration

The Phase 9 variables are documented in `.env.example`:

```text
DEPLOYMENT_ENV=local
TRUSTED_HOSTS=localhost,127.0.0.1,testserver
MAX_REQUEST_BYTES=16777216
ENABLE_API_DOCS=true
AUTH_MODE=none
REQUIRE_HTTPS=false
RATE_LIMITING_MODE=none
MONITORING_SINK=
BACKUP_POLICY=
```

The readiness endpoint treats the local defaults as blocked for production research. This is intentional.

## Important evaluation limit

These measures test whether the software followed its declared governance rules. They do not establish clinical accuracy, outcome benefit, model calibration, subgroup fairness, external validity, or site-specific safety.
