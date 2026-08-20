from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from api.contracts import HumanDecisionRecordRequest


def build_human_decision_receipt(payload: HumanDecisionRecordRequest) -> dict[str, Any]:
    """Create a deterministic receipt without mutating or storing the workflow result."""

    canonical = {
        "case_id": payload.case_id,
        "workflow_request_id": payload.workflow_request_id,
        "system_decision": payload.system_decision,
        "clinician_judgment": payload.clinician_judgment.model_dump(),
        "board_decision": payload.board_decision.model_dump(),
    }
    digest = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()
    recorded_at = datetime.now(UTC).isoformat()

    events: list[dict[str, Any]] = [
        {
            "event": "system_synthesis_preserved",
            "actor": "system",
            "timestamp": recorded_at,
            "detail": "The governed system decision was copied unchanged into the receipt.",
        },
        {
            "event": "clinician_judgment_attested",
            "actor": "clinician",
            "timestamp": recorded_at,
            "detail": f"Clinician recorded position: {payload.clinician_judgment.position}.",
        },
    ]
    if payload.board_decision.status == "recorded":
        events.append(
            {
                "event": "board_decision_attested",
                "actor": "tumor_board",
                "timestamp": recorded_at,
                "detail": f"Board recorded outcome: {payload.board_decision.outcome}.",
            }
        )
    else:
        events.append(
            {
                "event": "board_decision_pending",
                "actor": "tumor_board",
                "timestamp": recorded_at,
                "detail": "The board decision remains explicitly pending.",
            }
        )

    return {
        "recorded_at": recorded_at,
        "decision_record_id": digest,
        "workflow_request_id": payload.workflow_request_id,
        "system_decision": payload.system_decision,
        "clinician_judgment": payload.clinician_judgment,
        "board_decision": payload.board_decision,
        "decision_events": events,
        "persisted": False,
    }
