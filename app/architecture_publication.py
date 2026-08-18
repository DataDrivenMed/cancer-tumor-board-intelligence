from __future__ import annotations

from html import escape
from io import BytesIO
from textwrap import wrap

import streamlit as st
import streamlit.components.v1 as components
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A3, landscape
from reportlab.pdfgen import canvas


POSTER_W = 1414
POSTER_H = 1000
PDF_FILENAME = "Pan-Oncology_Tumor_Board_Full_Multi-Agent_Architecture.pdf"

COLORS = {
    "canvas": "#fbf9f3",
    "ink": "#1e2430",
    "muted": "#5e6470",
    "orange": "#e8580a",
    "blue": "#2d5ea8",
    "blue_fill": "#f1f6fb",
    "green": "#4b7e34",
    "green_fill": "#f4f8ee",
    "amber": "#b16d0b",
    "amber_fill": "#fff9ec",
    "purple": "#6842a3",
    "purple_fill": "#f7f3fb",
    "red": "#c84d50",
    "teal": "#2e7d76",
}

DISPLAY = {
    "intake": ("1. Case Intake", "internal: intake", "Receive de-identified source material."),
    "extraction": ("2. Extraction", "internal: extraction", "Build a structured, source-traced case."),
    "confirmation": ("3. Human Confirmation", "internal: confirmation", "Clinician verifies represented facts."),
    "integrity": ("4. Integrity Review", "internal: integrity", "Check consistency, provenance, and routing safety."),
    "missing": ("5. Missing Information Check", "internal: missing", "Surface absent, pending, or conflicting facts."),
    "clarification": ("6. Clarification Gate", "internal: clarification", "Determine whether the case can proceed."),
    "router": ("7. Clinical Router", "internal: router", "Route by disease program and question."),
    "correction": ("Case Correction Gate", "internal: correction", "Correct representation errors before reasoning."),
    "apply": ("Apply Clarification", "internal: apply", "Add verified clarification and re-run checks."),
    "guideline": ("1. Guideline Agent", "internal: guideline", "Match governed disease-specific guidance."),
    "molecular": ("2. Molecular Interpretation Agent", "internal: molecular", "Interpret governed molecular evidence."),
    "literature": ("3. Literature Agent", "internal: literature", "Retrieve current bounded literature."),
    "translational": ("4. Translational Biology Agent", "internal: translational", "Preserve mechanistic evidence as translational."),
    "trials": ("5. Clinical Trials Agent", "internal: trials", "Screen current trial records and unresolved eligibility."),
    "safety": ("6. Safety Agent", "internal: safety", "Surface bounded safety-source evidence."),
    "join": ("1. Join Specialist Evidence", "internal: join", "Assemble specialist outputs without flattening limits."),
    "redteam": ("2. Clinical Red Team", "internal: redteam", "Challenge evidence sufficiency, assumptions, and gaps."),
    "consensus": ("3. Consensus Engine", "internal: consensus", "Synthesize only after required gates are satisfied."),
    "brief": ("1. Tumor Board Brief", "internal: brief", "Present decision state, evidence, uncertainty, and limits."),
    "outputs": ("2. PDF / Structured Audit Output", "internal: outputs", "Provide readable and machine-auditable output."),
    "human": ("3. Clinician / Multidisciplinary Tumor Board", "human endpoint", "Human judgment and consensus drive the final decision."),
}

NODES = {
    "intake": (250, 165, 205, 78), "extraction": (480, 165, 205, 78), "confirmation": (710, 165, 205, 78), "integrity": (940, 165, 205, 78),
    "missing": (250, 270, 220, 78), "clarification": (500, 270, 220, 78), "router": (750, 270, 220, 78), "correction": (1000, 270, 175, 78), "apply": (500, 365, 220, 62),
    "guideline": (250, 500, 290, 64), "molecular": (555, 500, 290, 64), "literature": (860, 500, 290, 64), "translational": (250, 580, 290, 64), "trials": (555, 580, 290, 64), "safety": (860, 580, 290, 64),
    "join": (270, 710, 270, 68), "redteam": (565, 710, 290, 68), "consensus": (880, 710, 270, 68),
    "brief": (270, 850, 260, 68), "outputs": (555, 850, 290, 68), "human": (870, 850, 300, 68),
}

