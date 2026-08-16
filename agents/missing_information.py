from __future__ import annotations

from hashlib import sha1

from schemas.case import CancerTumorBoardCase, DataStatus
from schemas.missing_information import (
    MissingInformationAction,
    MissingInformationDisposition,
    MissingInformationItem,
    MissingInformationPriority,
    MissingInformationReport,
)


AGENT_ID = "missing_information"
AGENT_VERSION = "1.1.0"

_PRIORITY_SCORE = {
    MissingInformationPriority.CRITICAL: 100,
    MissingInformationPriority.HIGH: 80,
    MissingInformationPriority.MODERATE: 50,
    MissingInformationPriority.LOW: 20,
}


def _item_id(field: str, category: str, reason: str) -> str:
    raw = f"{field}|{category}|{reason}".lower().encode("utf-8")
    return f"MISS-{sha1(raw).hexdigest()[:12]}"


def _norm(value: object | None) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _status_unresolved(status: DataStatus) -> bool:
    return status in {
        DataStatus.UNKNOWN,
        DataStatus.NOT_DOCUMENTED,
        DataStatus.NOT_ASSESSED,
        DataStatus.PENDING,
        DataStatus.CONFLICTING,
        DataStatus.UNAVAILABLE,
    }


def _category_for(field: str, reason: str) -> str:
    text = f"{field} {reason}".lower()
    if any(token in text for token in ("stage", "staging")):
        return "stage"
    if any(token in text for token in ("flt3", "npm1", "idh1", "idh2", "fish", "cytogen", "karyotype", "molecular", "mutation", "sequenc", "ngs")):
        return "molecular"
    if any(token in text for token in ("pathology", "biopsy", "histology", "marrow", "tissue")):
        return "pathology"
    if any(token in text for token in ("ecog", "performance status", "functional status")):
        return "performance_status"
    if any(token in text for token in ("primary site", "diagnosis", "diagnostic", "classification")):
        return "diagnostic_clarification"
    if any(token in text for token in ("disease state", "relapse status", "response status", "progression status")):
        return "disease_state"
    if any(token in text for token in ("planned", "recommended", "not yet started", "treatment plan")):
        return "treatment_plan"
    if any(token in text for token in ("prior treatment", "treatment history", "prior therapy", "previous therapy")):
        return "treatment_history"
    return "other"


def _priority(value: str) -> MissingInformationPriority:
    try:
        return MissingInformationPriority(value)
    except ValueError:
        return MissingInformationPriority.MODERATE


def _action_for(*, availability: str, category: str) -> MissingInformationAction:
    availability_norm = _norm(availability)
    if category == "conflict_resolution":
        return MissingInformationAction.RESOLVE_CONFLICT
    if availability_norm in {"pending", "ordered"}:
        return MissingInformationAction.REVIEW
    if availability_norm in {"conflicting"}:
        return MissingInformationAction.RESOLVE_CONFLICT
    if availability_norm in {"not_documented", "unavailable", "not_assessed", "unknown", ""}:
        return MissingInformationAction.OBTAIN
    return MissingInformationAction.VERIFY


def _make_item(
    *,
    field: str,
    category: str,
    priority: MissingInformationPriority,
    reason: str,
    availability: str,
    recommendation_blocking: bool,
    action: MissingInformationAction,
    source: str,
    field_path: str | None = None,
    source_segment_ids: list[str] | None = None,
) -> MissingInformationItem:
    return MissingInformationItem(
        item_id=_item_id(field, category, reason),
        field=field,
        category=category,
        priority=priority,
        reason=reason,
        availability=availability,
        recommendation_blocking=recommendation_blocking,
        action=action,
        source=source,
        field_path=field_path,
        source_segment_ids=sorted(set(source_segment_ids or [])),
        priority_score=_PRIORITY_SCORE[priority],
    )


def _segments_from_fact(fact) -> list[str]:
    out: list[str] = []
    for provenance in fact.provenance or []:
        out.extend(provenance.source_segment_ids)
    return sorted(set(out))


