from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from services.governed_chat import answer_governed_question
from orchestration.context import WorkflowContext


def _txt(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if hasattr(value, "value"):
        value = value.value
    text = str(value).strip()
    return text or default


def chat_css() -> None:
    st.markdown(
        """
<style>
.tb-chat-shell{background:#fff;border:1px solid #e6e5e0;border-radius:12px;padding:12px;box-shadow:none;margin-top:8px}
.tb-chat-head{background:#fafaf7;color:#26251e;border:1px solid #efeee8;border-radius:10px;padding:16px}.tb-chat-head strong{font-size:20px;line-height:1.2;display:block;font-weight:400;letter-spacing:-.02em}.tb-chat-head span{font-size:11px;color:#5a5852;line-height:1.55;display:block;margin-top:6px}
.tb-chat-note{font-size:10px;line-height:1.55;color:#5a5852;background:#fff;border:1px solid #e6e5e0;border-radius:8px;padding:9px 10px;margin:8px 0 11px}.tb-chat-note strong{color:#f54e00;font-weight:600}
.tb-turn{margin:12px 0}.tb-user{font-size:11px;font-weight:600;color:#26251e;margin:0 0 6px}.tb-answer{background:#fff;border:1px solid #e6e5e0;border-radius:10px;padding:12px 13px}.tb-status{font:600 9px/13px "JetBrains Mono",ui-monospace,monospace;color:#807d72;text-transform:uppercase;letter-spacing:.09em}.tb-answer-text{font-size:12px;line-height:1.62;color:#5a5852;margin:7px 0 0;white-space:pre-wrap}.tb-block-title{font:600 9px/13px "JetBrains Mono",ui-monospace,monospace;color:#807d72;margin-top:11px;text-transform:uppercase;letter-spacing:.08em}.tb-chip{display:inline-flex;padding:4px 7px;border-radius:999px;background:#fafaf7;color:#5a5852;border:1px solid #e6e5e0;font-size:9px;font-weight:500;margin:4px 4px 0 0}.tb-limit{font-size:10px;line-height:1.5;color:#745c26;background:#fff8e7;border:1px solid #ead6a6;border-radius:8px;padding:8px 9px;margin-top:6px}.tb-change{font-size:10px;line-height:1.5;color:#5a5852;margin-top:4px}
[data-testid="stChatInput"]{background:#f7f7f4!important;border-top:1px solid #e6e5e0!important}
[data-testid="stChatInput"] textarea{background:#fff!important;color:#26251e!important;border:1px solid #cfcdc4!important;border-radius:8px!important}
</style>
""",
        unsafe_allow_html=True,
    )


def _history_for_model(rows: list[dict[str, Any]]) -> list[dict[str, str]]:
    history: list[dict[str, str]] = []
    for row in rows[-6:]:
        history.append({"role": "user", "content": _txt(row.get("question"))})
        history.append({"role": "assistant", "content": _txt(row.get("answer"))})
    return history


def _render_answer(row: dict[str, Any]) -> None:
    agents = row.get("agents_consulted", []) or []
    evidence = row.get("evidence_used", []) or []
    limitations = row.get("limitations", []) or []
    changes = row.get("what_could_change", []) or []
    st.markdown(f'<div class="tb-turn"><div class="tb-user">You: {escape(_txt(row.get("question")))}</div><div class="tb-answer"><div class="tb-status">{escape(_txt(row.get("status"), "Case-grounded synthesis"))}</div><div class="tb-answer-text">{escape(_txt(row.get("answer")))}</div>', unsafe_allow_html=True)
    if agents:
        st.markdown('<div class="tb-block-title">Agents consulted</div>' + ''.join(f'<span class="tb-chip">{escape(_txt(x))}</span>' for x in agents), unsafe_allow_html=True)
    if evidence:
        st.markdown('<div class="tb-block-title">Evidence used</div>' + ''.join(f'<span class="tb-chip">{escape(_txt(x))}</span>' for x in evidence), unsafe_allow_html=True)
    if limitations:
        st.markdown('<div class="tb-block-title">Limitations</div>' + ''.join(f'<div class="tb-limit">{escape(_txt(x))}</div>' for x in limitations[:6]), unsafe_allow_html=True)
    if changes:
        st.markdown('<div class="tb-block-title">What could change the answer</div>' + ''.join(f'<div class="tb-change">• {escape(_txt(x))}</div>' for x in changes[:6]), unsafe_allow_html=True)
    st.markdown('</div></div>', unsafe_allow_html=True)


def render_governed_chat(
    result: dict[str, Any],
    case: Any,
    *,
    key_prefix: str = "brief",
    context: WorkflowContext | None = None,
) -> None:
    chat_css()
    st.markdown('<div class="tb-chat-shell"><div class="tb-chat-head"><strong>Ask Tumor Board</strong><span>Use this panel to ask follow-up questions about the current structured case and the evidence that the governed workflow actually produced. It is not a general oncology chatbot and does not create a separate treatment recommendation from unrestricted model memory.</span></div><div class="tb-chat-note"><strong>Good questions:</strong> What is the best-supported strategy and why? What information is missing? Which trials surfaced? What did the Challenge Review question? What could change the decision?</div></div>', unsafe_allow_html=True)

    hist_key = f"{key_prefix}_governed_chat"
    if hist_key not in st.session_state:
        st.session_state[hist_key] = []

    prompts = [
        "Summarize for tumor board",
        "What is the best-supported treatment strategy and why?",
        "Which clinical trials matched and why?",
        "What is missing or uncertain?",
        "What did the Clinical Red Team challenge?",
        "What could change the decision?",
    ]
    if not st.session_state[hist_key]:
        cols = st.columns(2, gap="small")
        for i, prompt in enumerate(prompts):
            with cols[i % 2]:
                if st.button(prompt, key=f"{key_prefix}_smart_prompt_{i}", use_container_width=True):
                    response = answer_governed_question(
                        prompt,
                        result,
                        case,
                        history=[],
                        context=context,
                    )
                    response["question"] = prompt
                    st.session_state[hist_key].append(response)
                    st.rerun()

    for row in st.session_state[hist_key][-6:]:
        _render_answer(row)

    question = st.chat_input("Ask a question about this case and its governed evidence", key=f"{key_prefix}_smart_chat_input")
    if question:
        history = _history_for_model(st.session_state[hist_key])
        with st.spinner("Reviewing the governed case and relevant specialist outputs..."):
            response = answer_governed_question(
                question,
                result,
                case,
                history=history,
                context=context,
            )
        response["question"] = question
        st.session_state[hist_key].append(response)
        st.rerun()
