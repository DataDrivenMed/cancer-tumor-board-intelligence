from __future__ import annotations

import json
import os
from typing import Any

from orchestration.context import WorkflowContext
from services.model_gateway import ModelGatewayError, structured_json_response_raw


CHAT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": [
                "Case-grounded synthesis",
                "Evidence-backed synthesis",
                "Evidence incomplete",
                "Unable to answer from current case evidence",
            ],
        },
        "answer": {"type": "string"},
        "agents_consulted": {"type": "array", "items": {"type": "string"}},
        "evidence_used": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
        "what_could_change": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "status",
        "answer",
        "agents_consulted",
        "evidence_used",
        "limitations",
        "what_could_change",
    ],
    "additionalProperties": False,
}


def _val(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _txt(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if hasattr(value, "value"):
        value = value.value
    text = str(value).strip()
    return text or default


def _dump(obj: Any) -> Any:
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return {str(k): _dump(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_dump(x) for x in obj]
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if hasattr(obj, "value"):
        return obj.value
    return str(obj)


def _brief_values(result: dict[str, Any], *needles: str) -> list[str]:
    brief = result.get("tumor_board_brief")
    values: list[str] = []
    for section in _val(brief, "sections", []) or []:
        sid = _txt(_val(section, "section_id", "")).lower()
        title = _txt(_val(section, "title", "")).lower()
        if not any(n.lower() in sid or n.lower() in title for n in needles):
            continue
        for item in _val(section, "items", []) or []:
            label = _txt(_val(item, "label", ""))
            value = _txt(_val(item, "value", ""))
            if value:
                values.append(f"{label}: {value}" if label else value)
    return values


def _existing_output(result: dict[str, Any], key: str) -> Any:
    return (result.get("specialist_outputs", {}) or {}).get(key)


def _question_channels(question: str) -> list[str]:
    q = " ".join(question.lower().split())
    channels: list[str] = []
    if any(x in q for x in ["trial", "study", "clinicaltrials", "nct"]):
        channels.append("clinical_trials")
    if any(x in q for x in ["molecular", "mutation", "gene", "variant", "flt3", "egfr", "alk", "braf", "her2", "kras"]):
        channels.append("molecular")
    if any(x in q for x in ["safety", "tox", "contraind", "adverse", "interaction", "dose"]):
        channels.append("safety")
    if any(x in q for x in ["guideline", "standard", "recommended", "best treatment", "best therapy", "treatment", "therapy", "management"]):
        channels.extend(["guideline", "molecular", "safety"])
    if any(x in q for x in ["literature", "study", "publication", "evidence", "data"]):
        channels.append("literature")
    if any(x in q for x in ["translational", "mechanism", "pathway", "biology"]):
        channels.append("translational")
    return list(dict.fromkeys(channels))


def _consult_specialists(
    question: str,
    result: dict[str, Any],
    case: Any,
    *,
    context: WorkflowContext | None = None,
) -> tuple[dict[str, Any], list[str]]:
    outputs = dict(result.get("specialist_outputs", {}) or {})
    consulted: list[str] = []
    if case is None:
        return outputs, consulted

    requested = _question_channels(question)
    if not requested:
        return outputs, consulted

    if context is not None:
        agent_registry = context.agent_registry
    else:
        try:
            from orchestration.workflow import AGENT_REGISTRY
        except Exception:
            return outputs, consulted
        agent_registry = AGENT_REGISTRY

    labels = {
        "guideline": "Guideline Agent",
        "molecular": "Molecular Interpretation Agent",
        "literature": "Literature Agent",
        "translational": "Translational Biology Agent",
        "clinical_trials": "Clinical Trials Agent",
        "safety": "Safety Agent",
    }
    for key in requested:
        existing = outputs.get(key)
        existing_status = _txt(_val(existing, "status", "")).lower()
        # Reuse an already meaningful governed output. Re-run only when the channel
        # is absent or explicitly unavailable/no-match and the runtime agent can try.
        if existing is not None and existing_status not in {"", "source_unavailable", "not selected"}:
            consulted.append(labels.get(key, key))
            continue
        agent = agent_registry.get(key)
        if agent is None:
            continue
        try:
            refreshed = agent.run(case)
            outputs[key] = refreshed
            consulted.append(labels.get(key, key))
        except Exception as exc:
            outputs[key] = {
                "status": "tool_failure",
                "summary": f"{labels.get(key, key)} could not complete an on-demand governed query: {type(exc).__name__}.",
                "limitations": ["No claim was generated from the failed specialist invocation."],
            }
            consulted.append(labels.get(key, key))
    return outputs, consulted


def _trial_answer(output: Any) -> tuple[str, list[str], list[str]]:
    if output is None:
        return (
            "No governed clinical-trial output is available for this case. The system cannot name or imply a trial without a bounded ClinicalTrials.gov result.",
            [],
            ["Trial matching does not establish eligibility."],
        )
    matches = _val(output, "matches", []) or []
    status = _txt(_val(output, "status", ""))
    summary = _txt(_val(output, "summary", ""))
    if not matches:
        return (
            summary or "The governed trial channel did not return a patient-specific trial match.",
            [f"Clinical Trials Agent status: {status or 'not available'}"],
            list(_val(output, "limitations", []) or [])[:5],
        )
    lines: list[str] = []
    evidence: list[str] = []
    for match in matches[:6]:
        nct = _txt(_val(match, "nct_id", "NCT not represented"))
        title = _txt(_val(match, "title", "Untitled study"))
        rationale = _txt(_val(match, "rationale", ""))
        concepts = ", ".join(str(x) for x in (_val(match, "matched_concepts", []) or []))
        line = f"{nct} — {title}"
        if concepts:
            line += f"; matched on {concepts}"
        if rationale:
            line += f". {rationale}"
        lines.append(line)
        evidence.append(nct)
    answer = "Possible governed trial matches in the current record:\n" + "\n".join(f"• {x}" for x in lines)
    return answer, evidence, list(_val(output, "limitations", []) or [])[:5]


def _fallback(question: str, result: dict[str, Any], case: Any, outputs: dict[str, Any], consulted: list[str]) -> dict[str, Any]:
    q = " ".join(question.lower().split())
    diagnosis = _txt(_val(getattr(case, "diagnosis", None), "value", None), "Diagnosis not represented") if case is not None else "Diagnosis not represented"
    disease_state = _txt(_val(getattr(case, "disease_state", None), "value", None), "Disease state not represented") if case is not None else "Disease state not represented"
    stage = _txt(_val(getattr(case, "stage", None), "value", None), "Stage not represented") if case is not None else "Stage not represented"
    consensus = result.get("consensus_report")
    final = result.get("final_decision")
    missing = result.get("missing_information_report")
    red = result.get("red_team_report")
    decision = _txt(_val(final, "decision_state", _val(consensus, "decision_state", "")), "not established")
    consensus_summary = _txt(_val(consensus, "summary", ""))
    abstention = _txt(_val(final, "abstention_reason", ""))
    missing_summary = _txt(_val(missing, "summary", ""))
    change_values = _brief_values(result, "what_changes_recommendation", "what changes", "uncertainty")

    if any(x in q for x in ["trial", "clinical trial", "study"]):
        answer, evidence, limitations = _trial_answer(outputs.get("clinical_trials"))
        return {
            "status": "Evidence-backed synthesis" if evidence else "Evidence incomplete",
            "answer": answer,
            "agents_consulted": list(dict.fromkeys(consulted + ["Clinical Trials Agent"])),
            "evidence_used": evidence,
            "limitations": limitations,
            "what_could_change": change_values[:4],
        }

    if any(x in q for x in ["best treatment", "best therapy", "preferred treatment", "preferred therapy", "what treatment", "what therapy"]):
        strategies = [x for x in _brief_values(result, "management_strategy", "management strategy") if "WITHHELD" not in x.upper()]
        if strategies:
            answer = f"Within the current governed record, the best-supported management strategy is: {strategies[0]}."
            if consensus_summary:
                answer += f" The consensus rationale is: {consensus_summary}"
            if decision and decision != "not established":
                answer += f" The current decision state is {decision.replace('_', ' ')}."
            return {
                "status": "Evidence-backed synthesis",
                "answer": answer,
                "agents_consulted": list(dict.fromkeys(consulted + ["Consensus Engine", "Tumor Board Brief"])),
                "evidence_used": strategies[:3],
                "limitations": ([missing_summary] if missing_summary else []) + ([abstention] if abstention else []),
                "what_could_change": change_values[:5],
            }
        reason = abstention or consensus_summary or "The governed record does not establish a preferred treatment strategy."
        return {
            "status": "Evidence incomplete",
            "answer": f"The system cannot establish a best treatment from the current governed record. {reason}",
            "agents_consulted": list(dict.fromkeys(consulted + ["Consensus Engine", "Tumor Board Brief"])),
            "evidence_used": [],
            "limitations": [x for x in [missing_summary, abstention] if x],
            "what_could_change": change_values[:5],
        }

    if any(x in q for x in ["summar", "overview", "30 second"]):
        molecular = []
        for item in (getattr(case, "molecular_findings", []) or [])[:4] if case is not None else []:
            gene = _txt(getattr(item, "gene", ""))
            alteration = _txt(getattr(item, "alteration_type", ""))
            if gene or alteration:
                molecular.append(" ".join(x for x in [gene, alteration] if x))
        answer = f"{diagnosis}; {disease_state}; {stage}."
        if molecular:
            answer += " Key represented molecular finding(s): " + ", ".join(molecular) + "."
        if consensus_summary:
            answer += " " + consensus_summary
        elif abstention:
            answer += " " + abstention
        else:
            brief_summary = _txt(_val(result.get("tumor_board_brief"), "summary", ""))
            if brief_summary:
                answer += " " + brief_summary
        if missing_summary:
            answer += " Major information-completeness context: " + missing_summary
        return {
            "status": "Case-grounded synthesis",
            "answer": answer,
            "agents_consulted": list(dict.fromkeys(consulted + ["Case representation", "Consensus Engine"])),
            "evidence_used": [x for x in [consensus_summary] if x],
            "limitations": [x for x in [missing_summary] if x],
            "what_could_change": change_values[:5],
        }

    if any(x in q for x in ["missing", "incomplete", "need to know"]):
        return {
            "status": "Case-grounded synthesis",
            "answer": missing_summary or "No missing-information summary is available in the governed record.",
            "agents_consulted": ["Missing Information Agent"],
            "evidence_used": [],
            "limitations": [],
            "what_could_change": change_values[:5],
        }

    if any(x in q for x in ["challenge", "red team", "weakness", "concern"]):
        findings = _val(red, "findings", []) or []
        issues = [_txt(_val(f, "issue", "")) for f in findings[:6] if _txt(_val(f, "issue", ""))]
        return {
            "status": "Case-grounded synthesis",
            "answer": "Challenge Review identified: " + "; ".join(issues) if issues else "No governed Challenge Review finding is available.",
            "agents_consulted": ["Clinical Red Team"],
            "evidence_used": issues,
            "limitations": [],
            "what_could_change": change_values[:5],
        }

    return {
        "status": "Unable to answer from current case evidence",
        "answer": "The current governed record does not support a sufficiently specific answer to that question without introducing information outside the structured case or approved evidence. Ask about the case summary, treatment strategy, evidence, molecular findings, safety, trials, missing information, Challenge Review, or what could change the decision.",
        "agents_consulted": consulted,
        "evidence_used": [],
        "limitations": ["The chat does not use unrestricted model memory to create new patient-specific clinical claims."],
        "what_could_change": change_values[:5],
    }


def answer_governed_question(
    question: str,
    result: dict[str, Any],
    case: Any,
    *,
    history: list[dict[str, str]] | None = None,
    context: WorkflowContext | None = None,
) -> dict[str, Any]:
    """Reason across governed case/evidence objects without creating an independent care recommendation.

    The function may invoke already configured specialist agents on demand. Their outputs remain
    governed by the same source availability, verification, and abstention controls as the main
    workflow. A reasoning model is used only as a synthesis layer over the supplied record.
    """

    outputs, dynamically_consulted = _consult_specialists(
        question,
        result,
        case,
        context=context,
    )
    working_result = dict(result)
    working_result["specialist_outputs"] = outputs

    fallback = _fallback(question, working_result, case, outputs, dynamically_consulted)

    token = os.getenv("MODEL_AUTH_TOKEN") or os.getenv("HF_TOKEN")
    model = os.getenv("MODEL_NAME")
    if not token or not model:
        return fallback

    governed_record = {
        "case": _dump(case),
        "case_integrity_report": _dump(result.get("case_integrity_report")),
        "missing_information_report": _dump(result.get("missing_information_report")),
        "specialist_outputs": _dump(outputs),
        "red_team_report": _dump(result.get("red_team_report")),
        "consensus_report": _dump(result.get("consensus_report")),
        "final_decision": _dump(result.get("final_decision")),
        "tumor_board_brief": _dump(result.get("tumor_board_brief")),
    }
    history_payload = (history or [])[-8:]

    system = """You are the governed conversational synthesis layer for Pan-Oncology Tumor Board Intelligence.
Your job is synthesis and transparent reasoning across the supplied governed record, not free-form medical recall.

NON-NEGOTIABLE RULES
1. Use ONLY the supplied structured case, specialist outputs, verified/attested evidence objects, missing-information report, Challenge Review, consensus, final decision, and tumor-board brief.
2. Do not introduce treatment facts, guideline claims, molecular actionability, safety claims, trial names, eligibility claims, or prognostic claims from model memory.
3. You MAY compare, integrate, and explain relationships among supplied governed objects.
4. If the user asks for the "best" treatment, interpret this as the best-supported strategy WITHIN THE CURRENT GOVERNED RECORD. Never imply a universal best treatment. If the record abstains or does not establish a preferred option, say so and explain why.
5. Trial matching is never trial eligibility. Do not say a patient is eligible unless the governed record explicitly establishes eligibility, which this system generally does not.
6. Mechanistic/translational evidence must not be promoted to clinical actionability.
7. Preserve uncertainty, conflicts, missing information, and abstention. Do not smooth them away.
8. Name the agents/channels actually used. Evidence_used must contain only source identifiers, titles, NCT IDs, or governed brief/agent facts present in the supplied record.
9. For follow-up questions, use conversation history only to resolve references such as "why?" or "what about that option?"; history cannot add new medical facts.
10. If the record cannot support the answer, select the unable/evidence-incomplete status rather than guessing.

Answer in concise tumor-board language. Prefer a direct answer first, then why, limitations, and what could change the conclusion."""

    user = json.dumps(
        {
            "question": question,
            "recent_conversation": history_payload,
            "governed_record": governed_record,
            "deterministic_fallback_interpretation": fallback,
        },
        ensure_ascii=False,
        default=str,
    )
    # Keep the payload bounded for model endpoints with smaller context windows.
    if len(user) > 90000:
        user = user[:90000] + "\n[record truncated at bounded serialization limit]"

    try:
        response = structured_json_response_raw(
            model=model,
            system_instructions=system,
            user_input=user,
            schema_name="governed_tumor_board_chat",
            json_schema=CHAT_SCHEMA,
            auth_token=token,
            base_url=os.getenv("MODEL_BASE_URL"),
            reasoning_effort=os.getenv("MODEL_REASONING_EFFORT", "high"),
        )
    except ModelGatewayError:
        return fallback
    except Exception:
        return fallback

    if dynamically_consulted:
        response["agents_consulted"] = list(dict.fromkeys(dynamically_consulted + list(response.get("agents_consulted", []))))
    return response
