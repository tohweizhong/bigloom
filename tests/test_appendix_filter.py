"""Tests for the appendix and ID filter (track appendix_filter_20261022)."""

from __future__ import annotations

import re
import zipfile
from dataclasses import replace
from io import BytesIO
from pathlib import Path

import pytest

from bigloom.formats import longform_filter as lf

ID = re.compile(r"\b(?:[A-Z]{2,6}-)+\d{4}\b")


@pytest.fixture(scope="module")
def world(tmp_path_factory: pytest.TempPathFactory):  # type: ignore[no-untyped-def]
    from bigloom.corpus import resolve_corpus

    w, _ = resolve_corpus(corpus_dir=None, out_dir=tmp_path_factory.mktemp("lf"), seed=42)
    return w


@pytest.fixture(scope="module")
def long_doc(world):  # type: ignore[no-untyped-def]
    """The WorldLoom long document of the CFO memo, as the enterprise renderer builds it."""
    from worldloom.render import enterprise

    ctx = enterprise.context(world, ("docx",))
    memo = next(ir for ir in world.artifact_irs if "CFO" in ir.title)
    return ctx.doc(memo)


def _texts(doc) -> list[str]:  # type: ignore[no-untyped-def]
    out: list[str] = [doc.reference, doc.title]
    for part in doc.all_parts():
        for node in (part, *part.children):
            out.append(node.heading)
            for block in node.blocks:
                out.extend([block.text, block.caption, block.source])
                if block.table is not None:
                    out.extend(c.label for c in block.table.columns)
                    for row in block.table.rows:
                        out.append(row.label)
                        out.extend(str(cell.value) for cell in row.cells.values())
    out.extend(f"{r.title} ({r.artifact_id})" for r in doc.related)
    out.extend(c.text for c in doc.comments)
    out.extend(c.resolution for c in doc.comments)
    out.extend(r.summary for r in doc.history)
    out.extend(str(v) for v in doc.metadata.values())
    out.extend(doc.fact_ids)
    return out


def test_worldloom_still_has_the_four_appendix_headings() -> None:
    """Fails when WorldLoom renames an appendix that the filter removes."""
    assert lf.missing_worldloom_headings() == []


def test_missing_heading_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lf, "REMOVED_APPENDICES", (*lf.REMOVED_APPENDICES, "Renamed appendix"))
    assert lf.missing_worldloom_headings() == ["Renamed appendix"]


def test_source_document_has_the_defects(long_doc) -> None:  # type: ignore[no-untyped-def]
    headings = {p.heading for p in long_doc.appendices}
    assert headings & set(lf.REMOVED_APPENDICES)
    assert any(ID.search(t) for t in _texts(long_doc) if t)


def test_filter_removes_appendices_and_reletters(long_doc) -> None:  # type: ignore[no-untyped-def]
    out = lf.filter_document(long_doc)
    assert not {p.heading for p in out.appendices} & set(lf.REMOVED_APPENDICES)
    kept = [p for p in long_doc.appendices if p.heading not in lf.REMOVED_APPENDICES]
    assert [p.heading for p in out.appendices] == [p.heading for p in kept]
    assert [p.number for p in out.appendices] == list("ABCDEFGHIJ"[: len(kept)])
    for part in out.appendices:
        for block in part.blocks:
            if block.number:
                assert block.number.startswith(f"{part.number}.")


def test_filter_leaves_no_worldloom_id(long_doc, world) -> None:  # type: ignore[no-untyped-def]
    out = lf.filter_document(long_doc)
    ids = lf.world_ids(world)
    for text in _texts(out):
        assert not any(i in text for i in ids if text), text
        assert not ID.search(text or ""), text


def test_readable_reference(long_doc) -> None:  # type: ignore[no-untyped-def]
    out = lf.filter_document(long_doc)
    assert out.reference != long_doc.reference
    assert re.fullmatch(r"[A-Z]{2,6}/[A-Z]{3}/\d{4}/\d{3}", out.reference), out.reference
    assert lf.readable_reference("CO-0001-FINANCE-ART-0024", "Government Technology Agency (Synthetic)", "2026-03", "ART-0024") == "GTA/FIN/2026/024"


def test_body_parts_are_unchanged_apart_from_ids(long_doc) -> None:  # type: ignore[no-untyped-def]
    out = lf.filter_document(long_doc)
    assert [p.heading for p in out.parts] == [p.heading for p in long_doc.parts]
    assert [p.number for p in out.parts] == [p.number for p in long_doc.parts]


def test_wrap_restores_longform_document_after_an_error() -> None:
    from worldloom import longform

    original = longform.document
    with pytest.raises(RuntimeError), lf.filtered_longform():
        assert longform.document is not original
        raise RuntimeError("render failed")
    assert longform.document is original


def test_filter_is_idempotent(long_doc) -> None:  # type: ignore[no-untyped-def]
    once = lf.filter_document(long_doc)
    assert lf.filter_document(once) == once
    assert replace(once) == once


