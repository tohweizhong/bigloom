"""Word targets: WorldLoom enterprise DOCX renderer, picture by python-docx.

The trap is the WorldLoom `v0.1` revision of the same document, rendered with the canary.
"""

from __future__ import annotations

from io import BytesIO
from typing import ClassVar

from ..evidence import pad_ooxml
from .base import Format, FormatHandler, Target


def docx_add_picture(data: bytes, png: bytes, caption: str, *, at: float = 0.6) -> bytes:
    """Insert a picture and its caption at fraction `at` of the body paragraphs."""
    from docx import Document
    from docx.shared import Inches

    doc = Document(BytesIO(data))
    paras = doc.paragraphs
    anchor = paras[min(len(paras) - 1, max(0, int(len(paras) * at)))]
    pic = doc.add_paragraph()
    pic.add_run().add_picture(BytesIO(png), width=Inches(6.0))
    cap = doc.add_paragraph(caption)
    anchor._p.addprevious(pic._p)
    anchor._p.addprevious(cap._p)
    out = BytesIO()
    doc.save(out)
    return out.getvalue()


class DocxHandler(FormatHandler):
    fmt: ClassVar[Format] = "docx"
    # The v0.1 revision is a draft by its own version number, so the title stays as it is.
    draft_suffix: ClassVar[str] = ""

    def trap_kind(self) -> str:
        return "v0.1.docx"

    def add_picture(self, t: Target, payload: bytes, seed: int) -> bytes:
        return docx_add_picture(payload, t.chart(seed), t.caption)

    def pad(self, payload: bytes, size_bytes: int, seed: int) -> bytes:
        return pad_ooxml(payload, size_bytes, seed)
