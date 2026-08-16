# Production configuration

This repository is a research decision-support prototype. It is not clinically validated for autonomous or unsupervised patient-care use.

The product is designed to fail closed. Missing credentials or missing verified evidence do not cause the model to substitute memory. The affected evidence channel reports an unavailable or verification-failed state, and downstream Red Team / consensus gates may withhold management synthesis.

## 1. Model access for case extraction

Set these in the deployment secret store, not in source control.

```text
MODEL_AUTH_TOKEN=<provider token>
MODEL_NAME=openai/gpt-oss-120b:fireworks-ai
MODEL_REASONING_EFFORT=high
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

### CIViC molecular evidence

CIViC is the primary public molecular-actionability source selected for product v1. CIViC content is open and its API supports anonymous reads. A CIViC API key is optional and is useful for sustained automated access beyond the default anonymous rate limit.

```text
CIVIC_API_KEY=<optional CIViC API key>
```

`services/civic_molecular_adapter.py` retrieves only `ACCEPTED` CIViC Evidence Items through the official GraphQL API. Retrieved records are source-verified candidates, but **are not automatically marked as locally human-verified**. They therefore cannot pass the Molecular Agent's clinical-actionability gate until an explicit local attestation is applied.

This distinction is intentional: external expert curation is valuable evidence, but retrieval alone is not equivalent to local admission into the product's governed evidence store.

OncoKB is an optional future secondary molecular source. It is not required for v1. If added, the deployment must first obtain the appropriate OncoKB license and API token for the intended research or clinical use; OncoKB content must not be scraped or redistributed.

### FDA safety-label evidence

FDA Structured Product Labeling / openFDA is the primary public safety-label source selected for product v1.

```text
OPENFDA_API_KEY=<recommended free openFDA API key>
```

`services/fda_label_adapter.py` retrieves bounded label sections such as boxed warnings, contraindications, warnings/cautions, interactions, adverse reactions, and dosing/administration text. Retrieval produces source candidates only. A locally attested `SafetyEvidenceRecord` can be created only when the reviewer supplies an exact excerpt that is literally present in the selected label section.

FDA retrieval does not itself create a patient-specific contraindication, monitoring recommendation, or dose decision.

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

### Guideline contract and NCCN

For the initial AML deployment, institution-authorized NCCN guidance is the preferred governed formal-guideline source when the institution's access and reuse terms permit this use.

**Never commit NCCN PDFs, extracted text, recommendation tables, credentials, or other licensed content to this public repository.** A current institution-authorized NCCN AML source should be processed outside the public repository into a secure deployment-time package.

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

For public molecular evidence, the preferred commissioning path is:

1. retrieve accepted CIViC evidence with `CIViCMolecularClient`;
2. review the disease, molecular profile, evidence level, direction, therapy, and exact CIViC evidence statement;
3. explicitly attest only the approved evidence IDs with `attest_civic_records`;
4. serialize the resulting `MolecularEvidenceStore` to a secure `MOLECULAR_EVIDENCE_PATH` or `MOLECULAR_EVIDENCE_JSON` value.

### Safety contract

Safety records must validate against `SafetyEvidenceRecord`. Production-mode safety claims require independently verified, human-verified, non-synthetic source records.

For FDA safety evidence, the preferred commissioning path is:

1. retrieve current label-section candidates with `FDALabelClient`;
2. review the product/SPL identity and the exact label section;
3. create `SafetyRecordAttestation` objects containing only exact source spans and explicit structured safety metadata;
4. build the store with `build_attested_safety_store`;
5. serialize the result to `SAFETY_EVIDENCE_PATH` or `SAFETY_EVIDENCE_JSON`.

### Translational contract

Translational records remain non-decisional for management synthesis. Preclinical or mechanistic plausibility is not converted into clinical actionability.

## 4. Streamlit Community Cloud

For Streamlit Community Cloud, put secret values in the app's Secrets configuration. Do not commit `.streamlit/secrets.toml`.

Recommended initial secret names:

```toml
MODEL_AUTH_TOKEN = "..."
MODEL_NAME = "openai/gpt-oss-120b:fireworks-ai"
MODEL_REASONING_EFFORT = "high"

ENABLE_LIVE_PUBMED = "true"
PUBMED_EMAIL = "name@example.org"
NCBI_API_KEY = "" # optional

ENABLE_LIVE_CLINICALTRIALS = "true"

CIVIC_API_KEY = "" # optional for anonymous/low-volume reads
OPENFDA_API_KEY = "..." # recommended
```

Large governed evidence packages and licensed NCCN-derived packages are better mounted or loaded through a secure deployment mechanism rather than copied into a public repository.

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
