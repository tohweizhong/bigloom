"""Tests for the interactive WorldLoom wizard (`bigloom init`) and custom org-pack JSON loading."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from bigloom.build import _resolve_world_context
from bigloom.cli import app
from bigloom.proposal.facts import load_world_entities
from bigloom.proposal.spec import ProposalSpec
from bigloom.wizard import (
    build_org_pack_dict,
    write_org_pack_json,
    write_proposal_spec_yaml,
)

runner = CliRunner()


def test_custom_org_pack_json_resolves_in_build_and_proposal(tmp_path: Path) -> None:
    """Verify a custom org-pack JSON file populates company, currency, and business units."""
    pack_path = tmp_path / "merlion-pack.json"
    write_org_pack_json(
        pack_path,
        company_name="Merlion Sovereign Cloud",
        industry="Public Cloud Infrastructure",
        base_domain="retail",
        currency="SGD",
        divisions=["Core Compute Division", "Zero Trust Division"],
    )
    assert pack_path.is_file()

    ctx = _resolve_world_context(seed=42, world_pack=str(pack_path))
    assert ctx.currency == "SGD"
    assert any("Merlion Sovereign Cloud Core Compute Division" in t for t in ctx.topics)
    assert "Company: Merlion Sovereign Cloud" in ctx.governance_line

    spec = ProposalSpec(
        subject="Merlion Sovereign Cloud Expansion",
        id_prefix="MSCE",
        world_pack=str(pack_path),
        sizes_mb=[1],
    )
    entities = load_world_entities(spec, seed=42)
    assert entities.agency_name == "Merlion Sovereign Cloud"
    assert entities.currency == "SGD"
    assert "Core Compute Division" in entities.business_units


def test_build_org_pack_dict_and_write_proposal_spec_yaml(tmp_path: Path) -> None:
    """Verify helper functions produce valid org-pack JSON and proposal-spec YAML."""
    pack_dict = build_org_pack_dict(
        company_name="Temasek Harbour Grid",
        industry="Maritime Energy",
        base_domain="procurement",
        currency="usd",
        divisions=["Offshore Subsea Unit"],
    )
    assert pack_dict["company_name"] == "Temasek Harbour Grid"
    assert pack_dict["base"] == "procurement"
    assert pack_dict["currency"] == "USD"
    assert len(pack_dict["units"]) == 1

    spec_path = tmp_path / "proposal-spec.yaml"
    write_proposal_spec_yaml(
        spec_path,
        subject="Harbour Grid Modernization",
        id_prefix="HGM",
        sizes_mb=[1],
        world_pack=str(tmp_path / "org-pack.json"),
        domain=None,
        agency_name="Temasek Harbour Grid",
        currency="USD",
    )
    assert spec_path.is_file()
    text = spec_path.read_text(encoding="utf-8")
    assert "Harbour Grid Modernization" in text
    assert "HGM" in text


def test_cli_init_proposal_custom_company_and_run(tmp_path: Path) -> None:
    """Test `bigloom init` interactive proposal flow with a custom company and immediate build."""
    out_dir = tmp_path / "wizard_proposal_out"
    user_inputs = (
        "proposal\n"
        "custom\n"
        "Merlion Digital Agency\n"
        "Public Sector Digital\n"
        "retail\n"
        "SGD\n"
        "Cloud Platform Division, Cyber Defence Division\n"
        "Whole-of-Government Vault Modernisation\n"
        "WGVM\n"
        "1\n"
        "y\n"
        "y\n"
    )
    result = runner.invoke(
        app,
        ["init", "--out", str(out_dir), "--seed", "2026"],
        input=user_inputs,
    )
    assert result.exit_code == 0, result.stdout
    assert (out_dir / "org-pack.json").is_file()
    assert (out_dir / "proposal-spec.yaml").is_file()
    assert (out_dir / "manifest.jsonl").is_file()
    assert (out_dir / "evals.jsonl").is_file()
    assert (out_dir / "evals.csv").is_file()


def test_cli_init_corpus_domain_and_run(tmp_path: Path) -> None:
    """Test `bigloom init` interactive corpus flow with a WorldLoom domain preset."""
    out_dir = tmp_path / "wizard_corpus_out"
    user_inputs = "corpus\ndomain\nbanking\n0.2\ndocx\ny\n"
    result = runner.invoke(
        app,
        ["init", "--out", str(out_dir), "--seed", "42"],
        input=user_inputs,
    )
    assert result.exit_code == 0, result.stdout
    assert (out_dir / "manifest.jsonl").is_file()
    assert (out_dir / "cases.json").is_file()
    payload = json.loads(result.stdout[result.stdout.index("{") :])
    assert payload["mode"] == "corpus"
    assert payload["qualified"] is True


def test_cli_init_pack_no_run(tmp_path: Path) -> None:
    """Test `bigloom init` with a bundled pack when the user declines immediate execution."""
    out_dir = tmp_path / "wizard_no_run"
    user_inputs = (
        "proposal\n"
        "pack\n"
        "retail-close\n"
        "Aurora Grid Upgrade\n"
        "AGU\n"
        "5\n"
        "y\n"
        "n\n"
    )
    result = runner.invoke(
        app,
        ["init", "--out", str(out_dir), "--seed", "2026"],
        input=user_inputs,
    )
    assert result.exit_code == 0, result.stdout
    assert (out_dir / "proposal-spec.yaml").is_file()
    assert not (out_dir / "manifest.jsonl").exists()
