"""Unit tests for WorldLoom pack and SDK blueprint ingestion in BigLoom."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from bigloom.build import build_corpus
from bigloom.cli import app
from bigloom.corpus import CorpusError
from bigloom.qualify import load_corpus_snapshots, qualify_corpus
from bigloom.queries import generate_queries

runner = CliRunner()


def test_bundled_corpus_without_documents_is_refused(tmp_path: Path) -> None:
    """The bundled `retail-close` corpus holds facts but no planned documents.

    BigLoom takes all content from WorldLoom documents, so it stops with a clear error.
    """
    with pytest.raises(CorpusError, match="no planned documents"):
        build_corpus(out_dir=tmp_path / "pack_out", sizes_mb=(0.1,), seed=42, formats=("docx", "pdf"), world_pack="retail-close")

    with pytest.raises(ValueError, match="Specify at most one"):
        build_corpus(
            out_dir=tmp_path / "err_out",
            sizes_mb=(0.1,),
            world_pack="retail-close",
            domain="banking",
        )


def test_cli_build_with_sdk_domain(tmp_path: Path) -> None:
    out_dir = tmp_path / "sdk_out"
    res = runner.invoke(
        app,
        [
            "build",
            "--out-dir",
            str(out_dir),
            "--sizes-mb",
            "0.1",
            "--formats",
            "xlsx,docx",
            "--domain",
            "banking",
            "--seed",
            "42",
        ],
    )
    assert res.exit_code == 0, res.output
    manifest_path = out_dir / "manifest.jsonl"
    cases_path = out_dir / "cases.json"
    cases = generate_queries(manifest_path, cases_path)
    snapshots = load_corpus_snapshots(out_dir)
    report = qualify_corpus(snapshots, cases, check_retrieval=True)
    assert report.passed is True, f"Violations: {report.violations}"


def test_format_with_no_document_in_the_domain_is_refused(tmp_path: Path) -> None:
    """The banking engine plans no deck, so a PPTX target stops with a clear error."""
    with pytest.raises(CorpusError, match="renders as pptx"):
        build_corpus(out_dir=tmp_path / "out", sizes_mb=(0.1,), seed=42, formats=("pptx",), domain="banking")
