"""Phase 0, T4: add a picture fact to finished WorldLoom files, and an evidence slide to the deck.

Run from the BigLoom root after t3_ranking.py:
    .venv/bin/python conductor/tracks/worldloom_native_bigloom_20261016/phase0/t4_post_render.py
"""

from __future__ import annotations

import json
import sys
from io import BytesIO
from pathlib import Path

from docx import Document
from docx.shared import Inches
from PIL import Image, ImageDraw, ImageFont
from pptx import Presentation
from pptx.util import Inches as PInches
from pptx.util import Pt
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from worldloom.native_artifacts import inspect_artifact

SRC = Path("runs/phase0/t3")
OUT = Path("runs/phase0/t4")
IMAGE_VALUE = "38.47%"
TEXT_VALUE = "SGD 6,204,918"
CAPTION = "Figure: Peak utilisation of the close orchestrator by week"


def chart_png() -> bytes:
    """Draw one bar chart whose peak bar label holds the image value."""
    img = Image.new("RGB", (1600, 900), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 40)
    except OSError:
        font = ImageFont.load_default()
    heights = [210, 320, 460, 610, 380, 290]
    for i, h in enumerate(heights):
        x0 = 160 + i * 220
        draw.rectangle([x0, 820 - h, x0 + 140, 820], fill=(0, 84, 147))
        draw.text((x0, 840), f"W{i + 1}", fill="black", font=font)
    draw.text((160 + 3 * 220 - 10, 820 - 610 - 60), IMAGE_VALUE, fill="black", font=font)
    draw.line([120, 820, 1500, 820], fill="black", width=4)
    buf = BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def docx_add(data: bytes, png: bytes) -> bytes:
    """Insert a picture and caption at 60 percent of the body."""
    doc = Document(BytesIO(data))
    paras = doc.paragraphs
    anchor = paras[int(len(paras) * 0.6)]
    pic_par = doc.add_paragraph()
    pic_par.add_run().add_picture(BytesIO(png), width=Inches(6.0))
    cap = doc.add_paragraph(CAPTION)
    anchor._p.addprevious(pic_par._p)
    anchor._p.addprevious(cap._p)
    out = BytesIO()
    doc.save(out)
    return out.getvalue()


def pptx_add(data: bytes, png: bytes) -> bytes:
    """Add an evidence slide with the text value and the picture, at the middle of the deck."""
    prs = Presentation(BytesIO(data))
    layout = prs.slide_layouts[5] if len(prs.slide_layouts) > 5 else prs.slide_layouts[-1]
    slide = prs.slides.add_slide(layout)
    if slide.shapes.title is not None:
        slide.shapes.title.text = "Approved revenue reserve"
    box = slide.shapes.add_textbox(PInches(0.6), PInches(1.4), PInches(5.5), PInches(1.0))
    box.text_frame.text = f"Approved revenue reserve: {TEXT_VALUE}"
    box.text_frame.paragraphs[0].runs[0].font.size = Pt(20)
    slide.shapes.add_picture(BytesIO(png), PInches(6.3), PInches(1.4), width=PInches(6.4))
    ids = prs.slides._sldIdLst
    new = ids[-1]
    ids.remove(new)
    ids.insert(len(ids) // 2, new)
    out = BytesIO()
    prs.save(out)
    return out.getvalue()


def pdf_add(data: bytes, png: bytes) -> bytes:
    """Insert one A4 page with the picture and caption at the middle of the document."""
    page_buf = BytesIO()
    c = canvas.Canvas(page_buf, pagesize=A4)
    w, h = A4
    c.drawImage(ImageReader(BytesIO(png)), 50, h / 2 - 150, width=w - 100, height=(w - 100) * 9 / 16)
    c.setFont("Helvetica", 10)
    c.drawString(50, h / 2 - 170, CAPTION)
    c.save()
    reader = PdfReader(BytesIO(data))
    extra = PdfReader(BytesIO(page_buf.getvalue())).pages[0]
    writer = PdfWriter()
    mid = len(reader.pages) // 2
    for i, page in enumerate(reader.pages):
        if i == mid:
            writer.add_page(extra)
        writer.add_page(page)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def check(name: str, before: bytes, after: bytes, ext: str) -> dict[str, object]:
    """Reopen the file and confirm the size change, the unit counts, and that the image value is not in the text."""
    if ext == "pdf":
        b, a = PdfReader(BytesIO(before)), PdfReader(BytesIO(after))
        text = "\n".join(p.extract_text() or "" for p in a.pages)
        return {"pages_before": len(b.pages), "pages_after": len(a.pages), "image_value_in_text": IMAGE_VALUE in text}
    sb, sa = inspect_artifact(before, ext), inspect_artifact(after, ext)
    text = "\n".join(u.text for u in sa.units)
    row: dict[str, object] = {
        "units_before": len(sb.units),
        "units_after": len(sa.units),
        "image_value_in_text": IMAGE_VALUE in text,
    }
    if ext == "pptx":
        row["slides_before"] = len(Presentation(BytesIO(before)).slides)
        row["slides_after"] = len(Presentation(BytesIO(after)).slides)
        row["text_value_found"] = TEXT_VALUE in text
    return row


def main() -> int:
    png = chart_png()
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = {
        "target-art-0003-cfo-variance-memo.docx": docx_add,
        "target-art-0010-exec-committee-summary.pptx": pptx_add,
        "target-art-0007-incident-rca.pdf": pdf_add,
    }
    report = {}
    for name, fn in jobs.items():
        before = (SRC / name).read_bytes()
        after = fn(before, png)
        (OUT / name).write_bytes(after)
        report[name] = check(name, before, after, name.rsplit(".", 1)[-1])
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
