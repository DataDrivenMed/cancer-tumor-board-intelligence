from __future__ import annotations

from io import BytesIO
from html import escape
from typing import Any

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from services.oncology_programs import PROGRAM_BY_ID
from services.pathway_validation import get_pathway_validation_status


REPORT_VERSION = "1.0.0"


def _value(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _text(value: Any, default: str = "Not represented") -> str:
    if value is None:
        return default
    if hasattr(value, "value"):
        value = value.value
    text = str(value).strip()
    return text or default


def _fact_value(fact: Any) -> str:
    return _text(_value(fact, "value"))


def _safe(value: Any) -> str:
    return escape(_text(value, ""))


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "TBTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=HexColor("#0B1220"),
            alignment=TA_LEFT,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "TBSubtitle",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=HexColor("#667085"),
            spaceAfter=8,
        ),
        "section": ParagraphStyle(
            "TBSection",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12.5,
            leading=15,
            textColor=HexColor("#163B67"),
            spaceBefore=8,
            spaceAfter=6,
        ),
        "label": ParagraphStyle(
            "TBLabel",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=HexColor("#344054"),
        ),
        "body": ParagraphStyle(
            "TBBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12.5,
            textColor=HexColor("#1D2939"),
        ),
        "small": ParagraphStyle(
            "TBSmall",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=HexColor("#667085"),
        ),
        "warning": ParagraphStyle(
            "TBWarning",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=12,
            textColor=HexColor("#8A4B00"),
        ),
    }


