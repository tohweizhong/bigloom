"""PDF handler tests: text fact in the IR, picture page after render, draft trap, attachment padding."""

from __future__ import annotations

from io import BytesIO

from _format_fixtures import ir_with_sections, pdf_bytes, target
from pypdf import PdfReader

from bigloom.formats import EVIDENCE_DEPTH, handler_for
from bigloom.formats.pdf import PDF_BALLAST_NAME, pad_pdf


def test_canary_ir_marks_the_draft_title() -> None:
    h, t = handler_for("pdf"), target("pdf")
    ir = h.canary_ir(t, ir_with_sections(10))
    assert ir.title == "CFO Variance Memo (draft)"
    assert ir.sections[EVIDENCE_DEPTH].heading == "Revised revenue forecast"
    assert h.trap_kind() == "pdf"


def test_finish_target_inserts_picture_page_in_the_middle() -> None:
    h, t = handler_for("pdf"), target("pdf", size_bytes=250_000)
    out = h.finish_target(t, pdf_bytes(4), seed=9)
    assert 250_000 <= len(out) <= 254_096
    reader = PdfReader(BytesIO(out))
    assert len(reader.pages) == 5
    assert reader.pages[2].images, "the picture page sits at the middle"
    assert t.chart_title in reader.pages[2].extract_text()
    all_text = "\n".join(p.extract_text() for p in reader.pages)
    assert t.image_golden not in all_text
    assert "Page 1 text" in reader.pages[0].extract_text()


def test_pad_pdf_reaches_size_and_stays_readable() -> None:
    raw = pdf_bytes(1)
    padded = pad_pdf(raw, 150_000, seed=5)
    assert 150_000 <= len(padded) <= 154_096
    reader = PdfReader(BytesIO(padded))
    assert "Page 1 text" in reader.pages[0].extract_text()
    assert PDF_BALLAST_NAME in reader.attachments
    assert pad_pdf(raw, 10, seed=5) == raw
