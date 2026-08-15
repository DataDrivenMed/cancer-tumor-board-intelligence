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
from qualification.protocol import (
    TARGET_REPEATABILITY_RUNS,
    assert_frozen_suite_shape,
    protocol_metadata,
)
from qualification.scoring import score_case
from services.benchmark_persistence import build_run_payload
from services.document_parser import parse_text
from services.repeatability import (
    add_run,
    aggregate_study,
    load_latest_study,
    new_study,
    persist_study,
    study_to_case_csv,
)


st.set_page_config(page_title="Repeatability Qualification", page_icon="🔁", layout="wide")


def get_secret(name: str, default: str | None = None) -> str | None:
    try:
        return st.secrets[name]
    except Exception:
        return default


def _study_is_compatible(study: dict, model_name: str, reasoning_effort: str) -> tuple[bool, str]:
    expected = protocol_metadata()
    actual = study.get("protocol", {}) or {}
    if actual.get("suite_fingerprint") != expected.get("suite_fingerprint"):
        return False, "The study archive does not match the frozen Qualification Suite v1.0 fingerprint."
    if study.get("model_name") != model_name:
        return False, "The study archive was created with a different model configuration."
    if study.get("reasoning_effort") != reasoning_effort:
        return False, "The study archive was created with a different reasoning-effort configuration."
    return True, ""


def _persist_best_effort(study: dict) -> None:
    try:
        persist_study(study, PROJECT_ROOT / "runtime_data" / "repeatability_studies")
    except Exception as exc:
        st.warning(
            "Runtime persistence could not be written. Download the study JSON before leaving this page. "
            f"Persistence error: {exc}"
        )


assert_frozen_suite_shape()
protocol = protocol_metadata()
model_token = get_secret("MODEL_AUTH_TOKEN") or get_secret("HF_TOKEN")
model_name = get_secret("MODEL_NAME", "openai/gpt-oss-120b:fireworks-ai") or "openai/gpt-oss-120b:fireworks-ai"
model_base_url = get_secret("MODEL_BASE_URL")
reasoning_effort = get_secret("MODEL_REASONING_EFFORT", "high") or "high"
if model_base_url:
    os.environ["MODEL_BASE_URL"] = model_base_url

st.title("Repeatability Qualification")
st.caption("Frozen Extraction Qualification Suite v1.0 • 5-run reproducibility study • Synthetic cases only")
st.warning(
    "Research qualification environment only. Repeatability results do not constitute clinical validation. "
    "Do not upload PHI or real patient records."
)

with st.expander("Frozen protocol", expanded=True):
    st.markdown(
        f"""
**Qualification suite:** {protocol['qualification_suite_version']}  
**Protocol:** {protocol['qualification_protocol_version']}  
**Extraction prompt:** {protocol['extraction_prompt_version']}  
**Scoring:** {protocol['scoring_version']}  
**Semantic integrity:** {protocol['semantic_integrity_version']}  
**Normalization:** {protocol['normalization_version']}  
**Target:** {TARGET_REPEATABILITY_RUNS} independent complete runs / {TARGET_REPEATABILITY_RUNS * len(CASES)} case executions  
**Suite fingerprint:** `{protocol['suite_fingerprint'][:16]}...`

A run is counted only if all 10 cases return a score under this frozen configuration. Model or protocol changes require a new study.
        """
    )

c1, c2, c3 = st.columns(3)
c1.metric("Frozen cases", len(CASES))
c2.metric("Configured model", model_name.split(":")[0])
c3.metric("Reasoning effort", reasoning_effort.upper())

if not model_token and not model_base_url:
    st.error("No inference endpoint is configured. Add MODEL_AUTH_TOKEN/HF_TOKEN or MODEL_BASE_URL in Streamlit Secrets.")
    st.stop()