def _header_footer(canvas, doc):
    canvas.saveState()
    width, height = letter
    canvas.setStrokeColor(HexColor("#D9E2EC"))
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, 0.55 * inch, width - doc.rightMargin, 0.55 * inch)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(HexColor("#667085"))
    canvas.drawString(doc.leftMargin, 0.36 * inch, "Tumor Board Intelligence | Research decision support")
    canvas.drawRightString(width - doc.rightMargin, 0.36 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _summary_table(case: Any, styles: dict[str, ParagraphStyle]) -> Table:
    program = PROGRAM_BY_ID.get(_value(case, "disease_program"))
    program_label = program.display_name if program else _text(_value(case, "disease_program"))
    validation = get_pathway_validation_status(_value(case, "disease_program"))
    stage = _value(case, "stage")
    performance = _value(case, "performance_status")

    rows = [
        [Paragraph("Tumor board", styles["label"]), Paragraph(_safe(program_label), styles["body"])],
        [Paragraph("Validation state", styles["label"]), Paragraph(_safe(validation.label), styles["body"])],
        [Paragraph("Diagnosis", styles["label"]), Paragraph(_safe(_fact_value(_value(case, "diagnosis"))), styles["body"])],
        [Paragraph("Disease state", styles["label"]), Paragraph(_safe(_fact_value(_value(case, "disease_state"))), styles["body"])],
        [Paragraph("Stage", styles["label"]), Paragraph(_safe(_fact_value(stage) if stage is not None else "Not represented"), styles["body"])],
        [Paragraph("Performance status", styles["label"]), Paragraph(_safe(_fact_value(performance) if performance is not None else "Not represented"), styles["body"])],
    ]
    table = Table(rows, colWidths=[1.35 * inch, 5.55 * inch], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, -1), HexColor("#F4F7FA")),
        ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#D9E2EC")),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, HexColor("#E5EAF0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def _molecular_summary(case: Any, styles: dict[str, ParagraphStyle]):
    findings = list(_value(case, "molecular_findings", []) or [])
    if not findings:
        return Paragraph("No molecular findings represented in the canonical case.", styles["body"])
    rows = [[
        Paragraph("Gene", styles["label"]),
        Paragraph("Alteration", styles["label"]),
        Paragraph("VAF", styles["label"]),
        Paragraph("Verification", styles["label"]),
    ]]
    for item in findings:
        vaf = _value(item, "variant_allele_frequency")
        vaf_text = f"{float(vaf) * 100:.1f}%" if vaf is not None else "Not represented"
        verified = "Clinician confirmed" if bool(_value(item, "human_verified", False)) else "Not clinician confirmed"
        alteration = _value(item, "alteration_type") or _value(item, "hgvs_p") or _value(item, "hgvs_c")
        rows.append([
            Paragraph(_safe(_value(item, "gene")), styles["body"]),
            Paragraph(_safe(alteration), styles["body"]),
            Paragraph(_safe(vaf_text), styles["body"]),
            Paragraph(_safe(verified), styles["body"]),
        ])
    table = Table(rows, colWidths=[1.1 * inch, 2.35 * inch, 0.8 * inch, 2.65 * inch], hAlign="LEFT", repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#EEF3F8")),
        ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#D9E2EC")),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, HexColor("#E5EAF0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _section_block(section: Any, styles: dict[str, ParagraphStyle]):
    content = [Paragraph(_safe(_value(section, "title")), styles["section"])]
    note = _value(section, "section_note")
    if note:
        content.append(Paragraph(_safe(note), styles["small"]))
        content.append(Spacer(1, 4))

    items = list(_value(section, "items", []) or [])
    if not items:
        content.append(Paragraph("No items represented.", styles["body"]))
        return content

    rows = []
    for item in items:
        label = _safe(_value(item, "label"))
        value = _safe(_value(item, "value"))
        epistemic = _text(_value(item, "epistemic_label"), "")
        refs = list(_value(item, "source_refs", []) or [])
        limitations = list(_value(item, "limitations", []) or [])
        metadata = []
        if epistemic:
            metadata.append(epistemic)
        if refs:
            metadata.append("Sources: " + ", ".join(str(x) for x in refs))
        if limitations:
            metadata.append("Limitations: " + "; ".join(str(x) for x in limitations))
        right = [Paragraph(value, styles["body"])]
        if metadata:
            right.append(Spacer(1, 2))
            right.append(Paragraph(_safe(" | ".join(metadata)), styles["small"]))
        rows.append([Paragraph(label, styles["label"]), right])

    table = Table(rows, colWidths=[1.55 * inch, 5.35 * inch], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.35, HexColor("#E5EAF0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    content.append(table)
    return content


def build_tumor_board_pdf(result: dict[str, Any]) -> bytes:
    """Render the governed tumor-board brief as a readable clinician PDF.

    The PDF is a presentation transform of already-produced structured outputs. It
    does not create new evidence, infer new facts, or change recommendation gates.
    """
    case = result.get("case")
    brief = result.get("tumor_board_brief")
    if case is None or brief is None:
        raise ValueError("case and tumor_board_brief are required for PDF export")

    styles = _styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.62 * inch,
        bottomMargin=0.72 * inch,
        title=f"Tumor Board Intelligence - {_text(_value(case, 'case_id'))}",
        author="Tumor Board Intelligence",
    )

    story = [
        Paragraph("Tumor Board Intelligence", styles["title"]),
        Paragraph(
            "Evidence-grounded multidisciplinary decision-support brief. De-identified or synthetic data only unless institutionally approved for another use.",
            styles["subtitle"],
        ),
        _summary_table(case, styles),
        Spacer(1, 10),
    ]

    decision_state = _text(_value(brief, "decision_state"))
    strength = _text(_value(brief, "decision_support_strength"))
    status = _text(_value(brief, "status"))
    decision_rows = [[
        Paragraph("Decision state", styles["label"]), Paragraph(_safe(decision_state), styles["body"]),
        Paragraph("Support strength", styles["label"]), Paragraph(_safe(strength), styles["body"]),
        Paragraph("Brief status", styles["label"]), Paragraph(_safe(status), styles["body"]),
    ]]
    decision_table = Table(decision_rows, colWidths=[0.9*inch,1.35*inch,1.0*inch,1.35*inch,0.75*inch,1.55*inch])
    decision_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor("#EDF3FF")),
        ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#C9D7F2")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([decision_table, Spacer(1, 8)])

    summary = _value(brief, "summary")
    if summary:
        story.extend([
            Paragraph("Executive summary", styles["section"]),
            Paragraph(_safe(summary), styles["body"]),
            Spacer(1, 4),
        ])

    warnings = list(_value(brief, "critical_warnings", []) or [])
    if warnings:
        story.append(Paragraph("Critical warnings", styles["section"]))
        for warning in warnings:
            story.append(Paragraph("• " + _safe(warning), styles["warning"]))
        story.append(Spacer(1, 4))

    story.extend([
        Paragraph("Key molecular findings", styles["section"]),
        _molecular_summary(case, styles),
        Spacer(1, 6),
    ])

    sections = list(_value(brief, "sections", []) or [])
    for section in sections:
        story.extend(_section_block(section, styles))
        story.append(Spacer(1, 3))

    source_trace_count = _value(brief, "source_trace_count", 0)
    story.extend([
        Spacer(1, 8),
        Paragraph("Report controls", styles["section"]),
        Paragraph(
            _safe(
                f"Source traces represented in brief: {source_trace_count}. "
                f"Report renderer version: {REPORT_VERSION}. This PDF is generated from the structured tumor-board brief and does not add clinical claims."
            ),
            styles["small"],
        ),
        Spacer(1, 6),
        Paragraph(
            "Research decision support only. Clinical trial matching does not establish eligibility. Management output must not be treated as an autonomous treatment directive.",
            styles["small"],
        ),
    ])

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return buffer.getvalue()
