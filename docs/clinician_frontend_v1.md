# Clinician-Facing Frontend v1

## Purpose

This layer turns the qualified research backend into a single guided clinician-facing workflow without changing the safety contracts of the underlying extraction, integrity, evidence, Red Team, consensus, or brief-rendering components.

## Design language

The interface uses a warm executive visual system derived from the project design brief:

- Background: `#F7F7F4`
- Elevated surface: `#F2F1ED`
- Secondary elevated surface: `#E6E5E0`
- Primary text: `#26251E`
- Muted text: `#6B6B6B`
- Primary accent: `#C08532`
- Dark accent: `#9A6A28`
- Success: `#1F8A65`
- Error/blocking: `#CF2D56`
- 4 px radius vocabulary for cards and inputs
- Pill treatment for compact status chips and primary actions
- Low elevation only
- System-safe sans-serif typography with optional Inter if available in the browser

The interface does not copy third-party logos, brand marks, or identity assets.

## Clinician information architecture

Normal users should need only these views:

1. Overview
2. New Case
3. Case Review
4. Tumor Board Brief
5. Evidence
6. Audit

The detailed component-validation pages remain in the research application, but the main workflow no longer expects clinicians to operate individual agents manually.

## Progressive disclosure

The primary brief displays the information needed for multidisciplinary discussion. Evidence and Audit views expose the deeper machinery only when needed. This avoids turning the clinician experience into an agent-debugging console.

## Architecture anatomy

`app/pages/00_Architecture_Anatomy.py` provides an executive-level explanation of the full system:

1. Source truth and case construction
2. Deterministic integrity gates
3. Clinical routing
4. Parallel specialist evidence channels
5. Evidence verification and appraisal
6. Independent Clinical Red Team
7. Evidence-weighted consensus
8. Tumor Board Intelligence Brief
9. Human adjudication and future learning loop

It also explains the core safety invariants and the current software-validation boundary.

## Backend preservation

The frontend calls the existing backend contracts rather than reimplementing them. Narrative extraction uses `extract_case_v25`; downstream analysis uses `run_workflow`; final presentation uses the structured `tumor_board_brief` returned by the workflow.

A frontend redesign must not be described as requalification of the backend. Any future modification to qualified backend logic requires separate versioning and validation.

## Public-deployment boundary

The public Streamlit deployment remains limited to synthetic or fully de-identified cases. It is not configured as a production PHI environment and is not an autonomous clinical treatment system.
