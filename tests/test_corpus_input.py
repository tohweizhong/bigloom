"""Tests for reading a WorldLoom corpus as BigLoom input (track worldloom_native_bigloom_20261016, FR1)."""

from __future__ import annotations

import builtins
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from bigloom.build import build_corpus
from bigloom.corpus import (
    COMPOSED_MODEL_ID,
    WORLDLOOM_PIN,
    CorpusError,
    require_worldloom,
    resolve_corpus,
)

WORLDLOOM_CLI = Path(sys.executable).with_name("worldloom")


def _worldloom_build(out: Path, *, seed: int, narrate: bool) -> Path:
    args = [
        str(WORLDLOOM_CLI), "build", "--seed", str(seed), "--incident", "--periods", "1",
        "--realism", "enterprise", "--locale", "singapore", "--out", str(out), "--overwrite",
    ]
    if narrate:
        args.append("--narrate")
    subprocess.run(args, check=True, capture_output=True)
    return out


@pytest.fixture(scope="module")
def narrated_corpus(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _worldloom_build(tmp_path_factory.mktemp("wl") / "corpus", seed=11, narrate=True)


@pytest.fixture(scope="module")
def raw_corpus(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _worldloom_build(tmp_path_factory.mktemp("wl_raw") / "corpus", seed=11, narrate=False)


def test_loads_existing_corpus(narrated_corpus: Path, tmp_path: Path) -> None:
    world, prov = resolve_corpus(corpus_dir=narrated_corpus, out_dir=tmp_path, seed=99)
    assert world.company.name
    assert world.seed == 11
    assert prov.corpus_dir == str(narrated_corpus)
    assert prov.narration == "composed"
    assert not (tmp_path / "corpus").exists()


def test_corpus_dir_without_world_json_is_refused(tmp_path: Path) -> None:
    empty = tmp_path / "not-a-corpus"
    empty.mkdir()
    (empty / "notes.md").write_text("Some topic line\n", encoding="utf-8")
    with pytest.raises(CorpusError, match="world.json"):
        resolve_corpus(corpus_dir=empty, out_dir=tmp_path, seed=1)


def test_builds_corpus_when_none_given(tmp_path: Path) -> None:
    world, prov = resolve_corpus(corpus_dir=None, out_dir=tmp_path, seed=11, locale="singapore")
    assert (tmp_path / "corpus" / "world.json").is_file()
    assert world.seed == 11
    assert prov.narration == "composed"
    assert all(not s.awaiting_prose for ir in world.artifact_irs for s in ir.sections)


def test_fills_incomplete_narration(raw_corpus: Path, tmp_path: Path) -> None:
    world, prov = resolve_corpus(corpus_dir=raw_corpus, out_dir=tmp_path, seed=1)
    assert prov.narration == "partial"
    assert all(not s.awaiting_prose for ir in world.artifact_irs for s in ir.sections)


def test_missing_worldloom_gives_install_command(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def fake_import(name: str, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        if name == "worldloom" or name.startswith("worldloom."):
            raise ImportError("No module named 'worldloom'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(CorpusError) as exc:
        require_worldloom()
    assert WORLDLOOM_PIN in str(exc.value)
    assert "pip install" in str(exc.value)


def test_provenance_fields(narrated_corpus: Path, tmp_path: Path) -> None:
    _, prov = resolve_corpus(corpus_dir=narrated_corpus, out_dir=tmp_path, seed=1)
    assert prov.worldloom_commit
    assert prov.world_seed == 11
    assert re.fullmatch(r"[0-9a-f]{64}", prov.recipe_digest)
    assert prov.model_id == COMPOSED_MODEL_ID
    assert prov.prompt_version


def test_manifest_records_provenance(narrated_corpus: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    entries = build_corpus(out, sizes_mb=(0.12,), formats=("docx",), corpus_dir=narrated_corpus)
    assert entries
    row = json.loads((out / "manifest.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert row["world_seed"] == 11
    assert row["narration"] == "composed"
    assert row["model_id"] == COMPOSED_MODEL_ID
    assert re.fullmatch(r"[0-9a-f]{64}", row["recipe_digest"])
    assert row["worldloom_commit"]
