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
from qualification.challenge_cases_v2 import (
    REPEATED_STOCHASTIC_CASE_IDS,
    REPEATED_STOCHASTIC_REPEATS,
    TARGETED_CASES,
    UNSEEN_CASES,
    get_challenge_case,
)
from qualification.challenge_protocol_v2 import assert_challenge_suite_shape, challenge_protocol_metadata
from qualification.scoring import score_case
from services.benchmark_persistence import build_run_payload
from services.challenge_validation import (
    add_stream_run,
    aggregate_challenge_study,
    load_latest_challenge_study,
    new_challenge_study,
    persist_challenge_study,
    study_to_case_csv,
)
from services.document_parser import parse_text


st.set_page_config(page_title="Challenge Validation v2", page_icon="🧪", layout="wide")


def get_secret(name: str, default: str | None = None) -> str | None:
    try:
        return st.secrets[name]
    except Exception:
        return default


def _compatible(study: dict, model_name: str, reasoning_effort: str) -> tuple[bool, str]:
    current = challenge_protocol_metadata()
    actual = study.get("protocol") or {}
    if actual.get("challenge_fingerprint") != current.get("challenge_fingerprint"):
        return False, "Study fingerprint differs from frozen Challenge Validation v2."
    if study.get("model_name") != model_name:
        return False, "Study model differs from the currently configured model."
    if study.get("reasoning_effort") != reasoning_effort:
        return False, "Study reasoning effort differs from the currently configured reasoning effort."
    return True, ""


def _persist_best_effort(study: dict) -> None:
    try:
        persist_challenge_study(study, PROJECT_ROOT / "runtime_data" / "challenge_validation_v2")
    except Exception as exc:
        st.warning(f"Runtime persistence could not be written. Download the study JSON before leaving this page. Error: {exc}")


def _run_stream(cases, stream_name: str, model_token: str | None, model_name: str, reasoning_effort: str) -> None:
    scores = []
    diagnostics = {}
    failure = None
    progress = st.progress(0)
    status = st.empty()

    for idx, gold in enumerate(cases, start=1):
        status.write(f"{stream_name.title()} • {gold.case_id}: {gold.title}")
        document = parse_text(gold.narrative, document_id=f"V2-{gold.case_id}", filename=f"{gold.case_id}.txt")
        try:
            package = extract_case(
                document=document,
                api_key=model_token or "local-no-auth",
                model=model_name,
                case_id=f"V2-{gold.case_id}",
            )
            scores.append(score_case(gold, package))
            diagnostics[gold.case_id] = {
                "provenance_total": package.provenance_total,
                "provenance_verified": package.provenance_verified,
                "provenance_failures": package.provenance_failures,
                "warnings": package.warnings,
                "raw_extraction": package.raw_extraction,
            }
        except Exception as exc:
            failure = {
                "case_id": gold.case_id,
                "title": gold.title,
                "error_type": type(exc).__name__,
                "message": str(exc),
            }
            st.error(f"{gold.case_id} failed before producing a qualification score: {exc}")
            break
        progress.progress(idx / len(cases))

    payload = build_run_payload(
        scores=scores,
        diagnostics=diagnostics,
        model_name=model_name,
        reasoning_effort=reasoning_effort,
        completed=failure is None and len(scores) == len(cases),
        failure=failure,
    )
    payload["protocol"] = challenge_protocol_metadata()

    if failure is not None or len(scores) != len(cases):
        st.error("The stream is incomplete and was NOT added to the formal Challenge Validation v2 study.")
        st.download_button(
            "Download incomplete stream JSON",
            data=json.dumps(payload, indent=2, default=str).encode("utf-8"),
            file_name=f"challenge_v2_{stream_name}_incomplete.json",
            mime="application/json",
        )
        return

    try:
        updated = add_stream_run(st.session_state.challenge_v2_study, payload, stream_name)
        st.session_state.challenge_v2_study = updated
        _persist_best_effort(updated)
        st.success(f"Complete {stream_name} stream added to Challenge Validation v2.")
        st.rerun()
    except Exception as exc:
        st.error(f"Complete stream was not added because protocol validation failed: {exc}")
        st.download_button(
            "Download rejected complete stream JSON",
            data=json.dumps(payload, indent=2, default=str).encode("utf-8"),
            file_name=f"challenge_v2_{stream_name}_rejected.json",
            mime="application/json",
        )


assert_challenge_suite_shape()
protocol = challenge_protocol_metadata()
model_token = get_secret("MODEL_AUTH_TOKEN") or get_secret("HF_TOKEN")
model_name = get_secret("MODEL_NAME", "openai/gpt-oss-120b:fireworks-ai") or "openai/gpt-oss-120b:fireworks-ai"
model_base_url = get_secret("MODEL_BASE_URL")
reasoning_effort = get_secret("MODEL_REASONING_EFFORT", "high") or "high"
if model_base_url:
    os.environ["MODEL_BASE_URL"] = model_base_url

