"""Phase 5 tests: each realism reading fires on a DOCX or PDF file with that defect."""

from __future__ import annotations

from io import BytesIO

import pytest

from bigloom.models import EvalCase, ViolationCode
from bigloom.qualify import inspect_file_bytes, qualify_corpus
from bigloom.realism import file_findings

PROSE = [
    "Revenue for the quarter came in below plan because two stores closed for refits in March.",
    "The controller traced most of the gap to delayed supplier credits in the fresh category.",
    "Head office costs held flat, so the shortfall fell straight through to operating profit.",
    "Digital sales grew faster than the stores, although margin there stayed thinner than planned.",
    "The board asked for a revised forecast once the supplier credits are booked next month.",
    "Inventory write-downs were smaller than last year after the new markdown policy took effect.",
    "The audit team found no control breach, but it asked for a named owner of the mapping table.",
    "Cash conversion improved because payables terms with two large suppliers moved to sixty days.",
]


def _docx(paragraphs: list[str]) -> bytes:
    from docx import Document

    doc = Document()
    for text in paragraphs:
        doc.add_paragraph(text)
    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _pdf_sized(pages: list[list[tuple[int, str]]]) -> bytes:
    """Return a PDF whose lines carry their own font size, as WorldLoom sets tables smaller."""
    from reportlab.pdfgen import canvas

    buf = BytesIO()
    c = canvas.Canvas(buf, invariant=True)
    for lines in pages:
        y = 800
        for size, line in lines:
            c.setFont("Helvetica", size)
            c.drawString(40, y, line)
            y -= size + 4
        c.showPage()
    c.save()
    return buf.getvalue()


def _pdf(pages: list[list[str]], picture_on: int | None = None) -> bytes:
    from PIL import Image
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    buf = BytesIO()
    c = canvas.Canvas(buf, invariant=True)
    for number, lines in enumerate(pages, 1):
        y = 800
        for line in lines:
            c.drawString(40, y, line)
            y -= 14
        if picture_on == number:
            img = BytesIO()
            Image.new("RGB", (40, 30), "red").save(img, "PNG")
            c.drawImage(ImageReader(BytesIO(img.getvalue())), 40, 300, width=200, height=150)
        c.showPage()
    c.save()
    return buf.getvalue()


def _codes(payload: bytes, ext: str) -> set[str]:
    return {f.code for f in file_findings(inspect_file_bytes(payload, ext))}


def test_clean_docx_has_no_findings() -> None:
    assert _codes(_docx(PROSE), ".docx") == set()


def test_repeated_sentences_fire() -> None:
    assert "repeated_sentences" in _codes(_docx(PROSE[:4] + PROSE[:4] + PROSE[:2]), ".docx")


def test_repeated_sentences_mask_figures() -> None:
    template = "The verified figure for unit {n} is SGD {n},482,117 for the quarter under review."
    assert "repeated_sentences" in _codes(_docx(PROSE[:3] + [template.format(n=i) for i in range(1, 6)]), ".docx")


def test_template_openers_fire() -> None:
    lines = [f"In this period the team reviewed item number {w} against the approved plan." for w in "abcdefg"]
    assert "template_openers" in _codes(_docx(PROSE[:6] + [line.replace("number", f"case {i}") for i, line in enumerate(lines)]), ".docx")


def test_header_repeats_fire() -> None:
    header = "Southern Cross Retail Group FY2026 Final Audit Report"
    body = [p for text in PROSE for p in (header, text)]
    assert "header_repeats" in _codes(_docx(body), ".docx")


def test_cut_words_fire_in_pdf() -> None:
    page = [*PROSE[:3], "Classificatio", "n", "Responsibilit", "y", "Reconciliatio", "n", *PROSE[3:]]
    assert "cut_words" in _codes(_pdf([PROSE, page, PROSE]), ".pdf")


def test_thin_page_fires_and_picture_page_is_exempt() -> None:
    thin = ["Figure: revenue by unit"]
    assert "thin_pages" in _codes(_pdf([PROSE, thin, PROSE]), ".pdf")
    assert "thin_pages" not in _codes(_pdf([PROSE, thin, PROSE], picture_on=2), ".pdf")


def test_running_heads_do_not_count_as_header_repeats() -> None:
    head = "Junipera Commerce Group | Incident RCA | Confidential"
    pages = [[head, *PROSE[i : i + 4]] for i in range(0, 8, 2)] * 2
    assert "header_repeats" not in _codes(_pdf(pages), ".pdf")


def test_gate_reports_realism_violation_with_file_name() -> None:
    snaps = {"large/bad.docx": inspect_file_bytes(_docx(PROSE[:4] * 3), ".docx")}
    case = EvalCase(id="c1", query="q", target_file="large/bad.docx", modality="text", golden_value="SGD 9,999,999")
    report = qualify_corpus(snaps, [case], check_retrieval=False)
    hits = [v for v in report.violations if v.code == ViolationCode.REPEATED_SENTENCES]
    assert hits and hits[0].case_id == "file:large/bad.docx"
    off = qualify_corpus(snaps, [case], check_retrieval=False, check_realism=False)
    assert not [v for v in off.violations if v.code == ViolationCode.REPEATED_SENTENCES]


@pytest.mark.parametrize("ext", [".pptx", ".xlsx"])
def test_other_formats_are_not_read_yet(ext: str) -> None:
    from worldloom.native_artifacts import NativeSnapshot, NativeUnit

    snap = NativeSnapshot(format=ext[1:], sha256="0" * 64, units=(NativeUnit(locator="slide:1/text", text="x"),), metrics={})
    assert file_findings(snap) == []


def test_pdf_table_text_in_a_smaller_font_is_not_read_as_prose() -> None:
    row = "Source for these figures is the finance system; please keep the reference."
    body = [(10, p) for p in PROSE]
    end = [(10, "The paper closes with the approval record and the list of figures.")]
    pages = [body[:2], body[2:5] + [(8, row)] * 6, body[5:] + [(8, row)] * 6, end]
    assert "repeated_sentences" not in _codes(_pdf_sized(pages), ".pdf")
    same_size = [body[:2], body[2:5] + [(10, row)] * 6, body[5:] + [(10, row)] * 6, end]
    assert "repeated_sentences" in _codes(_pdf_sized(same_size), ".pdf")


def test_pdf_cover_summary_does_not_count_as_a_repeat() -> None:
    body = [(10, p) for p in PROSE]
    end = [(10, "The paper closes with the approval record and the list of figures.")]
    # The cover quotes the first three sentences. The body holds each sentence once.
    pages = [body[:3], body[:6], body[6:], end]
    assert "repeated_sentences" not in _codes(_pdf_sized(pages), ".pdf")
    # The same repeat inside the body still counts.
    assert "repeated_sentences" in _codes(_pdf_sized([end, body[:6], body[:3] + body[6:], end]), ".pdf")
