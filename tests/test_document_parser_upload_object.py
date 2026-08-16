from __future__ import annotations

from services.document_parser import parse_upload


class UploadStub:
    name = "case.txt"

    def getvalue(self):
        return b"Diagnosis: Acute myeloid leukemia\nDisease state: Relapsed"


def test_parse_upload_accepts_streamlit_style_upload_object():
    parsed = parse_upload(UploadStub())
    assert parsed.filename == "case.txt"
    assert parsed.document_type == "txt"
    assert len(parsed.segments) == 2
    assert parsed.segments[0].segment_id == "S0001"
    assert "Acute myeloid leukemia" in parsed.full_text
