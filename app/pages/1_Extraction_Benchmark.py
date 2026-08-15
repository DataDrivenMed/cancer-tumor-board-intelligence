from __future__ import annotations

import json
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
from services.benchmark_persistence import (
    build_run_payload,
    load_latest_run,
    payload_to_csv,
    persist_run,
    score_from_dict,
)
from services.document_parser import parse_text
from services.model_gateway import ModelGatewayError


st.set_page_config(page_title="Extraction Benchmark", page_icon="🧪", layout="wide")


def get_secret(name: str, default: str | None = None) -> str | None:
    try:
        return st.secrets[name]
    except Exception:
        return default


def _load_saved_run_into_session() -> None:
    """Restore the most recent saved benchmark run after a browser/session reset."""
    payload = load_latest_run(PROJECT_ROOT / "runtime_data" / "qualification_runs")
    if not payload:
        return

    if not st.session_state.benchmark_scores:
        st.session_state.benchmark_scores = {
            row["case_id"]: score_from_dict(row)
            for row in payload.get("scores", [])
            if isinstance(row, dict) and row.get("case_id")
        }
    if not st.session_state.benchmark_diagnostics:
        st.session_state.benchmark_diagnostics = payload.get("diagnostics", {}) or {}
    st.session_state.latest_saved_run = payload


def _results_rows(scores):
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
    return rows


def _current_payload(*, completed: bool = False, failure=None):
    scores = list(st.session_state.benchmark_scores.values())
    if not scores:
        return None
    return build_run_payload(
        scores=scores,
        diagnostics=st.session_state.benchmark_diagnostics,
        model_name=model_name,
        reasoning_effort=reasoning_effort,
        completed=completed,
        failure=failure,
    )


def _persist_current_session(*, completed: bool = False, failure=None) -> None:
    """Best-effort persistence after individual or batch runs.

    Streamlit Community Cloud filesystem can still be lost after an app restart or
    redeploy, so the page always exposes a browser download as the durable copy.
    """
    payload = _current_payload(completed=completed, failure=failure)
    if payload is None:
        return
    st.session_state.latest_saved_run = payload
    try:
        persist_run(payload, PROJECT_ROOT / "runtime_data" / "qualification_runs")
    except Exception:
        # Browser download remains available below even if runtime persistence fails.
        pass


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

**Important limitation:** the unsupported-provenance metric checks whether structured claims have exact source anchors. It is not a complete semantic hallucination detector. Human adjudication remains required before claiming clinical validation.
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
if "benchmark_diagnostics" not in st.session_state:
    st.session_state.benchmark_diagnostics = {}
if "latest_saved_run" not in st.session_state:
    st.session_state.latest_saved_run = None

_load_saved_run_into_session()

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
        st.session_state.benchmark_diagnostics[gold.case_id] = {
            "provenance_total": package.provenance_total,
            "provenance_verified": package.provenance_verified,
            "provenance_failures": package.provenance_failures,
            "warnings": package.warnings,
            "raw_extraction": package.raw_extraction,
        }
        _persist_current_session(completed=False)
        st.success(f"{gold.case_id} completed. Core gate: {'PASS' if score.passed_core_gate else 'REVIEW / FAIL'}")
        if score.notes:
            for note in score.notes:
                st.warning(note)
    except ModelGatewayError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"Qualification case failed safely: {exc}")

if gold.case_id in st.session_state.benchmark_diagnostics:
    diag = st.session_state.benchmark_diagnostics[gold.case_id]
    st.markdown("### Extraction diagnostics")
    d1, d2 = st.columns(2)
    d1.metric("Provenance anchors", diag["provenance_total"])
    d2.metric("Exactly verified", diag["provenance_verified"])
    if diag["provenance_failures"]:
        st.error("Provenance verification failure(s): " + ", ".join(diag["provenance_failures"]))
    else:
        st.success("No provenance verification failures were recorded.")
    if diag["warnings"]:
        for warning in diag["warnings"]:
            st.warning(warning)
    with st.expander("Inspect structured extraction JSON"):
        st.json(diag["raw_extraction"])

st.divider()
st.subheader("Full-suite run")
st.caption(
    "This makes ten sequential model calls and can consume inference credits. "
    "Completed and partial runs are saved before the page finishes so results survive normal browser refreshes and Streamlit reruns."
)
allow_batch = st.checkbox("I understand this will run all 10 synthetic cases and use inference credits.")

