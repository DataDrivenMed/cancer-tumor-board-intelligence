from types import SimpleNamespace

from services.governed_tumor_board_chat import answer_governed_tumor_board_question


def _case():
    return SimpleNamespace(
        diagnosis=SimpleNamespace(value="Acute myeloid leukemia"),
        disease_state=SimpleNamespace(value="Relapsed"),
        stage=None,
        clinical_question=SimpleNamespace(question="What management strategy is supported?"),
        molecular_findings=[],
        treatments=[],
    )


def test_fallback_summary_synthesizes_case_when_brief_summary_missing(monkeypatch):
    monkeypatch.delenv("MODEL_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("MODEL_BASE_URL", raising=False)
    result = {
        "tumor_board_brief": {"summary": ""},
        "consensus_report": {"summary": "Current governed consensus is conditional."},
        "missing_information_report": {"summary": "A required evidence channel remains incomplete."},
    }
    out = answer_governed_tumor_board_question("Summarize for tumor board", result, _case())
    assert "Acute myeloid leukemia" in out["answer"]
    assert "Relapsed" in out["answer"]
    assert "conditional" in out["answer"]


def test_treatment_question_uses_governed_decision_not_model_memory(monkeypatch):
    monkeypatch.delenv("MODEL_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("MODEL_BASE_URL", raising=False)
    result = {"consensus_report": {"summary": "Option A is the supported conditional strategy in the current record."}}
    out = answer_governed_tumor_board_question("What is the best treatment?", result, _case())
    assert out["status"] == "Evidence-backed"
    assert "Option A" in out["answer"]
    assert "current governed record" in out["answer"].lower()


def test_trial_question_does_not_invent_trials(monkeypatch):
    monkeypatch.delenv("MODEL_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("MODEL_BASE_URL", raising=False)
    out = answer_governed_tumor_board_question("What clinical trials are there?", {"specialist_outputs": {}}, _case())
    assert out["status"] == "Evidence incomplete"
    assert "No governed clinical-trial output" in out["answer"]
