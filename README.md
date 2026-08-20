# Cancer Tumor Board Intelligence Platform

Pan-oncology research decision-support platform for evidence-grounded multidisciplinary cancer case review.

The product is designed as a reusable **Tumor Board Intelligence platform**, not as a single-case or AML-only application. A common provenance, safety, evidence, challenge, consensus, and audit architecture supports registered oncology disease programs while disease-specific evidence remains separately governed. The platform is **not clinically validated for autonomous or unsupervised patient-care use**.

## Pan-oncology tumor-board programs

The governed disease-program registry currently includes:

1. Hematologic malignancies
2. Breast oncology
3. Thoracic oncology
4. Gastrointestinal oncology
5. Genitourinary oncology
6. Gynecologic oncology
7. Head and neck oncology
8. Neuro-oncology
9. Melanoma and cutaneous oncology
10. Sarcoma and bone oncology
11. Endocrine and neuroendocrine oncology
12. Ophthalmic oncology
13. Pediatric oncology
14. Rare cancers and carcinoma of unknown primary

The represented diagnosis remains the clinical concept used for evidence matching. Program assignment is an operational routing layer and does not substitute a broader tumor-board label for the patient's diagnosis.

## Product workflow

```text
De-identified narrative / document / synthetic case
  -> provenance-aware extraction
  -> canonical structured cancer case
  -> deterministic disease-program / tumor-board assignment
  -> clinician representation confirmation
  -> governed evidence review
       disease-specific authorized guidance when available
       accepted CIViC molecular candidates
       FDA label-section candidates
       PubMed discovery
       ClinicalTrials.gov discovery
       explicit local human attestation where required
  -> semantic-integrity + Case Integrity / Data QA
  -> Missing Information gate
  -> clinical routing
  -> independent evidence channels
       guidelines / authoritative evidence summaries
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

The system does not use agent voting as a proxy for truth. Required evidence-channel failures can prevent consensus. Trial matching is not eligibility. Biological plausibility is not clinical actionability. Failed verification does not propagate downstream. A disease program may use the common platform even when a disease-specific evidence package is unavailable, but the affected evidence channel then fails closed rather than generating a claim from model memory.

## Private clinician product

The production interface lives in [`web/`](web/) and uses Next.js, React, and TypeScript. It provides an authenticated home screen with two explicit entry paths:

1. a guided synthetic AML case that teaches the complete workflow
2. a real clinical case path that accepts only information de-identified before upload

The Next.js server acts as a backend-for-frontend. It keeps the OIDC session in secure, HTTP-only cookies and forwards authenticated API requests to FastAPI. FastAPI independently verifies the access token and scopes every saved case query to the verified organization. PostgreSQL is used in production; SQLite remains the local development fallback.

The original uploaded document is processed transiently and is not retained. A required user attestation and deterministic identifier screen add safeguards, but do not certify HIPAA de-identification.

See [`docs/PRODUCTION_RELEASE_GUIDE.md`](docs/PRODUCTION_RELEASE_GUIDE.md) for the beginner-oriented staging and release process and [`docs/DEIDENTIFIED_DATA_BOUNDARY.md`](docs/DEIDENTIFIED_DATA_BOUNDARY.md) for the allowed-data boundary.

For the first no-patient-data faculty evaluation, use [`docs/SYNTHETIC_EVALUATION_DEPLOYMENT.md`](docs/SYNTHETIC_EVALUATION_DEPLOYMENT.md). The default [`render.yaml`](render.yaml) creates only a free synthetic-evaluation API. The paid production Blueprint is preserved separately in [`render.production.yaml`](render.production.yaml).

## Legacy Streamlit clinician workspace

`app/main.py` opens the clinician-facing workspace. The normal interface uses five stages:

1. **Case intake**: paste a de-identified narrative, upload a de-identified document, or load a controlled synthetic case.
2. **Review**: verify the structured case. Clinician confirmation marks only facts that already carry verified source provenance as human-reviewed.
3. **Evidence**: retrieve bounded decision-critical evidence and explicitly approve only source records appropriate for local admission.
4. **Analysis**: run deterministic QA, routing, specialist evidence channels, Clinical Red Team, and consensus.
5. **Decision brief**: review decision state, evidence availability, challenge findings, Case QA, structured brief, and audit trace.

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

## Evidence architecture

### Disease-specific guidance

Guidance is disease-specific and fail-closed. The public research product currently includes a deliberately narrow machine-processable ELN 2022 AML consensus pathway as one commissioned example. Other programs can receive verified, authorized evidence packages without changing the common workflow.

NCCN material is **not** processed by this product when the supplied licensed document prohibits use with artificial-intelligence models or tools. Institutional access alone is not treated as permission for AI processing. See [`docs/NCCN_AI_USE_RESTRICTION.md`](docs/NCCN_AI_USE_RESTRICTION.md).

NCI PDQ is treated as an **authoritative evidence summary**, not automatically as a formal guideline. The existing AML adapter uses exact-source statements and explicit human verification before Evidence Gateway admission. Disease-specific adapters or reviewed evidence packages must preserve the same source-verification boundary.

### Molecular evidence

CIViC is the primary public molecular candidate source. Retrieval is diagnosis- and finding-aware. Retrieval sets source provenance but does not set local human verification. A clinician must explicitly approve individual records before they can enter the session's clinical-actionability evidence store.

```text
CIVIC_API_KEY=<optional but recommended for deployed sustained access>
```

### Safety evidence

FDA Structured Product Labeling through openFDA is the primary public safety-label source. Label discovery can use explicit therapies already represented in the case, therapies from verified guidance candidates, and therapy concepts surfaced by molecular evidence discovery. Discovery does not establish treatment appropriateness or patient-specific applicability. Clinician approval attests the exact displayed source span and product context only.

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

Guideline, molecular, safety, and optional translational evidence can be supplied at deployment without changing source code. See [`docs/PRODUCTION_CONFIGURATION.md`](docs/PRODUCTION_CONFIGURATION.md).

Evidence approvals and case decisions can be stored as immutable organization-scoped versions in PostgreSQL. Reviewed deployment packages remain the correct mechanism for durable institutional evidence governance.

## Safety invariants

Use synthetic or fully de-identified research cases unless an institution has separately completed the governance, privacy, validation, security, regulatory, and deployment work required for its intended clinical setting.

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
- safety non-match != absence of risk
- consensus abstain -> management withheld

Reasoning chain-of-thought is not stored or displayed. Audit outputs contain structured facts, provenance, source references, statuses, evidence boundaries, human-attestation state, and decision gates.

## Qualification and validation

The repository preserves its historical development failures and qualification milestones rather than rewriting them.

The frozen **Extraction Remediation Validation v2.5** completed 30/30 strict case-execution passes in its controlled synthetic remediation benchmark, with 144/144 exact provenance anchors and zero observed safety-gate violations.

The frozen **Whole-System Qualification v1.0.0** completed 36/36 strict controlled synthetic post-extraction integration case executions with zero observed safety-stop violations, and all repeated adversarial cases passed 3/3.

Those historical benchmarks predate the pan-oncology expansion and are not automatically transferred to every new disease pathway.

Pan-oncology expansion uses a separate pathway validation protocol in [`docs/PAN_ONCOLOGY_VALIDATION_PROTOCOL.md`](docs/PAN_ONCOLOGY_VALIDATION_PROTOCOL.md). It distinguishes four states:

- `architecture_ready`
- `software_qualified`
- `clinically_validated_silent`
- `clinical_release`

Architecture support and software qualification are not clinical validation. Formal clinical validation requires an independent disease-appropriate expert reference standard, retrospective and/or prospective-silent cases, prespecified endpoints, safety-critical error reporting, and pathway-specific governance before a clinical-release label can be used.

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

The Phase 1 FastAPI service can be run in a second terminal:

```bash
uvicorn api.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000/docs` to inspect and test the API contract. The API remains
limited to synthetic or fully de-identified research cases. See
[`docs/PHASE_1_FASTAPI_BOUNDARY.md`](docs/PHASE_1_FASTAPI_BOUNDARY.md) for the original
service boundary and [`docs/PHASE_4_DOCUMENT_EXTRACTION_API.md`](docs/PHASE_4_DOCUMENT_EXTRACTION_API.md)
for transient document extraction and provenance review. Phase 5's stateless evidence-admission
contract is documented in [`docs/PHASE_5_EVIDENCE_COMMISSIONING_API.md`](docs/PHASE_5_EVIDENCE_COMMISSIONING_API.md).
The Phase 6 clinician analysis fields and synthesis permissions are documented in
[`docs/PHASE_6_GOVERNED_ANALYSIS_CONTRACT.md`](docs/PHASE_6_GOVERNED_ANALYSIS_CONTRACT.md).
The Phase 7 stateless clinician-judgment and board-decision receipt is documented in
[`docs/PHASE_7_HUMAN_DECISION_CONTRACT.md`](docs/PHASE_7_HUMAN_DECISION_CONTRACT.md).
The Phase 8 append-only case-version store, update impact assessment, and targeted-rerun
rules are documented in [`docs/PHASE_8_CASE_VERSIONING_CONTRACT.md`](docs/PHASE_8_CASE_VERSIONING_CONTRACT.md).
The Phase 9 deterministic evaluation, HTTP security, and release-readiness contract is documented in
[`docs/PHASE_9_RELEASE_READINESS_CONTRACT.md`](docs/PHASE_9_RELEASE_READINESS_CONTRACT.md).

## Test

```bash
python -m pytest -q
```

GitHub Actions compiles the Python modules, runs the pan-oncology architecture gate, and runs the full regression suite on `main` and pull requests targeting `main`.

## Repository map

```text
agents/          bounded specialist and control agents
schemas/         Pydantic contracts
services/        source clients, evidence commissioning, gateways, configuration
orchestration/   routing and workflow integration
app/             Streamlit product and research UI
synthetic_cases/ controlled development fixtures
tests/           regression and pan-oncology architecture tests
qualification/   frozen qualification assets and protocols
docs/            architecture, validation, governance, and deployment documentation
```
