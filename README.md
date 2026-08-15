# Cancer Tumor Board Intelligence Platform

Research-prototype scaffold for an agentic, evidence-grounded tumor-board intelligence system.

## Current milestone

The current build includes provenance-aware case extraction, canonical case representation, data-quality checks, mock specialist routing, abstention logic, a tumor-board brief shell, and an audit trail.

It intentionally contains **no validated clinical recommendation engine** and **no real patient data**.

## Open-weight model architecture

The development build is no longer tied to the OpenAI API.

Primary open-weight reasoning model target:

```text
openai/gpt-oss-120b
reasoning effort: high
```

The application uses an OpenAI-compatible model gateway, so the same clinical workflow can point to:

- Hugging Face Inference Providers
- Groq or another compatible inference host
- a self-hosted vLLM-compatible endpoint
- later institutional GPU infrastructure

The model weights and the inference host are deliberately separated.

### Hosted Streamlit development configuration

For the current public Streamlit prototype, the default route is Hugging Face Inference Providers with the Fireworks backend because that route supports gpt-oss-120b and JSON-schema structured output.

Add these values only in Streamlit Secrets, never in GitHub:

```toml
MODEL_AUTH_TOKEN = "YOUR_HUGGING_FACE_TOKEN"
MODEL_NAME = "openai/gpt-oss-120b:fireworks-ai"
MODEL_REASONING_EFFORT = "high"
```

Optional self-hosted endpoint:

```toml
MODEL_BASE_URL = "https://your-compatible-model-endpoint/v1"
MODEL_AUTH_TOKEN = "OPTIONAL_ENDPOINT_TOKEN"
MODEL_NAME = "openai/gpt-oss-120b"
MODEL_REASONING_EFFORT = "high"
```

No `OPENAI_API_KEY` is required.

## Safety scope

Use synthetic or fully de-identified research cases only. This repository is not intended for direct clinical care.

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

## Architecture

```text
Narrative / document
  -> provenance-aware extraction
  -> canonical case
  -> integrity + missing-data gate
  -> human verification
  -> router
  -> independent specialist agents
  -> evidence verification
  -> preliminary synthesis
  -> red-team review
  -> deterministic abstention / confidence gate
  -> tumor-board brief
  -> audit trail
```

## Important design principles

- Observed, derived, and interpreted information remain distinct.
- Patient facts retain provenance.
- Missingness is explicit.
- Contradictions are first-class objects.
- Specialist outputs are structured rather than free-form essays.
- Agent disagreement is preserved.
- The system can abstain.
- Final output includes an audit trail.
- Model selection will be evaluated on oncology-specific benchmarks rather than accepted from vendor benchmark claims alone.
