from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.architecture_ui import render_architecture_page

st.set_page_config(
    page_title="Architecture · Pan-Oncology Tumor Board Intelligence",
    layout="wide",
    initial_sidebar_state="collapsed",
)

render_architecture_page()
