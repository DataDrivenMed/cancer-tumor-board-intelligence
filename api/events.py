from __future__ import annotations

from typing import Any

from api.contracts import WorkflowEvent


_EVENT_PRESENTATION: dict[str, tuple[str, str, str, str]] = {
    "workflow_started": (
        "intake",
        "started",
        "Case review started",
        "The submitted case entered the governed workflow. No management conclusion has been produced.",
    ),
    "semantic_integrity_check_complete": (
        "verify",
        "completed",
        "Structured representation checked",
        "The case was checked for unsafe contradictions between structured fields and the represented source extraction.",
    ),
    "quality_check_complete": (
        "verify",
        "completed",
        "Conflicts and missingness checked",
        "Detected conflicts and missing information remain explicit instead of being silently resolved.",
    ),
    "case_integrity_check_complete": (
        "verify",
        "completed",
        "Case integrity gate completed",
        "The canonical case was checked before any specialist output could influence synthesis.",
    ),
    "missing_information_analysis_complete": (
        "verify",
        "completed",
        "Decision-critical information checked",
        "The workflow determined whether missing or unresolved information permits specialist review.",
    ),
    "routing_complete": (
        "analyze",
        "completed",
        "Specialist reviews selected",
        "Only the specialist domains required by the represented clinical question were routed.",
    ),
    "agent_complete": (
        "evidence",
        "completed",
        "Specialist review recorded",
        "The specialist output and its status were recorded for bounded downstream review.",
    ),
    "agent_output_reused": (
        "evidence",
        "completed",
        "Unaffected specialist review reused",
        "A prior specialist output was reused only after the update dependency map showed that its clinical inputs were unchanged.",
    ),
    "targeted_rerun_started": (
        "verify",
        "started",
        "Targeted update review started",
        "The updated case entered a governed rerun with explicit lineage to the prior immutable version.",
    ),
    "clinical_red_team_complete": (
        "analyze",
        "completed",
        "Safety challenge completed",
        "The preliminary evidence package was challenged for unsupported claims, conflicts, and recommendation-blocking risks.",
    ),
    "consensus_complete": (
        "analyze",
        "completed",
        "Evidence integration completed",
        "Management options were integrated by governed evidence rules rather than agent voting.",
    ),
    "tumor_board_brief_complete": (
        "brief",
        "completed",
        "Tumor-board brief prepared",
        "A decision-support brief was rendered from previously governed outputs without adding new clinical claims.",
    ),
    "workflow_complete": (
        "brief",
        "completed",
        "Case review completed",
        "The decision-support package is ready for clinician review and remains separate from the board's final decision.",
    ),
    "workflow_abstained": (
        "verify",
        "blocked",
        "Management synthesis withheld",
        "A safety gate blocked management synthesis. The returned brief identifies what must be resolved next.",
    ),
}


def workflow_events(audit_events: list[dict[str, Any]], *, request_id: str) -> list[WorkflowEvent]:
    """Convert persisted audit events into clinical activity without inventing events."""

    rendered: list[WorkflowEvent] = []
    for sequence, audit in enumerate(audit_events, start=1):
        source_event = str(audit.get("event") or "workflow_event")
        phase, status, title, consequence = _EVENT_PRESENTATION.get(
            source_event,
            (
                "analyze",
                "completed",
                source_event.replace("_", " ").title(),
                "The backend recorded this governed workflow event for audit review.",
            ),
        )
        detail = str(audit.get("detail") or "")
        if source_event == "agent_complete" and detail:
            agent_name = detail.split(";", 1)[0].strip().replace("_", " ").title()
            title = f"{agent_name} review recorded"

        rendered.append(
            WorkflowEvent(
                sequence=sequence,
                event_id=f"{request_id}:{sequence}",
                timestamp=str(audit.get("timestamp") or ""),
                source_event=source_event,
                phase=phase,
                status=status,
                title=title,
                clinical_consequence=consequence,
                audit_detail=detail,
            )
        )
    return rendered
