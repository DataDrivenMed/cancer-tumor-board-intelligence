from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from schemas.case import CancerTumorBoardCase
from schemas.consensus import ConsensusReport
from schemas.red_team import ClinicalRedTeamReport
from schemas.tumor_board_brief import BriefItem, BriefSection, TumorBoardIntelligenceBrief


AGENT_ID = "tumor_board_brief"
AGENT_VERSION = "1.0.0"


def _value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, Mapping):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _list(obj: Any, key: str) -> list[Any]:
    return list(_value(obj, key, []) or [])


def _status(obj: Any) -> str:
    value = _value(obj, "status", "unknown")
    return str(getattr(value, "value", value))


def _source_refs_from_provenance(provenance: list[Any]) -> list[str]:
    refs: list[str] = []
    for prov in provenance:
        document_id = str(_value(prov, "document_id", "") or "").strip()
        if document_id:
            refs.append(document_id)
        for segment_id in _list(prov, "source_segment_ids"):
            segment = str(segment_id).strip()
            if segment:
                refs.append(segment)
    return list(dict.fromkeys(refs))


def _fact_item(label: str, fact: Any) -> BriefItem:
    if fact is None:
        return BriefItem(label=label, value="Not represented", epistemic_label="UNKNOWN")
    value = _value(fact, "value", None)
    status = str(getattr(_value(fact, "status", "unknown"), "value", _value(fact, "status", "unknown")))
    info_type = str(getattr(_value(fact, "information_type", "observed"), "value", _value(fact, "information_type", "observed")))
    rendered = "Not represented" if value is None or str(value).strip() == "" else str(value)
    return BriefItem(
        label=label,
        value=rendered,
        epistemic_label=info_type.upper(),
        source_refs=_source_refs_from_provenance(_list(fact, "provenance")),
        limitations=[] if status == "confirmed" else [f"Data status: {status}"],
    )


def _generic_text(obj: Any, preferred_keys: list[str]) -> str:
    for key in preferred_keys:
        value = _value(obj, key, None)
        if value not in (None, "", [], {}):
            if isinstance(value, list):
                return "; ".join(str(x) for x in value)
            return str(value)
    if hasattr(obj, "model_dump"):
        data = obj.model_dump(mode="json")
    elif isinstance(obj, Mapping):
        data = dict(obj)
    else:
        return str(obj)
    compact = []
    for key, value in data.items():
        if value not in (None, "", [], {}, False):
            compact.append(f"{key}={value}")
    return "; ".join(compact) if compact else "Structured finding present"


