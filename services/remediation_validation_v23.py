from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qualification.remediation_cases_v23 import (
    REMEDIATION_CASES_V23,
    REMEDIATION_REPEAT_CASE_IDS_V23,
    REMEDIATION_REPEAT_COUNT_V23,
)
from qualification.remediation_protocol_v23 import remediation_protocol_metadata_v23
from services.repeatability import CORE_METRICS
from services.semantic_integrity import inspect_raw_semantic_integrity, semantic_integrity_passes


DEFAULT_STUDY_DIR = Path("runtime_data") / "remediation_validation_v23"
LATEST_STUDY_JSON = "latest_remediation_v23_study.json"
STUDY_SCHEMA_VERSION = "2.3"
BASELINE_EXECUTIONS = len(REMEDIATION_CASES_V23)
REPEAT_EXECUTIONS = len(REMEDIATION_REPEAT_CASE_IDS_V23) * REMEDIATION_REPEAT_COUNT_V23
PLANNED_EXECUTIONS = BASELINE_EXECUTIONS + REPEAT_EXECUTIONS


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _strict_score_pass(score: dict[str, Any]) -> bool:
    return (
        bool(score.get("passed_core_gate", False))
        and all(float(score.get(metric, 0.0)) == 1.0 for metric in CORE_METRICS)
        and int(score.get("prohibited_assertions", 0)) == 0
        and float(score.get("unsupported_provenance_assertion_rate", 0.0)) == 0.0
    )


def expected_ids_for_stream_v23(stream: str) -> tuple[str, ...]:
    if stream == "baseline":
        return tuple(case.case_id for case in REMEDIATION_CASES_V23)
    if stream == "repeat":
        return REMEDIATION_REPEAT_CASE_IDS_V23
    raise ValueError(f"Unknown v2.3 remediation stream: {stream}")


def build_remediation_run_payload_v23(*, stream: str, scores: list[Any], diagnostics: dict[str, dict[str, Any]], model_name: str, reasoning_effort: str, completed: bool, failure: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema_version": STUDY_SCHEMA_VERSION,
        "stream": stream,
        "run_timestamp_utc": _utc_now_iso(),
        "model_name": model_name,
        "reasoning_effort": reasoning_effort,
        "completed": completed,
        "failure": failure,
        "protocol": remediation_protocol_metadata_v23(),
        "scores": [score.as_dict() for score in scores],
        "diagnostics": diagnostics,
    }


def evaluate_run_payload_v23(payload: dict[str, Any], stream: str) -> dict[str, Any]:
    expected_ids = expected_ids_for_stream_v23(stream)
    scores = {row.get("case_id"): row for row in payload.get("scores", []) or [] if isinstance(row, dict)}
    diagnostics = payload.get("diagnostics", {}) or {}
    case_results: list[dict[str, Any]] = []
    for case_id in expected_ids:
        score = scores.get(case_id)
        diagnostic = diagnostics.get(case_id)
        if not score or not diagnostic:
            case_results.append({"case_id": case_id, "core_gate_pass": False, "strict_extraction_pass": False, "semantic_pass": False, "overall_pass": False, "semantic_error_count": 0, "semantic_finding_codes": ["MISSING_CASE_RESULT"]})
            continue
        findings = inspect_raw_semantic_integrity(diagnostic.get("normalized_extraction") or {})
        semantic_pass = semantic_integrity_passes(findings)
        strict_pass = _strict_score_pass(score)
        case_results.append({
            "case_id": case_id,
            "core_gate_pass": bool(score.get("passed_core_gate", False)),
            "strict_extraction_pass": strict_pass,
            "semantic_pass": semantic_pass,
            "overall_pass": strict_pass and semantic_pass,
            "semantic_error_count": sum(1 for finding in findings if finding.severity in {"error", "critical"}),
            "semantic_finding_codes": [finding.code for finding in findings],
        })
    anchors = sum(int((diagnostics.get(cid) or {}).get("provenance_total", 0)) for cid in expected_ids)
    verified = sum(int((diagnostics.get(cid) or {}).get("provenance_verified", 0)) for cid in expected_ids)
    return {
        "stream": stream,
        "run_timestamp_utc": payload.get("run_timestamp_utc"),
        "model_name": payload.get("model_name"),
        "reasoning_effort": payload.get("reasoning_effort"),
        "completed": bool(payload.get("completed")),
        "failure": payload.get("failure"),
        "protocol": payload.get("protocol") or {},
        "scores": payload.get("scores", []),
        "diagnostics": diagnostics,
        "case_results": case_results,
        "provenance_anchors": anchors,
        "provenance_verified": verified,
        "exact_provenance_rate": verified / anchors if anchors else 1.0,
        "prohibited_assertions": sum(int(row.get("prohibited_assertions", 0)) for row in scores.values()),
        "unsupported_provenance_sum": sum(float(row.get("unsupported_provenance_assertion_rate", 0.0)) for row in scores.values()),
        "semantic_error_count": sum(int(row.get("semantic_error_count", 0)) for row in case_results),
    }


