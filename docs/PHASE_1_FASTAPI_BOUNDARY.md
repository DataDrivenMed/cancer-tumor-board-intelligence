# Phase 1: FastAPI Service Boundary

## Purpose

Phase 1 gives the existing governed Python workflow a stable HTTP interface for the
future Next.js clinician workspace. It is a thin boundary, not a second clinical
engine.

An analogy: the governed workflow is the hospital laboratory, and the API is the
specimen window. The window standardizes how a case enters and how a result leaves,
but it does not change the laboratory method.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Lightweight service health check |
| `GET` | `/api/v1/runtime/status` | Non-secret evidence-channel readiness for the inspector |
| `POST` | `/api/v1/workflows/run` | Validate a canonical case and run the governed workflow |
| `GET` | `/docs` | Interactive API documentation in local or protected environments |

## Request isolation

FastAPI calls `build_workflow_context()` through a request dependency. A new immutable
`WorkflowContext` is created for each status or workflow request. The API never installs
request dependencies in the process-wide legacy registry.

## Workflow response

The workflow endpoint returns:

- a generated or caller-supplied safe request identifier;
- the API version and case identifier;
- non-secret runtime readiness;
- the complete governed workflow result;
- user-facing activity events derived one-for-one from actual backend audit events.

Activity events include both a readable clinical consequence and the original audit
event name and detail. They do not expose or reconstruct hidden reasoning.

## Research-use boundary

This public API accepts only `synthetic` and `deidentified_research` cases. Requests
marked `clinical` or `prospective_silent` receive HTTP 403. Supporting those case types
requires a separately governed institutional deployment with privacy, security,
validation, authorization, and audit controls.

## Deliberately not included in Phase 1

- authentication or institutional single sign-on;
- persistent case storage;
- document upload and extraction endpoints;
- background job queues or streaming events;
- the Next.js interface;
- any change to routing, evidence gates, consensus, abstention, or brief logic.

These omissions keep Phase 1 small enough to verify and prevent the API layer from
quietly becoming a second source of clinical behavior.

## Run locally

From the repository folder, after installing `requirements.txt`:

```bash
uvicorn api.main:app --reload --port 8000
```

Then open `http://127.0.0.1:8000/docs` in a browser. The future Next.js application will
connect from `http://localhost:3000`. Other allowed frontend origins must be explicitly
listed in the deployment environment variable `CORS_ALLOWED_ORIGINS`.
