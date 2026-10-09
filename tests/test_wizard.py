"""Tests for the interactive WorldLoom wizard (`bigloom init`) and custom org-pack JSON loading."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner
from worldloom import packs

from bigloom.build import _resolve_world_context
from bigloom.cli import app
from bigloom.proposal.facts import load_world_entities
from bigloom.proposal.spec import ProposalSpec
from bigloom.wizard import (
    build_org_pack_dict,
    parse_facets,
    write_org_pack_json,
    write_proposal_spec_yaml,
)

runner = CliRunner()


def test_custom_org_pack_json_lints_clean_across_all_domains(tmp_path: Path) -> None:
    """Verify generated org-pack JSON files pass worldloom.packs.lint with 0 findings across all domains."""
    for domain in ("retail", "banking", "insurance", "procurement"):
        pack_path = tmp_path / f"{domain}-pack.json"
        write_org_pack_json(
            pack_path,
            company_name=f"Merlion {domain.title()} Authority",
            industry=f"Public {domain.title()}",
            base_domain=domain,
            currency="SGD",
            divisions=["Core Compute Division", "Zero Trust Division"],
            annual_revenue=1_700_000,
            employees=3_900,
            fiscal_year_start_month=4,
            headquarters="Mapletree Business City, Singapore",
            regions=["Central", "East", "West"],
            seasonality="flat",
            estate="large",
        )
        loaded = packs.load(str(pack_path))
        findings = packs.lint(loaded)
        assert findings == [], f"Unexpected lint findings for {domain}: {findings}"


def test_custom_org_pack_json_resolves_in_build_and_proposal_with_locale_and_facets(
    tmp_path: Path,
) -> None:
    """Verify a custom org-pack JSON file with locale and facets populates company, currency, and lore."""
    pack_path = tmp_path / "merlion-pack.json"
    write_org_pack_json(
        pack_path,
        company_name="Merlion Sovereign Cloud",
        industry="Public Cloud Infrastructure",
        base_domain="retail",
        currency="SGD",
        divisions=["Core Compute Division", "Zero Trust Division"],
        given_names=["Wei Ming", "Hui Min", "Arjun", "Priya"],
        surnames=["Tan", "Lim", "Kumar", "Abdullah"],
    )
    assert pack_path.is_file()

    ctx = _resolve_world_context(
        seed=42,
        world_pack=str(pack_path),
        locale="singapore",
        facets={"listing": "state_owned", "scale": "enterprise"},
    )
    assert ctx.currency == "SGD"
    assert any("Merlion Sovereign Cloud Core Compute Division" in t for t in ctx.topics)
    assert "Company: Merlion Sovereign Cloud" in ctx.governance_line

    spec = ProposalSpec(
        subject="Merlion Sovereign Cloud Expansion",
        id_prefix="MSCE",
        world_pack=str(pack_path),
        locale="singapore",
        facets={"listing": "state_owned", "scale": "enterprise"},
        sizes_mb=[1],
    )
    entities = load_world_entities(spec, seed=42)
    assert entities.agency_name == "Merlion Sovereign Cloud"
    assert entities.currency == "SGD"
    assert "Core Compute Division" in entities.business_units
    assert "Wei Ming" in entities.given_names


def test_build_org_pack_dict_and_write_proposal_spec_yaml(tmp_path: Path) -> None:
    """Verify helper functions produce valid org-pack JSON, parse facets, and write proposal-spec YAML."""
    facets = parse_facets("listing=state_owned, scale=enterprise, maturity=legacy")
    assert facets == {"listing": "state_owned", "scale": "enterprise", "maturity": "legacy"}

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
    assert len(pack_dict["lore"]) >= 1

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
        locale="singapore",
        facets=facets,
    )
    assert spec_path.is_file()
    text = spec_path.read_text(encoding="utf-8")
    assert "Harbour Grid Modernization" in text
    assert "singapore" in text
    assert "state_owned" in text


def test_cli_init_proposal_custom_company_default_and_run(tmp_path: Path) -> None:
    """Test `bigloom init` interactive proposal flow with default advanced options and immediate build."""
    out_dir = tmp_path / "wizard_proposal_out"
    user_inputs = (
        "proposal\n"
        "custom\n"
        "Merlion Digital Agency\n"
        "Public Sector Digital\n"
        "retail\n"
        "SGD\n"
        "Cloud Platform Division, Cyber Defence Division\n"
        "n\n"
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
    payload = json.loads(result.stdout[result.stdout.index("{") :])
    assert payload["pack_lint_findings"] == []


def test_cli_init_proposal_custom_company_advanced_options(tmp_path: Path) -> None:
    """Test `bigloom init` when the user enables advanced WorldLoom blueprint prompts."""
    out_dir = tmp_path / "wizard_advanced_out"
    user_inputs = (
        "proposal\n"
        "custom\n"
        "Government Technology Agency (Synthetic)\n"
        "Public Sector\n"
        "retail\n"
        "SGD\n"
        "Product & Engineering, Services & Cyber, Digital Transformation\n"
        "y\n"
        "1700000\n"
        "3900\n"
        "4\n"
        "flat\n"
        "singapore\n"
        "Mapletree Business City, Singapore\n"
        "Central, East, North, North-East, West\n"
        "large\n"
        "WOG Finance and Procurement System\n"
        "GCC Data Platform\n"
        "Wei Ming, Hui Min, Arjun, Priya\n"
        "Tan, Lim, Kumar, Abdullah\n"
        "formal and precise, British spelling, acronym-heavy\n"
        "listing=state_owned,scale=enterprise\n"
        "Under the 2018 cloud-first policy, legacy agency codes are maintained by hand.\n"
        "Greater Southern Waterfront Digital Twin Programme\n"
        "GSW\n"
        "1\n"
        "y\n"
        "n\n"
    )
    result = runner.invoke(
        app,
        ["init", "--out", str(out_dir), "--seed", "2026"],
        input=user_inputs,
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout[result.stdout.index("{") :])
    assert payload["pack_lint_findings"] == []
    assert payload["locale"] == "singapore"
    assert payload["facets"] == {"listing": "state_owned", "scale": "enterprise"}


def test_cli_init_corpus_domain_and_run(tmp_path: Path) -> None:
    """Test `bigloom init` interactive corpus flow with a WorldLoom domain preset."""
    out_dir = tmp_path / "wizard_corpus_out"
    user_inputs = "corpus\ndomain\nbanking\nsingapore\nlisting=listed\n0.2\ndocx\ny\n"
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
