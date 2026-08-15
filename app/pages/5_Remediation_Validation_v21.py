from __future__ import annotations

# Deployment marker: v2.1 import surface verified on main after schema synchronization.
import json
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.extraction_v21 import extract_case_v21
from qualification.remediation_cases_v21 import (
    REMEDIATION_CASES,
    REMEDIATION_REPEAT_CASE_IDS,
    REMEDIATION_REPEAT_COUNT,
    get_remediation_case,
)
from qualification.remediation_protocol_v21 import (
    assert_remediation_suite_shape,
    remediation_protocol_metadata,
)
from qualification.scoring_v21 import score_case_v21
from services.document_parser import parse_text
from services.remediation_validation import (
    add_run,
    aggregate_study,
    build_remediation_run_payload,
    load_latest_study,
    new_remediation_study,
    persist_study,
    study_to_case_csv,
)


st.set_page_config(page_title="Remediation Validation v2.1", page_icon="🛠️", layout="wide")


def get_secret(name: str, default: str | None = None) -> str | None:
    try:
        return st.secrets[name]
    except Exception:
        return default


def _compatible(study: dict, model_name: str, reasoning_effort: str) -> tuple[bool, str]:
    current = remediation_protocol_metadata()
    actual = study.get("protocol") or {}
    if actual.get("remediation_fingerprint") != current.get("remediation_fingerprint"):
        return False, "Study fingerprint differs from the current frozen Remediation Validation v2.1 configuration."
    if study.get("model_name") != model_name:
        return False, "Study model differs from the currently configured model."
    if study.get("reasoning_effort") != reasoning_effort:
        return False, "Study reasoning effort differs from the currently configured reasoning effort."
    return True, ""


def _persist_best_effort(study: dict) -> None:
    try:
        persist_study(study, PROJECT_ROOT / "runtime_data" / "remediation_validation_v21")
    except Exception as exc:
        st.warning(f"Runtime persistence could not be written. Download the study JSON before leaving this page. Error: {exc}")


def _preflight(protocol: dict, model_name: str, reasoning_effort: str) -> tuple[bool, list[str]]:
    failures: list[str] = []
    try:
        assert_remediation_suite_shape()
    except Exception as exc:
        failures.append(f"Frozen-suite shape: {exc}")
    fingerprint = str(protocol.get("remediation_fingerprint") or "")
    if len(fingerprint) != 64:
        failures.append("Remediation fingerprint is missing or malformed.")
    if not protocol.get("source_hashes"):
        failures.append("Frozen source hashes are missing.")
    if not model_name:
        failures.append("MODEL_NAME is empty.")
    if reasoning_effort.lower() not in {"low", "medium", "high"}:
        failures.append("MODEL_REASONING_EFFORT must be low, medium, or high.")
    return not failures, failures


