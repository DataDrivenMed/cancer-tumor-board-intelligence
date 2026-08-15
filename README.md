# Cancer Tumor Board Intelligence Platform

Research-prototype scaffold for an agentic, evidence-grounded tumor-board intelligence system.

## Current milestone

This repository intentionally contains **no clinical recommendation model** and **no real patient data**.

The current build proves the core plumbing:

1. Synthetic or manually pasted case input
2. Canonical case representation
3. Data-quality checks
4. Mock routing
5. Mock specialist-agent outputs
6. Preliminary consensus
7. Red-team challenge
8. Final tumor-board brief
9. Audit trail

The next development phase replaces mock services one at a time with validated LLM/tool implementations.

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
Input
  -> canonical case
  -> integrity + missing-data gate
  -> router
  -> independent specialist agents
  -> evidence-verification placeholder
  -> preliminary synthesis
  -> red-team review
  -> rule-based final state
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
