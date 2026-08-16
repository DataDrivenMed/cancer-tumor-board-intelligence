from pathlib import Path


def test_pdf_download_uses_defined_report_case():
    text = Path("app/pages/00_Clinical_Workspace.py").read_text(encoding="utf-8")
    assert 'report_case = result.get("case") or st.session_state.case' in text
    assert 'str(report_case.case_id)' in text
    assert 'str(case.case_id)' not in text
