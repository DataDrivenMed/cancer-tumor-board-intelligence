from pathlib import Path

from qualification.scoring import QualificationScore
from services.benchmark_persistence import (
    build_run_payload,
    load_latest_run,
    payload_to_csv,
    persist_run,
    score_from_dict,
)


def _score(case_id: str = "Q01") -> QualificationScore:
    return QualificationScore(
        case_id=case_id,
        title="Synthetic case",
        field_accuracy=1.0,
        provenance_verification=1.0,
        missing_information_recall=1.0,
        conflict_detection=1.0,
        molecular_accuracy=1.0,
        treatment_coverage=1.0,
        treatment_order_accuracy=1.0,
        prohibited_assertions=0,
        unsupported_provenance_assertion_rate=0.0,
        passed_core_gate=True,
        notes=[],
    )


def test_build_payload_and_restore_score():
    payload = build_run_payload(
        scores=[_score()],
        diagnostics={"Q01": {"provenance_total": 1}},
        model_name="test-model",
        reasoning_effort="high",
        completed=True,
    )

    assert payload["completed"] is True
    assert payload["model_name"] == "test-model"
    assert payload["scores"][0]["case_id"] == "Q01"

    restored = score_from_dict(payload["scores"][0])
    assert restored.case_id == "Q01"
    assert restored.passed_core_gate is True
    assert restored.provenance_verification == 1.0


def test_persist_and_load_latest_run(tmp_path: Path):
    payload = build_run_payload(
        scores=[_score()],
        diagnostics={"Q01": {"warnings": [], "raw_extraction": {}}},
        model_name="test-model",
        reasoning_effort="high",
        completed=True,
    )

    paths = persist_run(payload, tmp_path)
    assert paths["latest_json"].exists()
    assert paths["latest_csv"].exists()

    loaded = load_latest_run(tmp_path)
    assert loaded is not None
    assert loaded["completed"] is True
    assert loaded["scores"][0]["case_id"] == "Q01"


def test_csv_contains_safety_metrics():
    payload = build_run_payload(
        scores=[_score()],
        diagnostics={},
        model_name="test-model",
        reasoning_effort="high",
        completed=True,
    )

    csv_text = payload_to_csv(payload)
    assert "unsupported_provenance_assertion_rate" in csv_text
    assert "prohibited_assertions" in csv_text
    assert "Q01" in csv_text


def test_partial_run_records_failure(tmp_path: Path):
    payload = build_run_payload(
        scores=[_score("Q01")],
        diagnostics={"Q01": {}},
        model_name="test-model",
        reasoning_effort="high",
        completed=False,
        failure={"case_id": "Q02", "error_type": "ProviderError", "message": "quota"},
    )
    persist_run(payload, tmp_path)
    loaded = load_latest_run(tmp_path)

    assert loaded is not None
    assert loaded["completed"] is False
    assert loaded["failure"]["case_id"] == "Q02"
    assert len(loaded["scores"]) == 1