NODE_STYLE = {
    "intake": ("#f6f9fd", COLORS["blue"]), "extraction": ("#f6f9fd", COLORS["blue"]), "confirmation": ("#f6f9fd", COLORS["blue"]), "integrity": ("#f6f9fd", COLORS["blue"]),
    "missing": ("#f6f9fd", COLORS["blue"]), "clarification": ("#fff7ef", COLORS["orange"]), "router": ("#f6f9fd", COLORS["blue"]), "correction": ("#fff7ef", COLORS["orange"]), "apply": ("#fff7ef", COLORS["orange"]),
    "guideline": ("#f3f8ea", COLORS["green"]), "molecular": ("#f7f1fb", "#6b43a8"), "literature": ("#eef5fb", COLORS["blue"]), "translational": ("#edf8f4", COLORS["teal"]), "trials": ("#fff4e7", "#d87913"), "safety": ("#fff0f0", COLORS["red"]),
    "join": ("#fffaf0", COLORS["amber"]), "redteam": ("#fff8ee", COLORS["orange"]), "consensus": ("#fffaf0", COLORS["amber"]), "brief": ("#f8f3fb", COLORS["purple"]), "outputs": ("#f8f3fb", COLORS["purple"]), "human": ("#ffffff", COLORS["purple"]),
}

PRIMARY = [("intake", "extraction"), ("extraction", "confirmation"), ("confirmation", "integrity"), ("missing", "clarification"), ("clarification", "router"), ("join", "redteam"), ("redteam", "consensus"), ("brief", "outputs"), ("outputs", "human")]


def _lines(text: str, width: int) -> list[str]:
    return wrap(text, width=width, break_long_words=False, break_on_hyphens=False) or [""]


def _svg_node(node_id: str) -> str:
    x, y, w, h = NODES[node_id]
    fill, stroke = NODE_STYLE[node_id]
    title, internal, desc = DISPLAY[node_id]
    sw = 2.6 if node_id in {"redteam", "human"} else 1.4
    dash = ' stroke-dasharray="4 4"' if node_id in {"correction", "apply"} else ""
    desc_lines = _lines(desc, 31 if w < 260 else 38)[:2]
    desc_svg = "".join(
        f'<text x="{x+12}" y="{y+54+i*14}" font-family="Arial,sans-serif" font-size="9.5" fill="{COLORS["muted"]}">{escape(line)}</text>'
        for i, line in enumerate(desc_lines)
    )
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{dash}/>'
        f'<text x="{x+12}" y="{y+21}" font-family="Arial,sans-serif" font-size="12.3" font-weight="700" fill="{COLORS["ink"]}">{escape(title)}</text>'
        f'<text x="{x+12}" y="{y+38}" font-family="Arial,sans-serif" font-size="9.7" font-style="italic" fill="{stroke}">{escape(internal)}</text>'
        f'{desc_svg}'
    )


