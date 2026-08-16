from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from schemas.case import CancerTumorBoardCase
from schemas.tumor_board_brief import BriefItem, BriefSection, TumorBoardIntelligenceBrief
from services.tumor_board_pdf import build_tumor_board_pdf


ROOT = Path(__file__).resolve().parents[1]


def _result():
    payload = json.loads((ROOT / "synthetic_cases" / "syn_aml_001.json").read_text(encoding="utf-8"))
    case = CancerTumorBoardCase.model_validate(payload)
    brief = TumorBoardIntelligenceBrief(
        case_id=case.case_id,
        status="completed_with_limitations",
        decision_state="conditional",
        decision_support_strength="moderate",
        safe_to_display=True,
        source_trace_count=3,
        summary="A concise tumor-board summary for clinician review.",
        critical_warnings=["One decision-critical item remains unresolved."],
        sections=[
            BriefSection(
                section_id="management_strategy",
                title="Management Strategy and Alternatives",
                items=[
                    BriefItem(
                        label="Management strategy",
                        value="Discuss evidence-supported options after verification.",
                        epistemic_label="INTERPRETED",
                        source_refs=["SYN-DOC-001"],
                    )
                ],
            )
        ],
    )
    return {"case": case, "tumor_board_brief": brief}


def test_pdf_export_is_valid_and_human_readable():
    pdf = build_tumor_board_pdf(_result())
    assert pdf.startswith(b"%PDF")
    reader = PdfReader(BytesIO(pdf))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Tumor Board Intelligence" in text
    assert "Acute myeloid leukemia" in text
    assert "Management Strategy and Alternatives" in text
    assert "Research decision support" in text


def test_pdf_export_requires_governed_brief():
    try:
        build_tumor_board_pdf({})
    except ValueError as exc:
        assert "case and tumor_board_brief" in str(exc)
    else:
        raise AssertionError("Expected missing brief to block PDF export")
