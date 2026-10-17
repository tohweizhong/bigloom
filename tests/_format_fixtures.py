"""Small shared inputs for the format handler tests."""

from __future__ import annotations

from io import BytesIO

from worldloom.models import ArtifactIR, ArtifactSection

from bigloom.formats import Target


def target(fmt: str, size_bytes: int = 200_000) -> Target:
    return Target(
        file_id=f"bl-001-{fmt}-test", fmt=fmt, size_bytes=size_bytes, ir_id="ART-0001",  # type: ignore[arg-type]
        artifact_type="cfo_variance_memo", label="revised revenue forecast",
        chart_title="Revised gross margin forecast by business unit", chart_categories=("Food", "Digital", "Home"),
        chart_peak=1, text_question="Q?", image_question="Q?", text_golden="SGD 4,827,319",
        text_canary="SGD 1,154,920", image_golden="38.47%", image_canary="14.29%",
    )


def ir_with_sections(n: int) -> ArtifactIR:
    sections = [ArtifactSection(heading=f"Section {i}", body=f"Body text {i}.") for i in range(1, n + 1)]
    return ArtifactIR(id="ART-0001", intent_id="INT-0001", title="CFO Variance Memo", sections=sections)


def docx_bytes(paragraphs: int = 20) -> bytes:
    from docx import Document

    doc = Document()
    for i in range(paragraphs):
        doc.add_paragraph(f"Paragraph {i} of the memo body.")
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def pdf_bytes(pages: int = 4) -> bytes:
    from reportlab.pdfgen import canvas

    buf = BytesIO()
    c = canvas.Canvas(buf, invariant=True)
    for i in range(pages):
        c.drawString(72, 720, f"Page {i + 1} text")
        c.showPage()
    c.save()
    return buf.getvalue()