st.title("Challenge Validation v2")
st.caption("Frozen synthetic phase-2 validation • targeted failure modes + unseen generalization + repeated stochastic subset")
st.warning(
    "Research qualification environment only. This synthetic challenge study is not clinical validation and does not authorize autonomous clinical use. "
    "Do not upload PHI or real patient records."
)

with st.expander("Frozen phase-2 protocol", expanded=True):
    st.markdown(
        f"""
**Challenge suite:** {protocol['challenge_suite_version']}  
**Protocol:** {protocol['challenge_protocol_version']}  
**Targeted stream:** {protocol['targeted_case_count']} cases, single pass  
**Unseen stream:** {protocol['unseen_case_count']} cases, single pass  
**Repeated stochastic subset:** {protocol['repeated_stochastic_case_count']} cases × {protocol['repeated_stochastic_repeats']} repeats  
**Total planned executions:** {protocol['targeted_case_count'] + protocol['unseen_case_count'] + protocol['repeated_stochastic_case_count'] * protocol['repeated_stochastic_repeats']}  
**Challenge fingerprint:** `{protocol['challenge_fingerprint'][:16]}...`

The cases and validation rules are frozen before the first phase-2 inference call. Do not modify cases, extraction logic, scoring, normalization, semantic integrity, model, provider, or reasoning effort during this study.
        """
    )
    st.caption(
        "Final classification is assigned only after all 38 planned executions. GREEN = 100% strict overall pass. "
        "AMBER = at least 95% with perfect provenance, zero prohibited/unsupported assertions, and no repeated case failing more than once. "
        "RED = below 95% or recurrent repeated-case failure. Any provenance failure or prohibited/unsupported assertion triggers an immediate SAFETY STOP."
    )

m1, m2, m3 = st.columns(3)
m1.metric("Configured model", model_name.split(":")[0])
m2.metric("Reasoning effort", reasoning_effort.upper())
m3.metric("Planned executions", 38)

if not model_token and not model_base_url:
    st.error("No inference endpoint is configured. Add MODEL_AUTH_TOKEN/HF_TOKEN or MODEL_BASE_URL in Streamlit Secrets.")
    st.stop()

if "challenge_v2_study" not in st.session_state:
    saved = load_latest_challenge_study(PROJECT_ROOT / "runtime_data" / "challenge_validation_v2")
    if saved:
        ok, _ = _compatible(saved, model_name, reasoning_effort)
        st.session_state.challenge_v2_study = saved if ok else new_challenge_study(model_name=model_name, reasoning_effort=reasoning_effort)
    else:
        st.session_state.challenge_v2_study = new_challenge_study(model_name=model_name, reasoning_effort=reasoning_effort)

st.divider()
st.subheader("Restore study after a reboot")
uploaded = st.file_uploader("Optional: restore Challenge Validation v2 study JSON", type=["json"], key="challenge_v2_upload")
if uploaded is not None:
    try:
        candidate = json.loads(uploaded.getvalue().decode("utf-8"))
        ok, reason = _compatible(candidate, model_name, reasoning_effort)
        if not ok:
            st.error(reason)
        elif st.button("Use uploaded challenge study"):
            st.session_state.challenge_v2_study = candidate
            _persist_best_effort(candidate)
            st.success("Challenge study restored.")
            st.rerun()
    except Exception as exc:
        st.error(f"Could not read study archive: {exc}")

study = st.session_state.challenge_v2_study
summary = aggregate_challenge_study(study)

st.divider()
st.subheader("Study status")
a, b, c, d, e = st.columns(5)
a.metric("Targeted", "DONE" if summary["targeted_complete"] else "PENDING")
b.metric("Unseen", "DONE" if summary["unseen_complete"] else "PENDING")
c.metric("Stochastic repeats", f"{summary['stochastic_runs_completed']} / {REPEATED_STOCHASTIC_REPEATS}")
d.metric("Overall strict PASS", f"{summary['overall_passes']} / {summary['total_case_executions']}")
e.metric("Classification", summary["classification"])

if summary["safety_stop"]:
    st.error(
        "SAFETY STOP: at least one completed stream contains a provenance verification failure, prohibited assertion, or unsupported-provenance assertion. "
        "Do not run additional phase-2 inference until the recorded result is adjudicated outside this frozen study."
    )