if "repeatability_study" not in st.session_state:
    saved = load_latest_study(PROJECT_ROOT / "runtime_data" / "repeatability_studies")
    if saved:
        compatible, _ = _study_is_compatible(saved, model_name, reasoning_effort)
        st.session_state.repeatability_study = saved if compatible else new_study(model_name=model_name, reasoning_effort=reasoning_effort)
    else:
        st.session_state.repeatability_study = new_study(model_name=model_name, reasoning_effort=reasoning_effort)

st.divider()
st.subheader("Restore or import study")
st.caption("Use this after a Streamlit reboot. The downloaded study JSON is the durable copy because Community Cloud runtime storage can be ephemeral.")
uploaded_study = st.file_uploader("Optional: restore a repeatability study JSON", type=["json"], key="repeatability_study_upload")
if uploaded_study is not None:
    try:
        candidate = json.loads(uploaded_study.getvalue().decode("utf-8"))
        compatible, reason = _study_is_compatible(candidate, model_name, reasoning_effort)
        if not compatible:
            st.error(reason)
        elif st.button("Use uploaded study archive"):
            st.session_state.repeatability_study = candidate
            _persist_best_effort(candidate)
            st.success("Study archive restored.")
            st.rerun()
    except Exception as exc:
        st.error(f"Could not read study archive: {exc}")

study = st.session_state.repeatability_study
summary = aggregate_study(study)

st.divider()
st.subheader("Study status")
a, b, c, d, e = st.columns(5)
a.metric("Runs completed", f"{summary['runs_completed']} / {TARGET_REPEATABILITY_RUNS}")
b.metric("Case executions", f"{summary['total_case_executions']} / {TARGET_REPEATABILITY_RUNS * len(CASES)}")
c.metric("Overall qualified", f"{summary['overall_passes']} / {summary['total_case_executions'] or 0}")
d.metric("Exact provenance", f"{summary['exact_provenance_rate'] * 100:.1f}%")
e.metric("Prohibited assertions", summary["prohibited_assertions"])

if summary["runs_completed"]:
    stability_rows = []
    for case_id, row in summary["case_stability"].items():
        stability_rows.append(
            {
                "Case": case_id,
                "Overall PASS": f"{row['passes']}/{row['runs']}",
                "Pass rate": f"{row['pass_rate'] * 100:.1f}%",
            }
        )
    st.markdown("### Case stability")
    st.dataframe(pd.DataFrame(stability_rows), use_container_width=True, hide_index=True)

    run_rows = []
    for index, run in enumerate(study.get("runs", []), start=1):
        case_results = run.get("case_results", [])
        run_rows.append(
            {
                "Run": index,
                "Timestamp (UTC)": run.get("run_timestamp_utc"),
                "Extraction PASS": f"{sum(1 for r in case_results if r.get('extraction_pass'))}/10",
                "Semantic PASS": f"{sum(1 for r in case_results if r.get('semantic_pass'))}/10",
                "Overall PASS": f"{sum(1 for r in case_results if r.get('overall_pass'))}/10",
                "Exact provenance": f"{float(run.get('exact_provenance_rate', 0.0)) * 100:.1f}%",
                "Prohibited": run.get("prohibited_assertions", 0),
            }
        )
    st.markdown("### Run history")
    st.dataframe(pd.DataFrame(run_rows), use_container_width=True, hide_index=True)

    failing = [
        (idx, row)
        for idx, run in enumerate(study.get("runs", []), start=1)
        for row in run.get("case_results", [])
        if not row.get("overall_pass")
    ]
    if failing:
        st.error("At least one case execution failed overall qualification. Do not hide this with an aggregate average.")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Run": idx,
                        "Case": row.get("case_id"),
                        "Extraction": "PASS" if row.get("extraction_pass") else "FAIL",
                        "Semantic": "PASS" if row.get("semantic_pass") else "FAIL",
                        "Finding codes": ", ".join(row.get("semantic_finding_codes", [])),
                    }
                    for idx, row in failing
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )

