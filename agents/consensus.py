from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from schemas.agent import RoutingDecision
from schemas.case import CancerTumorBoardCase
from schemas.consensus import (
    ConsensusCandidate,
    ConsensusDisposition,
    ConsensusEvidenceChannel,
    ConsensusReport,
    EvidenceChannelState,
)
from schemas.red_team import ClinicalRedTeamReport, RedTeamDisposition


AGENT_ID = "consensus"
AGENT_VERSION = "1.0.0"

_BLOCKING_STATUSES = {
    "insufficient_input",
    "source_unavailable",
    "verification_failed",
    "schema_error",
    "tool_failure",
    "abstain_domain",
    "escalate_human",
}


def _value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _status(obj: Any) -> str:
    value = _value(obj, "status", "unknown")
    return str(getattr(value, "value", value))


def _bool(obj: Any, key: str) -> bool:
    return bool(_value(obj, key, False))


def _list(obj: Any, key: str) -> list[Any]:
    return list(_value(obj, key, []) or [])


def _channel_state(agent_id: str, output: Any) -> ConsensusEvidenceChannel:
    status = _status(output)
    if status in _BLOCKING_STATUSES:
        return ConsensusEvidenceChannel(
            agent_id=agent_id,
            state=EvidenceChannelState.UNAVAILABLE,
            status=status,
            supports_decision=False,
            rationale="Evidence channel is unavailable, failed verification, or requires escalation.",
        )
    if status == "no_evidence_found":
        return ConsensusEvidenceChannel(
            agent_id=agent_id,
            state=EvidenceChannelState.LIMITING,
            status=status,
            supports_decision=False,
            rationale="Bounded no-result is preserved as a limitation and is not negative evidence.",
        )

    support_flags = {
        "guideline": "can_support_guideline_claim",
        "molecular": "can_support_clinical_actionability_claim",
        "translational": "can_support_mechanistic_claim",
        "clinical_trials": "can_support_trial_match_claim",
        "safety": "can_support_safety_claim",
    }
    flag = support_flags.get(agent_id)
    if flag is not None and _bool(output, flag):
        decisional = agent_id in {"guideline", "molecular", "safety"}
        return ConsensusEvidenceChannel(
            agent_id=agent_id,
            state=EvidenceChannelState.SUPPORTIVE if decisional else EvidenceChannelState.NON_DECISIONAL,
            status=status,
            supports_decision=decisional,
            rationale=(
                "Verified channel can contribute bounded decision support."
                if decisional
                else "Verified channel is informative but cannot independently establish a treatment recommendation."
            ),
        )

    return ConsensusEvidenceChannel(
        agent_id=agent_id,
        state=EvidenceChannelState.NON_DECISIONAL,
        status=status,
        supports_decision=False,
        rationale="Channel completed but does not expose a verified decision-support gate for recommendation synthesis.",
    )


def _guideline_candidates(output: Any) -> list[ConsensusCandidate]:
    if output is None or not _bool(output, "can_support_guideline_claim"):
        return []
    candidates: list[ConsensusCandidate] = []
    for match in _list(output, "matched_guidance"):
        source_type = str(getattr(_value(match, "source_type", ""), "value", _value(match, "source_type", "")))
        if source_type not in {"formal_guideline", "consensus_guideline"}:
            continue
        recommendation_text = str(_value(match, "recommendation_text", "") or "").strip()
        excerpt = str(_value(match, "source_excerpt", "") or "").strip()
        if not recommendation_text or not excerpt:
            continue
        candidates.append(
            ConsensusCandidate(
                candidate_id=f"guideline:{_value(match, 'recommendation_id', 'unknown')}",
                strategy=recommendation_text,
                source_agent_id="guideline",
                source_record_id=str(_value(match, "recommendation_id", "unknown")),
                source_type=source_type,
                evidence_strength=str(getattr(_value(match, "strength", None), "value", _value(match, "strength", None))) if _value(match, "strength", None) is not None else None,
                source_excerpt=excerpt,
                source_locator=_value(match, "source_locator", None),
                conditions=[str(x) for x in _list(match, "conditions")],
                exclusions=[str(x) for x in _list(match, "exclusions")],
            )
        )
    return candidates


