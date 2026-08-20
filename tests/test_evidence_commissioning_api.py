from services.evidence_commissioning_api import (
    build_commissioned_context,
    collect_commissioning_snapshot,
)
from schemas.case import CancerTumorBoardCase

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _case() -> CancerTumorBoardCase:
    payload = json.loads((ROOT / "synthetic_cases" / "syn_aml_001.json").read_text(encoding="utf-8"))
    return CancerTumorBoardCase.model_validate(payload)


def test_guided_snapshot_is_deterministic_and_request_scoped() -> None:
    first = collect_commissioning_snapshot(_case(), mode="guided_fixture")
    second = collect_commissioning_snapshot(_case(), mode="guided_fixture")
    assert first is not second
    assert first.candidate_set_id == second.candidate_set_id
    assert [item["candidate_id"] for item in first.candidates] == [
        item["candidate_id"] for item in second.candidates
    ]


def test_rejected_fixtures_are_not_admitted_to_commissioned_context() -> None:
    snapshot = collect_commissioning_snapshot(_case(), mode="guided_fixture")
    decisions = [
        {
            "candidate_id": candidate["candidate_id"],
            "decision": "approved" if candidate["channel"] == "guideline" else "rejected",
            "reason": "Synthetic fixture is not admitted." if candidate["synthetic"] else "",
        }
        for candidate in snapshot.candidates
    ]
    context, receipt = build_commissioned_context(
        snapshot,
        candidate_set_id=snapshot.candidate_set_id,
        decisions=decisions,
        attested=True,
    )
    assert receipt["approved_count"] == 1
    assert context.status_snapshot()["guideline"]["configuration_origin"] == "session_human_attested"
    assert context.status_snapshot()["molecular"]["record_count"] == 1
    assert context.agent("molecular").run(_case()).status == "source_unavailable"