def publication_svg() -> str:
    s = [f'''<svg viewBox="0 0 {POSTER_W} {POSTER_H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Pan-Oncology Tumor Board Intelligence full multi-agent architecture">
<defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#34383f"/></marker></defs>
<rect width="100%" height="100%" fill="{COLORS['canvas']}"/>
<text x="707" y="42" text-anchor="middle" font-family="Georgia,serif" font-size="34" font-weight="700" fill="{COLORS['ink']}">Pan-Oncology Tumor Board Intelligence: Full Multi-Agent Architecture</text>
<text x="707" y="78" text-anchor="middle" font-family="Georgia,serif" font-style="italic" font-size="18" fill="{COLORS['orange']}">Governed research decision-support workflow for multidisciplinary tumor board review</text>
<line x1="50" y1="108" x2="190" y2="108" stroke="{COLORS['orange']}" stroke-width="2" stroke-dasharray="5 5"/><circle cx="48" cy="108" r="5" fill="{COLORS['orange']}"/>
<text x="707" y="113" text-anchor="middle" font-family="Arial,sans-serif" font-size="12.5" font-style="italic" fill="{COLORS['ink']}">This architecture separates case verification, specialist evidence generation, challenge, and final synthesis so that no single model silently replaces clinical review.</text>
<line x1="1224" y1="108" x2="1364" y2="108" stroke="{COLORS['orange']}" stroke-width="2" stroke-dasharray="5 5"/><circle cx="1366" cy="108" r="5" fill="{COLORS['orange']}"/>''']

    bands = [
        ("PHASE 01", "CASE UNDERSTANDING & SAFETY", "case verification before specialist reasoning", 135, 310, COLORS["blue_fill"], COLORS["blue"]),
        ("PHASE 02", "SPECIALIST AGENTS", "parallel governed evidence channels", 455, 210, COLORS["green_fill"], COLORS["green"]),
        ("PHASE 03", "CHALLENGE & CONSENSUS", "challenge before synthesis", 675, 120, COLORS["amber_fill"], COLORS["amber"]),
        ("PHASE 04", "OUTPUT & HUMAN DECISION SUPPORT", "presentation, not autonomous care", 805, 125, COLORS["purple_fill"], COLORS["purple"]),
    ]
    for phase, title, sub, y, h, fill, accent in bands:
        s.append(f'<rect x="20" y="{y}" width="1185" height="{h}" rx="14" fill="{fill}" stroke="{accent}" stroke-opacity=".45"/>')
        s.append(f'<text x="40" y="{y+28}" font-family="Arial,sans-serif" font-size="15" font-weight="700" fill="{accent}">{phase}</text>')
        yy = y + 58
        for line in _lines(title, 25):
            s.append(f'<text x="40" y="{yy}" font-family="Georgia,serif" font-size="17" font-weight="700" fill="{COLORS["ink"]}">{escape(line)}</text>')
            yy += 20
        for line in _lines(sub, 28):
            s.append(f'<text x="40" y="{yy+4}" font-family="Georgia,serif" font-size="13" font-style="italic" fill="{accent}">{escape(line)}</text>')
            yy += 18

    s += [
        '<text x="700" y="480" text-anchor="middle" font-family="Georgia,serif" font-size="13" font-style="italic" fill="#30343a">The router sends the structured case to relevant evidence specialists in parallel.</text>',
        '<text x="700" y="658" text-anchor="middle" font-family="Georgia,serif" font-size="12.5" font-style="italic" fill="#30343a">Each specialist returns structured evidence, provenance, limitations, and availability status.</text>',
        f'<text x="700" y="790" text-anchor="middle" font-family="Georgia,serif" font-size="12.5" font-style="italic" fill="{COLORS["orange"]}">Challenge occurs before consensus: missingness, unsupported assumptions, and evidence weakness remain visible.</text>',
    ]

    for node_id in NODES:
        s.append(_svg_node(node_id))

    def right(node_id: str) -> tuple[float, float]:
        x, y, w, h = NODES[node_id]
        return x + w, y + h / 2

    def left(node_id: str) -> tuple[float, float]:
        x, y, _, h = NODES[node_id]
        return x, y + h / 2

    for source, target in PRIMARY:
        x1, y1 = right(source)
        x2, y2 = left(target)
        s.append(f'<line x1="{x1}" y1="{y1}" x2="{x2-7}" y2="{y2}" stroke="#34383f" stroke-width="1.8" marker-end="url(#a)"/>')

    s += [
        '<path d="M1042 243 V252 H230 V309 H245" fill="none" stroke="#34383f" stroke-width="1.5" marker-end="url(#a)"/>',
        '<line x1="860" y1="348" x2="860" y2="447" stroke="#34383f" stroke-width="1.7" marker-end="url(#a)"/>',
        '<line x1="700" y1="665" x2="700" y2="702" stroke="#34383f" stroke-width="1.8" marker-end="url(#a)"/>',
        '<line x1="700" y1="796" x2="700" y2="842" stroke="#34383f" stroke-width="1.8" marker-end="url(#a)"/>',
        '<path d="M915 204 H1090 V262" fill="none" stroke="#34383f" stroke-width="1.6" stroke-dasharray="3 4" marker-end="url(#a)"/>',
        '<path d="M1088 270 V250 H1042" fill="none" stroke="#34383f" stroke-width="1.6" stroke-dasharray="3 4" marker-end="url(#a)"/>',
        '<path d="M610 348 V362" fill="none" stroke="#34383f" stroke-width="1.6" stroke-dasharray="3 4" marker-end="url(#a)"/>',
        '<path d="M500 396 H430 V350" fill="none" stroke="#34383f" stroke-width="1.6" stroke-dasharray="3 4" marker-end="url(#a)"/>',
        '<path d="M720 396 H850 V350" fill="none" stroke="#34383f" stroke-width="1.6" stroke-dasharray="3 4" marker-end="url(#a)"/>',
        f'<rect x="978" y="365" width="200" height="60" rx="10" fill="#ffffff" stroke="{COLORS["blue"]}" stroke-width="1.2" stroke-dasharray="4 4"/>',
        f'<text x="1078" y="388" text-anchor="middle" font-family="Georgia,serif" font-size="12" font-style="italic" fill="{COLORS["blue"]}">Clinician review is explicit.</text>',
        f'<text x="1078" y="407" text-anchor="middle" font-family="Georgia,serif" font-size="11" font-style="italic" fill="{COLORS["blue"]}">Recommendation-blocking missingness stays visible.</text>',
        f'<rect x="1180" y="852" width="180" height="55" rx="10" fill="#ffffff" stroke="{COLORS["blue"]}" stroke-width="1.2" stroke-dasharray="4 4"/>',
        f'<text x="1270" y="880" text-anchor="middle" font-family="Georgia,serif" font-size="12" font-style="italic" fill="{COLORS["blue"]}">Clinician judgment remains central.</text>',
    ]

    lx, ly, lw, lh = 1225, 330, 165, 430
    s += [
        f'<rect x="{lx}" y="{ly}" width="{lw}" height="{lh}" rx="12" fill="#fffdf8" stroke="#a99b7b"/>',
        f'<text x="{lx+lw/2}" y="{ly+26}" text-anchor="middle" font-family="Georgia,serif" font-size="15" font-weight="700" fill="{COLORS["ink"]}">LEGEND</text>',
        f'<text x="{lx+14}" y="{ly+55}" font-family="Arial,sans-serif" font-size="10" font-weight="700" fill="{COLORS["ink"]}">LINE STYLE</text>',
        f'<line x1="{lx+15}" y1="{ly+80}" x2="{lx+52}" y2="{ly+80}" stroke="#34383f" stroke-width="1.7"/><text x="{lx+62}" y="{ly+84}" font-family="Arial,sans-serif" font-size="9.3" fill="{COLORS["ink"]}">Primary flow</text>',
        f'<line x1="{lx+15}" y1="{ly+111}" x2="{lx+52}" y2="{ly+111}" stroke="#34383f" stroke-width="1.7" stroke-dasharray="3 4"/><text x="{lx+62}" y="{ly+115}" font-family="Arial,sans-serif" font-size="9.3" fill="{COLORS["ink"]}">Optional / conditional</text>',
        f'<line x1="{lx+15}" y1="{ly+142}" x2="{lx+52}" y2="{ly+142}" stroke="#34383f" stroke-width="1.7" stroke-dasharray="8 4"/><text x="{lx+62}" y="{ly+146}" font-family="Arial,sans-serif" font-size="9.3" fill="{COLORS["ink"]}">Human review dependency</text>',
        f'<text x="{lx+14}" y="{ly+182}" font-family="Arial,sans-serif" font-size="10" font-weight="700" fill="{COLORS["ink"]}">COLOR GROUPS</text>',
    ]
    legend_rows = [
        ("Case & safety", COLORS["blue_fill"], COLORS["blue"]),
        ("Specialist evidence", COLORS["green_fill"], COLORS["green"]),
        ("Challenge & consensus", COLORS["amber_fill"], COLORS["amber"]),
        ("Output & human support", COLORS["purple_fill"], COLORS["purple"]),
        ("Human review / gates", "#fff7ef", COLORS["orange"]),
    ]
    yy = ly + 211
    for label, fill, stroke in legend_rows:
        s.append(f'<rect x="{lx+15}" y="{yy-11}" width="18" height="14" rx="2" fill="{fill}" stroke="{stroke}"/><text x="{lx+43}" y="{yy}" font-family="Arial,sans-serif" font-size="9.3" fill="{COLORS["ink"]}">{escape(label)}</text>')
        yy += 29

    s += [
        f'<text x="72" y="962" font-family="Arial,sans-serif" font-size="12" font-weight="700" fill="{COLORS["ink"]}">Designed and developed by Ram Paragi</text>',
        f'<text x="72" y="980" font-family="Arial,sans-serif" font-size="11" fill="{COLORS["ink"]}">LSU Health New Orleans School of Medicine · rparag@lsuhsc.edu</text>',
        f'<text x="1340" y="968" text-anchor="end" font-family="Georgia,serif" font-size="11" font-style="italic" fill="{COLORS["ink"]}">Research concept for faculty review and multidisciplinary discussion.</text>',
        '</svg>',
    ]
    return "".join(s)


