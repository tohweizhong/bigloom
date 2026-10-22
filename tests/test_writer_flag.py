"""Tests for the narration writer flag (track worldloom_native_bigloom_20261016, FR3)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bigloom.cli import app
from bigloom.corpus import (
    COMPOSED_MODEL_ID,
    DEFAULT_WRITER,
    WRITERS,
    CorpusError,
    resolve_corpus,
)

runner = CliRunner()


def _prose_digest(world) -> str:  # type: ignore[no-untyped-def]
    h = hashlib.sha256()
    for ir in sorted(world.artifact_irs, key=lambda i: i.id):
        for sec in ir.sections:
            h.update(f"{ir.id}|{sec.heading}|{sec.body or ''}\n".encode())
    return h.hexdigest()


def test_template_is_the_default_writer_and_handshake_is_supported() -> None:
    assert DEFAULT_WRITER == "template"
    assert WRITERS == ("template", "handshake")


def test_template_writer_narrates_every_section(tmp_path: Path) -> None:
    world, prov = resolve_corpus(corpus_dir=None, out_dir=tmp_path, seed=7, writer="template")
    assert all(not s.awaiting_prose for ir in world.artifact_irs for s in ir.sections)
    assert prov.narration == "composed"
    assert prov.model_id == COMPOSED_MODEL_ID
    assert world.recipe.get("artifact_realism") == "enterprise/v2"


def test_unknown_writer_lists_values_that_work(tmp_path: Path) -> None:
    with pytest.raises(CorpusError) as exc:
        resolve_corpus(corpus_dir=None, out_dir=tmp_path, seed=7, writer="claude")
    message = str(exc.value)
    assert "claude" in message
    assert "template" in message


def test_cli_rejects_unknown_writer(tmp_path: Path) -> None:
    res = runner.invoke(app, ["build", "--out-dir", str(tmp_path / "o"), "--sizes-mb", "0.1", "--formats", "docx", "--writer", "codex"])
    assert res.exit_code != 0
    assert "template" in (res.output + str(res.exception))


def test_two_builds_give_the_same_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BIGLOOM_CORPUS_CACHE", raising=False)
    first, _ = resolve_corpus(corpus_dir=None, out_dir=tmp_path / "a", seed=31, writer="template")
    second, _ = resolve_corpus(corpus_dir=None, out_dir=tmp_path / "b", seed=31, writer="template")
    assert _prose_digest(first) == _prose_digest(second)


def test_manifest_records_writer(tmp_path: Path) -> None:
    out = tmp_path / "out"
    res = runner.invoke(app, ["build", "--out-dir", str(out), "--sizes-mb", "0.1", "--formats", "docx", "--writer", "template"])
    assert res.exit_code == 0, res.output
    row = json.loads((out / "manifest.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert row["narration"] == "composed"
    assert row["model_id"] == COMPOSED_MODEL_ID


def test_init_rejects_unknown_writer(tmp_path: Path) -> None:
    res = runner.invoke(app, ["init", "--out", str(tmp_path / "w"), "--writer", "claude"], input="")
    assert res.exit_code != 0
    assert isinstance(res.exception, CorpusError)
    assert "template" in str(res.exception)


def test_handshake_writer_needs_a_narrated_corpus(tmp_path: Path) -> None:
    with pytest.raises(CorpusError, match="bigloom narrate prepare"):
        resolve_corpus(corpus_dir=None, out_dir=tmp_path, seed=7, writer="handshake")


@pytest.mark.parametrize("command", ["build", "init"])
def test_help_lists_the_writers_that_work(command: str) -> None:
    res = runner.invoke(app, [command, "--help"], terminal_width=200)
    assert res.exit_code == 0
    text = " ".join(res.output.split())
    assert "template" in text and "handshake" in text
    assert "This release supports: template." not in text
