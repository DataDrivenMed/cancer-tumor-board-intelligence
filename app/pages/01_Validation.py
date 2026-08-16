from __future__ import annotations

import streamlit as st

from app.faculty_ui import render_validation_page

st.set_page_config(
    page_title="Validation · Pan-Oncology Tumor Board Intelligence",
    page_icon="TB",
    layout="wide",
    initial_sidebar_state="collapsed",
)

render_validation_page()
