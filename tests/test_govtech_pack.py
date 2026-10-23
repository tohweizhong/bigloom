"""Tests for the GovTech company pack (track worldloom_native_bigloom_20261016, FR2)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from worldloom.world import World

from bigloom.corpus import build_worldloom_corpus
from bigloom.realism import document_sentences, repeated_sentence_rate

PACK = Path(__file__).resolve().parents[1] / "packs" / "govtech.json"
WORLDLOOM_CLI = Path(sys.executable).with_name("worldloom")
GOVTECH_TERMS = ("WOG Finance", "agency code", "Government Technology Agency", "Whole-of-Government")


@pytest.fixture(scope="module")
def govtech_world(tmp_path_factory: pytest.TempPathFactory) -> World:
    path = build_worldloom_corpus(tmp_path_factory.mktemp("gt") / "corpus", seed=2026, pack=str(PACK), locale="singapore")
    return World.load(path)


@pytest.fixture(scope="module")
def retail_world(tmp_path_factory: pytest.TempPathFactory) -> World:
    path = build_worldloom_corpus(tmp_path_factory.mktemp("rt") / "corpus", seed=2026, locale="singapore")
    return World.load(path)


def _pack_types() -> list[str]:
    return [t["key"] for t in json.loads(PACK.read_text(encoding="utf-8"))["artifact_types"]]


def test_pack_check_passes() -> None:
    out = subprocess.run([str(WORLDLOOM_CLI), "pack", "check", str(PACK)], capture_output=True, text=True, check=False)
    assert out.returncode == 0, out.stdout + out.stderr
    assert "validates against the retail engine" in out.stdout
    assert "no lint findings" in out.stdout


def test_pack_declares_and_builds_sixteen_document_types(govtech_world: World) -> None:
    declared = _pack_types()
    assert len(declared) >= 16
    built = {i.artifact_type for i in govtech_world.artifact_intents}
    missing = sorted(set(declared) - built)
    assert not missing, f"Pack types that the build did not plan: {missing}"


def test_pack_text_overrides_reach_the_corpus(govtech_world: World) -> None:
    summaries = " ".join(e.summary for e in govtech_world.events)
    assert "agency code mapping" in summaries
    assert "inventory valuation pipeline" not in summaries


def test_govtech_terms_stay_out_of_retail_builds(retail_world: World) -> None:
    text = " ".join(
        [e.summary for e in retail_world.events]
        + [s.body or "" for ir in retail_world.artifact_irs for s in ir.sections]
        + [retail_world.company.name]
    )
    for term in GOVTECH_TERMS:
        assert term not in text, f"GovTech term '{term}' reached a retail build"


def test_each_govtech_document_has_low_repetition(govtech_world: World) -> None:
    pack_types = set(_pack_types())
    by_id = {i.id: i for i in govtech_world.artifact_intents}
    worst: list[tuple[str, float]] = []
    for ir in govtech_world.artifact_irs:
        intent = by_id.get(ir.intent_id)
        if intent is None or intent.artifact_type not in pack_types:
            continue
        sentences = document_sentences(govtech_world, ir)
        if len(sentences) < 5:
            continue
        worst.append((intent.artifact_type, repeated_sentence_rate(sentences)))
    assert worst
    bad = [w for w in worst if w[1] > 0.2]
    assert not bad, f"Documents above the 0.2 repeated-sentence limit: {bad}"


def test_loaded_govtech_corpus_renders_every_pack_type(tmp_path: Path) -> None:
    from bigloom.corpus import resolve_corpus

    corpus = build_worldloom_corpus(tmp_path / "corpus", seed=2026, pack=str(PACK), locale="singapore")
    world, _ = resolve_corpus(corpus_dir=corpus, out_dir=tmp_path, seed=2026)
    types = {i.id: i.artifact_type for i in world.artifact_intents}
    rendered = world.render("docx")._rendered
    got = {types[r.artifact_id] for r in rendered if r.artifact_id in types}
    missing = sorted(set(_pack_types()) - got)
    assert not missing, f"Pack types with no Word file after load: {missing}"


def test_public_sector_planted_labels_name_a_surplus(govtech_world: World, retail_world: World) -> None:
    """Loop v2: a public-sector pack plants surplus nouns, and a retail build keeps its own."""
    from bigloom.questions import plan_targets

    irs = govtech_world.artifact_irs[:6]
    plans = plan_targets(govtech_world, irs, [0] * len(irs), set())
    planted = " ".join(f"{p.text_label} {p.chart_title} {p.text_question} {p.image_question}" for p in plans).lower()
    assert "gross profit" not in planted and "gross margin" not in planted
    assert "surplus" in planted

    rplans = plan_targets(retail_world, retail_world.artifact_irs[:6], [0] * 6, set())
    assert not any("surplus" in p.text_label for p in rplans)


def test_build_targets_come_from_three_document_families(govtech_world: World) -> None:
    """Loop v2: the targets that build chooses span three families and include the operations type."""
    from bigloom.build import _choose, _renderable

    fmts = ["docx", "pdf", "pptx"]
    formats_of = _renderable(govtech_world, fmts)
    used_ids: set[str] = set()
    used_types: set[str] = set()
    picked = [_choose(govtech_world, fmt, formats_of, used_ids, used_types)[1] for fmt in fmts]
    domain = {i.artifact_type: str(i.domain) for i in govtech_world.artifact_intents}
    assert len({domain[t] for t in picked}) == 3, picked
    assert picked[0] == "service_impact_assessment", picked  # the DOCX target, the first format
    assert "knowledge_article" not in picked, picked


def test_knowledge_article_is_never_a_target_or_a_candidate(govtech_world: World) -> None:
    """Loop v2: an excluded type is never chosen, even when every other type is used."""
    from bigloom.build import CorpusError, _choose, _renderable

    formats_of = _renderable(govtech_world, ["docx"])
    used_ids: set[str] = set()
    used_types: set[str] = set()
    seen = []
    while True:
        try:
            seen.append(_choose(govtech_world, "docx", formats_of, used_ids, used_types)[1])
        except CorpusError:
            break
    assert seen and "knowledge_article" not in seen, seen


def test_knowledge_article_is_never_a_candidate(tmp_path: Path) -> None:
    """Loop v2: prepare never gives agent prose to an excluded type, even with many spares."""
    import json as _json

    from worldloom.world import World as _World

    from bigloom.narration import prepare

    p = prepare(tmp_path / "seed-2026", seed=2026, formats=("docx", "pdf", "pptx"), world_pack=str(PACK), spares=12)
    world = _World.load(p.corpus_dir)
    types = {i.id: i.artifact_type for i in world.artifact_intents}
    intent_of = {ir.id: ir.intent_id for ir in world.artifact_irs}
    chosen = _json.loads((p.requests_path.parent / "plan.json").read_text(encoding="utf-8"))["artifact_ids"]
    kinds = [types[intent_of[a]] for a in chosen]
    assert len(kinds) > 5 and "knowledge_article" not in kinds, kinds
