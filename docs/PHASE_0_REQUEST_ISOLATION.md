# Phase 0: Request Isolation and Baseline Protection

## Purpose

Phase 0 prepares the existing governed Python core for a concurrent web API without
changing its clinical decision logic, evidence policies, qualification assets, or
public research-use boundary.

## Baseline

- Branch point: `9662fc82e284169008fa0bd9a14565b2b2111231`
- Baseline result: 577 tests passed.
- Known pre-existing failure discovered: `tests/test_dark_product_ui.py::test_shared_warm_editorial_theme_is_wired`.
- The failure reflected a mismatch between the current dark legacy theme and an older
  warm-theme assertion. The test now checks the theme that the Streamlit code actually
  implements. No interface code or palette was changed. The approved new Next.js
  application still uses the light Clinical Editorial Intelligence direction.

## Risk addressed

The clinician workspace previously built session-specific evidence agents and assigned
them to the module-level `orchestration.workflow.AGENT_REGISTRY`. Python modules are
shared within a server process, so a later browser session could replace the registry
while another case was running.

## Phase 0 design

`WorkflowContext` now owns the agent registry and non-secret runtime status for one
request or browser session. The context:

- copies the supplied mappings;
- exposes them as read-only mappings;
- resolves routed agents explicitly;
- can provide a plain status snapshot for the UI;
- is passed directly into `run_workflow`;
- is also passed to governed on-demand specialist questions.

The module-level registry remains only as a backward-compatible default for frozen
tests and legacy research pages that do not install user-specific evidence overrides.
The clinician workspace uses the request-specific path.

## Behavior intentionally unchanged

- semantic-integrity inspection;
- deterministic case-integrity gates;
- missing-information gates;
- clinical routing;
- specialist agent logic;
- evidence admission rules;
- Clinical Red Team behavior;
- evidence-weighted consensus;
- abstention;
- tumor-board brief rendering;
- audit event contents;
- qualification history;
- synthetic and de-identified research-use limitation.

## New proof

The Phase 0 test suite creates two different workflow contexts and executes alternating
case runs concurrently. One context has governed public AML guidance and the other has
an empty guideline store. Each run must retain the evidence behavior of its own context.
The test also confirms that the context registry cannot be mutated after construction.

## Next phase

Phase 1 will add a thin FastAPI boundary around the governed Python core. The API will
create one `WorkflowContext` per request or case run rather than modifying process-wide
state.
