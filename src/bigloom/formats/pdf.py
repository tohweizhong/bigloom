"""PDF targets: WorldLoom enterprise PDF renderer, picture page by pypdf and reportlab.

Padding is an embedded file, so the page text does not change.
"""

from __future__ import annotations

from io import BytesIO
from typing import ClassVar

from ..evidence import random_chunks
from .base import Format, FormatHandler, Target

PDF_BALLAST_NAME = "bigloom-ballast.bin"


def pdf_add_picture(data: bytes, png: bytes, caption: str) -> bytes:
    """Append one A4 page with the picture and its caption at the end of the document."""
    from pypdf import PdfReader, PdfWriter
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    page_buf = BytesIO()
    c = canvas.Canvas(page_buf, pagesize=A4, invariant=True)
    w, h = A4
    c.drawImage(ImageReader(BytesIO(png)), 50, h / 2 - 150, width=w - 100, height=(w - 100) * 10 / 16)
    c.setFont("Helvetica", 10)
    c.drawString(50, h / 2 - 170, caption[:110])
    c.save()
    reader = PdfReader(BytesIO(data))
    extra = PdfReader(BytesIO(page_buf.getvalue())).pages[0]
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_page(extra)
    if reader.metadata:
        writer.add_metadata({k: str(v) for k, v in reader.metadata.items()})
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def _pad_pdf_once(data: bytes, need: int, seed: int) -> bytes:
    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter(clone_from=PdfReader(BytesIO(data)))
    writer.add_attachment(PDF_BALLAST_NAME, b"".join(random_chunks(need, seed)))
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def pad_pdf(data: bytes, target_bytes: int, seed: int) -> bytes:
    """Embed a file of seeded random bytes so that the PDF reaches at least `target_bytes`."""
    if len(data) >= target_bytes:
        return data
    need = target_bytes - len(data)
    out = _pad_pdf_once(data, need, seed)
    gap = target_bytes - len(out)
    if gap != 0:
        # The rewrite changes the size of the original objects. Correct the payload once.
        out = _pad_pdf_once(data, max(1, need + gap), seed)
    if len(out) < target_bytes:
        out = _pad_pdf_once(data, need + (target_bytes - len(out)) + 64, seed)
    return out


class PdfHandler(FormatHandler):
    fmt: ClassVar[Format] = "pdf"

    def add_picture(self, t: Target, payload: bytes, seed: int) -> bytes:
        return pdf_add_picture(payload, t.chart(seed), t.caption)

    def pad(self, payload: bytes, size_bytes: int, seed: int) -> bytes:
        return pad_pdf(payload, size_bytes, seed)
