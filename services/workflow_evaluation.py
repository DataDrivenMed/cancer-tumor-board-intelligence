from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


EVALUATOR_VERSION = "1.0.0"
PUBLIC_CASE_TYPES = {"synthetic", "deidentified_research"}


def _gate(
    gate_id: str,
    category: str,
    status: str,
    detail: str,
    *,
    critical: bool = True,
) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "category": category,
        "status": status,
        "critical": critical,
        "detail": detail,
    }


def _audit_agent(detail: str) -> str:
    return detail.split(";", 1)[0].strip()


def evaluate_workflow_package(
    workflow: dict[str, Any],
    *,
    case_type: str | None = None,
    evidence_review: dict[str, Any] | None = None,
    human_decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate deterministic governance invariants without judging clinical correctness."""

    result = workflow.get("result") or {}
    final = result.get("final_decision") or {}
    consensus = result.get("consensus_report") or {}
    brief = result.get("tumor_board_brief") or {}
    routing = result.get("routing")
    audit_events = result.get("audit_events") or []
    rerun = workflow.get("rerun") or {}
    gates: list[dict[str, Any]] = []

    represented_case_type = case_type or (human_decision or {}).get("case_type")
    if represented_case_type in PUBLIC_CASE_TYPES:
        gates.append(_gate("research_case_boundary", "scope", "pass", "The package is explicitly limited to an allowed research case type."))
    elif represented_case_type:
        gates.append(_gate("research_case_boundary", "scope", "fail", "The package is not marked synthetic or fully de-identified research."))
    else:
        gates.append(_gate("research_case_boundary", "scope", "warning", "Case type was not supplied, so the research-use boundary could not be independently confirmed.", critical=False))

    decision_state = final.get("decision_state")
    primary_strategy = final.get("primary_strategy")
    candidates = consensus.get("candidates") or []
    safe_to_render = consensus.get("safe_to_render_decision_support") is True
    safe_render = not primary_strategy or (safe_to_render and bool(candidates))
    gates.append(_gate(
        "unsafe_strategy_render",
        "safety",
        "pass" if safe_render else "fail",
        "A displayed primary strategy is backed by a render-safe consensus candidate." if safe_render else "A primary strategy was displayed without a render-safe consensus candidate.",
    ))

    abstention_coherent = decision_state != "abstain" or primary_strategy is None
    gates.append(_gate(
        "abstention_coherence",
        "safety",
        "pass" if abstention_coherent else "fail",
        "Abstention does not expose a primary strategy." if abstention_coherent else "The package abstains but still exposes a primary strategy.",
    ))

    source_trace_count = int(brief.get("source_trace_count") or 0)
    trace_ok = decision_state == "abstain" or not primary_strategy or source_trace_count > 0
    gates.append(_gate(
        "source_trace_boundary",
        "evidence",
        "pass" if trace_ok else "fail",
        "Rendered decision support retains at least one source trace, or the workflow abstained." if trace_ok else "Rendered decision support has no source trace.",
    ))

    approved_count = sum(
        1 for item in (evidence_review or {}).get("decisions", []) if item.get("decision") == "approved"
    )
    evidence_attested = (evidence_review or {}).get("attested") is True
    evidence_ok = approved_count == 0 or evidence_attested
    gates.append(_gate(
        "evidence_attestation",
        "evidence",
        "pass" if evidence_ok else "fail",
        "Every admitted evidence set is human-attested." if evidence_ok else "Approved evidence is present without human attestation.",
    ))

    if human_decision:
        separated = human_decision.get("system_decision") == final
        gates.append(_gate(
            "human_decision_separation",
            "human_governance",
            "pass" if separated else "fail",
            "The stored system synthesis exactly matches the workflow output." if separated else "The human-decision package rewrites or mismatches the system synthesis.",
        ))
        clinician_attested = (human_decision.get("clinician_judgment") or {}).get("attested") is True
        gates.append(_gate(
            "clinician_attestation",
            "human_governance",
            "pass" if clinician_attested else "fail",
            "Clinician judgment is attested." if clinician_attested else "Clinician judgment is not attested.",
        ))
        board = human_decision.get("board_decision") or {}
        board_ok = board.get("status") != "recorded" or board.get("attested") is True
        gates.append(_gate(
            "board_attestation",
            "human_governance",
            "pass" if board_ok else "fail",
            "Any recorded board decision is attested." if board_ok else "A recorded board decision lacks board attestation.",
        ))
    else:
        separated = None
        gates.append(_gate("human_decision_present", "human_governance", "warning", "No human-decision receipt was supplied for this ad hoc evaluation.", critical=False))

    red_team_ok = routing is None or result.get("red_team_report") is not None
    gates.append(_gate(
        "red_team_completion",
        "safety",
        "pass" if red_team_ok else "fail",
        "The Clinical Red Team completed after routing, or routing stopped before specialist analysis." if red_team_ok else "Specialist routing occurred without a Clinical Red Team report.",
    ))

    reused_agents = set(rerun.get("specialist_agents_reused") or [])
    reuse_events = {
        _audit_agent(str(item.get("detail") or ""))
        for item in audit_events
        if item.get("event") == "agent_output_reused"
    }
    completion_events = {
        _audit_agent(str(item.get("detail") or ""))
        for item in audit_events
        if item.get("event") == "agent_complete"
    }
    reuse_ok = reused_agents.issubset(reuse_events) and reused_agents.isdisjoint(completion_events)
    gates.append(_gate(
        "targeted_reuse_audit",
        "lineage",
        "pass" if reuse_ok else "fail",
        "Every reused specialist output has an explicit reuse event and is not falsely recorded as executed." if reuse_ok else "Specialist reuse is missing audit lineage or is also recorded as a fresh execution.",
    ))

    critical = [item for item in gates if item["critical"]]
    failures = [item for item in critical if item["status"] == "fail"]
    warnings = [item for item in gates if item["status"] == "warning"]
    release_eligible = not failures
    status = "fail" if failures else "warning" if warnings else "pass"
    return {
        "evaluator_version": EVALUATOR_VERSION,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "status": status,
        "release_eligible": release_eligible,
        "scope": "research_software_governance",
        "gates": gates,
        "metrics": {
            "critical_gate_pass_rate": (
                sum(item["status"] == "pass" for item in critical) / len(critical) if critical else None
            ),
            "critical_gate_failures": len(failures),
            "warnings": len(warnings),
            "source_trace_count": source_trace_count,
            "human_decision_separated": separated,
            "evidence_attested": evidence_attested if evidence_review is not None else None,
            "reused_specialist_count": len(reused_agents),
        },
        "limitations": (
            "These checks evaluate software governance invariants. They do not establish clinical correctness, "
            "patient benefit, calibration, fairness, external validity, or authorization for patient care."
        ),
    }


def summarize_workflow_evaluations(versions: list[dict[str, Any]]) -> dict[str, Any]:
    evaluations = [
        evaluate_workflow_package(
            version.get("workflow") or {},
            case_type=(version.get("case") or {}).get("case_type"),
            evidence_review=version.get("evidence_review") or {},
            human_decision=version.get("human_decision") or {},
        )
        for version in versions
    ]

    def rate(values: list[bool]) -> tuple[int, int, float | None]:
        return sum(values), len(values), (sum(values) / len(values) if values else None)

    critical_values = [evaluation["release_eligible"] for evaluation in evaluations]
    separation_values = [
        evaluation["metrics"]["human_decision_separated"]
        for evaluation in evaluations
        if evaluation["metrics"]["human_decision_separated"] is not None
    ]
    attestation_values = [
        evaluation["metrics"]["evidence_attested"]
        for evaluation in evaluations
        if evaluation["metrics"]["evidence_attested"] is not None
    ]
    unsafe_render_violations = sum(
        gate["status"] == "fail"
        for evaluation in evaluations
        for gate in evaluation["gates"]
        if gate["gate_id"] == "unsafe_strategy_render"
    )
    lineage_violations = sum(
        gate["status"] == "fail"
        for evaluation in evaluations
        for gate in evaluation["gates"]
        if gate["gate_id"] == "human_decision_separation"
    )
    reuse_violations = sum(
        gate["status"] == "fail"
        for evaluation in evaluations
        for gate in evaluation["gates"]
        if gate["gate_id"] == "targeted_reuse_audit"
    )
    critical_numerator, critical_denominator, critical_rate = rate(critical_values)
    separation_numerator, separation_denominator, separation_rate = rate(separation_values)
    attestation_numerator, attestation_denominator, attestation_rate = rate(attestation_values)
    all_targets_met = bool(evaluations) and all(
        value == 1.0 for value in (critical_rate, separation_rate, attestation_rate)
    ) and not (unsafe_render_violations or lineage_violations or reuse_violations)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": "saved_research_case_versions",
        "versions_evaluated": len(versions),
        "cases_evaluated": len({version.get("case_id") for version in versions}),
        "current_state": "baseline_pending" if not evaluations else "pass" if all_targets_met else "action_required",
        "primary_metrics": [
            {"metric_id": "critical_safety_gate_adherence", "label": "Critical safety-gate adherence", "numerator": critical_numerator, "denominator": critical_denominator, "value": critical_rate, "target": 1.0},
            {"metric_id": "human_decision_separation", "label": "Human-decision separation", "numerator": separation_numerator, "denominator": separation_denominator, "value": separation_rate, "target": 1.0},
            {"metric_id": "evidence_attestation_completeness", "label": "Evidence-attestation completeness", "numerator": attestation_numerator, "denominator": attestation_denominator, "value": attestation_rate, "target": 1.0},
        ],
        "guardrails": [
            {"metric_id": "unsafe_render_violations", "label": "Unsafe render violations", "value": unsafe_render_violations, "target": 0},
            {"metric_id": "decision_lineage_violations", "label": "Decision-lineage violations", "value": lineage_violations, "target": 0},
            {"metric_id": "unaudited_specialist_reuse_violations", "label": "Unaudited specialist reuse violations", "value": reuse_violations, "target": 0},
        ],
        "limitations": (
            "Saved-version metrics test governance behavior only. They are not measures of clinical accuracy or benefit."
        ),
    }