def _existing_missing_items(case: CancerTumorBoardCase) -> list[MissingInformationItem]:
    items: list[MissingInformationItem] = []
    for idx, item in enumerate(case.missing_items):
        category = getattr(item, "category", None) or _category_for(item.field, item.reason)
        priority = _priority(item.importance)
        items.append(_make_item(
            field=item.field,
            category=category,
            priority=priority,
            reason=item.reason,
            availability=item.availability,
            recommendation_blocking=item.recommendation_blocking,
            action=_action_for(availability=item.availability, category=category),
            source="canonical_missing_item",
            field_path=f"missing_items[{idx}]",
        ))
    return items


def _structural_items(case: CancerTumorBoardCase) -> list[MissingInformationItem]:
    items: list[MissingInformationItem] = []

    if _status_unresolved(case.diagnosis.status) or case.diagnosis.value in {None, ""}:
        items.append(_make_item(
            field="diagnostic confirmation",
            category="diagnostic_clarification",
            priority=MissingInformationPriority.CRITICAL,
            reason="The underlying diagnosis is not confirmed in the canonical case.",
            availability=case.diagnosis.status.value,
            recommendation_blocking=True,
            action=MissingInformationAction.OBTAIN if case.diagnosis.status != DataStatus.PENDING else MissingInformationAction.REVIEW,
            source="structural_rule",
            field_path="diagnosis",
            source_segment_ids=_segments_from_fact(case.diagnosis),
        ))

    if _status_unresolved(case.disease_state.status) or case.disease_state.value in {None, ""}:
        items.append(_make_item(
            field="current disease state",
            category="disease_state",
            priority=MissingInformationPriority.HIGH,
            reason="Current disease state is unresolved, which can materially change tumor-board routing and management framing.",
            availability=case.disease_state.status.value,
            recommendation_blocking=False,
            action=MissingInformationAction.REVIEW if case.disease_state.status == DataStatus.PENDING else MissingInformationAction.OBTAIN,
            source="structural_rule",
            field_path="disease_state",
            source_segment_ids=_segments_from_fact(case.disease_state),
        ))

    stage = case.stage
    if stage is not None and (_status_unresolved(stage.status) or stage.value in {None, ""}):
        stage_conflicting = stage.status == DataStatus.CONFLICTING
        items.append(_make_item(
            field="cancer stage",
            category="stage",
            priority=MissingInformationPriority.CRITICAL if stage_conflicting else MissingInformationPriority.HIGH,
            reason=(
                "Distinct explicit stage statements are represented and require source or temporal reconciliation before management synthesis."
                if stage_conflicting
                else "Stage is explicitly represented as unresolved and requires review before it is used in tumor-board reasoning."
            ),
            availability=stage.status.value,
            recommendation_blocking=stage_conflicting,
            action=MissingInformationAction.RESOLVE_CONFLICT if stage_conflicting else (
                MissingInformationAction.REVIEW if stage.status == DataStatus.PENDING else MissingInformationAction.OBTAIN
            ),
            source="structural_rule",
            field_path="stage",
            source_segment_ids=_segments_from_fact(stage),
        ))

    ps = case.performance_status
    if ps is None or _status_unresolved(ps.status) or ps.value in {None, ""}:
        availability = "not_documented" if ps is None else ps.status.value
        items.append(_make_item(
            field="performance status",
            category="performance_status",
            priority=MissingInformationPriority.HIGH,
            reason="Performance status is unresolved and can affect treatment intensity, tolerability assessment, and trial screening.",
            availability=availability,
            recommendation_blocking=False,
            action=MissingInformationAction.OBTAIN,
            source="structural_rule",
            field_path="performance_status",
            source_segment_ids=[] if ps is None else _segments_from_fact(ps),
        ))

    state_text = _norm(case.disease_state.value)
    relapsed_like = any(token in state_text for token in ("relapsed", "refractory", "progressive", "progression"))
    if relapsed_like and not case.treatments:
        items.append(_make_item(
            field="prior treatment history",
            category="treatment_history",
            priority=MissingInformationPriority.CRITICAL,
            reason="Relapsed, refractory, or progressive disease is represented without prior treatment history.",
            availability="not_documented",
            recommendation_blocking=True,
            action=MissingInformationAction.OBTAIN,
            source="structural_rule",
            field_path="treatments",
        ))

    question_text = _norm(case.clinical_question.question_type) + " " + _norm(case.clinical_question.question)
    trial_or_treatment = any(token in question_text for token in ("treatment", "therapy", "trial", "relapsed", "refractory", "management"))
    if trial_or_treatment and case.disease_program == "hematologic_malignancy" and not case.molecular_findings:
        items.append(_make_item(
            field="molecular/cytogenetic characterization",
            category="molecular",
            priority=MissingInformationPriority.MODERATE,
            reason="No molecular or cytogenetic findings are represented for a treatment- or trial-oriented hematologic malignancy question.",
            availability="not_documented",
            recommendation_blocking=False,
            action=MissingInformationAction.REVIEW,
            source="structural_rule",
            field_path="molecular_findings",
        ))

    return items