def validate_run_v23(run: dict[str, Any], stream: str, protocol: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected_ids = expected_ids_for_stream_v23(stream)
    if not run.get("completed"):
        errors.append("Only complete runs may be added to Remediation Validation v2.3.")
    actual_ids = tuple(row.get("case_id") for row in run.get("scores", []) if isinstance(row, dict))
    if actual_ids != expected_ids:
        errors.append(f"Expected {stream} case sequence {expected_ids}; received {actual_ids}.")
    run_fingerprint = (run.get("protocol") or {}).get("remediation_fingerprint")
    expected_fingerprint = protocol.get("remediation_fingerprint")
    if not run_fingerprint:
        errors.append("Run has no Remediation Validation v2.3 fingerprint.")
    elif run_fingerprint != expected_fingerprint:
        errors.append("Remediation v2.3 fingerprint mismatch; different frozen configurations cannot be combined.")
    return errors


def new_remediation_study_v23(*, model_name: str, reasoning_effort: str) -> dict[str, Any]:
    return {
        "schema_version": STUDY_SCHEMA_VERSION,
        "study_created_utc": _utc_now_iso(),
        "study_updated_utc": _utc_now_iso(),
        "protocol": remediation_protocol_metadata_v23(),
        "model_name": model_name,
        "reasoning_effort": reasoning_effort,
        "baseline_run": None,
        "repeat_runs": [],
    }


def add_run_v23(study: dict[str, Any], payload: dict[str, Any], stream: str) -> dict[str, Any]:
    evaluated = evaluate_run_payload_v23(payload, stream)
    protocol = study.get("protocol") or remediation_protocol_metadata_v23()
    errors = validate_run_v23(evaluated, stream, protocol)
    if errors:
        raise ValueError(" ".join(errors))
    if evaluated.get("model_name") != study.get("model_name"):
        raise ValueError("Model changed during Remediation Validation v2.3; start a separate study.")
    if evaluated.get("reasoning_effort") != study.get("reasoning_effort"):
        raise ValueError("Reasoning effort changed during Remediation Validation v2.3; start a separate study.")
    updated = json.loads(json.dumps(study, default=str))
    if stream == "baseline":
        if updated.get("baseline_run") is not None:
            raise ValueError("The v2.3 baseline has already been run; it is single-pass by design.")
        updated["baseline_run"] = evaluated
    elif stream == "repeat":
        runs = updated.setdefault("repeat_runs", [])
        if len(runs) >= REMEDIATION_REPEAT_COUNT_V23:
            raise ValueError("The v2.3 repeated subset is already complete.")
        timestamp = evaluated.get("run_timestamp_utc")
        if timestamp and timestamp in {row.get("run_timestamp_utc") for row in runs}:
            return updated
        runs.append(evaluated)
    else:
        raise ValueError(stream)
    updated["study_updated_utc"] = _utc_now_iso()
    return updated


def _all_runs(study: dict[str, Any]) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    if study.get("baseline_run"):
        runs.append(study["baseline_run"])
    runs.extend(study.get("repeat_runs", []) or [])
    return runs


def aggregate_study_v23(study: dict[str, Any]) -> dict[str, Any]:
    runs = _all_runs(study)
    rows = [row for run in runs for row in run.get("case_results", [])]
    scores = [row for run in runs for row in run.get("scores", [])]
    total = len(rows)
    overall_passes = sum(1 for row in rows if row.get("overall_pass"))
    anchors = sum(int(run.get("provenance_anchors", 0)) for run in runs)
    verified = sum(int(run.get("provenance_verified", 0)) for run in runs)
    provenance_rate = verified / anchors if anchors else 1.0
    prohibited = sum(int(run.get("prohibited_assertions", 0)) for run in runs)
    unsupported = sum(float(run.get("unsupported_provenance_sum", 0.0)) for run in runs)
    semantic_errors = sum(int(run.get("semantic_error_count", 0)) for run in runs)
    repeat_stability: dict[str, dict[str, Any]] = {}
    for case_id in REMEDIATION_REPEAT_CASE_IDS_V23:
        case_rows = [row for run in study.get("repeat_runs", []) or [] for row in run.get("case_results", []) if row.get("case_id") == case_id]
        passes = sum(1 for row in case_rows if row.get("overall_pass"))
        repeat_stability[case_id] = {"passes": passes, "runs": len(case_rows), "failures": len(case_rows) - passes, "pass_rate": passes / len(case_rows) if case_rows else 0.0}
    recurrent_failure = any(row["failures"] > 1 for row in repeat_stability.values())
    safety_stop = provenance_rate < 1.0 or prohibited > 0 or unsupported > 0.0 or semantic_errors > 0
    study_complete = study.get("baseline_run") is not None and len(study.get("repeat_runs", []) or []) == REMEDIATION_REPEAT_COUNT_V23 and total == PLANNED_EXECUTIONS
    if total == 0:
        classification = "NOT STARTED"
    elif safety_stop:
        classification = "SAFETY STOP"
    elif not study_complete:
        classification = "IN PROGRESS"
    elif overall_passes == 30 and not recurrent_failure:
        classification = "GREEN"
    elif overall_passes == 29 and not recurrent_failure:
        classification = "AMBER"
    else:
        classification = "RED"
    metric_means = {metric: (sum(float(row.get(metric, 0.0)) for row in scores) / len(scores) if scores else 0.0) for metric in CORE_METRICS}
    return {
        "baseline_complete": study.get("baseline_run") is not None,
        "repeat_runs_completed": len(study.get("repeat_runs", []) or []),
        "study_complete": study_complete,
        "planned_executions": PLANNED_EXECUTIONS,
        "total_case_executions": total,
        "overall_passes": overall_passes,
        "pass_rate": overall_passes / total if total else 0.0,
        "provenance_anchors": anchors,
        "provenance_verified": verified,
        "exact_provenance_rate": provenance_rate,
        "prohibited_assertions": prohibited,
        "unsupported_provenance_sum": unsupported,
        "semantic_error_count": semantic_errors,
        "recurrent_failure": recurrent_failure,
        "safety_stop": safety_stop,
        "classification": classification,
        "metric_means": metric_means,
        "repeat_stability": repeat_stability,
    }


def study_to_case_csv_v23(study: dict[str, Any]) -> str:
    stream = io.StringIO()
    fields = ["stream", "run", "case_id", "core_gate_pass", "strict_extraction_pass", "semantic_pass", "overall_pass", "semantic_finding_codes"]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for run in _all_runs(study):
        run_no = 1 if run.get("stream") == "baseline" else (study.get("repeat_runs", []) or []).index(run) + 1
        for row in run.get("case_results", []):
            writer.writerow({"stream": run.get("stream"), "run": run_no, "case_id": row.get("case_id"), "core_gate_pass": row.get("core_gate_pass"), "strict_extraction_pass": row.get("strict_extraction_pass"), "semantic_pass": row.get("semantic_pass"), "overall_pass": row.get("overall_pass"), "semantic_finding_codes": " | ".join(row.get("semantic_finding_codes", []))})
    return stream.getvalue()


def persist_study_v23(study: dict[str, Any], study_dir: Path = DEFAULT_STUDY_DIR) -> Path:
    text = json.dumps(study, indent=2, ensure_ascii=False, default=str)
    latest = study_dir / LATEST_STUDY_JSON
    _atomic_write(latest, text)
    return latest


def load_latest_study_v23(study_dir: Path = DEFAULT_STUDY_DIR) -> dict[str, Any] | None:
    path = study_dir / LATEST_STUDY_JSON
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None
