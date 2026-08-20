# Phase 6: Governed analysis response contract

Phase 6 uses the existing commissioned-workflow endpoint:

`POST /api/v1/workflows/run-commissioned`

The service runs the request-specific evidence context through deterministic case gates, question routing, bounded specialist reviews, the Clinical Red Team, consensus, and brief rendering.

## Response fields used by the clinician workspace

- `result.routing` identifies the reviews selected for the represented board question.
- `result.specialist_outputs` preserves each channel's status, summary, records, limitations, warnings, and claim-permission flags.
- `result.red_team_report` preserves the independent challenge disposition, complete findings, blocking count, affected channels, and limitations.
- `result.consensus_report` records every evidence-channel state, candidate, challenge, uncertainty, discussion priority, abstention reason, and the `safe_to_render_decision_support` gate.
- `result.final_decision` provides the stable top-level decision state and support strength.
- `events` provides the clinician-facing activity sequence derived from backend audit events.
- `evidence_commission` records the revalidated candidate-set receipt for the same request.

## Synthesis permissions

Consensus does not count votes across agents. An explicit management candidate requires a verified formal or consensus guidance anchor. Molecular, literature, translational, clinical-trial, and safety outputs retain their own claim boundaries and may contextualize, constrain, or block a candidate.

If a required channel is unavailable, verification fails, a safety block remains, or the Clinical Red Team identifies a recommendation-blocking problem, `safe_to_render_decision_support` is false and the response preserves a structured abstention with next actions.
