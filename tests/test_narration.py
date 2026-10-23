"""Tests for the handshake writer: `bigloom narrate prepare` and `accept`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bigloom.cli import app
from bigloom.narration import _RoutingProvider, accept, prepare

runner = CliRunner()


class _Fake:
    def __init__(self, ident: str) -> None:
        self.id = ident
        self.seen: list[str] = []

    def complete(self, request, prompt, facts, *, feedback=""):  # type: ignore[no-untyped-def]
        self.seen.append(request.artifact_id)
        return self.id


class _Request:
    def __init__(self, artifact_id: str) -> None:
        self.artifact_id = artifact_id


def test_routing_provider_sends_chosen_documents_to_the_agent() -> None:
    agent, template = _Fake("agent"), _Fake("composed-prose-2")
    router = _RoutingProvider(agent, template, {"ART-0007"}, "jetski")
    assert router.id == "jetski+composed-prose-2"
    assert router.complete(_Request("ART-0007"), None, {}) == "agent"
    assert router.complete(_Request("ART-0001"), None, {}) == "composed-prose-2"
    assert agent.seen == ["ART-0007"] and template.seen == ["ART-0001"]


@pytest.fixture(scope="module")
def prepared(tmp_path_factory: pytest.TempPathFactory):  # type: ignore[no-untyped-def]
    out = tmp_path_factory.mktemp("hs") / "run"
    return out, prepare(out, seed=42, formats=("docx", "pdf"))


def test_prepare_writes_requests_for_the_chosen_documents_only(prepared) -> None:  # type: ignore[no-untyped-def]
    out, result = prepared
    document = json.loads(result.requests_path.read_text(encoding="utf-8"))
    ids = {r["artifact_id"] for r in document["requests"]}
    assert ids == set(result.artifact_ids)
    assert len(result.artifact_ids) == 4  # one for each format, plus two spares
    assert result.target_words == sum(r["target_words"] for r in document["requests"])
    assert {"rules", "reference_syntax", "response_shape"} <= set(document)
    plan = json.loads((out / "narration" / "plan.json").read_text(encoding="utf-8"))
    assert plan["artifact_ids"] == list(result.artifact_ids)
    world_json = json.loads((result.corpus_dir / "world.json").read_text(encoding="utf-8"))
    assert world_json  # a corpus with no prose exists for `accept`


def test_accept_reports_every_violation_and_writes_nothing(prepared, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    out, result = prepared
    document = json.loads(result.requests_path.read_text(encoding="utf-8"))
    first = document["requests"][0]
    bad = {"responses": [{"id": first["id"], "text": "Revenue was 1,234 this month.", "claims": []}]}
    path = tmp_path / "responses.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    before = (result.corpus_dir / "world.json").read_bytes()
    report = accept(out, path, model_id="test")
    assert report["accepted"] is False
    assert first["id"] in report["rejected"]
    missing = [r["id"] for r in document["requests"][1:]]
    assert all(m in report["rejected"] for m in missing)
    assert (result.corpus_dir / "world.json").read_bytes() == before


def test_cli_accept_exits_one_on_rejection(prepared, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    out, _ = prepared
    path = tmp_path / "empty.json"
    path.write_text(json.dumps({"responses": []}), encoding="utf-8")
    res = runner.invoke(app, ["narrate", "accept", "--out-dir", str(out), "--from", str(path)])
    assert res.exit_code == 1
    assert json.loads(res.output)["accepted"] is False


def test_public_sector_requests_name_a_surplus(tmp_path: Path) -> None:
    """Loop v2: the requests a writer reads name the public-sector term for gross profit facts."""
    import json as _json

    from bigloom.narration import prepare
    from bigloom.realism_loop import FORMATS, PACK

    pack = Path(__file__).resolve().parents[1] / PACK
    p = prepare(tmp_path / "seed-2026", seed=2026, formats=FORMATS, world_pack=str(pack))
    requests = _json.loads(p.requests_path.read_text(encoding="utf-8"))["requests"]
    with_profit = [r for r in requests if any("gross_profit" in str(f.get("kind", "")) for f in r["facts"])]
    assert with_profit, "the govtech world has gross profit facts"
    for r in with_profit:
        assert "gross surplus" in r["terminology"]["gross_profit"]
