"""Tests for the realism metric vector (`realism_metrics.py`)."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from bigloom import realism_metrics as rm

PROSE = [
    "Revenue for the quarter came in below plan because two sites closed for refits in March.",
    "The controller traced most of the gap to delayed supplier credits in the operations line.",
    "Head office costs held flat, so the shortfall fell straight through to the surplus line.",
    "Digital services grew faster than the counters, although cost recovery stayed below target.",
]


def _docx(path: Path, paragraphs: list[str]) -> Path:
    from docx import Document

    doc = Document()
    for text in paragraphs:
        doc.add_paragraph(text)
    buf = BytesIO()
    doc.save(buf)
    path.write_bytes(buf.getvalue())
    return path


def test_defects_count_ids_and_terms_per_thousand_words() -> None:
    text = " ".join(["word"] * 994) + " FACT-0001 ART-0002 gross profit SKU stores"  # 1000 words
    d = rm.defects(text)
    assert d["wl_id_per_k"] == round(1000 * 2 / 1000, 2)
    assert d["commercial_per_k"] == round(1000 * 1 / 1000, 2)
    assert d["retail_per_k"] == round(1000 * 2 / 1000, 2)


def test_dates_after_the_document_date() -> None:
    text = "Date: 3 Apr 2026. The close ended on 1 Apr 2026. The review is set for 9 May 2026."
    assert rm.defects(text)["dates_after_doc_date"] == 1


def test_sentences_mask_figures_and_drop_short_ones() -> None:
    out = rm.sentences("Revenue was SGD 4,827,319 against a budget of SGD 5m this month. Too short.")
    assert out == ["Revenue was SGD # against a budget of SGD #m this month."]


def test_size_twins_do_not_count_as_reuse(tmp_path: Path) -> None:
    _docx(tmp_path / "a_2mb.docx", PROSE)
    _docx(tmp_path / "a_5mb.docx", PROSE)
    _docx(tmp_path / "b.docx", [p.replace("quarter", "month").replace("controller", "officer") for p in PROSE[:2]] + PROSE[2:3])
    result = rm.metrics(tmp_path)
    assert ("a_2mb.docx", "a_5mb.docx") in [tuple(t) for t in result["size_twins"]]
    # Only PROSE[2] is shared between a* and b: 1 sentence in each of 3 files, of 4 + 4 + 3 sentences.
    assert result["cross_document_reuse"] == round(3 / 11, 3)


def test_grader_digest_is_stable_and_recorded(tmp_path: Path) -> None:
    _docx(tmp_path / "a.docx", PROSE)
    result = rm.metrics(tmp_path)
    assert result["grader_sha256"] == rm.grader_digest() == rm.grader_digest()
    assert len(result["grader_sha256"]) == 64
    vector = rm.summary(result)
    assert set(vector) >= {"wl_id_per_k", "commercial_per_k", "within_file_repeat", "cross_document_reuse"}


def test_manifest_document_type_marks_twins(tmp_path: Path) -> None:
    import json

    _docx(tmp_path / "x_2mb.docx", PROSE[:2] + ["The Alpha agency closed its accounts late after a long review of the old ledger."])
    _docx(tmp_path / "x_5mb.docx", PROSE[:2] + ["The Beta agency closed its accounts late after a long review of the old ledger."])
    (tmp_path / "manifest.jsonl").write_text(
        "\n".join(json.dumps({"target_file": f"large/{n}", "document_type": "memo"}) for n in ("x_2mb.docx", "x_5mb.docx")),
        encoding="utf-8",
    )
    result = rm.metrics(tmp_path)
    assert result["size_twins"] == [("x_2mb.docx", "x_5mb.docx")]
    assert result["cross_document_reuse"] == 0.0
