from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qualification.protocol import protocol_metadata
from qualification.scoring import QualificationScore


DEFAULT_RUN_DIR = Path("runtime_data") / "qualification_runs"
LATEST_JSON = "latest.json"
LATEST_CSV = "latest.csv"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _score_row(score: QualificationScore) -> dict[str, Any]:
    return {
        "case_id": score.case_id,
        "title": score.title,
        "field_accuracy": score.field_accuracy,
        "provenance_verification": score.provenance_verification,
        "missing_information_recall": score.missing_information_recall,
        "conflict_detection": score.conflict_detection,
        "molecular_accuracy": score.molecular_accuracy,
        "treatment_coverage": score.treatment_coverage,
        "treatment_order_accuracy": score.treatment_order_accuracy,
        "prohibited_assertions": score.prohibited_assertions,
        "unsupported_provenance_assertion_rate": score.unsupported_provenance_assertion_rate,
        "passed_core_gate": score.passed_core_gate,
        "notes": list(score.notes),
    }


def build_run_payload(
    *,
    scores: list[QualificationScore],
    diagnostics: dict[str, dict[str, Any]],
    model_name: str,
    reasoning_effort: str,
    completed: bool,
    failure: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "1.1",
        "run_timestamp_utc": _utc_now_iso(),
        "model_name": model_name,
        "reasoning_effort": reasoning_effort,
        "completed": completed,
        "failure": failure,
        "protocol": protocol_metadata(),
        "scores": [_score_row(score) for score in sorted(scores, key=lambda item: item.case_id)],
        "diagnostics": diagnostics,
    }


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def payload_to_csv(payload: dict[str, Any]) -> str:
    rows = payload.get("scores", [])
    if not rows:
        return ""

    fieldnames = [
        "case_id",
        "title",
        "field_accuracy",
        "provenance_verification",
        "missing_information_recall",
        "conflict_detection",
        "molecular_accuracy",
        "treatment_coverage",
        "treatment_order_accuracy",
        "prohibited_assertions",
        "unsupported_provenance_assertion_rate",
        "passed_core_gate",
        "notes",
    ]
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        csv_row = dict(row)
        csv_row["notes"] = " | ".join(row.get("notes", []))
        writer.writerow(csv_row)
    return stream.getvalue()


def persist_run(payload: dict[str, Any], run_dir: Path = DEFAULT_RUN_DIR) -> dict[str, Path]:
    run_dir.mkdir(parents=True, exist_ok=True)
    timestamp = payload["run_timestamp_utc"].replace(":", "-").replace("+", "_")
    json_text = json.dumps(payload, indent=2, ensure_ascii=False, default=str)
    csv_text = payload_to_csv(payload)

    timestamp_json = run_dir / f"qualification_run_{timestamp}.json"
    timestamp_csv = run_dir / f"qualification_run_{timestamp}.csv"
    latest_json = run_dir / LATEST_JSON
    latest_csv = run_dir / LATEST_CSV

    _atomic_write_text(timestamp_json, json_text)
    _atomic_write_text(timestamp_csv, csv_text)
    _atomic_write_text(latest_json, json_text)
    _atomic_write_text(latest_csv, csv_text)

    return {
        "timestamp_json": timestamp_json,
        "timestamp_csv": timestamp_csv,
        "latest_json": latest_json,
        "latest_csv": latest_csv,
    }


def load_latest_run(run_dir: Path = DEFAULT_RUN_DIR) -> dict[str, Any] | None:
    latest = run_dir / LATEST_JSON
    if not latest.exists():
        return None
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def score_from_dict(data: dict[str, Any]) -> QualificationScore:
    return QualificationScore(
        case_id=data["case_id"],
        title=data["title"],
        field_accuracy=float(data["field_accuracy"]),
        provenance_verification=float(data["provenance_verification"]),
        missing_information_recall=float(data["missing_information_recall"]),
        conflict_detection=float(data["conflict_detection"]),
        molecular_accuracy=float(data["molecular_accuracy"]),
        treatment_coverage=float(data["treatment_coverage"]),
        treatment_order_accuracy=float(data["treatment_order_accuracy"]),
        prohibited_assertions=int(data["prohibited_assertions"]),
        unsupported_provenance_assertion_rate=float(data["unsupported_provenance_assertion_rate"]),
        passed_core_gate=bool(data["passed_core_gate"]),
        notes=list(data.get("notes", [])),
    )
