from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app.architecture_warm_ui as architecture_ui
from app.architecture_publication_view import render_publication_panel

st.set_page_config(
    page_title="Architecture · Pan-Oncology Tumor Board Intelligence",
    layout="wide",
    initial_sidebar_state="expanded",
)

if not hasattr(architecture_ui, "_base_research_footer"):
    architecture_ui._base_research_footer = architecture_ui.research_footer


def _footer_with_publication_figure() -> None:
    render_publication_panel(key_prefix="architecture", compact=False)
    architecture_ui._base_research_footer()


architecture_ui.research_footer = _footer_with_publication_figure
architecture_ui.render_architecture_page()
