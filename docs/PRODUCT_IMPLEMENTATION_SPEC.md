# Tumor Board Intelligence: Approved Implementation Foundation

## Product objective

Convert incomplete oncology records into a decision-ready tumor-board package faster,
while preserving provenance, missingness, conflicting information, evidence boundaries,
uncertainty, and human judgment.

The current release remains a public research preview for synthetic or fully
de-identified cases. It is not clinically validated for autonomous or unsupervised
patient care.

## Approved technical and UX foundations

1. Next.js, React, and TypeScript for the professional web interface.
2. FastAPI as a thin service boundary around the governed Python core.
3. Vercel for the frontend and preview environments.
4. Render for the Python API and optional background workers.
5. One canonical clinician workspace: Intake, Verify, Evidence, Analyze, Brief.
6. A distinct research and qualification console using the same design system.
7. A contextual right-side inspector for Evidence, Activity, and Audit.
8. A light Clinical Editorial Intelligence visual system.
9. Backend-emitted workflow events with user-facing clinical consequences.
10. An immutable per-request `WorkflowContext` instead of shared runtime mutation.
11. Progressive disclosure from clinical task, to evidence and activity, to technical audit.

## Approved clinical interaction model

- accept narrative or documents before requiring structured fields;
- propose a board question when it is absent and require clinician confirmation before routing;
- make the longitudinal disease and treatment timeline central to case review;
- preserve competing source statements and audited clinician corrections;
- organize evidence by clinical question and evidence hierarchy, not by agent name;
- make abstention actionable by identifying what must be obtained or resolved next;
- show actual agent activity and its clinical consequence;
- preserve system synthesis, clinician judgment, and the eventual board decision separately;
- never force a ranking when the governed evidence cannot support one;
- keep agents mostly invisible in the primary workflow and inspectable in the activity layer.

## Non-negotiable boundaries

- no source means no patient fact;
- no verified evidence means no evidence claim;
- trial matching is not eligibility;
- biological plausibility is not clinical actionability;
- agent agreement is not truth;
- failed verification does not propagate;
- missing or conflicting decision-critical information can block synthesis;
- model memory does not replace a failed governed source;
- hidden chain-of-thought is not stored or displayed;
- software qualification is not clinical validation;
- a later correction never erases the historical record.
