"""Word handler tests: text fact in the IR, picture after render, v0.1 trap, ZIP padding."""

from __future__ import annotations

import zipfile
from io import BytesIO

from _format_fixtures import docx_bytes, ir_with_sections, target
from docx import Document

from bigloom.evidence import BALLAST_NAME, pad_ooxml
from bigloom.formats import EVIDENCE_DEPTH, handler_for


def test_golden_ir_puts_text_fact_at_depth_and_keeps_title() -> None:
    h, t = handler_for("docx"), target("docx")
    ir = h.golden_ir(t, ir_with_sections(10))
    assert ir.sections[EVIDENCE_DEPTH].heading == "Revised revenue forecast"
    cells = [c.value for r in ir.sections[EVIDENCE_DEPTH].table.rows for c in r.cells.values()]
    assert t.text_golden in cells and t.text_canary not in cells
    assert ir.title == "CFO Variance Memo"


def test_canary_ir_holds_both_canaries_and_no_golden() -> None:
    h, t = handler_for("docx"), target("docx")
    ir = h.canary_ir(t, ir_with_sections(10))
    cells = [str(c.value) for r in ir.sections[EVIDENCE_DEPTH].table.rows for c in r.cells.values()]
    assert t.text_canary in cells and t.image_canary in cells
    assert t.text_golden not in cells and t.image_golden not in cells
    # The trap is the WorldLoom v0.1 revision, so the title needs no draft marker.
    assert ir.title == "CFO Variance Memo"
    assert h.trap_kind() == "v0.1.docx"


def test_short_document_takes_the_fact_at_the_end() -> None:
    ir = handler_for("docx").golden_ir(target("docx"), ir_with_sections(3))
    assert ir.sections[-1].heading == "Revised revenue forecast"


def test_finish_target_adds_one_picture_and_reaches_size() -> None:
    h, t = handler_for("docx"), target("docx", size_bytes=300_000)
    out = h.finish_target(t, docx_bytes(), seed=7)
    assert 300_000 <= len(out) <= 300_512
    doc = Document(BytesIO(out))
    assert len(doc.inline_shapes) == 1
    text = "\n".join(p.text for p in doc.paragraphs)
    assert t.caption in text
    assert t.image_golden not in text
    assert h.finish_target(t, docx_bytes(), seed=7) == out


def test_finish_trap_keeps_the_rendered_revision() -> None:
    payload = docx_bytes()
    assert handler_for("docx").finish_trap(target("docx"), payload) == payload


def test_pad_ooxml_reaches_exact_size_and_stays_readable() -> None:
    raw = docx_bytes(1)
    padded = pad_ooxml(raw, 200_000, seed=3)
    assert 200_000 <= len(padded) <= 200_512
    assert BALLAST_NAME in zipfile.ZipFile(BytesIO(padded)).namelist()
    assert Document(BytesIO(padded)).paragraphs[0].text.startswith("Paragraph 0")
    assert pad_ooxml(raw, 200_000, seed=3) == padded
    assert pad_ooxml(raw, 10, seed=3) == raw


def test_fact_goes_before_sign_off_sections() -> None:
    from worldloom.models import ArtifactSection

    ir = ir_with_sections(4)
    tail = [ArtifactSection(heading="Approval"), ArtifactSection(heading="Supporting facts", hidden=True)]
    ir = ir.model_copy(update={"sections": [*ir.sections, *tail]})
    out = handler_for("docx").golden_ir(target("docx"), ir)
    assert [s.heading for s in out.sections][4:] == ["Revised revenue forecast", "Approval", "Supporting facts"]


def test_reader_handles_a_package_above_512_mib(tmp_path) -> None:  # type: ignore[no-untyped-def]
    """The padding member alone takes the package past the WorldLoom 512 MiB budget."""
    import hashlib

    from worldloom.native_artifacts import NativeArtifactError, inspect_artifact

    from bigloom.qualify import inspect_file_bytes

    raw = docx_bytes()
    buf = BytesIO(raw)
    zero = bytes(1 << 20)
    with zipfile.ZipFile(buf, "a", zipfile.ZIP_DEFLATED) as zf, zf.open(BALLAST_NAME, "w", force_zip64=True) as fh:
        for _ in range(600):
            fh.write(zero)
    big = buf.getvalue()
    try:
        inspect_artifact(big, "docx")
        raise AssertionError("WorldLoom accepted a package above its budget")
    except NativeArtifactError:
        pass
    snap = inspect_file_bytes(big, ".docx")
    assert any(u.text.startswith("Paragraph 0") for u in snap.units)
    assert snap.metrics["file_size_bytes"] == len(big)
    assert snap.sha256 == hashlib.sha256(big).hexdigest()


def test_text_fact_table_shows_each_measure_once_per_row() -> None:
    h, t = handler_for("docx"), target("docx")
    table = h.golden_ir(t, ir_with_sections(10)).sections[EVIDENCE_DEPTH].table
    for r in table.rows:
        row_text = [r.label, *(str(c.value) for c in r.cells.values())]
        assert row_text.count(r.label) == 1
    assert [c.label for c in table.columns] == ["Value"]
