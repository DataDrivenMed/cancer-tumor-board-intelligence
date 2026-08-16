from pathlib import Path

from app.faculty_ui import answer_case_question


def test_faculty_landing_page_replaces_auto_redirect():
    text = Path("app/main.py").read_text(encoding="utf-8")
    assert "render_overview" in text
    assert "switch_page" not in text


def test_workspace_contains_governed_chat_and_thirty_second_view():
    text = Path("app/pages/00_Clinical_Workspace.py").read_text(encoding="utf-8")
    assert "render_thirty_second_view(result, case)" in text
    assert "render_case_chat(result, case, key_prefix=\"brief\")" in text
    assert "render_case_chat(analysis_result" in text
    assert "render_case_chat({\"specialist_outputs\": evidence_chat_outputs}" in text
    assert "Ram Paragi · rparag@lsuhsc.edu" in text


def test_chat_abstains_outside_governed_record():
    answer, sources, status = answer_case_question("What is the weather?", {}, object())
    assert "cannot answer" in answer.lower()
    assert sources == []
    assert status == "Unable to answer from current case evidence"


def test_expandable_affordance_is_explicit():
    text = Path("app/faculty_ui.py").read_text(encoding="utf-8")
    assert "View details" in text
    assert "Synthetic demonstration case" in text