def _package_text(path: Path) -> str:
    if path.suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        meta = " ".join(str(v) for v in (reader.metadata or {}).values())
        return meta + "\n" + "\n".join(p.extract_text() or "" for p in reader.pages)
    with zipfile.ZipFile(BytesIO(path.read_bytes())) as z:
        return "\n".join(
            z.read(n).decode("utf-8", "ignore")
            for n in z.namelist()
            if n.endswith((".xml", ".rels")) and "ballast" not in n
        )


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory):  # type: ignore[no-untyped-def]
    from bigloom.build import build_corpus

    out = tmp_path_factory.mktemp("lfbuild") / "out"
    entries = build_corpus(out, sizes_mb=(0.3,), seed=42)
    return out, entries


def test_targets_and_traps_hold_no_worldloom_id(built, world) -> None:  # type: ignore[no-untyped-def]
    out, entries = built
    from worldloom.world import World

    w = World.load(out / "corpus")
    ids = lf.world_ids(w)
    for e in entries:
        for rel in (e.target_file, e.distractor_file):
            text = _package_text(out / rel)
            found = sorted({i for i in ids if re.search(rf"(?<![\w-]){re.escape(i)}(?![\w-])", text)})
            assert not found, f"{rel}: {found[:5]}"
            for heading in lf.REMOVED_APPENDICES:
                assert heading not in text, f"{rel}: {heading}"


def test_fact_depth_still_holds(built) -> None:  # type: ignore[no-untyped-def]
    _, entries = built
    assert all(e.text_unit_index >= 6 for e in entries)


def test_scrub_ir_drops_lineage_and_id_cells(world) -> None:  # type: ignore[no-untyped-def]
    workbook = next(ir for ir in world.artifact_irs if any(s.heading == "Lineage" for s in ir.sections))
    out = lf.scrub_ir(workbook)
    assert not any(s.heading in lf.REMOVED_IR_SECTIONS for s in out.sections)
    for sec in out.sections:
        if sec.table is None:
            continue
        for row in sec.table.rows:
            assert not any(ID.fullmatch(str(c.value or "")) for c in row.cells.values()), sec.heading


def test_bare_ids_in_comments_become_plain_words(world, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    names = lf.id_names(world)
    fact = next(f for f in world.facts if getattr(f, "text_value", None))
    monkeypatch.setattr(lf, "_NAMES", names)
    out = lf._clean(f"Please confirm this section states {fact.id} (confirmed).")
    assert fact.id not in out
    assert fact.text_value.split()[0] in out
    assert lf._clean("See the model (ART-0002).") == "See the model."


def test_review_record_keeps_one_row_for_each_comment_text(long_doc) -> None:  # type: ignore[no-untyped-def]
    """Loop v2: a reviewer does not write the same comment on every section."""
    from dataclasses import replace

    from bigloom.formats.longform_filter import filter_document

    assert long_doc.comments, "the fixture document has a review record"
    first = long_doc.comments[0]
    doc = replace(long_doc, comments=tuple(replace(first, part=str(i)) for i in range(1, 5)))
    out = filter_document(doc)
    assert len(out.comments) == 1
    assert out.comments[0].part == "1"


def test_related_documents_table_has_no_copied_column_or_title_as_reference() -> None:
    """Loop v2: the register shows a reference, and type and role are not the same column twice."""
    from worldloom.models import Cell, Column, Row, Table

    from bigloom.formats import longform_filter as lf

    table = Table(key="related", title="Reference", columns=[
        Column(key="title", label="Title"), Column(key="type", label="Type"), Column(key="role", label="Role in pack")],
        rows=[Row(key=f"ART-00{n}", label=f"ART-00{n}", cells={
            "title": Cell(value=f"March {t}"), "type": Cell(value=t.capitalize()), "role": Cell(value=t.capitalize())})
            for n, t in ((19, "Board Paper"), (24, "Exco Update"))])
    refs = getattr(lf, "_REFS", {})  # the old code has no map, so its failure shows the behaviour
    refs.update({"ART-0019": "GTA/FIN/2026/019", "ART-0024": "GTA/FIN/2026/024"})
    try:
        out = lf._table(table)
    finally:
        refs.clear()
    assert [c.key for c in out.columns] == ["title", "type"]
    assert [r.label for r in out.rows] == ["GTA/FIN/2026/019", "GTA/FIN/2026/024"]


def test_a_figure_table_with_two_equal_columns_keeps_both() -> None:
    """Only the related documents table drops copied columns. A planted figure must stay."""
    from worldloom.models import Cell, Column, Row, Table

    from bigloom.formats import longform_filter as lf

    table = Table(key="variance", title="Budget against actual", columns=[
        Column(key="budget", label="Budget"), Column(key="actual", label="Actual")],
        rows=[Row(key="r1", label="Services", cells={"budget": Cell(value=48.1), "actual": Cell(value=48.1)})])
    out = lf._table(table)
    assert [c.key for c in out.columns] == ["budget", "actual"]
