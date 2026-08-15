from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from qualification.challenge_cases_v2 import (
    REPEATED_STOCHASTIC_CASE_IDS,
    REPEATED_STOCHASTIC_REPEATS,
    TARGETED_CASES,
    UNSEEN_CASES,
)
from qualification.challenge_protocol_v2 import challenge_protocol_metadata
from services.repeatability import CORE_METRICS
from services.semantic_integrity import inspect_raw_semantic_integrity, semantic_integrity_passes


DEFAULT_STUDY_DIR = Path("runtime_data") / "challenge_validation_v2"
LATEST_STUDY_JSON = "latest_challenge_study.json"
STUDY_SCHEMA_VERSION = "2.0"


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


def expected_ids_for_stream(stream: str) -> tuple[str, ...]:
    if stream == "targeted":
        return tuple(c.case_id for c in TARGETED_CASES)
    if stream == "unseen":
        return tuple(c.case_id for c in UNSEEN_CASES)
    if stream == "stochastic":
        return REPEATED_STOCHASTIC_CASE_IDS
    raise ValueError(f"Unknown validation stream: {stream}")


def evaluate_stream_payload(payload: dict[str, Any], stream: str) -> dict[str, Any]:
    expected_ids = expected_ids_for_stream(stream)
    scores = {r.get("case_id"): r for r in payload.get("scores", []) or [] if isinstance(r, dict)}
    diagnostics = payload.get("diagnostics", {}) or {}
    case_results: list[dict[str, Any]] = []

    for case_id in expected_ids:
        score = scores.get(case_id)
        diagnostic = diagnostics.get(case_id)
        if not score or not diagnostic:
            case_results.append({
                "case_id": case_id,
                "core_gate_pass": False,
                "strict_extraction_pass": False,
                "semantic_pass": False,
                "overall_pass": False,
                "semantic_error_count": 0,
                "semantic_finding_codes": ["MISSING_CASE_RESULT"],
            })
            continue
        findings = inspect_raw_semantic_integrity((diagnostic.get("raw_extraction") or {}))
        semantic_pass = semantic_integrity_passes(findings)
        strict_pass = _strict_score_pass(score)
        case_results.append({
            "case_id": case_id,
            "core_gate_pass": bool(score.get("passed_core_gate", False)),
            "strict_extraction_pass": strict_pass,
            "semantic_pass": semantic_pass,
            "overall_pass": strict_pass and semantic_pass,
            "semantic_error_count": sum(1 for f in findings if f.severity in {"error", "critical"}),
            "semantic_finding_codes": [f.code for f in findings],
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
    }


def validate_stream_run(run: dict[str, Any], stream: str, protocol: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected_ids = expected_ids_for_stream(stream)
    if not run.get("completed"):
        errors.append("Only complete stream runs may be added to Challenge Validation v2.")
    actual_ids = tuple(r.get("case_id") for r in run.get("scores", []) if isinstance(r, dict))
    if actual_ids != expected_ids:
        errors.append(f"Expected {stream} case sequence {expected_ids}; received {actual_ids}.")
    run_fingerprint = (run.get("protocol") or {}).get("challenge_fingerprint")
    expected_fingerprint = protocol.get("challenge_fingerprint")
    if not run_fingerprint:
        errors.append("Run has no Challenge Validation v2 fingerprint.")
    elif run_fingerprint != expected_fingerprint:
        errors.append("Challenge fingerprint mismatch; do not combine results from different frozen configurations.")
    return errors


def new_challenge_study(*, model_name: str, reasoning_effort: str) -> dict[str, Any]:
    return {
        "schema_version": STUDY_SCHEMA_VERSION,
        "study_created_utc": _utc_now_iso(),
        "study_updated_utc": _utc_now_iso(),
        "protocol": challenge_protocol_metadata(),
        "model_name": model_name,
        "reasoning_effort": reasoning_effort,
        "targeted_run": None,
        "unseen_run": None,
        "stochastic_runs": [],
    }


def _check_model(study: dict[str, Any], run: dict[str, Any]) -> None:
    if run.get("model_name") != study.get("model_name"):
        raise ValueError("Model changed during Challenge Validation v2; start a separate study.")
    if run.get("reasoning_effort") != study.get("reasoning_effort"):
        raise ValueError("Reasoning effort changed during Challenge Validation v2; start a separate study.")


def add_stream_run(study: dict[str, Any], payload: dict[str, Any], stream: str) -> dict[str, Any]:
    evaluated = evaluate_stream_payload(payload, stream)
    protocol = study.get("protocol") or challenge_protocol_metadata()
    errors = validate_stream_run(evaluated, stream, protocol)
    if errors:
        raise ValueError(" ".join(errors))
    _check_model(study, evaluated)

    updated = json.loads(json.dumps(study, default=str))
    if stream == "targeted":
        if updated.get("targeted_run") is not None:
            raise ValueError("Targeted challenge stream has already been run; the frozen stream is single-pass by design.")
        updated["targeted_run"] = evaluated
    elif stream == "unseen":
        if updated.get("unseen_run") is not None:
            raise ValueError("Unseen challenge stream has already been run; the frozen stream is single-pass by design.")
        updated["unseen_run"] = evaluated
    elif stream == "stochastic":
        runs = updated.setdefault("stochastic_runs", [])
        if len(runs) >= REPEATED_STOCHASTIC_REPEATS:
            raise ValueError("Repeated stochastic subset is already complete.")
        timestamp = evaluated.get("run_timestamp_utc")
        if timestamp and timestamp in {r.get("run_timestamp_utc") for r in runs}:
            return updated
        runs.append(evaluated)
    else:
        raise ValueError(stream)
    updated["study_updated_utc"] = _utc_now_iso()
    return updated


def _all_runs(study: dict[str, Any]) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    if study.get("targeted_run"):
        runs.append(study["targeted_run"])
    if study.get("unseen_run"):
        runs.append(study["unseen_run"])
    runs.extend(study.get("stochastic_runs", []) or [])
    return runs


def aggregate_challenge_study(study: dict[str, Any]) -> dict[str, Any]:
    runs = _all_runs(study)
    rows = [row for run in runs for row in run.get("case_results", [])]
    scores = [row for run in runs for row in run.get("scores", [])]
    anchors = sum(int(run.get("provenance_anchors", 0)) for run in runs)
    verified = sum(int(run.get("provenance_verified", 0)) for run in runs)
    overall_passes = sum(1 for row in rows if row.get("overall_pass"))
    total = len(rows)
    pass_rate = overall_passes / total if total else 0.0

    stochastic_case_stability: dict[str, dict[str, Any]] = {}
    for cid in REPEATED_STOCHASTIC_CASE_IDS:
        cid_rows = [
            row for run in study.get("stochastic_runs", []) or []
            for row in run.get("case_results", []) if row.get("case_id") == cid
        ]
        passes = sum(1 for row in cid_rows if row.get("overall_pass"))
        stochastic_case_stability[cid] = {
            "passes": passes,
            "runs": len(cid_rows),
            "failures": len(cid_rows) - passes,
            "pass_rate": passes / len(cid_rows) if cid_rows else 0.0,
        }

    provenance_rate = verified / anchors if anchors else 1.0
    prohibited = sum(int(run.get("prohibited_assertions", 0)) for run in runs)
    unsupported = sum(float(run.get("unsupported_provenance_sum", 0.0)) for run in runs)
    recurrent_failure = any(v["failures"] > 1 for v in stochastic_case_stability.values())

    if total == 0:
        classification = "NOT STARTED"
    elif provenance_rate < 1.0 or prohibited > 0 or unsupported > 0.0 or recurrent_failure or pass_rate < 0.95:
        classification = "RED"
    elif pass_rate == 1.0:
        classification = "GREEN"
    else:
        classification = "AMBER"

    metric_means = {
        metric: (sum(float(row.get(metric, 0.0)) for row in scores) / len(scores) if scores else 0.0)
        for metric in CORE_METRICS
    }
    return {
        "targeted_complete": study.get("targeted_run") is not None,
        "unseen_complete": study.get("unseen_run") is not None,
        "stochastic_runs_completed": len(study.get("stochastic_runs", []) or []),
        "total_case_executions": total,
        "overall_passes": overall_passes,
        "pass_rate": pass_rate,
        "provenance_anchors": anchors,
        "provenance_verified": verified,
        "exact_provenance_rate": provenance_rate,
        "prohibited_assertions": prohibited,
        "unsupported_provenance_sum": unsupported,
        "recurrent_failure": recurrent_failure,
        "classification": classification,
        "metric_means": metric_means,
        "stochastic_case_stability": stochastic_case_stability,
    }


def study_to_case_csv(study: dict[str, Any]) -> str:
    stream = io.StringIO()
    fields = ["stream", "run", "case_id", "core_gate_pass", "strict_extraction_pass", "semantic_pass", "overall_pass", "semantic_finding_codes"]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for run in _all_runs(study):
        if run.get("stream") == "stochastic":
            run_no = (study.get("stochastic_runs", []) or []).index(run) + 1
        else:
            run_no = 1
        for row in run.get("case_results", []):
            writer.writerow({
                "stream": run.get("stream"),
                "run": run_no,
                "case_id": row.get("case_id"),
                "core_gate_pass": row.get("core_gate_pass"),
                "strict_extraction_pass": row.get("strict_extraction_pass"),
                "semantic_pass": row.get("semantic_pass"),
                "overall_pass": row.get("overall_pass"),
                "semantic_finding_codes": " | ".join(row.get("semantic_finding_codes", [])),
            })
    return stream.getvalue()


def persist_challenge_study(study: dict[str, Any], study_dir: Path = DEFAULT_STUDY_DIR) -> Path:
    text = json.dumps(study, indent=2, ensure_ascii=False, default=str)
    latest = study_dir / LATEST_STUDY_JSON
    _atomic_write(latest, text)
    return latest


def load_latest_challenge_study(study_dir: Path = DEFAULT_STUDY_DIR) -> dict[str, Any] | None:
    path = study_dir / LATEST_STUDY_JSON
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None
