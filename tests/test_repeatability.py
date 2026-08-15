from qualification.protocol import EXPECTED_CASE_IDS, protocol_metadata
from services.repeatability import add_run, aggregate_study, evaluate_benchmark_payload, new_study, validate_repeatability_run


def _score(case_id: str, passed: bool = True) -> dict:
    return {
        "case_id": case_id,
        "title": case_id,
        "field_accuracy": 1.0 if passed else 0.5,
        "provenance_verification": 1.0,
        "missing_information_recall": 1.0,
        "conflict_detection": 1.0,
        "molecular_accuracy": 1.0,
        "treatment_coverage": 1.0,
        "treatment_order_accuracy": 1.0,
        "prohibited_assertions": 0,
        "unsupported_provenance_assertion_rate": 0.0,
        "passed_core_gate": passed,
        "notes": [],
    }


def _payload(*, failed_case: str | None = None, timestamp: str = "2026-08-15T20:00:00+00:00") -> dict:
    return {
        "schema_version": "1.1",
        "run_timestamp_utc": timestamp,
        "model_name": "openai/gpt-oss-120b:fireworks-ai",
        "reasoning_effort": "high",
        "completed": True,
        "failure": None,
        "protocol": protocol_metadata(),
        "scores": [_score(cid, passed=(cid != failed_case)) for cid in EXPECTED_CASE_IDS],
        "diagnostics": {
            cid: {
                "provenance_total": 1,
                "provenance_verified": 1,
                "provenance_failures": [],
                "warnings": [],
                "raw_extraction": {
                    "care_site": None,
                    "treatments": [],
                    "current_medications": [],
                    "transplant_cellular_therapy": [],
                },
            }
            for cid in EXPECTED_CASE_IDS
        },
    }


def test_completed_frozen_run_is_valid():
    evaluated = evaluate_benchmark_payload(_payload())
    assert validate_repeatability_run(evaluated) == []
    assert all(row["overall_pass"] for row in evaluated["case_results"])


def test_run_without_frozen_fingerprint_is_rejected():
    payload = _payload()
    payload.pop("protocol")
    evaluated = evaluate_benchmark_payload(payload)
    errors = validate_repeatability_run(evaluated)
    assert any("fingerprint" in error.lower() for error in errors)


def test_failing_case_is_retained_not_averaged_away():
    study = new_study(model_name="openai/gpt-oss-120b:fireworks-ai", reasoning_effort="high")
    study = add_run(study, _payload(failed_case="Q03"))
    summary = aggregate_study(study)
    assert summary["runs_completed"] == 1
    assert summary["total_case_executions"] == 10
    assert summary["overall_passes"] == 9
    assert summary["case_stability"]["Q03"]["passes"] == 0
    assert summary["case_stability"]["Q03"]["runs"] == 1


def test_duplicate_run_timestamp_is_not_counted_twice():
    study = new_study(model_name="openai/gpt-oss-120b:fireworks-ai", reasoning_effort="high")
    payload = _payload()
    study = add_run(study, payload)
    study = add_run(study, payload)
    assert aggregate_study(study)["runs_completed"] == 1


def test_model_change_is_rejected():
    study = new_study(model_name="openai/gpt-oss-120b:fireworks-ai", reasoning_effort="high")
    payload = _payload()
    payload["model_name"] = "different-model"
    try:
        add_run(study, payload)
    except ValueError as exc:
        assert "model changed" in str(exc).lower()
    else:
        raise AssertionError("Expected model mismatch to be rejected")
