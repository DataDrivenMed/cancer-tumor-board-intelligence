from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from app.architecture_publication import PDF_FILENAME, build_publication_pdf, publication_svg


def render_publication_panel(*, key_prefix: str, compact: bool = False) -> None:
    st.markdown(
        '<div style="margin-top:24px"><div class="eyebrow">Publication figure</div>'
        '<h2 style="font-size:28px;margin:5px 0 8px">Full multi-agent architecture</h2>'
        '<p style="font-size:15px;line-height:1.6;color:var(--x-body);max-width:900px;margin:0 0 14px">'
        'Publication-style architecture with the full workflow, specialist-agent roles, safety gates, conditional loops, challenge logic, human review points, and final clinician-facing outputs.'</n        'p></div>',
        unsafe_allow_html=True,
    )
    svg = publication_svg().replace(
        '<svg ',
        '<svg style="width:100%;height:auto;display:block" ',
        1,
    )
    components.html(
        '<div style="width:100%;background:#fbf9f3;border:1px solid #e6e5e0;border-radius:12px;overflow:hidden;padding:4px">'
        + svg
        + '</div>',
        height=520 if compact else 760,
        scrolling=False,
    )
    st.download_button(
        'Download Full Multi-Agent Architecture (PDF)',
        data=build_publication_pdf(),
        file_name=PDF_FILENAME,
        mime='application/pdf',
        key=f'{key_prefix}_download_full_architecture_pdf',
        use_container_width=True,
    )
