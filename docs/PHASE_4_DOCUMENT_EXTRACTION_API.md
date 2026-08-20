# Phase 4: Document extraction API

The FastAPI boundary now exposes `POST /api/v1/cases/extract` for transient synthetic or fully de-identified document intake.

## Request

The request contains:

- a case identifier;
- a research case type;
- a document identifier;
- a filename ending in `.pdf`, `.docx`, `.txt`, or `.md`;
- base64-encoded document bytes.

The service rejects unsupported formats, invalid base64, empty documents, and documents larger than 8 MB.

## Processing

The endpoint uses the existing document parser and extraction v2.5 pipeline. Model credentials remain server-side. The source document is not written to disk or a database by this endpoint.

## Response

The response includes:

- the canonical `CancerTumorBoardCase`;
- raw normalized extraction data for downstream semantic integrity;
- exact source segments for provenance highlighting;
- extraction and API versions;
- provenance totals and failures;
- extraction warnings and normalization events;
- diagnostic-certainty classification.

## Fail-closed behavior

When neither `MODEL_AUTH_TOKEN` nor a local `MODEL_BASE_URL` is configured, live extraction returns HTTP 503. The service does not substitute fabricated facts or a hidden fallback extraction.
