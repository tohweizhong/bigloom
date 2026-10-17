"""One handler for each target format. See `base.FormatHandler`."""

from __future__ import annotations

from .base import EVIDENCE_DEPTH, Format, FormatHandler, Target
from .docx import DocxHandler
from .pdf import PdfHandler
from .pptx import PptxHandler
from .xlsx import XlsxHandler

FORMATS: tuple[Format, ...] = ("docx", "xlsx", "pptx", "pdf")
HANDLERS: dict[str, FormatHandler] = {h.fmt: h for h in (DocxHandler(), PdfHandler(), PptxHandler(), XlsxHandler())}


def handler_for(fmt: str) -> FormatHandler:
    """Return the handler for `fmt`. Raise ValueError for an unknown format."""
    try:
        return HANDLERS[fmt]
    except KeyError:
        raise ValueError(f"Unsupported format '{fmt}'.") from None


__all__ = ["EVIDENCE_DEPTH", "FORMATS", "HANDLERS", "Format", "FormatHandler", "Target", "handler_for"]