study_json = json.dumps(study, indent=2, ensure_ascii=False, default=str).encode("utf-8")
study_csv = study_to_case_csv(study).encode("utf-8")
d1, d2 = st.columns(2)
d1.download_button(
    "Download repeatability study (JSON)",
    data=study_json,
    file_name="extraction_repeatability_v1_study.json",
    mime="application/json",
    use_container_width=True,
)
d2.download_button(
    "Download case-level results (CSV)",
    data=study_csv,
    file_name="extraction_repeatability_v1_cases.csv",
    mime="text/csv",
    use_container_width=True,
)

st.divider()
st.subheader("Run next independent trial")
remaining = TARGET_REPEATABILITY_RUNS - summary["runs_completed"]
if remaining <= 0:
    all_case_executions_pass = summary["overall_passes"] == TARGET_REPEATABILITY_RUNS * len(CASES)
    zero_unsupported = summary["unsupported_provenance_sum"] == 0.0
    if all_case_executions_pass and summary["exact_provenance_rate"] == 1.0 and summary["prohibited_assertions"] == 0 and zero_unsupported:
        st.success("Repeatability target completed: all 50 case executions passed overall qualification with exact provenance and zero prohibited/unsupported assertions.")
    else:
        st.warning("Five runs are complete, but one or more qualification targets were not met. Review case-level instability before any downstream reasoning work.")
else:
    st.write(
        f"The next trial will make 10 sequential model calls. {remaining} full trial(s) remain. "
        "Do not change the model, reasoning effort, suite, prompt, scorer, normalization, or semantic gate during this study."
    )
    acknowledge = st.checkbox("I understand this will run all 10 frozen synthetic cases and use inference credits.", key="repeatability_ack")
    if st.button("Run next repeatability trial", type="primary", disabled=not acknowledge):
        scores = []
        diagnostics = {}
        failure = None
        progress = st.progress(0)
        status = st.empty()

        for idx, gold in enumerate(CASES, start=1):
            status.write(f"Run {summary['runs_completed'] + 1} • {gold.case_id}: {gold.title}")
            document = parse_text(gold.narrative, document_id=f"REPEAT-{gold.case_id}", filename=f"{gold.case_id}.txt")
            try:
                package = extract_case(
                    document=document,
                    api_key=model_token or "local-no-auth",
                    model=model_name,
                    case_id=f"REPEAT-{gold.case_id}",
                )
                score = score_case(gold, package)
                scores.append(score)
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
            progress.progress(idx / len(CASES))

        benchmark_payload = build_run_payload(
            scores=scores,
            diagnostics=diagnostics,
            model_name=model_name,
            reasoning_effort=reasoning_effort,
            completed=failure is None and len(scores) == len(CASES),
            failure=failure,
        )

        if failure is not None or len(scores) != len(CASES):
            st.error(
                "This trial is incomplete and was NOT added to the repeatability denominator. "
                "Resolve the endpoint/tool failure before trying another complete trial."
            )
            st.download_button(
                "Download incomplete trial JSON",
                data=json.dumps(benchmark_payload, indent=2, default=str).encode("utf-8"),
                file_name="incomplete_repeatability_trial.json",
                mime="application/json",
            )
        else:
            try:
                updated = add_run(st.study if False else st.session_state.repeatability_study, benchmark_payload)
                st.session_state.repeatability_study = updated
                _persist_best_effort(updated)
                st.success("Complete 10-case trial added to the frozen repeatability study.")
                st.rerun()
            except Exception as exc:
                st.error(f"The complete trial was not added because protocol validation failed: {exc}")

st.markdown("### Qualification interpretation")
st.write(
    "The pre-specified repeatability target is five complete runs (50 case executions). "
    "A perfect aggregate average is not sufficient if an individual case is unstable. "
    "Any failed overall case execution is retained and surfaced. Completing this phase supports reproducibility of the development extraction benchmark; it does not establish clinical validity or authorize autonomous clinical reasoning."
)
