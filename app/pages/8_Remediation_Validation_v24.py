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

from agents.extraction_v24 import extract_case_v24
from qualification.remediation_cases_v24 import REMEDIATION_CASES_V24, REMEDIATION_REPEAT_CASE_IDS_V24, REMEDIATION_REPEAT_COUNT_V24, get_remediation_case_v24
from qualification.remediation_protocol_v24 import assert_remediation_suite_shape_v24, remediation_protocol_metadata_v24
from qualification.scoring_v24 import score_case_v24
from services.document_parser import parse_text
from services.remediation_validation_v24 import add_run_v24, aggregate_study_v24, build_remediation_run_payload_v24, load_latest_study_v24, new_remediation_study_v24, persist_study_v24, study_to_case_csv_v24

st.set_page_config(page_title="Remediation Validation v2.4", page_icon="🧪", layout="wide")


def get_secret(name: str, default: str | None = None) -> str | None:
    try:
        return st.secrets[name]
    except Exception:
        return default


def _compatible(study: dict, model_name: str, reasoning_effort: str) -> tuple[bool, str]:
    current = remediation_protocol_metadata_v24()
    actual = study.get("protocol") or {}
    if actual.get("remediation_fingerprint") != current.get("remediation_fingerprint"):
        return False, "Study fingerprint differs from the current frozen v2.4 configuration."
    if study.get("model_name") != model_name:
        return False, "Study model differs from the configured model."
    if study.get("reasoning_effort") != reasoning_effort:
        return False, "Study reasoning effort differs from the configured reasoning effort."
    return True, ""


def _persist(study: dict) -> None:
    try:
        persist_study_v24(study, PROJECT_ROOT / "runtime_data" / "remediation_validation_v24")
    except Exception as exc:
        st.warning(f"Runtime persistence failed. Download the JSON before leaving the page. Error: {exc}")


def _preflight(protocol: dict, model_name: str, reasoning_effort: str) -> tuple[bool, list[str]]:
    failures: list[str] = []
    try:
        assert_remediation_suite_shape_v24()
    except Exception as exc:
        failures.append(f"Frozen-suite shape: {exc}")
    if len(str(protocol.get("remediation_fingerprint") or "")) != 64:
        failures.append("v2.4 remediation fingerprint is missing or malformed.")
    if not protocol.get("source_hashes"):
        failures.append("Frozen source hashes are missing.")
    if not model_name:
        failures.append("MODEL_NAME is empty.")
    if reasoning_effort.lower() not in {"low", "medium", "high"}:
        failures.append("MODEL_REASONING_EFFORT must be low, medium, or high.")
    return not failures, failures


def _run_cases(cases, stream_name: str, model_token: str | None, model_name: str, reasoning_effort: str, protocol: dict) -> None:
    scores = []
    diagnostics: dict[str, dict] = {}
    failure = None
    progress = st.progress(0)
    status = st.empty()
    for idx, gold in enumerate(cases, start=1):
        status.write(f"{stream_name.title()} • {gold.case_id}: {gold.title}")
        document = parse_text(gold.narrative, document_id=f"V24-{gold.case_id}", filename=f"{gold.case_id}.txt")
        try:
            package = extract_case_v24(document=document, api_key=model_token or "local-no-auth", model=model_name, case_id=f"V24-{gold.case_id}")
            score = score_case_v24(gold, package)
            scores.append(score)
            diagnostics[gold.case_id] = {
                "provenance_total": package.provenance_total,
                "provenance_verified": package.provenance_verified,
                "provenance_failures": package.provenance_failures,
                "warnings": package.warnings,
                "raw_model_output": package.raw_model_output,
                "normalized_extraction": package.normalized_extraction,
                "normalization_events": package.normalization_events,
                "diagnostic_certainty": package.diagnostic_certainty,
                "stage": package.stage,
                "treatment_completeness_performed": package.treatment_completeness_performed,
                "treatment_candidates_found": package.treatment_candidates_found,
                "treatment_episodes_added": package.treatment_episodes_added,
                "extraction_version": package.extraction_version,
            }
        except Exception as exc:
            failure = {"case_id": gold.case_id, "title": gold.title, "error_type": type(exc).__name__, "message": str(exc)}
            st.error(f"{gold.case_id} failed before producing a qualification score: {exc}")
            break
        progress.progress(idx / len(cases))

    payload = build_remediation_run_payload_v24(stream=stream_name, scores=scores, diagnostics=diagnostics, model_name=model_name, reasoning_effort=reasoning_effort, completed=failure is None and len(scores) == len(cases), failure=failure)
    payload["protocol"] = protocol
    st.session_state.remediation_v24_latest_payload = payload
    if failure is not None or len(scores) != len(cases):
        st.error("The batch is incomplete and was NOT added to the formal v2.4 study.")
        st.download_button("Download incomplete batch JSON", data=json.dumps(payload, indent=2, default=str).encode("utf-8"), file_name=f"remediation_v24_{stream_name}_incomplete.json", mime="application/json")
        return
    try:
        updated = add_run_v24(st.session_state.remediation_v24_study, payload, stream_name)
        st.session_state.remediation_v24_study = updated
        _persist(updated)
        st.success(f"Complete {stream_name} batch added to Remediation Validation v2.4.")
        st.rerun()
    except Exception as exc:
        st.error(f"Complete batch was not added because protocol validation failed: {exc}")
        st.download_button("Download rejected complete batch JSON", data=json.dumps(payload, indent=2, default=str).encode("utf-8"), file_name=f"remediation_v24_{stream_name}_rejected.json", mime="application/json")


