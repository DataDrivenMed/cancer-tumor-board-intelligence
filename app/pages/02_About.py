from __future__ import annotations

import streamlit as st

from app.faculty_ui import render_about_page

st.set_page_config(
    page_title="About · Pan-Oncology Tumor Board Intelligence",
    layout="wide",
    initial_sidebar_state="collapsed",
)

render_about_page()
