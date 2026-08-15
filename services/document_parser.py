from __future__ import annotations

from io import BytesIO
from pathlib import Path
from pypdf import PdfReader
from docx import Document


def extract_text_from_upload(filename: str, raw_bytes: bytes) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        reader = PdfReader(BytesIO(raw_bytes))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages)

    if suffix == ".docx":
        doc = Document(BytesIO(raw_bytes))
        return "\n".join(p.text for p in doc.paragraphs)

    if suffix in {".txt", ".md"}:
        return raw_bytes.decode("utf-8", errors="replace")

    raise ValueError(f"Unsupported file type: {suffix}")