def _conflict_items(case: CancerTumorBoardCase) -> list[MissingInformationItem]:
    items: list[MissingInformationItem] = []
    for idx, conflict in enumerate(case.conflicts):
        if conflict.resolution_status != "unresolved":
            continue
        priority = MissingInformationPriority.CRITICAL if conflict.severity == "critical" else (
            MissingInformationPriority.HIGH if conflict.severity == "high" else MissingInformationPriority.MODERATE
        )
        blocking = conflict.severity in {"high", "critical"}
        items.append(_make_item(
            field=f"resolve conflict: {conflict.field}",
            category="conflict_resolution",
            priority=priority,
            reason=f"Conflicting source values remain unresolved: {conflict.value_a!r} versus {conflict.value_b!r}.",
            availability="conflicting",
            recommendation_blocking=blocking,
            action=MissingInformationAction.RESOLVE_CONFLICT,
            source="conflict_rule",
            field_path=f"conflicts[{idx}]",
            source_segment_ids=conflict.source_segment_ids,
        ))
    return items


def _deduplicate(items: list[MissingInformationItem]) -> list[MissingInformationItem]:
    # Keep the highest-priority representation of a semantically equivalent gap.
    best: dict[tuple[str, str], MissingInformationItem] = {}
    rank = {"low": 1, "moderate": 2, "high": 3, "critical": 4}
    for item in items:
        key = (_norm(item.field), item.category)
        current = best.get(key)
        if current is None:
            best[key] = item
            continue
        if rank[item.priority.value] > rank[current.priority.value]:
            best[key] = item
        elif rank[item.priority.value] == rank[current.priority.value] and item.recommendation_blocking and not current.recommendation_blocking:
            best[key] = item
    return sorted(
        best.values(),
        key=lambda x: (-x.priority_score, not x.recommendation_blocking, x.category, _norm(x.field), x.item_id),
    )


def run_missing_information(case: CancerTumorBoardCase) -> MissingInformationReport:
    """Identify unresolved information without inventing or repairing patient facts.

    The agent is deterministic. It reads only the canonical case and produces a
    prioritized information-gap report for downstream routing and human review.
    """
    items = _deduplicate(
        _existing_missing_items(case)
        + _structural_items(case)
        + _conflict_items(case)
    )
    blocking_count = sum(item.recommendation_blocking for item in items)
    critical_count = sum(item.priority == MissingInformationPriority.CRITICAL for item in items)
    high_count = sum(item.priority == MissingInformationPriority.HIGH for item in items)
    moderate_count = sum(item.priority == MissingInformationPriority.MODERATE for item in items)
    low_count = sum(item.priority == MissingInformationPriority.LOW for item in items)

    if blocking_count:
        disposition = MissingInformationDisposition.BLOCKED
    elif items:
        disposition = MissingInformationDisposition.CONDITIONAL
    else:
        disposition = MissingInformationDisposition.READY

    if disposition == MissingInformationDisposition.READY:
        summary = "No unresolved information gaps were identified by the current deterministic rule set."
    elif disposition == MissingInformationDisposition.BLOCKED:
        summary = f"{len(items)} unresolved information item(s) identified; {blocking_count} block specialist routing."
    else:
        summary = f"{len(items)} unresolved information item(s) identified; none currently block specialist routing."

    return MissingInformationReport(
        case_id=case.case_id,
        disposition=disposition,
        items=items,
        blocking_count=blocking_count,
        critical_count=critical_count,
        high_count=high_count,
        moderate_count=moderate_count,
        low_count=low_count,
        safe_to_route_to_specialists=blocking_count == 0,
        requires_human_review=bool(items),
        summary=summary,
    )
