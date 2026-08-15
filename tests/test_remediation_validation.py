from qualification.remediation_protocol_v21 import remediation_protocol_metadata
from services.remediation_validation import (
    add_run,
    aggregate_study,
    build_remediation_run_payload,
    new_remediation_study,
)


CORE_SCORE = {
    "field_accuracy": 1.0,
    "provenance_verification": 1.0,
    "missing_information_recall": 1.0,
    "conflict_detection": 1.0,
    "molecular_accuracy": 1.0,
    "treatment_coverage": 1.0,
    "treatment_order_accuracy": 1.0,
    "prohibited_assertions": 0,
    "unsupported_provenance_assertion_rate": 0.0,
    "passed_core_gate": True,
    "notes": [],
}


class _Score:
    def __init__(self, case_id):
        self.case_id = case_id

    def as_dict(self):
        return {"case_id": self.case_id, "title": self.case_id, **CORE_SCORE}


def _diag():
    return {
        "provenance_total": 1,
        "provenance_verified": 1,
        "normalized_extraction": {},
        "raw_model_output": {},
        "normalization_events": [],
    }


def test_new_study_is_fingerprint_stamped():
    study = new_remediation_study(model_name="m", reasoning_effort="high")
    assert len(study["protocol"]["remediation_fingerprint"]) == 64
    assert study["baseline_run"] is None
    assert study["repeat_runs"] == []


def test_complete_baseline_can_be_added_and_is_in_progress():
    study = new_remediation_study(model_name="m", reasoning_effort="high")
    ids = [f"R{i:02d}" for i in range(1, 13)]
    payload = build_remediation_run_payload(
        stream="baseline",
        scores=[_Score(case_id) for case_id in ids],
        diagnostics={case_id: _diag() for case_id in ids},
        model_name="m",
        reasoning_effort="high",
        completed=True,
    )
    payload["protocol"] = remediation_protocol_metadata()
    updated = add_run(study, payload, "baseline")
    summary = aggregate_study(updated)
    assert summary["baseline_complete"]
    assert summary["total_case_executions"] == 12
    assert summary["overall_passes"] == 12
    assert summary["classification"] == "IN PROGRESS"


def test_fingerprint_mismatch_is_rejected():
    study = new_remediation_study(model_name="m", reasoning_effort="high")
    ids = [f"R{i:02d}" for i in range(1, 13)]
    payload = build_remediation_run_payload(
        stream="baseline",
        scores=[_Score(case_id) for case_id in ids],
        diagnostics={case_id: _diag() for case_id in ids},
        model_name="m",
        reasoning_effort="high",
        completed=True,
    )
    payload["protocol"]["remediation_fingerprint"] = "0" * 64
    try:
        add_run(study, payload, "baseline")
    except ValueError as exc:
        assert "fingerprint mismatch" in str(exc).lower()
    else:
        raise AssertionError("Fingerprint mismatch should have been rejected")