def render_tumor_board_brief(
    case: CancerTumorBoardCase,
    specialist_outputs: Mapping[str, Any],
    red_team_report: ClinicalRedTeamReport,
    consensus_report: ConsensusReport,
) -> TumorBoardIntelligenceBrief:
    """Render a source-traceable tumor-board brief without generating new clinical claims.

    This is a deterministic presentation transformer. It may display canonical facts,
    specialist outputs within their existing claim gates, Red Team challenges, and
    Consensus candidates. It does not use an LLM, model memory, or external retrieval.
    """
    sections: list[BriefSection] = []

    snapshot_items = [
        BriefItem(label="Case ID", value=case.case_id, epistemic_label="OBSERVED"),
        BriefItem(label="Age", value=str(case.age) if case.age is not None else "Not represented", epistemic_label="OBSERVED"),
        BriefItem(label="Sex", value=case.sex or "Not represented", epistemic_label="OBSERVED"),
        _fact_item("Diagnosis", case.diagnosis),
        _fact_item("Disease state", case.disease_state),
        _fact_item("Performance status", case.performance_status),
    ]
    sections.append(BriefSection(section_id="patient_snapshot", title="Patient Snapshot", items=snapshot_items))

    treatment_items: list[BriefItem] = []
    for episode in case.treatments:
        status = str(getattr(episode.treatment_status, "value", episode.treatment_status))
        parts = [episode.regimen, f"status={status}"]
        if episode.line_of_therapy is not None:
            parts.append(f"line={episode.line_of_therapy}")
        if episode.best_response:
            parts.append(f"best response={episode.best_response}")
        treatment_items.append(
            BriefItem(
                label=episode.episode_id,
                value="; ".join(parts),
                epistemic_label="OBSERVED",
                source_refs=_source_refs_from_provenance(episode.provenance),
                limitations=["Treatment status remains unknown"] if status == "unknown" else [],
            )
        )
    sections.append(
        BriefSection(
            section_id="treatment_timeline",
            title="Prior Treatment Timeline",
            items=treatment_items,
            section_note="No treatment episode is inferred when it is absent from the canonical case.",
        )
    )

    pathology_items = [_fact_item(f"Pathology {i+1}", fact) for i, fact in enumerate(case.pathology)]
    sections.append(BriefSection(section_id="pathology", title="Pathology", items=pathology_items))

    molecular_items: list[BriefItem] = []
    for finding in case.molecular_findings:
        alteration = finding.hgvs_p or finding.hgvs_c or finding.alteration_type or "alteration not specified"
        molecular_items.append(
            BriefItem(
                label=finding.gene,
                value=alteration,
                epistemic_label="OBSERVED",
                source_refs=_source_refs_from_provenance(finding.provenance),
            )
        )
    sections.append(BriefSection(section_id="molecular_profile", title="Molecular Profile", items=molecular_items))

    sections.append(
        BriefSection(
            section_id="clinical_question",
            title="Current Clinical Question",
            items=[BriefItem(label=case.clinical_question.question_type, value=case.clinical_question.question, epistemic_label="OBSERVED")],
        )
    )

    missing_items = [
        BriefItem(
            label=item.field,
            value=item.reason,
            epistemic_label="UNKNOWN",
            limitations=["Recommendation blocking"] if item.recommendation_blocking else [],
        )
        for item in case.missing_items
    ]
    conflict_items = [
        BriefItem(
            label=conflict.field,
            value=f"Conflict: {conflict.value_a} vs {conflict.value_b}",
            epistemic_label="CONFLICTING",
            source_refs=list(conflict.source_segment_ids),
            limitations=[f"Severity: {conflict.severity}; resolution: {conflict.resolution_status}"],
        )
        for conflict in case.conflicts
    ]
    sections.append(
        BriefSection(
            section_id="decision_critical_information",
            title="Decision-Critical Information",
            items=missing_items + conflict_items,
            section_note="Missing, pending, and conflicting information is preserved rather than inferred.",
        )
    )

    guideline = specialist_outputs.get("guideline")
    guideline_items: list[BriefItem] = []
    if guideline is not None:
        for match in _list(guideline, "matched_guidance"):
            source_type = str(getattr(_value(match, "source_type", ""), "value", _value(match, "source_type", "")))
            guideline_items.append(
                BriefItem(
                    label=str(_value(match, "source_title", source_type) or source_type),
                    value=str(_value(match, "recommendation_text", "") or ""),
                    epistemic_label="GUIDELINE-SUPPORTED" if source_type in {"formal_guideline", "consensus_guideline"} else "CLINICALLY-ESTABLISHED",
                    source_refs=[str(_value(match, "source_id", "")), str(_value(match, "recommendation_id", ""))],
                    limitations=[f"Source type: {source_type}", f"Locator: {_value(match, 'source_locator', 'not stated')}"],
                )
            )
    sections.append(
        BriefSection(
            section_id="guideline_analysis",
            title="Guideline Analysis",
            items=guideline_items,
            section_note="Authoritative evidence summaries remain distinct from formal or consensus guidelines.",
        )
    )

    literature = specialist_outputs.get("literature")
    literature_items: list[BriefItem] = []
    if literature is not None:
        for article in _list(literature, "articles"):
            literature_items.append(
                BriefItem(
                    label=f"PMID {str(_value(article, 'pmid', 'unknown'))}",
                    value=str(_value(article, "title", "Untitled PubMed record")),
                    epistemic_label="EMERGING-CLINICAL",
                    source_refs=[f"PMID:{str(_value(article, 'pmid', 'unknown'))}"],
                    limitations=["Retrieved literature record is not itself a verified clinical recommendation."],
                )
            )
    sections.append(BriefSection(section_id="current_evidence", title="Relevant Current Evidence", items=literature_items))

    molecular_report = specialist_outputs.get("molecular")
    translational_report = specialist_outputs.get("translational")
    mt_items: list[BriefItem] = []
    if molecular_report is not None:
        for item in _list(molecular_report, "interpretations"):
            mt_items.append(
                BriefItem(
                    label=f"Molecular: {_value(item, 'gene', 'finding')}",
                    value=_generic_text(item, ["alteration", "clinical_actionability"]),
                    epistemic_label="CLINICALLY-ESTABLISHED" if bool(_value(item, "can_support_clinical_actionability_claim", False)) else "UNKNOWN",
                    source_refs=[str(x) for x in _list(item, "matched_evidence_ids")],
                    limitations=["Molecular match does not by itself establish treatment eligibility."],
                )
            )
    if translational_report is not None:
        for item in _list(translational_report, "findings"):
            mt_items.append(
                BriefItem(
                    label=f"Translational: {_value(item, 'subject', 'finding')}",
                    value=_generic_text(item, ["mechanisms", "interventions", "directions"]),
                    epistemic_label="TRANSLATIONAL",
                    source_refs=[str(x) for x in _list(item, "matched_evidence_ids")],
                    limitations=["Mechanistic or preclinical evidence does not independently establish clinical actionability."],
                )
            )
    sections.append(BriefSection(section_id="molecular_translational", title="Molecular / Translational Interpretation", items=mt_items))

    trials = specialist_outputs.get("clinical_trials")
    trial_items: list[BriefItem] = []
    if trials is not None:
        for match in _list(trials, "matches"):
            trial_items.append(
                BriefItem(
                    label=str(_value(match, "nct_id", "Unknown trial")),
                    value=str(_value(match, "title", "Possible trial match")),
                    epistemic_label="EMERGING-CLINICAL",
                    source_refs=[str(_value(match, "nct_id", ""))],
                    limitations=["Possible match only; patient-specific eligibility is not determined."],
                )
            )
    sections.append(BriefSection(section_id="clinical_trials", title="Clinical Trial Options", items=trial_items))

    strategy_items: list[BriefItem] = []
    if consensus_report.safe_to_render_decision_support:
        for index, candidate in enumerate(consensus_report.candidates):
            strategy_items.append(
                BriefItem(
                    label="Primary management candidate" if index == 0 else f"Alternative {index}",
                    value=candidate.strategy,
                    epistemic_label="GUIDELINE-SUPPORTED",
                    source_refs=[candidate.source_record_id],
                    limitations=(candidate.conditions + candidate.exclusions + ["Decision support only; requires tumor-board adjudication."]),
                )
            )
    else:
        strategy_items.append(
            BriefItem(
                label="Management strategy",
                value="WITHHELD",
                epistemic_label="UNKNOWN",
                limitations=[consensus_report.abstention_reason or "Consensus did not permit management-candidate rendering."],
            )
        )
    sections.append(BriefSection(section_id="management_strategy", title="Management Strategy and Alternatives", items=strategy_items))

    safety = specialist_outputs.get("safety")
    safety_items: list[BriefItem] = []
    if safety is not None:
        for finding in _list(safety, "findings"):
            safety_items.append(
                BriefItem(
                    label="Safety finding",
                    value=_generic_text(finding, ["safety_issue", "issue", "contraindication", "monitoring_requirement"]),
                    epistemic_label="CLINICALLY-ESTABLISHED" if bool(_value(safety, "can_support_safety_claim", False)) else "UNKNOWN",
                    limitations=["Recommendation blocking"] if bool(_value(safety, "recommendation_blocking", False)) else [],
                )
            )
    sections.append(BriefSection(section_id="safety", title="Contraindications / Safety", items=safety_items))

    red_items = [
        BriefItem(
            label=finding.code,
            value=finding.issue,
            epistemic_label="INTERPRETED",
            limitations=[finding.effect_on_recommendation] + (["Recommendation blocking"] if finding.recommendation_blocking else []),
        )
        for finding in red_team_report.findings
    ]
    sections.append(BriefSection(section_id="red_team", title="Red-Team Challenge", items=red_items))

    disagreement_items: list[BriefItem] = []
    for channel in consensus_report.evidence_channels:
        if channel.state.value in {"limiting", "unavailable", "non_decisional"}:
            disagreement_items.append(
                BriefItem(
                    label=channel.agent_id,
                    value=channel.rationale,
                    epistemic_label="INTERPRETED",
                    limitations=[f"Agent status: {channel.status}"],
                )
            )
    sections.append(BriefSection(section_id="agent_disagreements", title="Agent Disagreements / Evidence Boundaries", items=disagreement_items))

    uncertainty_items = [BriefItem(label="Major uncertainty", value=x, epistemic_label="UNKNOWN") for x in consensus_report.major_uncertainties]
    uncertainty_items.extend(BriefItem(label="Red Team challenge", value=x, epistemic_label="INTERPRETED") for x in consensus_report.red_team_challenges)
    sections.append(BriefSection(section_id="uncertainty", title="Uncertainty", items=uncertainty_items))

    change_items = [BriefItem(label="Discussion priority", value=x, epistemic_label="INTERPRETED") for x in consensus_report.discussion_priorities]
    sections.append(BriefSection(section_id="what_changes_recommendation", title="What Could Change the Recommendation", items=change_items))

    source_refs = []
    for section in sections:
        for item in section.items:
            source_refs.extend(ref for ref in item.source_refs if ref)
    source_refs = list(dict.fromkeys(source_refs))
    sections.append(
        BriefSection(
            section_id="audit_trace",
            title="Evidence Sources / Audit Trace",
            items=[
                BriefItem(label="Source trace count", value=str(len(source_refs)), epistemic_label="DERIVED"),
                BriefItem(label="Specialist statuses", value="; ".join(f"{agent_id}={_status(output)}" for agent_id, output in specialist_outputs.items()), epistemic_label="DERIVED"),
                BriefItem(label="Red Team", value=f"{red_team_report.disposition.value}; blocking={red_team_report.blocking_count}", epistemic_label="DERIVED"),
                BriefItem(label="Consensus", value=f"{consensus_report.decision_state}; strength={consensus_report.decision_support_strength}", epistemic_label="DERIVED"),
            ],
            section_note="Reasoning chain-of-thought is not stored or displayed; the audit trace contains structured facts, source references, statuses, and decision gates only.",
        )
    )

    warnings: list[str] = []
    if not consensus_report.safe_to_render_decision_support:
        warnings.append("Management recommendation is withheld by the Consensus Engine.")
    if red_team_report.blocking_count:
        warnings.append("Recommendation-blocking Clinical Red Team finding(s) remain unresolved.")
    if any(item.recommendation_blocking for item in case.missing_items):
        warnings.append("Recommendation-blocking case information remains missing.")

    status = "abstain" if consensus_report.decision_state == "abstain" else ("completed_with_limitations" if warnings or red_team_report.findings else "completed")
    return TumorBoardIntelligenceBrief(
        case_id=case.case_id,
        status=status,
        decision_state=consensus_report.decision_state,
        decision_support_strength=consensus_report.decision_support_strength,
        sections=sections,
        critical_warnings=warnings,
        source_trace_count=len(source_refs),
        safe_to_display=True,
        decision_support_only=True,
        summary=(
            "Structured tumor-board intelligence brief rendered from canonical case facts, bounded specialist outputs, "
            "Clinical Red Team findings, and Consensus Engine gates. No new clinical claim was generated by the renderer."
        ),
    )