if summary["total_case_executions"]:
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Observed pass rate", f"{summary['pass_rate'] * 100:.1f}%")
    q2.metric("Exact provenance", f"{summary['exact_provenance_rate'] * 100:.1f}%")
    q3.metric("Prohibited assertions", summary["prohibited_assertions"])
    q4.metric("Unsupported provenance", f"{summary['unsupported_provenance_sum']:.1f}")

    metric_rows = [{"Metric": k.replace("_", " ").title(), "Mean": f"{v * 100:.1f}%"} for k, v in summary["metric_means"].items()]
    st.markdown("### Core metric means")
    st.dataframe(pd.DataFrame(metric_rows), use_container_width=True, hide_index=True)

    failures = []
    for label, run in [("targeted", study.get("targeted_run")), ("unseen", study.get("unseen_run"))]:
        if run:
            for row in run.get("case_results", []):
                if not row.get("overall_pass"):
                    failures.append({"Stream": label, "Run": 1, "Case": row.get("case_id"), "Core": row.get("core_gate_pass"), "Strict": row.get("strict_extraction_pass"), "Semantic": row.get("semantic_pass")})
    for idx, run in enumerate(study.get("stochastic_runs", []) or [], start=1):
        for row in run.get("case_results", []):
            if not row.get("overall_pass"):
                failures.append({"Stream": "stochastic", "Run": idx, "Case": row.get("case_id"), "Core": row.get("core_gate_pass"), "Strict": row.get("strict_extraction_pass"), "Semantic": row.get("semantic_pass")})
    if failures:
        st.error("One or more executions failed strict overall qualification. Failures remain visible and are not averaged away.")
        st.dataframe(pd.DataFrame(failures), use_container_width=True, hide_index=True)

if summary["stochastic_runs_completed"]:
    stability_rows = [
        {"Case": cid, "PASS": f"{row['passes']}/{row['runs']}", "Failures": row['failures'], "Pass rate": f"{row['pass_rate'] * 100:.1f}%"}
        for cid, row in summary["stochastic_case_stability"].items()
    ]
    st.markdown("### Repeated-subset stability")
    st.dataframe(pd.DataFrame(stability_rows), use_container_width=True, hide_index=True)

study_json = json.dumps(study, indent=2, ensure_ascii=False, default=str).encode("utf-8")
study_csv = study_to_case_csv(study).encode("utf-8")
d1, d2 = st.columns(2)
d1.download_button("Download Challenge v2 study (JSON)", data=study_json, file_name="challenge_validation_v2_study.json", mime="application/json", use_container_width=True)
d2.download_button("Download Challenge v2 case results (CSV)", data=study_csv, file_name="challenge_validation_v2_cases.csv", mime="text/csv", use_container_width=True)

st.divider()
st.subheader("Phase A • Targeted failure-mode challenge")
st.write("Ten frozen cases specifically stress the residual risks observed in v1: treatment-history omission, historical/current-state separation, medication temporality, planned-vs-administered therapy, repeated regimen components, staging conflict, and pending molecular results.")
if study.get("targeted_run") is None:
    ack_a = st.checkbox("I understand Phase A makes 10 model calls and the frozen cases must not be edited after results are observed.", key="challenge_a_ack")
    if st.button("Run Phase A targeted challenge", type="primary", disabled=not ack_a):
        _run_stream(TARGETED_CASES, "targeted", model_token, model_name, reasoning_effort)
else:
    st.success("Phase A complete. Do not rerun or replace it inside this study.")

st.divider()
st.subheader("Phase B • Unseen synthetic generalization")
st.write("Ten frozen cases broaden disease coverage beyond the development suite. This stream is single-pass to reduce tuning against observed outputs.")
if summary["safety_stop"]:
    st.error("Phase B is locked by the protocol safety stop.")
elif study.get("targeted_run") is None:
    st.info("Complete Phase A before opening Phase B.")
elif study.get("unseen_run") is None:
    ack_b = st.checkbox("I understand Phase B makes 10 model calls and is single-pass by design.", key="challenge_b_ack")
    if st.button("Run Phase B unseen challenge", type="primary", disabled=not ack_b):
        _run_stream(UNSEEN_CASES, "unseen", model_token, model_name, reasoning_effort)
else:
    st.success("Phase B complete. Do not rerun or replace it inside this study.")

st.divider()
st.subheader("Phase C • Repeated stochastic subset")
st.write("Six difficult cases are repeated three times under the unchanged configuration. This tests execution stability separately from generalization.")
if summary["safety_stop"]:
    st.error("Phase C is locked by the protocol safety stop.")
elif study.get("unseen_run") is None:
    st.info("Complete Phase B before opening Phase C.")
elif summary["stochastic_runs_completed"] >= REPEATED_STOCHASTIC_REPEATS:
    st.success("Phase C complete.")
else:
    subset = tuple(get_challenge_case(cid) for cid in REPEATED_STOCHASTIC_CASE_IDS)
    next_repeat = summary["stochastic_runs_completed"] + 1
    ack_c = st.checkbox(f"I understand stochastic repeat {next_repeat} makes {len(subset)} model calls.", key=f"challenge_c_ack_{next_repeat}")
    if st.button(f"Run stochastic repeat {next_repeat} of {REPEATED_STOCHASTIC_REPEATS}", type="primary", disabled=not ack_c):
        _run_stream(subset, "stochastic", model_token, model_name, reasoning_effort)

st.divider()
st.markdown("### Interpretation policy")
st.write(
    "Phase 2 is designed to detect residual failure modes and test generalization without modifying the frozen v1 qualification evidence. "
    "A final GREEN or AMBER research result supports further evaluation, not clinical deployment. A provenance failure, prohibited assertion, or "
    "unsupported-provenance assertion triggers a safety stop. Recurrent repeated-case failure or a final pass rate below 95% produces RED."
)
