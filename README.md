# Cancer Tumor Board Intelligence Platform

Research decision-support platform for evidence-grounded, agentic multidisciplinary cancer case review.

The current product focuses on hematologic malignancies and is designed around provenance, explicit missingness, governed evidence, independent challenge review, consensus gates, abstention, and a structured tumor-board brief. It is **not clinically validated for autonomous or unsupervised patient-care use**.

## Product workflow

```text
De-identified narrative / document / synthetic case
  -> provenance-aware extraction
  -> canonical structured case
  -> clinician representation confirmation
  -> governed evidence review
       bounded ELN AML consensus guidance
       accepted CIViC molecular candidates
       FDA label-section candidates
       explicit local human attestation
  -> semantic-integrity + Case Integrity / Data QA
  -> Missing Information gate
  -> clinical routing
  -> independent evidence channels
       guidelines
       current literature
       molecular evidence
       translational evidence
       ClinicalTrials.gov
       safety evidence
  -> Clinical Red Team
  -> evidence-weighted Consensus Engine
  -> recommendation / conditional state / abstention
  -> structured Tumor Board Intelligence Brief
  -> audit trace
```

The system does not use agent voting as a proxy for truth. Required evidence-channel failures can prevent consensus. Trial matching is not eligibility. Biological plausibility is not clinical actionability. Failed verification does not propagate downstream.

## Executive clinician workspace

`app/main.py` opens the clinician-facing workspace. The normal interface uses five stages:

1. **Case intake** - paste a de-identified narrative, upload a de-identified document, or load the synthetic AML fixture.
2. **Review** - verify the structured case. Clinician confirmation marks only facts that already carry verified source provenance as human-reviewed.
3. **Evidence** - retrieve bounded decision-critical evidence and explicitly approve only the source records appropriate for local admission.
4. **Analysis** - run deterministic QA, routing, specialist evidence channels, Clinical Red Team, and consensus.
5. **Decision brief** - review the decision state, evidence availability, challenge findings, Case QA, structured brief, and audit trace.

Implementation details and technical agent terminology are intentionally de-emphasized in the normal workflow.

## Open-weight model architecture

The extraction layer is provider-neutral and uses an OpenAI-compatible gateway. The current default open-weight reasoning model target is:

```text
openai/gpt-oss-120b:fireworks-ai
```

No OpenAI API key is required for this configuration. Model weights and the inference host remain separate so the workflow can later point to another compatible provider or institutional infrastructure.

Set model credentials only in the deployment secret store:

```text
MODEL_AUTH_TOKEN=<provider token>
MODEL_NAME=openai/gpt-oss-120b:fireworks-ai
MODEL_REASONING_EFFORT=high
MODEL_BASE_URL=<optional compatible endpoint>
```

Never commit credentials to this repository.

## Evidence sources

### AML consensus guidance

The public/research product contains one deliberately narrow machine-processable ELN 2022 AML consensus pathway for relapsed/refractory AML with a verified FLT3 molecular prerequisite. The record is source-located and bounded; it is not a scraped copy of the source article. Targeted guidance cannot match unless required molecular facts are represented with verified case provenance and clinician confirmation.

NCCN material is **not** processed by this product when the supplied licensed document prohibits use with artificial-intelligence models or tools. Institutional access alone is not treated as permission for AI processing. See [`docs/NCCN_AI_USE_RESTRICTION.md`](docs/NCCN_AI_USE_RESTRICTION.md).

### Molecular evidence

CIViC is the primary public molecular candidate source. The adapter retrieves only accepted CIViC Evidence Items. Retrieval sets source provenance but does not set local human verification. A clinician must explicitly approve individual records in the Evidence Review screen before they can enter the session's clinical-actionability evidence store.

```text
CIVIC_API_KEY=<optional but recommended for deployed sustained access>
```

### Safety evidence

FDA Structured Product Labeling through openFDA is the primary public safety-label source. The product retrieves bounded label sections for structured guideline-candidate therapy terms. Clinician approval attests the exact displayed source span and product context only. It does not infer that a warning, contraindication, interaction, or dose rule applies to the patient.

```text
OPENFDA_API_KEY=<recommended>
```

### Literature and trials

```text
ENABLE_LIVE_PUBMED=true
PUBMED_EMAIL=<NCBI contact email>
NCBI_API_KEY=<optional>
ENABLE_LIVE_CLINICALTRIALS=true
```

ClinicalTrials.gov matching applies deterministic disease context, recruitment status, and explicit registry age-bound screening. It does not determine eligibility. PubMed retrieval remains evidence discovery, not evidence verification.

## Governed deployment evidence

Guideline, molecular, safety, and optional translational evidence can also be supplied at deployment without changing source code. See [`docs/PRODUCTION_CONFIGURATION.md`](docs/PRODUCTION_CONFIGURATION.md).

Session evidence approvals are intentionally ephemeral in the current research release. Durable institutional evidence governance should use reviewed deployment packages and an approved persistence layer rather than browser-session state.

NCI PDQ is handled as an **authoritative evidence summary**, not a formal guideline. Its AML adapter uses exact-source statements and requires explicit human verification before admission through the evidence gateway.

## Safety scope

Use synthetic or fully de-identified research cases only.

Key invariants include:

- no source -> no patient fact
- no verified evidence -> no evidence claim
- pending != negative
- biological plausibility != clinical actionability
- trial match != trial eligibility
- agent agreement != truth
- low information -> abstain or request more information
- critical conflict -> human review
- failed verification -> do not propagate the claim
- consensus abstain -> management withheld

Reasoning chain-of-thought is not stored or displayed. Audit outputs contain structured facts, provenance, source references, statuses, evidence boundaries, human-attestation state, and decision gates.

## Validation history and boundary

The repository preserves its historical development failures and qualification milestones rather than rewriting them.

The frozen **Extraction Remediation Validation v2.5** completed 30/30 strict case-execution passes in its controlled synthetic remediation benchmark, with 144/144 exact provenance anchors and zero observed safety-gate violations.

The frozen **Whole-System Qualification v1.0.0** completed 36/36 strict controlled synthetic post-extraction integration case executions with zero observed safety-stop violations, and all repeated adversarial cases passed 3/3.

These are controlled synthetic development benchmarks. They are **not clinical validation**. Product, retrieval, evidence-configuration, evidence-commissioning, and frontend changes made after the frozen qualification commits are post-qualification integration work unless the frozen protocol is explicitly rerun. Passing ordinary regression CI does not constitute requalification.

## Run locally

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app/main.py
```

## Test

```bash
pytest -q
```

GitHub Actions compiles the Python modules and runs the regression suite for pull requests targeting `main`.

## Repository map

```text
agents/          bounded specialist and control agents
schemas/         Pydantic contracts
services/        source clients, evidence commissioning, gateways, configuration
orchestration/   routing and workflow integration
app/             Streamlit product and research UI
synthetic_cases/ controlled development fixtures
tests/           regression tests
qualification/   frozen qualification assets and protocols
docs/            architecture and deployment documentation
```
