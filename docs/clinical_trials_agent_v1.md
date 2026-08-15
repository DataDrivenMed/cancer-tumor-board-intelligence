# Clinical Trials Agent v1.0.0

## Purpose
Retrieve current ClinicalTrials.gov study records through the official API v2 and identify conservative possible trial matches from bounded structured case concepts.

## Safety boundary
**TRIAL MATCH IS NOT TRIAL ELIGIBILITY.** The agent never asserts enrollment eligibility, site availability, expected benefit, or that an investigational intervention should be selected.

## External-data minimization
The API query is constructed from the canonical represented diagnosis and up to five represented gene symbols. Free-text tumor-board narrative and care-site fields are not transmitted.

## Match rule
A returned record becomes a possible match only when:
1. the record is source-verified from ClinicalTrials.gov;
2. overall status is RECRUITING, NOT_YET_RECRUITING, or ENROLLING_BY_INVITATION; and
3. the record overlaps at least one bounded structured case concept.

The agent does not infer eligibility from these overlaps.

## Required human resolution before eligibility
Full inclusion/exclusion criteria, site-specific recruitment, laboratory/organ-function thresholds, prior-treatment and washout rules, and investigator confirmation remain unresolved by default.

## Failure behavior
- No client configured: SOURCE_UNAVAILABLE.
- API failure: TOOL_FAILURE.
- No returned records or no records passing the conservative rule: NO_EVIDENCE_FOUND.
- A no-result search does not establish absence of relevant trials.

## Source
ClinicalTrials.gov REST API v2. The API version timestamp is captured when available so the search can be audited against the registry refresh state.

## Validation scope
Unit tests use deterministic offline fixtures. Live registry retrieval is exercised explicitly on the Streamlit validation page and is not performed by CI.