def _pdf_rect(c: canvas.Canvas, x: float, y: float, w: float, h: float, fill: str, stroke: str, X, Y, scale: float, radius: float = 10, width: float = 1) -> None:
    c.setFillColor(HexColor(fill))
    c.setStrokeColor(HexColor(stroke))
    c.setLineWidth(width * scale)
    c.roundRect(X(x), Y(y + h), w * scale, h * scale, radius * scale, fill=1, stroke=1)


@st.cache_data(show_spinner=False)
def build_publication_pdf() -> bytes:
    out = BytesIO()
    page_w, page_h = landscape(A3)
    scale = min(page_w / POSTER_W, page_h / POSTER_H)
    xoff = (page_w - POSTER_W * scale) / 2
    yoff = (page_h - POSTER_H * scale) / 2
    X = lambda value: xoff + value * scale
    Y = lambda value: page_h - yoff - value * scale
    c = canvas.Canvas(out, pagesize=(page_w, page_h))
    c.setTitle("Pan-Oncology Tumor Board Intelligence: Full Multi-Agent Architecture")
    c.setAuthor("Ram Paragi, LSU Health New Orleans School of Medicine")
    c.setFillColor(HexColor(COLORS["canvas"]))
    c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    c.setFillColor(HexColor(COLORS["ink"]))
    c.setFont("Times-Bold", 24 * scale)
    c.drawCentredString(X(707), Y(42), "Pan-Oncology Tumor Board Intelligence: Full Multi-Agent Architecture")
    c.setFillColor(HexColor(COLORS["orange"]))
    c.setFont("Times-Italic", 14 * scale)
    c.drawCentredString(X(707), Y(78), "Governed research decision-support workflow for multidisciplinary tumor board review")
    c.setFillColor(HexColor(COLORS["ink"]))
    c.setFont("Times-Italic", 8.8 * scale)
    c.drawCentredString(X(707), Y(111), "This architecture separates case verification, specialist evidence generation, challenge, and final synthesis so that no single model silently replaces clinical review.")

    bands = [
        ("PHASE 01", "CASE UNDERSTANDING & SAFETY", "case verification before specialist reasoning", 135, 310, COLORS["blue_fill"], COLORS["blue"]),
        ("PHASE 02", "SPECIALIST AGENTS", "parallel governed evidence channels", 455, 210, COLORS["green_fill"], COLORS["green"]),
        ("PHASE 03", "CHALLENGE & CONSENSUS", "challenge before synthesis", 675, 120, COLORS["amber_fill"], COLORS["amber"]),
        ("PHASE 04", "OUTPUT & HUMAN DECISION SUPPORT", "presentation, not autonomous care", 805, 125, COLORS["purple_fill"], COLORS["purple"]),
    ]
    for phase, title, sub, y, h, fill, accent in bands:
        _pdf_rect(c, 20, y, 1185, h, fill, accent, X, Y, scale, 14, .8)
        c.setFillColor(HexColor(accent)); c.setFont("Helvetica-Bold", 10.5 * scale); c.drawString(X(40), Y(y + 28), phase)
        c.setFillColor(HexColor(COLORS["ink"])); c.setFont("Times-Bold", 11.5 * scale)
        yy = y + 58
        for line in _lines(title, 25): c.drawString(X(40), Y(yy), line); yy += 17
        c.setFillColor(HexColor(accent)); c.setFont("Times-Italic", 9.3 * scale)
        for line in _lines(sub, 28): c.drawString(X(40), Y(yy + 3), line); yy += 15

    c.setFillColor(HexColor(COLORS["ink"])); c.setFont("Times-Italic", 8.6 * scale)
    c.drawCentredString(X(700), Y(480), "The router sends the structured case to relevant evidence specialists in parallel.")
    c.drawCentredString(X(700), Y(658), "Each specialist returns structured evidence, provenance, limitations, and availability status.")
    c.setFillColor(HexColor(COLORS["orange"])); c.drawCentredString(X(700), Y(790), "Challenge occurs before consensus: missingness, unsupported assumptions, and evidence weakness remain visible.")

    for node_id, (x, y, w, h) in NODES.items():
        fill, stroke = NODE_STYLE[node_id]
        _pdf_rect(c, x, y, w, h, fill, stroke, X, Y, scale, 9, 2.2 if node_id in {"redteam", "human"} else 1)
        title, internal, desc = DISPLAY[node_id]
        c.setFillColor(HexColor(COLORS["ink"])); c.setFont("Helvetica-Bold", 8.3 * scale); c.drawString(X(x + 12), Y(y + 21), title)
        c.setFillColor(HexColor(stroke)); c.setFont("Helvetica-Oblique", 6.7 * scale); c.drawString(X(x + 12), Y(y + 38), internal)
        c.setFillColor(HexColor(COLORS["muted"])); c.setFont("Helvetica", 6.6 * scale)
        for i, line in enumerate(_lines(desc, 31 if w < 260 else 38)[:2]): c.drawString(X(x + 12), Y(y + 54 + i * 12), line)

    def arrow(x1: float, y1: float, x2: float, y2: float, dashed: bool = False) -> None:
        c.setStrokeColor(HexColor("#34383f")); c.setFillColor(HexColor("#34383f")); c.setLineWidth(1.1 * scale); c.setDash(2 * scale, 3 * scale) if dashed else c.setDash()
        c.line(X(x1), Y(y1), X(x2), Y(y2)); c.setDash()
        size = 5 * scale
        p = c.beginPath(); p.moveTo(X(x2), Y(y2)); p.lineTo(X(x2) - size, Y(y2) + size * .55); p.lineTo(X(x2) - size, Y(y2) - size * .55); p.close(); c.drawPath(p, fill=1, stroke=0)

    def right(node_id: str) -> tuple[float, float]:
        x, y, w, h = NODES[node_id]; return x + w, y + h / 2

    def left(node_id: str) -> tuple[float, float]:
        x, y, _, h = NODES[node_id]; return x, y + h / 2

    for source, target in PRIMARY:
        x1, y1 = right(source); x2, y2 = left(target); arrow(x1, y1, x2 - 5, y2)

    # primary phase transitions and conditional loops
    c.setStrokeColor(HexColor("#34383f")); c.setLineWidth(1 * scale)
    c.line(X(1042), Y(243), X(1042), Y(252)); c.line(X(1042), Y(252), X(230), Y(252)); c.line(X(230), Y(252), X(230), Y(309)); arrow(230, 309, 245, 309)
    arrow(860, 348, 860, 447); arrow(700, 665, 700, 702); arrow(700, 796, 700, 842)
    c.setDash(2 * scale, 3 * scale)
    for a, b in [((915, 204), (1090, 204)), ((1090, 204), (1090, 262)), ((610, 348), (610, 362)), ((500, 396), (430, 396)), ((430, 396), (430, 350)), ((720, 396), (850, 396)), ((850, 396), (850, 350))]:
        c.line(X(a[0]), Y(a[1]), X(b[0]), Y(b[1]))
    c.setDash()

    _pdf_rect(c, 978, 365, 200, 60, "#ffffff", COLORS["blue"], X, Y, scale, 10, 1)
    c.setFillColor(HexColor(COLORS["blue"])); c.setFont("Times-Italic", 8.4 * scale); c.drawCentredString(X(1078), Y(388), "Clinician review is explicit.")
    c.setFont("Times-Italic", 7.4 * scale); c.drawCentredString(X(1078), Y(407), "Recommendation-blocking missingness stays visible.")
    _pdf_rect(c, 1180, 852, 180, 55, "#ffffff", COLORS["blue"], X, Y, scale, 10, 1)
    c.setFont("Times-Italic", 8.3 * scale); c.drawCentredString(X(1270), Y(880), "Clinician judgment remains central.")

    # legend
    _pdf_rect(c, 1225, 330, 165, 430, "#fffdf8", "#a99b7b", X, Y, scale, 10, 1)
    c.setFillColor(HexColor(COLORS["ink"])); c.setFont("Times-Bold", 10 * scale); c.drawCentredString(X(1307.5), Y(356), "LEGEND")
    c.setFont("Helvetica-Bold", 7 * scale); c.drawString(X(1239), Y(385), "LINE STYLE")
    y = 410
    for label, dash in [("Primary flow", None), ("Optional / conditional", (2, 3)), ("Human review dependency", (5, 3))]:
        c.setStrokeColor(HexColor("#34383f")); c.setLineWidth(1 * scale); c.setDash(*(dash or ())) if dash else c.setDash(); c.line(X(1240), Y(y), X(1277), Y(y)); c.setDash(); c.setFillColor(HexColor(COLORS["ink"])); c.setFont("Helvetica", 6.5 * scale); c.drawString(X(1287), Y(y + 3), label); y += 31
    c.setFont("Helvetica-Bold", 7 * scale); c.drawString(X(1239), Y(y + 5), "COLOR GROUPS"); y += 31
    for label, fill, stroke in [("Case & safety", COLORS["blue_fill"], COLORS["blue"]), ("Specialist evidence", COLORS["green_fill"], COLORS["green"]), ("Challenge & consensus", COLORS["amber_fill"], COLORS["amber"]), ("Output & human support", COLORS["purple_fill"], COLORS["purple"]), ("Human review / gates", "#fff7ef", COLORS["orange"])]:
        _pdf_rect(c, 1240, y - 14, 18, 14, fill, stroke, X, Y, scale, 2, .7); c.setFillColor(HexColor(COLORS["ink"])); c.setFont("Helvetica", 6.5 * scale); c.drawString(X(1268), Y(y), label); y += 29

    c.setFillColor(HexColor(COLORS["ink"])); c.setFont("Helvetica-Bold", 8.4 * scale); c.drawString(X(72), Y(962), "Designed and developed by Ram Paragi")
    c.setFont("Helvetica", 7.7 * scale); c.drawString(X(72), Y(980), "LSU Health New Orleans School of Medicine · rparag@lsuhsc.edu")
    c.setFont("Times-Italic", 7.7 * scale); c.drawRightString(X(1340), Y(968), "Research concept for faculty review and multidisciplinary discussion.")
    c.showPage(); c.save()
    return out.getvalue()


def render_publication_figure(*, key_prefix: str, compact: bool = False) -> None:
    height = 520 if compact else 760
    components.html(
        f'<div style="width:100%;background:#fbf9f3;border:1px solid #e6e5e0;border-radius:12px;overflow:hidden">{publication_svg()}</div>',
        height=height,
        scrolling=False,
    )
    st.download_button(
        "Download Full Multi-Agent Architecture (PDF)",
        data=build_publication_pdf(),
        file_name=PDF_FILENAME,
        mime="application/pdf",
        key=f"{key_prefix}_download_full_architecture_pdf",
        use_container_width=True,
    )
