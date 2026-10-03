"""Unit tests for WorldLoom pack and SDK blueprint ingestion in BigLoom."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from bigloom.build import build_corpus
from bigloom.cli import app
from bigloom.qualify import load_corpus_snapshots, qualify_corpus
from bigloom.queries import generate_queries

runner = CliRunner()


def test_build_corpus_with_world_pack(tmp_path: Path) -> None:
    out_dir = tmp_path / "pack_out"
    entries = build_corpus(
        out_dir=out_dir,
        sizes_mb=(0.1,),
        seed=42,
        formats=("docx", "pdf"),
        world_pack="retail-close",
    )
    assert len(entries) == 2
    assert all(e.text_golden_value.startswith("AUD ") for e in entries)
    assert all("Southern Cross Retail Group" in e.topic for e in entries)

    snapshots = load_corpus_snapshots(out_dir)
    target_snap = snapshots[entries[0].target_file]
    joined_text = "\n".join(u.text for u in target_snap.units)
    assert "Southern Cross Retail Group" in joined_text
    assert "CC-1000" in joined_text
    assert "Helios ERP" in joined_text

    cases = generate_queries(out_dir / "manifest.jsonl", out_dir / "cases.json")
    report = qualify_corpus(snapshots, cases, check_retrieval=True)
    assert report.passed is True, f"Violations: {report.violations}"


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
            "xlsx,pptx",
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
