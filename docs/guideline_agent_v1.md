# Guideline Agent v1.0.0

## Purpose

The Guideline Agent is an evidence-bounded specialist service that matches a canonical hematologic-malignancy case to pre-ingested, verified, authorized guidance statements.

It does **not** generate guideline content from model memory, infer recommendations from general knowledge, scrape or reproduce licensed guideline text without authorization, or promote an evidence summary into a formal guideline.

## Position in the pipeline

`v2.5 qualified extraction -> semantic integrity -> Case Integrity / Data QA -> Missing Information Agent -> Clinical Router -> Guideline Agent`

The v2.5 extraction implementation and its frozen qualification evidence are not modified by this component.

## Core safety principle

**No verified source -> no guideline claim.**

A clinical statement is only returned when all of the following are true:

1. The source is registered and verified.
2. The recommendation record is independently marked source-verified.
3. The record contains a non-empty exact source excerpt.
4. The source/recommendation is current under explicit version/effective-date metadata.
5. The represented diagnosis, disease state, and question domain match the recommendation's bounded applicability fields.

## Source taxonomy

The source type is preserved in the output:

- `formal_guideline`
- `consensus_guideline`
- `authoritative_evidence_summary`
- `regulatory`
- `institutional_policy`
- `synthetic_fixture`

Only formal or consensus guideline matches can set `can_support_guideline_claim=true`.

An authoritative evidence summary may be clinically useful evidence, but it is not relabeled as a guideline recommendation. For example, NCI PDQ health-professional summaries explicitly describe themselves as comprehensive, peer-reviewed, evidence-based information and state that they do not provide formal guidelines or recommendations. Therefore PDQ belongs in the `authoritative_evidence_summary` category rather than `formal_guideline`.

## Public repository / licensing policy

The production evidence store is empty by default. This is intentional.

Licensed or institution-authorized guideline content must not be copied into the public repository unless the applicable license permits it. Future ingestion must retain source identity, version, jurisdiction, license status, content hash, exact excerpt, and locator.

## Typed output

`GuidelineReport` includes:

- execution status
- matched source-bounded statements
- source identity and organization
- source type and jurisdiction
- exact source excerpt and locator
- match dimensions
- evidence/strength metadata when explicitly present in the source record
- warnings and limitations
- count of formal guideline matches
- `can_support_guideline_claim`

## Execution states

- `completed`: at least one current verified formal or consensus guideline statement matched.
- `completed_with_limitations`: verified evidence matched, but no formal/consensus guideline matched.
- `no_evidence_found`: verified sources exist, but no current record matched the represented case.
- `source_unavailable`: no source is configured.
- `verification_failed`: configured sources are unverified or not authorized for the current execution.
- `abstain_domain`: case is outside hematologic malignancies in v1.

## Synthetic validation fixture

The repository contains a fictional synthetic guidance fixture for software testing. It is disabled by default and requires `allow_synthetic=True`. Synthetic fixture output can never set `can_support_guideline_claim=true`.

## What v1 validates

Automated tests validate deterministic matching, source verification, diagnosis/state/domain mismatch handling, explicit source-currentness checks, synthetic-fixture isolation, and prevention of evidence-summary-to-guideline relabeling.

Passing these software tests is not clinical validation and does not demonstrate completeness of guideline coverage, clinical correctness of a real guideline corpus, or patient-care safety.
