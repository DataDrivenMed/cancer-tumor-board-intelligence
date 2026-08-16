from __future__ import annotations

import json
import os
from typing import Any

from services.model_gateway import ModelGatewayError, structured_json_response_raw


CHAT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "status": {
            "type": "string",
            "enum": ["Evidence-backed", "Case-grounded answer", "Evidence incomplete", "Unable to answer from current case evidence"],
        },
        "answer": {"type": "string"},
        "supporting_sources": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 8,
        },
        "limitations": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 6,
        },
    },
    "required": ["status", "answer", "supporting_sources", "limitations"],
}


def _primitive(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(k): _primitive(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_primitive(v) for v in value]
    if hasattr(value, "value"):
        return _primitive(value.value)
    return str(value)


def build_governed_chat_context(result: dict[str, Any], case: Any) -> dict[str, Any]:
    """Create the bounded record that the conversational reasoning layer may use.

    Deliberately excludes secrets, raw chain-of-thought, and unrestricted external
    knowledge. The model may synthesize only across this supplied record.
    """
    outputs = result.get("specialist_outputs", {}) or {}
    context = {
        "case": _primitive(case),
        "case_integrity_report": _primitive(result.get("case_integrity_report")),
        "missing_information_report": _primitive(result.get("missing_information_report")),
        "specialist_outputs": _primitive(outputs),
        "red_team_report": _primitive(result.get("red_team_report")),
        "consensus_report": _primitive(result.get("consensus_report")),
        "final_decision": _primitive(result.get("final_decision")),
        "tumor_board_brief": _primitive(result.get("tumor_board_brief")),
    }
    return context


def _fallback(question: str, context: dict[str, Any]) -> dict[str, Any]:
    q = " ".join(question.lower().split())
    brief = context.get("tumor_board_brief") or {}
    consensus = context.get("consensus_report") or {}
    final = context.get("final_decision") or {}
    missing = context.get("missing_information_report") or {}
    outputs = context.get("specialist_outputs") or {}

    def summary(obj: Any) -> str:
        if isinstance(obj, dict):
            value = obj.get("summary")
            return str(value).strip() if value else ""
        return ""

    sources: list[str] = []
    if any(term in q for term in ("summar", "overview", "30 second")):
        parts = []
        case = context.get("case") or {}
        diagnosis = ((case.get("diagnosis") or {}).get("value") if isinstance(case, dict) else None)
        state = ((case.get("disease_state") or {}).get("value") if isinstance(case, dict) else None)
        stage = ((case.get("stage") or {}).get("value") if isinstance(case, dict) else None)
        if diagnosis:
            parts.append(f"Diagnosis: {diagnosis}.")
        if state or stage:
            parts.append(f"Disease status: {'; '.join(str(x) for x in (state, stage) if x)}.")
        if summary(consensus):
            parts.append(summary(consensus))
            sources.append("Consensus report")
        elif summary(final):
            parts.append(summary(final))
            sources.append("Final decision")
        elif summary(brief):
            parts.append(summary(brief))
            sources.append("Tumor board brief")
        if summary(missing):
            parts.append(f"Key uncertainty: {summary(missing)}")
            sources.append("Missing Information Agent")
        return {
            "status": "Case-grounded answer" if parts else "Evidence incomplete",
            "answer": " ".join(parts) if parts else "The governed record does not yet contain enough synthesized output for a tumor-board summary.",
            "supporting_sources": sources,
            "limitations": ["Reasoning model unavailable; deterministic governed fallback used."],
        }

    if any(term in q for term in ("best treatment", "best therapy", "treatment", "recommend")):
        text = summary(consensus) or summary(final) or summary(brief)
        if text:
            return {
                "status": "Evidence-backed",
                "answer": "The governed record supports the following decision state rather than an unrestricted 'best treatment' claim: " + text,
                "supporting_sources": ["Consensus / final decision"],
                "limitations": ["This answer is limited to the current governed record and does not establish a universally best treatment."],
            }

    if "trial" in q:
        trials = outputs.get("clinical_trials") or outputs.get("clinical_trials_agent")
        if trials:
            return {
                "status": "Evidence-backed",
                "answer": summary(trials) or "A governed clinical-trial output is present; inspect the trial details in the Evidence view.",
                "supporting_sources": ["Clinical Trials Agent"],
                "limitations": ["Trial matching does not establish eligibility."],
            }
        return {
            "status": "Evidence incomplete",
            "answer": "No governed clinical-trial output is available in the current record. Trial retrieval may not yet have run, may have returned no match, or may have been stopped by an earlier gate.",
            "supporting_sources": ["Clinical Trials Agent"],
            "limitations": ["No trial-specific inference was added from model memory."],
        }

    return {
        "status": "Unable to answer from current case evidence",
        "answer": "The current governed record does not support a reliable answer to that question without adding information outside the case and approved evidence.",
        "supporting_sources": [],
        "limitations": ["Reasoning model unavailable or the question is unsupported by the governed record."],
    }


def answer_governed_tumor_board_question(
    question: str,
    result: dict[str, Any],
    case: Any,
    *,
    model: str | None = None,
    auth_token: str | None = None,
    base_url: str | None = None,
    reasoning_effort: str | None = None,
) -> dict[str, Any]:
    context = build_governed_chat_context(result, case)
    model_name = model or os.getenv("MODEL_NAME") or "openai/gpt-oss-120b:fireworks-ai"
    token = auth_token or os.getenv("MODEL_AUTH_TOKEN") or os.getenv("HF_TOKEN")
    endpoint = base_url or os.getenv("MODEL_BASE_URL")
    effort = reasoning_effort or os.getenv("MODEL_REASONING_EFFORT") or "high"

    if not token and not endpoint:
        return _fallback(question, context)

    system = """You are the governed conversational reasoning layer for a pan-oncology tumor-board research decision-support system.

You may reason ONLY from GOVERNED_RECORD supplied by the application. Do not add medical facts, treatment knowledge, guideline claims, trial facts, drug facts, eligibility assumptions, or molecular actionability from memory.

Your job is synthesis, not retrieval. Integrate relevant case facts, approved evidence, specialist outputs, missing-information findings, Challenge Review, consensus, final decision, and the tumor-board brief. Explain relationships and tradeoffs that are explicitly supportable from those objects.

For treatment questions, never claim a universally 'best treatment'. If the governed record contains a preferred or supported strategy, describe it as the best-supported option IN THE CURRENT GOVERNED RECORD, explain why the record supports it, identify alternatives or uncertainty represented in the record, and state what could change the decision. If the record abstains or does not support a preference, say so clearly.

For clinical-trial questions, report only trials actually represented in the governed clinical-trial output and explain why they matched if that information is represented. Always state that matching does not establish eligibility.

For summary questions, produce a useful tumor-board synthesis even if tumor_board_brief.summary is empty by integrating the other governed objects.

Citations/supporting_sources must name only supplied governed objects or source identifiers actually present in the record. Do not invent citations.

Do not reveal hidden chain-of-thought. Provide a concise clinical reasoning summary: conclusion, supporting factors, uncertainties, and decision-changing factors when relevant.

If the record cannot support the requested answer, abstain with status 'Unable to answer from current case evidence' or 'Evidence incomplete'."""

    payload = {
        "QUESTION": question,
        "GOVERNED_RECORD": context,
    }
    try:
        response = structured_json_response_raw(
            model=model_name,
            system_instructions=system,
            user_input=json.dumps(payload, ensure_ascii=False, default=str),
            schema_name="governed_tumor_board_chat",
            json_schema=CHAT_SCHEMA,
            auth_token=token,
            base_url=endpoint,
            reasoning_effort=effort,
        )
        if not response.get("answer"):
            raise ModelGatewayError("Governed chat returned an empty answer.")
        return response
    except Exception:
        return _fallback(question, context)
