"""Word targets: WorldLoom enterprise DOCX renderer, picture by python-docx.

The trap is the WorldLoom `v0.1` revision of the same document, rendered with the canary.
"""

from __future__ import annotations

from io import BytesIO
from typing import ClassVar

from ..evidence import pad_ooxml
from .base import Format, FormatHandler, Target


def docx_add_picture(data: bytes, png: bytes, caption: str, *, near: str | None = None, at: float = 0.6) -> bytes:
    """Insert a picture and its caption.

    With `near`, the picture goes directly after the first table that holds a cell with that
    text: the text fact table. A figure then sits next to the figures it belongs to. Without a
    match, the picture goes at fraction `at` of the body paragraphs.
    """
    from docx import Document
    from docx.shared import Inches

    doc = Document(BytesIO(data))
    pic = doc.add_paragraph()
    pic.add_run().add_picture(BytesIO(png), width=Inches(6.0))
    table = None
    if near:
        table = next((tb for tb in reversed(doc.tables) for cell in tb._cells if cell.text.strip() == near), None)
    if table is not None:
        row = table.add_row()
        row.cells[0].text = caption
        table._tbl.addnext(pic._p)
    else:
        cap = doc.add_paragraph(caption)
        paras = [p for p in doc.paragraphs if p._p is not pic._p and p._p is not cap._p]
        anchor = paras[min(len(paras) - 1, max(0, int(len(paras) * at)))]
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
        return docx_add_picture(payload, t.chart(seed), t.caption, near=t.heading)

    def pad(self, payload: bytes, size_bytes: int, seed: int) -> bytes:
        return pad_ooxml(payload, size_bytes, seed)
