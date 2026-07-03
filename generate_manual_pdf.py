from pathlib import Path
import html
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "K_WaterGuard_AI_Student_Manual.md"
OUTPUT = ROOT / "K_WaterGuard_AI_Student_Manual.pdf"


def clean_inline_markdown(text):
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", text)
    text = text.replace("**", "")
    text = text.replace("__", "")
    return text


def make_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ManualTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=34,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=18,
        ),
        "subtitle": ParagraphStyle(
            "ManualSubtitle",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=13,
            leading=18,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#2563eb"),
            spaceAfter=28,
        ),
        "h1": ParagraphStyle(
            "Heading1Readable",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=23,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=14,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "Heading2Readable",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1f2937"),
            spaceBefore=12,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "BodyReadable",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10.6,
            leading=15.2,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#111827"),
            spaceAfter=7,
        ),
        "bullet": ParagraphStyle(
            "BulletReadable",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10.4,
            leading=14.8,
            leftIndent=18,
            firstLineIndent=-10,
            textColor=colors.HexColor("#111827"),
            spaceAfter=4,
        ),
        "code": ParagraphStyle(
            "CodeReadable",
            fontName="Courier",
            fontSize=8.6,
            leading=10.6,
            leftIndent=0,
            rightIndent=0,
            textColor=colors.HexColor("#111827"),
            backColor=colors.HexColor("#f3f4f6"),
            borderColor=colors.HexColor("#d1d5db"),
            borderWidth=0.5,
            borderPadding=7,
            spaceBefore=5,
            spaceAfter=9,
        ),
        "toc": ParagraphStyle(
            "TocReadable",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10.2,
            leading=14.5,
            textColor=colors.HexColor("#111827"),
            spaceAfter=3,
        ),
        "footer": ParagraphStyle(
            "FooterReadable",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            textColor=colors.HexColor("#6b7280"),
            alignment=TA_CENTER,
        ),
    }


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawCentredString(
        A4[0] / 2,
        0.38 * inch,
        f"K-WaterGuard AI Student Technical Manual | Page {doc.page}",
    )
    canvas.restoreState()


def parse_manual(source_path, styles):
    lines = source_path.read_text(encoding="utf-8").splitlines()
    story = []
    headings = []
    paragraph = []
    code = []
    in_code = False
    first_title = True

    def flush_paragraph():
        nonlocal paragraph
        if not paragraph:
            return
        text = " ".join(item.strip() for item in paragraph).strip()
        if text:
            story.append(Paragraph(clean_inline_markdown(html.escape(text)), styles["body"]))
        paragraph = []

    def flush_code():
        nonlocal code
        if not code:
            return
        code_text = "\n".join(code)
        story.append(Preformatted(code_text, styles["code"], maxLineLength=82))
        code = []

    for line in lines:
        if line.startswith("```"):
            if in_code:
                flush_code()
                in_code = False
            else:
                flush_paragraph()
                in_code = True
                code = []
            continue

        if in_code:
            code.append(line)
            continue

        if not line.strip():
            flush_paragraph()
            continue

        heading = re.match(r"^(#{1,3})\s+(.*)$", line)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            text = heading.group(2).strip()

            if first_title and level == 1:
                story.append(Spacer(1, 1.5 * inch))
                story.append(Paragraph(html.escape(text), styles["title"]))
                story.append(Paragraph("Readable classroom PDF edition", styles["subtitle"]))
                story.append(Paragraph("Prepared for students learning agentic AI, data automation, dashboards, and deployment.", styles["body"]))
                story.append(PageBreak())
                story.append(Paragraph("Table of Contents", styles["h1"]))
                first_title = False
                continue

            if level == 2:
                headings.append(text)
                story.append(Paragraph(html.escape(text), styles["h1"]))
            else:
                story.append(Paragraph(html.escape(text), styles["h2"]))
            continue

        stripped = line.strip()
        if stripped.startswith("- "):
            flush_paragraph()
            text = stripped[2:].strip()
            story.append(Paragraph("- " + clean_inline_markdown(html.escape(text)), styles["bullet"]))
            continue

        paragraph.append(line)

    flush_paragraph()
    flush_code()

    toc = []
    for index, heading in enumerate(headings, 1):
        toc.append([Paragraph(f"{index}. {html.escape(heading)}", styles["toc"])])

    toc_table = Table(toc, colWidths=[6.65 * inch]) if toc else None
    if toc_table is not None:
        toc_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))

    final_story = []
    inserted_toc = False
    for item in story:
        final_story.append(item)
        if not inserted_toc and isinstance(item, Paragraph) and item.getPlainText() == "Table of Contents":
            if toc_table is not None:
                final_story.append(Spacer(1, 0.1 * inch))
                final_story.append(toc_table)
            final_story.append(PageBreak())
            inserted_toc = True

    return final_story


def build_pdf():
    styles = make_styles()
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=0.68 * inch,
        leftMargin=0.68 * inch,
        topMargin=0.72 * inch,
        bottomMargin=0.68 * inch,
        title="K-WaterGuard AI Student Technical Manual",
        author="K-WaterGuard AI",
    )
    story = parse_manual(SOURCE, styles)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    build_pdf()