def _run_cases(cases, stream_name: str, model_token: str | None, model_name: str, reasoning_effort: str) -> None:
    scores = []
    diagnostics: dict[str, dict] = {}
    failure = None
    progress = st.progress(0)
    status = st.empty()

    for idx, gold in enumerate(cases, start=1):
        status.write(f"{stream_name.title()} • {gold.case_id}: {gold.title}")
        document = parse_text(
            gold.narrative,
            document_id=f"V21-{gold.case_id}",
            filename=f"{gold.case_id}.txt",
        )
        try:
            package = extract_case_v21(
                document=document,
                api_key=model_token or "local-no-auth",
                model=model_name,
                case_id=f"V21-{gold.case_id}",
            )
            score = score_case_v21(gold, package)
            scores.append(score)
            diagnostics[gold.case_id] = {
                "provenance_total": package.provenance_total,
                "provenance_verified": package.provenance_verified,
                "provenance_failures": package.provenance_failures,
                "warnings": package.warnings,
                "raw_model_output": package.raw_model_output,
                "normalized_extraction": package.normalized_extraction,
                "normalization_events": package.normalization_events,
                "treatment_completeness_performed": package.treatment_completeness_performed,
                "treatment_candidates_found": package.treatment_candidates_found,
                "treatment_episodes_added": package.treatment_episodes_added,
                "extraction_version": package.extraction_version,
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

    payload = build_remediation_run_payload(
        stream=stream_name,
        scores=scores,
        diagnostics=diagnostics,
        model_name=model_name,
        reasoning_effort=reasoning_effort,
        completed=failure is None and len(scores) == len(cases),
        failure=failure,
    )
    payload["protocol"] = protocol
    st.session_state.remediation_v21_latest_payload = payload

    if failure is not None or len(scores) != len(cases):
        st.error("The batch is incomplete and was NOT added to the formal Remediation Validation v2.1 study.")
        st.download_button(
            "Download incomplete batch JSON",
            data=json.dumps(payload, indent=2, default=str).encode("utf-8"),
            file_name=f"remediation_v21_{stream_name}_incomplete.json",
            mime="application/json",
        )
        return

    try:
        updated = add_run(st.session_state.remediation_v21_study, payload, stream_name)
        st.session_state.remediation_v21_study = updated
        _persist_best_effort(updated)
        st.success(f"Complete {stream_name} batch added to Remediation Validation v2.1.")
        st.rerun()
    except Exception as exc:
        st.error(f"Complete batch was not added because protocol validation failed: {exc}")
        st.download_button(
            "Download rejected complete batch JSON",
            data=json.dumps(payload, indent=2, default=str).encode("utf-8"),
            file_name=f"remediation_v21_{stream_name}_rejected.json",
            mime="application/json",
        )


assert_remediation_suite_shape()
protocol = remediation_protocol_metadata()
model_token = get_secret("MODEL_AUTH_TOKEN") or get_secret("HF_TOKEN")
model_name = get_secret("MODEL_NAME", "openai/gpt-oss-120b:fireworks-ai") or "openai/gpt-oss-120b:fireworks-ai"
model_base_url = get_secret("MODEL_BASE_URL")
reasoning_effort = get_secret("MODEL_REASONING_EFFORT", "high") or "high"
if model_base_url:
    os.environ["MODEL_BASE_URL"] = model_base_url

st.title("Remediation Validation v2.1")
st.caption("Fresh frozen validation of disease-state consistency, treatment completeness, uncertainty handling, semantic equivalence, and auditable normalization")
st.warning(
    "Research qualification only. This is not clinical validation and does not authorize autonomous clinical use. "
    "Use synthetic or fully de-identified material only."
)

with st.expander("Frozen v2.1 protocol", expanded=True):
    st.markdown(
        f"""
**Suite:** {protocol['remediation_suite_version']}  
**Protocol:** {protocol['remediation_protocol_version']}  
**Extraction:** {protocol['extraction_version']}  
**Scoring:** {protocol['scoring_version']}  
**Fresh baseline:** {protocol['case_count']} cases, one pass  
**Repeated subset:** {protocol['repeat_case_count']} cases × {protocol['repeat_count']} repeats  
**Total planned case executions:** {protocol['planned_executions']}  
**Remediation fingerprint:** `{protocol['remediation_fingerprint'][:16]}...`

This study uses new R01-R12 cases. The v2.0 RED result remains historical evidence and is not overwritten. Once the first v2.1 baseline inference starts, do not modify extraction logic, cases, scoring, normalization, semantic checks, model, or reasoning effort inside this study.
        """
    )
    st.caption(
        "GREEN = 30/30 strict passes with perfect provenance and safety metrics, plus every repeated case 3/3. "
        "AMBER = exactly 29/30 with the same safety requirements and no repeat case failing more than once. Otherwise RED."
    )

preflight_ok, preflight_failures = _preflight(protocol, model_name, reasoning_effort)
p1, p2, p3, p4 = st.columns(4)
p1.metric("Preflight", "PASS" if preflight_ok else "FAIL")
p2.metric("Configured model", model_name.split(":")[0])
p3.metric("Reasoning effort", reasoning_effort.upper())
p4.metric("Case executions", protocol["planned_executions"])

if preflight_failures:
    for failure in preflight_failures:
        st.error(failure)

if not model_token and not model_base_url:
    st.error("No inference endpoint is configured. Add MODEL_AUTH_TOKEN/HF_TOKEN or MODEL_BASE_URL in Streamlit Secrets.")
    st.stop()
if not preflight_ok:
    st.stop()

if "remediation_v21_study" not in st.session_state:
    saved = load_latest_study(PROJECT_ROOT / "runtime_data" / "remediation_validation_v21")
    if saved:
        ok, _ = _compatible(saved, model_name, reasoning_effort)
        st.session_state.remediation_v21_study = saved if ok else new_remediation_study(model_name=model_name, reasoning_effort=reasoning_effort)
    else:
        st.session_state.remediation_v21_study = new_remediation_study(model_name=model_name, reasoning_effort=reasoning_effort)

st.divider()
st.subheader("Restore study after reboot")
uploaded = st.file_uploader("Optional: restore Remediation Validation v2.1 JSON", type=["json"], key="remediation_v21_upload")
if uploaded is not None:
    try:
        candidate = json.loads(uploaded.getvalue().decode("utf-8"))
        ok, reason = _compatible(candidate, model_name, reasoning_effort)
        if not ok:
            st.error(reason)
        elif st.button("Use uploaded remediation study"):
            st.session_state.remediation_v21_study = candidate
            _persist_best_effort(candidate)
            st.success("Remediation study restored.")
            st.rerun()
    except Exception as exc:
        st.error(f"Could not read study archive: {exc}")

study = st.session_state.remediation_v21_study
summary = aggregate_study(study)

st.divider()
st.subheader("Study status")
a, b, c, d, e = st.columns(5)
a.metric("Baseline", "DONE" if summary["baseline_complete"] else "PENDING")
b.metric("Repeat runs", f"{summary['repeat_runs_completed']} / {REMEDIATION_REPEAT_COUNT}")
c.metric("Strict PASS", f"{summary['overall_passes']} / {summary['total_case_executions']}")
d.metric("Exact provenance", f"{summary['exact_provenance_rate'] * 100:.1f}%")
e.metric("Classification", summary["classification"])

if summary["safety_stop"]:
    st.error(
        "SAFETY STOP: a completed batch contains a provenance failure, prohibited assertion, unsupported-provenance assertion, or semantic-integrity error. "
        "Additional v2.1 runs are locked until the recorded result is adjudicated outside this frozen study."
    )

if summary["total_case_executions"]:
    q1, q2, q3, q4 = st.columns(4)
    q1.metric("Observed strict pass rate", f"{summary['pass_rate'] * 100:.1f}%")
    q2.metric("Prohibited assertions", summary["prohibited_assertions"])
    q3.metric("Unsupported provenance", f"{summary['unsupported_provenance_sum']:.1f}")
    q4.metric("Semantic errors", summary["semantic_error_count"])

    metric_rows = [
        {"Metric": key.replace("_", " ").title(), "Mean": f"{value * 100:.1f}%"}
        for key, value in summary["metric_means"].items()
    ]
    st.markdown("### Core metric means")
    st.dataframe(pd.DataFrame(metric_rows), use_container_width=True, hide_index=True)

    failures = []
    if study.get("baseline_run"):
        for row in study["baseline_run"].get("case_results", []):
            if not row.get("overall_pass"):
                failures.append({"Stream": "baseline", "Run": 1, "Case": row.get("case_id"), "Core": row.get("core_gate_pass"), "Strict": row.get("strict_extraction_pass"), "Semantic": row.get("semantic_pass")})
    for idx, run in enumerate(study.get("repeat_runs", []) or [], start=1):
        for row in run.get("case_results", []):
            if not row.get("overall_pass"):
                failures.append({"Stream": "repeat", "Run": idx, "Case": row.get("case_id"), "Core": row.get("core_gate_pass"), "Strict": row.get("strict_extraction_pass"), "Semantic": row.get("semantic_pass")})
    if failures:
        st.error("One or more executions failed strict overall qualification. Failures remain visible and are never averaged away.")
        st.dataframe(pd.DataFrame(failures), use_container_width=True, hide_index=True)

if summary["repeat_runs_completed"]:
    rows = [
        {"Case": case_id, "PASS": f"{result['passes']}/{result['runs']}", "Failures": result["failures"], "Pass rate": f"{result['pass_rate'] * 100:.1f}%"}
        for case_id, result in summary["repeat_stability"].items()
    ]
    st.markdown("### Repeated-subset stability")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

study_json = json.dumps(study, indent=2, ensure_ascii=False, default=str).encode("utf-8")
study_csv = study_to_case_csv(study).encode("utf-8")
d1, d2 = st.columns(2)
d1.download_button("Download Remediation v2.1 study (JSON)", data=study_json, file_name="remediation_validation_v21_study.json", mime="application/json", use_container_width=True)
d2.download_button("Download case results (CSV)", data=study_csv, file_name="remediation_validation_v21_cases.csv", mime="text/csv", use_container_width=True)

st.divider()
st.subheader("Phase 1 • Fresh 12-case remediation baseline")
st.write(
    "R01-R12 are newly constructed cases that target the failure classes identified in the closed v2.0 challenge study. "
    "Each case is executed once. Treatment-rich cases may invoke one bounded treatment-completeness second pass, so 12 case executions can require more than 12 model requests."
)
if study.get("baseline_run") is None:
    ack = st.checkbox(
        "I understand the baseline contains 12 frozen case executions, may make additional bounded treatment-completeness model requests, and must not be edited after results are observed.",
        key="remediation_baseline_ack",
    )
    if st.button("Run v2.1 remediation baseline", type="primary", disabled=not ack or summary["safety_stop"]):
        _run_cases(REMEDIATION_CASES, "baseline", model_token, model_name, reasoning_effort)
else:
    st.success("Fresh baseline complete. Do not rerun or replace it inside this study.")

st.divider()
st.subheader("Phase 2 • Frozen repeated subset")
st.write(
    "Six cases were selected before inference for repeated testing: disease-state promotion, treatment completeness, uncertainty handling, and conflict-preserving abstention. "
    "Run them only after the baseline has completed without a safety stop."
)
if summary["safety_stop"]:
    st.error("Repeat testing is locked by the protocol safety stop.")
elif study.get("baseline_run") is None:
    st.info("Complete the fresh baseline first.")
elif summary["repeat_runs_completed"] >= REMEDIATION_REPEAT_COUNT:
    st.success("All repeated-subset runs are complete.")
else:
    subset = tuple(get_remediation_case(case_id) for case_id in REMEDIATION_REPEAT_CASE_IDS)
    next_repeat = summary["repeat_runs_completed"] + 1
    ack_repeat = st.checkbox(
        f"I understand repeat {next_repeat} makes {len(subset)} case executions and must use the unchanged frozen configuration.",
        key=f"remediation_repeat_ack_{next_repeat}",
    )
    if st.button(
        f"Run repeated subset {next_repeat} of {REMEDIATION_REPEAT_COUNT}",
        type="primary",
        disabled=not ack_repeat,
    ):
        _run_cases(subset, "repeat", model_token, model_name, reasoning_effort)

st.divider()
st.markdown("### Interpretation policy")
st.write(
    "This is a synthetic remediation qualification study, not clinical validation. A GREEN result supports that the identified v2.0 extraction failure classes were not reproduced in this frozen v2.1 test set under the fixed model configuration. It does not establish real-world clinical safety, generalization to unseen institutions, or suitability for autonomous decision-making."
)