assert_remediation_suite_shape_v24()
protocol = remediation_protocol_metadata_v24()
model_token = get_secret("MODEL_AUTH_TOKEN") or get_secret("HF_TOKEN")
model_name = get_secret("MODEL_NAME", "openai/gpt-oss-120b:fireworks-ai") or "openai/gpt-oss-120b:fireworks-ai"
model_base_url = get_secret("MODEL_BASE_URL")
reasoning_effort = get_secret("MODEL_REASONING_EFFORT", "high") or "high"
if model_base_url:
    os.environ["MODEL_BASE_URL"] = model_base_url

st.title("Remediation Validation v2.4")
st.caption("Single-canonicalization validation: bounded reconciliation-only layer plus final uncertainty invariant")
st.warning("Research qualification only. Use synthetic or fully de-identified material. This does not authorize autonomous clinical use.")

with st.expander("Frozen v2.4 protocol", expanded=True):
    st.markdown(f"""
**Suite:** {protocol['remediation_suite_version']}  
**Protocol:** {protocol['remediation_protocol_version']}  
**Extraction:** {protocol['extraction_version']}  
**Scoring:** {protocol['scoring_version']}  
**Fresh baseline:** {protocol['case_count']} cases × 1  
**Repeated subset:** {protocol['repeat_case_count']} cases × {protocol['repeat_count']}  
**Total planned case executions:** {protocol['planned_executions']}  
**Fingerprint:** `{protocol['remediation_fingerprint']}`

X01-X12 are fresh v2.4 cases. Once baseline inference starts, do not modify extraction logic, scoring, cases, model, reasoning effort, or the frozen source set inside this study.
""")
    st.caption("GREEN = 30/30 with perfect provenance/safety and every repeated case 3/3. AMBER = exactly 29/30 with perfect provenance/safety and no repeated case failing more than once. Otherwise RED.")

preflight_ok, preflight_failures = _preflight(protocol, model_name, reasoning_effort)
a, b, c, d = st.columns(4)
a.metric("Preflight", "PASS" if preflight_ok else "FAIL")
b.metric("Configured model", model_name.split(":")[0])
c.metric("Reasoning effort", reasoning_effort.upper())
d.metric("Case executions", protocol["planned_executions"])
for item in preflight_failures:
    st.error(item)
if not model_token and not model_base_url:
    st.error("No inference endpoint is configured. Add MODEL_AUTH_TOKEN/HF_TOKEN or MODEL_BASE_URL in Streamlit Secrets.")
    st.stop()
if not preflight_ok:
    st.stop()

if "remediation_v24_study" not in st.session_state:
    saved = load_latest_study_v24(PROJECT_ROOT / "runtime_data" / "remediation_validation_v24")
    if saved:
        ok, _ = _compatible(saved, model_name, reasoning_effort)
        st.session_state.remediation_v24_study = saved if ok else new_remediation_study_v24(model_name=model_name, reasoning_effort=reasoning_effort)
    else:
        st.session_state.remediation_v24_study = new_remediation_study_v24(model_name=model_name, reasoning_effort=reasoning_effort)