def run_consensus(
    case: CancerTumorBoardCase,
    routing: RoutingDecision,
    specialist_outputs: Mapping[str, Any],
    red_team_report: ClinicalRedTeamReport,
) -> ConsensusReport:
    """Integrate verified specialist outputs without agent voting.

    v1 only permits formal/consensus guideline recommendations to become explicit
    management candidates. Molecular, translational, trial, literature, and safety
    outputs can constrain, contextualize, or block those candidates, but they do not
    become treatment recommendations by themselves.
    """
    channels = [
        _channel_state(agent_id, specialist_outputs[agent_id])
        for agent_id in routing.selected_agents
        if agent_id in specialist_outputs
    ]
    challenges = [finding.issue for finding in red_team_report.findings]
    uncertainties = [item.field for item in case.missing_items if item.importance in {"high", "critical"}]

    if red_team_report.disposition == RedTeamDisposition.BLOCKED or not red_team_report.safe_for_consensus:
        return ConsensusReport(
            case_id=case.case_id,
            status="escalate_human",
            disposition=ConsensusDisposition.ABSTAIN,
            decision_state="abstain",
            decision_support_strength="insufficient",
            evidence_channels=channels,
            red_team_challenges=challenges,
            major_uncertainties=uncertainties,
            discussion_priorities=[
                finding.effect_on_recommendation
                for finding in red_team_report.findings
                if finding.recommendation_blocking
            ],
            summary="Consensus withheld because the Clinical Red Team identified recommendation-blocking findings.",
            abstention_reason="Recommendation-blocking Red Team findings must be resolved or explicitly adjudicated before consensus.",
            safe_to_render_decision_support=False,
        )

    guideline = specialist_outputs.get("guideline")
    candidates = _guideline_candidates(guideline)

    required_unavailable = [
        channel.agent_id
        for channel in channels
        if channel.agent_id in set(routing.required_agents) and channel.state == EvidenceChannelState.UNAVAILABLE
    ]
    if required_unavailable:
        return ConsensusReport(
            case_id=case.case_id,
            status="escalate_human",
            disposition=ConsensusDisposition.ABSTAIN,
            decision_state="abstain",
            decision_support_strength="insufficient",
            candidates=candidates,
            evidence_channels=channels,
            red_team_challenges=challenges,
            major_uncertainties=uncertainties,
            discussion_priorities=[f"Restore required evidence channel: {agent_id}" for agent_id in required_unavailable],
            summary="Consensus withheld because one or more required evidence channels are unavailable.",
            abstention_reason="Required evidence channels are unavailable or failed verification.",
            safe_to_render_decision_support=False,
        )

    if not candidates:
        return ConsensusReport(
            case_id=case.case_id,
            status="completed_with_limitations",
            disposition=ConsensusDisposition.ABSTAIN,
            decision_state="abstain",
            decision_support_strength="insufficient",
            evidence_channels=channels,
            red_team_challenges=challenges,
            major_uncertainties=uncertainties,
            discussion_priorities=[
                "Obtain a verified formal or consensus guideline recommendation relevant to the represented case and question.",
                "Preserve molecular, translational, trial, literature, and safety outputs as bounded context rather than converting them into an unsupported management recommendation.",
            ],
            summary="No verified formal or consensus guideline recommendation is available to anchor a management candidate.",
            abstention_reason="Consensus Engine v1 will not generate a management strategy from agent agreement, model memory, translational plausibility, or trial matching alone.",
            safe_to_render_decision_support=False,
        )

    safety = specialist_outputs.get("safety")
    if safety is not None and _bool(safety, "recommendation_blocking"):
        return ConsensusReport(
            case_id=case.case_id,
            status="escalate_human",
            disposition=ConsensusDisposition.ABSTAIN,
            decision_state="abstain",
            decision_support_strength="insufficient",
            candidates=candidates,
            evidence_channels=channels,
            red_team_challenges=challenges,
            major_uncertainties=uncertainties,
            discussion_priorities=["Resolve the recommendation-blocking safety issue before selecting a strategy."],
            summary="Consensus withheld because a recommendation-blocking safety condition remains unresolved.",
            abstention_reason="Safety gate blocks recommendation synthesis.",
            safe_to_render_decision_support=False,
        )

    if len(candidates) == 1:
        decision_state = "preferred_conditional"
        disposition = ConsensusDisposition.CONDITIONAL
        summary = "One verified formal/consensus guideline management candidate is available; it remains conditional on case fit, exclusions, safety, and human tumor-board adjudication."
    else:
        decision_state = "multiple_reasonable_options"
        disposition = ConsensusDisposition.READY
        summary = f"{len(candidates)} verified formal/consensus guideline management candidates are available; the engine does not rank them by agent vote."

    priorities = []
    for candidate in candidates:
        priorities.extend(candidate.conditions)
        priorities.extend(candidate.exclusions)
    priorities.extend(challenges)
    priorities = list(dict.fromkeys(item for item in priorities if item))

    return ConsensusReport(
        case_id=case.case_id,
        status="completed" if not challenges else "completed_with_limitations",
        disposition=disposition,
        decision_state=decision_state,
        decision_support_strength="moderate",
        candidates=candidates,
        evidence_channels=channels,
        red_team_challenges=challenges,
        major_uncertainties=uncertainties,
        discussion_priorities=priorities,
        summary=summary,
        abstention_reason=None,
        safe_to_render_decision_support=True,
    )
