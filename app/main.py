from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app.overview_ui as overview_ui
from app.architecture_publication_view import render_publication_panel

st.set_page_config(
    page_title="Pan-Oncology Tumor Board Intelligence",
    layout="wide",
    initial_sidebar_state="expanded",
)

if not hasattr(overview_ui, "_base_research_footer"):
    overview_ui._base_research_footer = overview_ui.research_footer


def _footer_with_publication_figure() -> None:
    render_publication_panel(key_prefix="overview", compact=True)
    overview_ui._base_research_footer()


overview_ui.research_footer = _footer_with_publication_figure
overview_ui.render_final_overview()