if st.button("Run all 10 qualification cases", disabled=not allow_batch):
    # A full-suite run starts clean. Do not mix prior single-case results into its summary.
    st.session_state.benchmark_scores = {}
    st.session_state.benchmark_diagnostics = {}
    progress = st.progress(0)
    status = st.empty()
    batch_failure = None

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
            st.session_state.benchmark_diagnostics[case.case_id] = {
                "provenance_total": package.provenance_total,
                "provenance_verified": package.provenance_verified,
                "provenance_failures": package.provenance_failures,
                "warnings": package.warnings,
                "raw_extraction": package.raw_extraction,
            }
        except Exception as exc:
            batch_failure = {
                "case_id": case.case_id,
                "title": case.title,
                "error_type": type(exc).__name__,
                "message": str(exc),
            }
            st.error(f"{case.case_id} failed safely: {exc}")
            break
        progress.progress(idx / len(CASES))

    current_scores = list(st.session_state.benchmark_scores.values())
    payload = build_run_payload(
        scores=current_scores,
        diagnostics=st.session_state.benchmark_diagnostics,
        model_name=model_name,
        reasoning_effort=reasoning_effort,
        completed=batch_failure is None and len(current_scores) == len(CASES),
        failure=batch_failure,
    )
    try:
        persist_run(payload, PROJECT_ROOT / "runtime_data" / "qualification_runs")
        st.session_state.latest_saved_run = payload
    except Exception as exc:
        st.warning(
            "The benchmark finished, but the runtime persistence file could not be written. "
            f"Use the download buttons below before leaving this page. Persistence error: {exc}"
        )
        st.session_state.latest_saved_run = payload

    if batch_failure is None and len(current_scores) == len(CASES):
        st.success("All 10 qualification cases completed and the run was saved.")
    else:
        st.warning(
            f"Partial suite saved: {len(current_scores)}/{len(CASES)} cases completed. "
            "The failed model/tool call is not counted as a qualification failure for cases that never produced a score."
        )

st.divider()
st.subheader("Qualification results")
scores = list(st.session_state.benchmark_scores.values())

if not scores:
    st.info("No qualification cases are available in this session or in the latest saved runtime run.")
else:
    rows = _results_rows(scores)
    results_df = pd.DataFrame(rows)
    st.dataframe(results_df, use_container_width=True, hide_index=True)

    summary = summarize(scores)
    a, b, c, d, e = st.columns(5)
    a.metric("Cases run", summary["cases_run"])
    b.metric("Cases passing core gate", summary["cases_passing_core_gate"])
    c.metric("Mean provenance", f"{summary['provenance_verification'] * 100:.1f}%")
    d.metric("Prohibited assertions", summary["prohibited_assertions"])
    e.metric(
        "Mean unsupported provenance",
        f"{summary['mean_unsupported_provenance_assertion_rate'] * 100:.1f}%",
    )

    # Always build an export from the current in-memory results, including individual runs.
    current_export = build_run_payload(
        scores=scores,
        diagnostics=st.session_state.benchmark_diagnostics,
        model_name=model_name,
        reasoning_effort=reasoning_effort,
        completed=len(scores) == len(CASES),
        failure=None,
    )
    st.session_state.latest_saved_run = current_export

    completed_label = "COMPLETE" if current_export.get("completed") else "PARTIAL"
    st.caption(
        f"Current export: {current_export.get('run_timestamp_utc', 'unknown time')} UTC • "
        f"{completed_label} • {current_export.get('model_name', 'unknown model')} • "
        f"reasoning={current_export.get('reasoning_effort', 'unknown')}"
    )

    json_bytes = json.dumps(current_export, indent=2, ensure_ascii=False, default=str).encode("utf-8")
    csv_bytes = payload_to_csv(current_export).encode("utf-8")
    b1, b2 = st.columns(2)
    b1.download_button(
        "Download current results (JSON)",
        data=json_bytes,
        file_name="qualification_benchmark_current.json",
        mime="application/json",
        use_container_width=True,
    )
    b2.download_button(
        "Download current results (CSV)",
        data=csv_bytes,
        file_name="qualification_benchmark_current.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.info(
        "Individual-case results are now saved best-effort after each run and are always exportable from this page. "
        "Streamlit Community Cloud storage is ephemeral across some app restarts/redeployments, so download the JSON before rebooting or redeploying the app."
    )

    st.markdown("### Qualification policy")
    st.write(
        "The extraction layer should not advance to clinical reasoning based on one successful case. "
        "For this development suite, the provisional target is 10/10 cases passing the core gate, 100% exact provenance verification, "
        "zero prohibited assertions, and zero unsupported-provenance assertions. Any miss is reviewed before proceeding."
    )
