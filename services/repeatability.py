from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qualification.protocol import EXPECTED_CASE_IDS, protocol_metadata
from services.semantic_integrity import inspect_raw_semantic_integrity, semantic_integrity_passes


DEFAULT_STUDY_DIR = Path("runtime_data") / "repeatability_studies"
LATEST_STUDY_JSON = "latest_study.json"
STUDY_SCHEMA_VERSION = "1.0"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def evaluate_benchmark_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Add deterministic semantic/overall qualification results to one benchmark run."""
    scores = {
        row.get("case_id"): row
        for row in payload.get("scores", []) or []
        if isinstance(row, dict) and row.get("case_id")
    }
    diagnostics = payload.get("diagnostics", {}) or {}
    case_results: list[dict[str, Any]] = []

    for case_id in EXPECTED_CASE_IDS:
        score = scores.get(case_id)
        diagnostic = diagnostics.get(case_id)
        if not score or not diagnostic:
            case_results.append(
                {
                    "case_id": case_id,
                    "extraction_pass": False,
                    "semantic_pass": False,
                    "overall_pass": False,
                    "semantic_error_count": 0,
                    "semantic_finding_codes": ["MISSING_CASE_RESULT"],
                }
            )
            continue

        raw = diagnostic.get("raw_extraction", {}) or {}
        findings = inspect_raw_semantic_integrity(raw)
        semantic_pass = semantic_integrity_passes(findings)
        extraction_pass = bool(score.get("passed_core_gate", False))
        case_results.append(
            {
                "case_id": case_id,
                "extraction_pass": extraction_pass,
                "semantic_pass": semantic_pass,
                "overall_pass": extraction_pass and semantic_pass,
                "semantic_error_count": sum(1 for f in findings if f.severity in {"error", "critical"}),
                "semantic_finding_codes": [f.code for f in findings],
            }
        )

    total_anchors = sum(int((diagnostics.get(cid) or {}).get("provenance_total", 0)) for cid in EXPECTED_CASE_IDS)
    verified_anchors = sum(int((diagnostics.get(cid) or {}).get("provenance_verified", 0)) for cid in EXPECTED_CASE_IDS)
    exact_provenance_rate = verified_anchors / total_anchors if total_anchors else 1.0

    return {
        "run_timestamp_utc": payload.get("run_timestamp_utc"),
        "model_name": payload.get("model_name"),
        "reasoning_effort": payload.get("reasoning_effort"),
        "completed": bool(payload.get("completed")),
        "failure": payload.get("failure"),
        "protocol": payload.get("protocol") or protocol_metadata(),
        "scores": payload.get("scores", []),
        "diagnostics": payload.get("diagnostics", {}),
        "case_results": case_results,
        "exact_provenance_rate": exact_provenance_rate,
        "provenance_anchors": total_anchors,
        "provenance_verified": verified_anchors,
        "prohibited_assertions": sum(int(row.get("prohibited_assertions", 0)) for row in scores.values()),
        "unsupported_provenance_sum": sum(float(row.get("unsupported_provenance_assertion_rate", 0.0)) for row in scores.values()),
    }


def validate_repeatability_run(run: dict[str, Any], current_protocol: dict[str, Any] | None = None) -> list[str]:
    current_protocol = current_protocol or protocol_metadata()
    errors: list[str] = []
    if not run.get("completed"):
        errors.append("Only completed 10-case benchmark runs may enter the repeatability study.")
    case_ids = tuple(row.get("case_id") for row in run.get("scores", []) if isinstance(row, dict))
    if case_ids != EXPECTED_CASE_IDS:
        errors.append(f"Expected case sequence {EXPECTED_CASE_IDS}; received {case_ids}.")
    run_protocol = run.get("protocol") or {}
    run_fingerprint = run_protocol.get("suite_fingerprint")
    current_fingerprint = current_protocol.get("suite_fingerprint")
    if run_fingerprint and run_fingerprint != current_fingerprint:
        errors.append("Suite fingerprint differs from the frozen Qualification Suite v1.0 fingerprint.")
    return errors


def new_study(*, model_name: str, reasoning_effort: str) -> dict[str, Any]:
    return {
        "schema_version": STUDY_SCHEMA_VERSION,
        "study_created_utc": _utc_now_iso(),
        "study_updated_utc": _utc_now_iso(),
        "protocol": protocol_metadata(),
        "model_name": model_name,
        "reasoning_effort": reasoning_effort,
        "runs": [],
    }


def add_run(study: dict[str, Any], benchmark_payload: dict[str, Any]) -> dict[str, Any]:
    evaluated = evaluate_benchmark_payload(benchmark_payload)
    errors = validate_repeatability_run(evaluated, study.get("protocol") or protocol_metadata())
    if errors:
        raise ValueError(" ".join(errors))

    if study.get("model_name") and evaluated.get("model_name") != study.get("model_name"):
        raise ValueError("Model changed during the repeatability study; start a separate study for a different model.")
    if study.get("reasoning_effort") and evaluated.get("reasoning_effort") != study.get("reasoning_effort"):
        raise ValueError("Reasoning effort changed during the repeatability study; start a separate study.")

    run_key = evaluated.get("run_timestamp_utc")
    existing_keys = {run.get("run_timestamp_utc") for run in study.get("runs", [])}
    if run_key in existing_keys:
        return study

    updated = json.loads(json.dumps(study, default=str))
    updated.setdefault("runs", []).append(evaluated)
    updated["study_updated_utc"] = _utc_now_iso()
    return updated


def aggregate_study(study: dict[str, Any]) -> dict[str, Any]:
    runs = study.get("runs", []) or []
    case_rows = [case for run in runs for case in run.get("case_results", [])]
    scores = [score for run in runs for score in run.get("scores", [])]
    total_anchors = sum(int(run.get("provenance_anchors", 0)) for run in runs)
    verified = sum(int(run.get("provenance_verified", 0)) for run in runs)

    case_stability: dict[str, dict[str, int | float]] = {}
    for case_id in EXPECTED_CASE_IDS:
        rows = [row for row in case_rows if row.get("case_id") == case_id]
        passes = sum(1 for row in rows if row.get("overall_pass"))
        case_stability[case_id] = {
            "passes": passes,
            "runs": len(rows),
            "pass_rate": passes / len(rows) if rows else 0.0,
        }

    metric_names = (
        "field_accuracy",
        "provenance_verification",
        "missing_information_recall",
        "conflict_detection",
        "molecular_accuracy",
        "treatment_coverage",
        "treatment_order_accuracy",
    )
    metric_means = {
        name: (sum(float(row.get(name, 0.0)) for row in scores) / len(scores) if scores else 0.0)
        for name in metric_names
    }

    return {
        "runs_completed": len(runs),
        "total_case_executions": len(case_rows),
        "extraction_core_passes": sum(1 for row in case_rows if row.get("extraction_pass")),
        "semantic_passes": sum(1 for row in case_rows if row.get("semantic_pass")),
        "overall_passes": sum(1 for row in case_rows if row.get("overall_pass")),
        "exact_provenance_rate": verified / total_anchors if total_anchors else 1.0,
        "provenance_anchors": total_anchors,
        "provenance_verified": verified,
        "prohibited_assertions": sum(int(run.get("prohibited_assertions", 0)) for run in runs),
        "unsupported_provenance_sum": sum(float(run.get("unsupported_provenance_sum", 0.0)) for run in runs),
        "case_stability": case_stability,
        "metric_means": metric_means,
    }


def study_to_case_csv(study: dict[str, Any]) -> str:
    stream = io.StringIO()
    fields = ["run", "run_timestamp_utc", "case_id", "extraction_pass", "semantic_pass", "overall_pass", "semantic_error_count", "semantic_finding_codes"]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for run_index, run in enumerate(study.get("runs", []), start=1):
        for row in run.get("case_results", []):
            writer.writerow(
                {
                    "run": run_index,
                    "run_timestamp_utc": run.get("run_timestamp_utc"),
                    "case_id": row.get("case_id"),
                    "extraction_pass": row.get("extraction_pass"),
                    "semantic_pass": row.get("semantic_pass"),
                    "overall_pass": row.get("overall_pass"),
                    "semantic_error_count": row.get("semantic_error_count"),
                    "semantic_finding_codes": " | ".join(row.get("semantic_finding_codes", [])),
                }
            )
    return stream.getvalue()


def persist_study(study: dict[str, Any], study_dir: Path = DEFAULT_STUDY_DIR) -> Path:
    study_dir.mkdir(parents=True, exist_ok=True)
    text = json.dumps(study, indent=2, ensure_ascii=False, default=str)
    latest = study_dir / LATEST_STUDY_JSON
    _atomic_write(latest, text)
    stamp = str(study.get("study_updated_utc") or _utc_now_iso()).replace(":", "-").replace("+", "_")
    archive = study_dir / f"repeatability_study_{stamp}.json"
    _atomic_write(archive, text)
    return latest


def load_latest_study(study_dir: Path = DEFAULT_STUDY_DIR) -> dict[str, Any] | None:
    path = study_dir / LATEST_STUDY_JSON
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None
