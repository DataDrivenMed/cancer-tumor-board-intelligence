from pathlib import Path


def test_shared_dark_theme_is_wired():
    theme = Path("app/xai_theme.py").read_text(encoding="utf-8")
    faculty = Path("app/faculty_ui.py").read_text(encoding="utf-8")
    workspace = Path("app/pages/00_Clinical_Workspace.py").read_text(encoding="utf-8")
    overview = Path("app/overview_ui.py").read_text(encoding="utf-8")
    assert "--x-canvas:#0a0a0a" in theme
    assert "inject_xai_theme()" in faculty
    assert "inject_xai_theme()" in workspace
    assert "inject_xai_theme()" in overview


def test_architecture_uses_dark_canvas():
    html = Path("app/assets/architecture_interactive.html").read_text(encoding="utf-8")
    assert "--paper:#0a0a0a" in html
    assert "background:#0d0d0d" in html
    assert "Hover over any box" in html
