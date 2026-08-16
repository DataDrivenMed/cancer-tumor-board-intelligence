# Production configuration

This repository is a research decision-support prototype. It is not clinically validated for autonomous or unsupervised patient-care use.

The product is designed to fail closed. Missing credentials or missing verified evidence do not cause the model to substitute memory. The affected evidence channel reports an unavailable or verification-failed state, and downstream Red Team / consensus gates may withhold management synthesis.

## 1. Model access for case extraction

Set these in the deployment secret store, not in source control.

```text
MODEL_AUTH_TOKEN=<provider token>
MODEL_NAME=openai/gpt-oss-120b:fireworks-ai
MODEL_BASE_URL=<optional provider-compatible base URL>
```

`MODEL_AUTH_TOKEN` is required only for model-assisted extraction. A canonical structured synthetic case can be tested without it.

## 2. Live public evidence retrieval

### PubMed

```text
ENABLE_LIVE_PUBMED=true
PUBMED_EMAIL=<contact email for NCBI E-utilities>
NCBI_API_KEY=<optional NCBI API key>
```

The contact email is required by this project's PubMed client. An NCBI API key is optional.

### ClinicalTrials.gov

```text
ENABLE_LIVE_CLINICALTRIALS=true
```

The official ClinicalTrials.gov API v2 does not require a secret API key for the current client. Trial matching remains distinct from eligibility. The product applies deterministic disease, recruitment-status, and explicit age-bound screening, but never asserts patient eligibility.

## 3. Governed clinical evidence packages

The following channels can be supplied as either an inline JSON secret or a path to a JSON file mounted by the deployment environment.

```text
GUIDELINE_EVIDENCE_JSON=<JSON object>
GUIDELINE_EVIDENCE_PATH=/secure/path/guideline.json

MOLECULAR_EVIDENCE_JSON=<JSON object or records list>
MOLECULAR_EVIDENCE_PATH=/secure/path/molecular.json

SAFETY_EVIDENCE_JSON=<JSON object or records list>
SAFETY_EVIDENCE_PATH=/secure/path/safety.json

TRANSLATIONAL_EVIDENCE_JSON=<JSON object or records list>
TRANSLATIONAL_EVIDENCE_PATH=/secure/path/translational.json
```

The `*_JSON` value takes precedence over the corresponding `*_PATH` value. Invalid packages fail closed and are not admitted into the production evidence store.

### Guideline contract

A guideline package contains:

```json
{
  "sources": [],
  "recommendations": []
}
```

Each source and recommendation must validate against `schemas/guideline.py`. Recommendation `source_id` values must resolve to a configured source. Management candidates remain gated by the existing Consensus Engine, which requires verified formal or consensus guideline support.

NCI PDQ is intentionally classified as an `authoritative_evidence_summary`, not a formal or consensus guideline. The existing NCI AML PDQ adapter preserves this distinction and requires explicit human verification before admission.

### Molecular contract

Molecular records must validate against `MolecularEvidenceRecord`. Production-mode molecular interpretation requires independently verified, human-verified, non-synthetic evidence. Gene identity alone is not treated as clinical actionability.

### Safety contract

Safety records must validate against `SafetyEvidenceRecord`. Production-mode safety claims require independently verified, human-verified, non-synthetic source records.

### Translational contract

Translational records remain non-decisional for management synthesis. Preclinical or mechanistic plausibility is not converted into clinical actionability.

## 4. Streamlit Community Cloud

For Streamlit Community Cloud, put secret values in the app's Secrets configuration. Do not commit `.streamlit/secrets.toml`.

Example secret names:

```toml
MODEL_AUTH_TOKEN = "..."
MODEL_NAME = "openai/gpt-oss-120b:fireworks-ai"
ENABLE_LIVE_PUBMED = "true"
PUBMED_EMAIL = "name@example.org"
ENABLE_LIVE_CLINICALTRIALS = "true"
```

Large governed evidence packages are better mounted or loaded through a secure deployment mechanism rather than copied into a public repository.

## 5. Safety boundaries

The production configuration does not change these invariants:

- No source -> no patient fact.
- No verified evidence -> no evidence claim.
- Pending != negative.
- Biological plausibility != clinical actionability.
- Trial match != trial eligibility.
- Agent agreement != truth.
- Low information -> abstain or request more information.
- Critical conflict -> human review.
- Failed verification -> do not propagate the claim.
- Consensus abstain -> management withheld.

Reasoning chain-of-thought is not stored or displayed. The audit layer contains structured facts, source references, statuses, evidence boundaries, and decision gates only.

## 6. Validation boundary

The historical frozen qualification results in this repository apply to their exact frozen benchmark versions and commits. Later product, retrieval, evidence-configuration, and UI changes are post-qualification integration work unless the frozen protocol is explicitly rerun. Passing ordinary regression CI is not equivalent to clinical validation or requalification.
