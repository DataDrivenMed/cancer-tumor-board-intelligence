from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.benchmark_persistence import load_latest_run
from services.semantic_integrity import inspect_raw_semantic_integrity, semantic_integrity_passes


st.set_page_config(page_title="Semantic Integrity", page_icon="🛡️", layout="wide")
st.title("Semantic Integrity Gate")
st.caption("Deterministic cross-field checks after extraction • No model calls • No inference credits")
st.warning("Research qualification environment only. Semantic integrity checks do not constitute clinical validation.")

st.markdown(
    """
This page inspects structured extraction for representation errors that can be missed by field-level accuracy metrics. It currently checks:

- serialized JSON accidentally placed inside scalar fields such as `care_site`
- therapy explicitly described as not started but represented as an administered treatment episode
- historical/ambiguous medication text placed in `current_medications` without explicit current-tense support
- `confirmed` transplant/cellular-therapy or current-medication facts with null values

The gate is deliberately deterministic. It does not infer diagnosis, stage, treatment response, or actionability.

**Combined qualification policy:** a case qualifies only when both the original extraction core gate and the semantic-integrity gate pass.
    """
)

payload = load_latest_run(PROJECT_ROOT / "runtime_data" / "qualification_runs")
uploaded = st.file_uploader("Optional: upload a saved qualification benchmark JSON", type=["json"])
if uploaded is not None:
    try:
        payload = json.loads(uploaded.getvalue().decode("utf-8"))
    except Exception as exc:
        st.error(f"Could not read benchmark JSON: {exc}")
        st.stop()

if not payload:
    st.info("No saved benchmark run is available. Run the extraction benchmark or upload a saved benchmark JSON.")
    st.stop()

st.caption(
    f"Run: {payload.get('run_timestamp_utc', 'unknown')} • "
    f"model={payload.get('model_name', 'unknown')} • "
    f"reasoning={payload.get('reasoning_effort', 'unknown')}"
)

diagnostics = payload.get("diagnostics", {}) or {}
score_lookup = {
    row.get("case_id"): row
    for row in (payload.get("scores", []) or [])
    if isinstance(row, dict) and row.get("case_id")
}

rows = []
all_findings = {}
combined_pass_by_case = {}
for case_id in sorted(diagnostics):
    raw = diagnostics.get(case_id, {}).get("raw_extraction", {}) or {}
    findings = inspect_raw_semantic_integrity(raw)
    all_findings[case_id] = findings
    semantic_pass = semantic_integrity_passes(findings)
    extraction_pass = bool(score_lookup.get(case_id, {}).get("passed_core_gate", False))
    combined_pass = extraction_pass and semantic_pass
    combined_pass_by_case[case_id] = combined_pass
    rows.append(
        {
            "Case": case_id,
            "Extraction core gate": "PASS" if extraction_pass else "REVIEW / FAIL",
            "Semantic integrity": "PASS" if semantic_pass else "REVIEW / FAIL",
            "Overall qualification": "PASS" if combined_pass else "REVIEW / FAIL",
            "Semantic errors": sum(1 for f in findings if f.severity in {"error", "critical"}),
            "Finding codes": ", ".join(f.code for f in findings) if findings else "",
        }
    )

results = pd.DataFrame(rows)
st.dataframe(results, use_container_width=True, hide_index=True)

semantic_passed = sum(1 for findings in all_findings.values() if semantic_integrity_passes(findings))
semantic_failed = len(all_findings) - semantic_passed
combined_passed = sum(1 for passed in combined_pass_by_case.values() if passed)
combined_failed = len(combined_pass_by_case) - combined_passed

c1, c2, c3, c4 = st.columns(4)
c1.metric("Cases inspected", len(all_findings))
c2.metric("Semantic PASS", semantic_passed)
c3.metric("Overall qualified", combined_passed)
c4.metric("Overall review / FAIL", combined_failed)

if combined_failed == 0 and len(combined_pass_by_case) == len(diagnostics):
    st.success("All inspected cases passed both extraction and semantic-integrity gates.")
else:
    st.error(
        "One or more cases failed the combined qualification gate. Downstream reasoning should remain blocked for those cases."
    )

for case_id, findings in all_findings.items():
    if not findings:
        continue
    with st.expander(f"{case_id} semantic-integrity findings", expanded=True):
        for finding in findings:
            st.error(f"{finding.code} • {finding.field}: {finding.message}")

st.markdown("### Gate policy")
st.write(
    "A field-accuracy or extraction-core PASS does not override a semantic-integrity failure. A case is considered qualified only when "
    "both gates pass. Any error or critical semantic finding blocks downstream reasoning until the structured representation is corrected "
    "or explicitly adjudicated by a human reviewer."
)
