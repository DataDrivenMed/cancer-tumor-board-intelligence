# Phase 8: Case versioning and targeted-rerun contract

Phase 8 adds append-only local persistence and governed update lineage. The API contract version is `0.5.0`.

## Endpoints

```text
POST /api/v1/cases/versions
GET  /api/v1/cases/{case_id}/versions
GET  /api/v1/cases/{case_id}/versions/{version_id}
POST /api/v1/case-version-updates/assess
POST /api/v1/workflows/rerun-targeted
```

## Immutable saved package

A version contains:

- canonical case
- raw extraction when available
- complete workflow response
- commissioned evidence review
- clinician and board decision receipt
- parent version identifier
- update trigger and change summary
- creation timestamp and SHA-256 content hash

The service validates that the case, workflow, and human decision refer to the same case and workflow request. It also confirms that the human receipt contains the workflow's system decision unchanged.

The `(case_id, content_hash)` uniqueness rule makes an identical save idempotent. A repeated submission returns the existing immutable version.

## Local persistence

The default database is:

```text
.local/tumor_board_state.sqlite3
```

The `.local` directory is excluded from source control. A different local path can be configured with:

```text
TUMOR_BOARD_STATE_DB=/approved/local/path/tumor_board_state.sqlite3
```

SQLite uses a transaction when assigning each case's next version number. Version records are append-only through the public API.

## Update impact assessment

The assessment endpoint compares the full canonical JSON of a selected base version and a proposed updated case. It rejects:

- a changed case identifier
- a changed case type
- an update with no actual field changes
- an unattested update
- a missing base version

The response identifies changed paths and roots, change severity, affected specialist agents, specialist agents eligible for reuse, and the controls that must always run again.

## Targeted rerun rules

A targeted rerun always executes:

- semantic-integrity validation
- deterministic quality review
- case-integrity gate
- missing-information analysis
- routing
- Clinical Red Team
- consensus
- tumor-board brief rendering

Specialist evidence outputs may be reused only when all of these are true:

1. The specialist is selected for the updated case.
2. The changed-field dependency map does not affect that specialist.
3. The evidence decision package for that specialist has not changed.
4. The prior JSON output validates against the specialist's current Pydantic report schema.

Every other selected specialist runs again. The response lists executed and reused specialists separately and adds structured audit events for reuse.

## Decision lineage

The prior clinician judgment and board decision are never carried forward as the new decision. They remain historical in the base version. The updated workflow must receive a new Phase 7 human decision package before the child version can be saved.
