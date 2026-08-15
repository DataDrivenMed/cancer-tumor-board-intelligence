from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.extraction import extract_case
from qualification.cases import CASES
from qualification.scoring import score_case, summarize
from services.document_parser import parse_text
from services.model_gateway import ModelGatewayError


st.set_page_config(page_title="Extraction Benchmark", page_icon="🧪", layout="wide")


def get_secret(name: str, default: str | None = None) -> str | None:
    try:
        return st.secrets[name]
    except Exception:
        return default


st.title("Extraction Qualification Benchmark")
st.caption("Synthetic hematologic malignancy stress-test suite • No PHI • No treatment recommendations")
st.warning("Research qualification environment only. Results from this suite do not constitute clinical validation.")

with st.expander("What this benchmark measures", expanded=True):
    st.markdown(
        """
This suite deliberately tests extraction failure modes before downstream oncology reasoning is enabled. It scores:

- key-field accuracy for diagnosis, disease state and ECOG/performance status
- exact provenance verification
- missing-information recall
- conflict detection
- molecular extraction coverage
- treatment-history coverage and chronology
- prohibited inferred assertions
- unsupported-provenance assertion rate

**Important limitation:** the unsupported-provenance metric checks whether confirmed claims have exact source anchors. It is not a complete semantic hallucination detector. Human adjudication remains required before claiming clinical validation.
        """
    )

model_token = get_secret("MODEL_AUTH_TOKEN") or get_secret("HF_TOKEN")
model_name = get_secret("MODEL_NAME", "openai/gpt-oss-120b:fireworks-ai") or "openai/gpt-oss-120b:fireworks-ai"
model_base_url = get_secret("MODEL_BASE_URL")
reasoning_effort = get_secret("MODEL_REASONING_EFFORT", "high") or "high"
if model_base_url:
    os.environ["MODEL_BASE_URL"] = model_base_url

c1, c2, c3 = st.columns(3)
c1.metric("Qualification cases", len(CASES))
c2.metric("Configured model", model_name.split(":")[0])
c3.metric("Reasoning effort", reasoning_effort.upper())

if not model_token and not model_base_url:
    st.error("No inference endpoint is configured. Add MODEL_AUTH_TOKEN/HF_TOKEN or MODEL_BASE_URL in Streamlit Secrets.")
    st.stop()

if "benchmark_scores" not in st.session_state:
    st.session_state.benchmark_scores = {}

case_labels = {f"{c.case_id} • {c.title}": c for c in CASES}
selected_label = st.selectbox("Select a stress-test case", list(case_labels))
gold = case_labels[selected_label]

st.markdown(f"**Target failure mode:** {gold.target_failure_mode}")
with st.expander("View synthetic source narrative"):
    st.code(gold.narrative, language="text")
with st.expander("View pre-specified gold expectations"):
    st.json({
        "expected_diagnosis": gold.expected_diagnosis,
        "expected_disease_state": gold.expected_disease_state,
        "expected_ecog": gold.expected_ecog,
        "expected_molecular_genes": gold.expected_molecular_genes,
        "expected_treatments": gold.expected_treatments,
        "expected_missing_fields": gold.expected_missing_fields,
        "expected_conflict_fields": gold.expected_conflict_fields,
        "prohibited_confirmed_values": gold.prohibited_confirmed_values,
        "notes": gold.notes,
    })

if st.button("Run selected qualification case", type="primary"):
    document = parse_text(gold.narrative, document_id=f"QUAL-{gold.case_id}", filename=f"{gold.case_id}.txt")
    try:
        with st.spinner(f"Running {gold.case_id} with {model_name} and verifying provenance..."):
            package = extract_case(
                document=document,
                api_key=model_token or "local-no-auth",
                model=model_name,
                case_id=f"QUAL-{gold.case_id}",
            )
            score = score_case(gold, package)
        st.session_state.benchmark_scores[gold.case_id] = score
        st.success(f"{gold.case_id} completed. Core gate: {'PASS' if score.passed_core_gate else 'REVIEW / FAIL'}")
        if score.notes:
            for note in score.notes:
                st.warning(note)
    except ModelGatewayError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"Qualification case failed safely: {exc}")

st.divider()
st.subheader("Qualification results")
scores = list(st.session_state.benchmark_scores.values())
if not scores:
    st.info("No qualification cases have been run in this browser session yet.")
else:
    rows = []
    for s in sorted(scores, key=lambda x: x.case_id):
        rows.append({
            "Case": s.case_id,
            "Title": s.title,
            "Field accuracy": round(s.field_accuracy * 100, 1),
            "Provenance": round(s.provenance_verification * 100, 1),
            "Missing recall": round(s.missing_information_recall * 100, 1),
            "Conflict detection": round(s.conflict_detection * 100, 1),
            "Molecular": round(s.molecular_accuracy * 100, 1),
            "Treatment coverage": round(s.treatment_coverage * 100, 1),
            "Treatment order": round(s.treatment_order_accuracy * 100, 1),
            "Prohibited assertions": s.prohibited_assertions,
            "Unsupported provenance %": round(s.unsupported_provenance_assertion_rate * 100, 1),
            "Core gate": "PASS" if s.passed_core_gate else "REVIEW / FAIL",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    summary = summarize(scores)
    a, b, c, d = st.columns(4)
    a.metric("Cases run", summary["cases_run"])
    b.metric("Cases passing core gate", summary["cases_passing_core_gate"])
    c.metric("Mean provenance", f"{summary['provenance_verification'] * 100:.1f}%")
    d.metric("Prohibited assertions", summary["prohibited_assertions"])

    st.markdown("### Qualification policy")
    st.write(
        "The extraction layer should not advance to clinical reasoning based on one successful case. "
        "For this development suite, the provisional target is 10/10 cases passing the core gate, 100% exact provenance verification, "
        "zero prohibited assertions, and zero unsupported-provenance confirmed assertions. Any miss is reviewed before proceeding."
    )

st.divider()
st.subheader("Optional full-suite run")
st.caption("This makes ten sequential model calls and can consume inference credits. Individual-case review is preferred during development.")
allow_batch = st.checkbox("I understand this will run all 10 synthetic cases and use inference credits.")
if st.button("Run all 10 qualification cases", disabled=not allow_batch):
    progress = st.progress(0)
    status = st.empty()
    for idx, case in enumerate(CASES, start=1):
        status.write(f"Running {case.case_id}: {case.title}")
        document = parse_text(case.narrative, document_id=f"QUAL-{case.case_id}", filename=f"{case.case_id}.txt")
        try:
            package = extract_case(
                document=document,
                api_key=model_token or "local-no-auth",
                model=model_name,
                case_id=f"QUAL-{case.case_id}",
            )
            st.session_state.benchmark_scores[case.case_id] = score_case(case, package)
        except Exception as exc:
            st.error(f"{case.case_id} failed safely: {exc}")
            break
        progress.progress(idx / len(CASES))
    else:
        st.success("All 10 qualification cases completed. Review the results table above, then rerun the page if needed to refresh summary values.")
