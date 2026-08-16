# Cancer Tumor Board Intelligence Platform

Research decision-support platform for evidence-grounded, agentic multidisciplinary cancer case review.

The current product focuses on hematologic malignancies and is designed around provenance, explicit missingness, independent evidence channels, challenge review, consensus gates, abstention, and a structured tumor-board brief. It is **not clinically validated for autonomous or unsupervised patient-care use**.

## Product workflow

```text
De-identified narrative / document / synthetic case
  -> provenance-aware extraction
  -> canonical structured case
  -> clinician review
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

`app/main.py` opens the clinician-facing workspace. The normal interface emphasizes:

- case intake and source provenance
- structured case review before analysis
- decision state and evidence availability
- human-readable challenge findings
- Case QA and information completeness
- structured evidence and audit views

Implementation details and technical agent terminology are intentionally de-emphasized in the normal clinical workflow.

## Open-weight model architecture

The extraction layer is provider-neutral and uses an OpenAI-compatible gateway. The current default open-weight reasoning model target is:

```text
openai/gpt-oss-120b:fireworks-ai
```

No OpenAI API key is required for this configuration. Model weights and the inference host remain separate so the same workflow can later point to another compatible provider or institutional infrastructure.

Set model credentials only in the deployment secret store:

```text
MODEL_AUTH_TOKEN=<provider token>
MODEL_NAME=openai/gpt-oss-120b:fireworks-ai
MODEL_BASE_URL=<optional compatible endpoint>
```

Never commit credentials to this repository.

## Public evidence retrieval

The product supports opt-in live retrieval from official public sources:

```text
ENABLE_LIVE_PUBMED=true
PUBMED_EMAIL=<NCBI contact email>
NCBI_API_KEY=<optional>
ENABLE_LIVE_CLINICALTRIALS=true
```

ClinicalTrials.gov matching applies deterministic disease context, recruitment status, and explicit registry age-bound screening. It does not determine eligibility.

PubMed retrieval remains evidence discovery, not evidence verification. Obvious title-level pediatric/adult population mismatches can be removed from surfaced records, but study applicability still requires evidence appraisal.

## Governed clinical evidence

Guideline, molecular, safety, and optional translational evidence can be supplied at deployment without changing source code. See [`docs/PRODUCTION_CONFIGURATION.md`](docs/PRODUCTION_CONFIGURATION.md).

The production stores fail closed when evidence is missing or invalid. The repository does not bundle licensed guideline content.

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

Reasoning chain-of-thought is not stored or displayed. Audit outputs contain structured facts, provenance, source references, statuses, evidence boundaries, and decision gates.

## Validation history and boundary

The repository preserves its historical development failures and qualification milestones rather than rewriting them.

The frozen **Extraction Remediation Validation v2.5** completed 30/30 strict case-execution passes in its controlled synthetic remediation benchmark, with 144/144 exact provenance anchors and zero observed safety-gate violations.

The frozen **Whole-System Qualification v1.0.0** completed 36/36 strict controlled synthetic post-extraction integration case executions with zero observed safety-stop violations, and all repeated adversarial cases passed 3/3.

These are controlled synthetic development benchmarks. They are **not clinical validation**. Product, retrieval, evidence-configuration, and frontend changes made after the frozen qualification commits are post-qualification integration work unless the frozen protocol is explicitly rerun. Passing ordinary regression CI does not constitute requalification.

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

GitHub Actions also compiles the Python modules and runs the regression suite for pull requests targeting `main`.

## Repository map

```text
agents/          bounded specialist and control agents
schemas/         Pydantic contracts
services/        source clients, evidence gateways, configuration, normalization
orchestration/   routing and workflow integration
app/             Streamlit product and research UI
synthetic_cases/ controlled development fixtures
tests/           regression tests
qualification/   frozen qualification assets and protocols
docs/            architecture and deployment documentation
```