st.divider()
st.subheader("Restore study after reboot")
uploaded = st.file_uploader("Optional: restore Remediation Validation v2.4 JSON", type=["json"], key="remediation_v24_upload")
if uploaded is not None:
    try:
        candidate = json.loads(uploaded.getvalue().decode("utf-8"))
        ok, reason = _compatible(candidate, model_name, reasoning_effort)
        if not ok:
            st.error(reason)
        elif st.button("Use uploaded v2.4 study"):
            st.session_state.remediation_v24_study = candidate
            _persist(candidate)
            st.rerun()
    except Exception as exc:
        st.error(f"Could not read study archive: {exc}")

study = st.session_state.remediation_v24_study
summary = aggregate_study_v24(study)
st.divider()
st.subheader("Study status")
a, b, c, d, e = st.columns(5)
a.metric("Baseline", "DONE" if summary["baseline_complete"] else "PENDING")
b.metric("Repeat runs", f"{summary['repeat_runs_completed']} / {REMEDIATION_REPEAT_COUNT_V24}")
c.metric("Strict PASS", f"{summary['overall_passes']} / {summary['total_case_executions']}")
d.metric("Exact provenance", f"{summary['exact_provenance_rate'] * 100:.1f}%")
e.metric("Classification", summary["classification"])

if summary["safety_stop"]:
    st.error("SAFETY STOP: provenance, unsupported-assertion, prohibited-assertion, or semantic-integrity criteria failed. Later runs are locked in this frozen study.")

if summary["total_case_executions"]:
    x1, x2, x3, x4 = st.columns(4)
    x1.metric("Observed strict pass rate", f"{summary['pass_rate'] * 100:.1f}%")
    x2.metric("Prohibited assertions", summary["prohibited_assertions"])
    x3.metric("Unsupported provenance", f"{summary['unsupported_provenance_sum']:.1f}")
    x4.metric("Semantic errors", summary["semantic_error_count"])
    rows = [{"Metric": key.replace("_", " ").title(), "Mean": f"{value * 100:.1f}%"} for key, value in summary["metric_means"].items()]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

study_json = json.dumps(study, indent=2, ensure_ascii=False, default=str).encode("utf-8")
study_csv = study_to_case_csv_v24(study).encode("utf-8")
d1, d2 = st.columns(2)
d1.download_button("Download Remediation v2.4 study (JSON)", data=study_json, file_name="remediation_validation_v24_study.json", mime="application/json", use_container_width=True)
d2.download_button("Download v2.4 case results (CSV)", data=study_csv, file_name="remediation_validation_v24_cases.csv", mime="text/csv", use_container_width=True)

st.divider()
st.subheader("Phase 1 • Fresh 12-case v2.4 baseline")
if study.get("baseline_run") is None:
    ack = st.checkbox("I understand this is a single-pass frozen 12-case baseline and I will not rerun individual cases to replace failures.", key="v24_baseline_ack")
    if st.button("Run v2.4 remediation baseline", type="primary", disabled=not ack or summary["safety_stop"]):
        _run_cases(REMEDIATION_CASES_V24, "baseline", model_token, model_name, reasoning_effort, protocol)
else:
    st.success("v2.4 fresh baseline complete. Do not rerun or replace it inside this study.")

st.divider()
st.subheader("Phase 2 • Frozen repeated subset")
repeat_cases = [get_remediation_case_v24(case_id) for case_id in REMEDIATION_REPEAT_CASE_IDS_V24]
next_repeat = summary["repeat_runs_completed"] + 1
if not summary["baseline_complete"]:
    st.info("Complete and audit the fresh baseline first.")
elif summary["safety_stop"]:
    st.error("Repeated subset is locked by the safety stop.")
elif summary["repeat_runs_completed"] >= REMEDIATION_REPEAT_COUNT_V24:
    st.success("All three repeat runs are complete.")
else:
    ack_repeat = st.checkbox(f"I understand Repeat {next_repeat} makes six frozen case executions and must not be selectively rerun.", key=f"v24_repeat_ack_{next_repeat}")
    if st.button(f"Run stochastic Repeat {next_repeat} of {REMEDIATION_REPEAT_COUNT_V24}", disabled=not ack_repeat):
        _run_cases(repeat_cases, "repeat", model_token, model_name, reasoning_effort, protocol)
