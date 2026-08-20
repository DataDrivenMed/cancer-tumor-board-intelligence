# Phase 5: Governed evidence commissioning API

Phase 5 adds a human-controlled evidence admission step between case confirmation and analysis. Retrieval produces candidates only. A candidate cannot enter the request's evidence stores until the clinician records a decision.

## Request flow

1. `POST /api/v1/evidence/candidates` receives a validated synthetic or de-identified case.
2. The service retrieves case-matched guideline, molecular, and safety candidates.
3. The response includes exact source excerpts, locators, verification state, and a SHA-256 `candidate_set_id`.
4. The clinician approves or rejects every candidate. Every rejection requires a reason. Any approval requires a human attestation.
5. `POST /api/v1/workflows/run-commissioned` receives the case, the candidate-set identifier, and the complete decision list.
6. The service retrieves the candidates again and verifies the hash before analysis. A changed or incomplete set is rejected with HTTP 409.
7. Approved records are placed into evidence stores created only for that request. The governed workflow then runs with a new `WorkflowContext`.

No server session or process-wide approval registry is used. A request cannot inherit another request's evidence decisions.

## Modes

- `guided_fixture` is a no-network demonstration. It includes the public ELN guidance candidate plus controlled molecular and safety fixtures. Synthetic records retain `synthetic=true`, so production agents exclude them even if they are submitted as approved.
- `live` uses the existing CIViC and FDA Structured Product Labeling retrieval paths. Source discovery still does not establish clinical applicability.

## Evidence boundaries

This phase directly commissions the channels that already have exact-record human-attestation support: guideline, molecular, and safety evidence.

Literature, ClinicalTrials.gov, and translational evidence remain separate downstream governed channels. Literature discovery requires independent verification, a possible trial match is not eligibility, and mechanistic evidence cannot independently support a clinical action.

## Local use

Start the service:

```bash
uvicorn api.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000/docs`, call `/api/v1/evidence/candidates` first, and use the returned `candidate_set_id` and complete decision list in `/api/v1/workflows/run-commissioned`.
