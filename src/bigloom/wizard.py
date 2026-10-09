"""Interactive CLI wizard (`bigloom init`) that configures WorldLoom and runs BigLoom."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import typer
import yaml

from .build import build_corpus
from .proposal import build_proposal, load_proposal_spec, verify_proposal_outputs
from .qualify import load_corpus_snapshots, qualify_corpus
from .queries import generate_queries


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "custom-org"


def build_org_pack_dict(
    *,
    company_name: str,
    industry: str,
    base_domain: str = "retail",
    currency: str = "SGD",
    divisions: Sequence[str] = ("Core Platform Division", "Operations Division"),
) -> dict[str, Any]:
    """Construct a valid WorldLoom organisation pack dictionary from user answers."""
    clean_divs = [d.strip() for d in divisions if d.strip()]
    if not clean_divs:
        clean_divs = ["Core Operations Division"]

    n = len(clean_divs)
    base_share = round(1.0 / n, 4)
    units: list[dict[str, Any]] = []
    for idx, div_name in enumerate(clean_divs):
        share = round(1.0 - base_share * (n - 1), 4) if idx == n - 1 else base_share
        key = _slugify(div_name).replace("-", "_")[:24] or f"unit_{idx + 1}"
        units.append(
            {
                "key": f"{key}_{idx + 1}",
                "name": div_name,
                "kind": key,
                "share": share,
                "categories": [
                    {"name": f"{div_name} Primary Service", "share": 0.6, "margin": 0.25},
                    {"name": f"{div_name} Managed Operations", "share": 0.4, "margin": 0.20},
                ],
                "site_formats": [
                    {"name": f"{div_name} Hub", "count": 4, "revenue_weight": 1.0},
                ],
            }
        )

    return {
        "name": _slugify(company_name),
        "base": base_domain.strip().lower() or "retail",
        "description": f"SYNTHETIC. {company_name} ({industry}). All figures are invented.",
        "company_name": company_name.strip(),
        "industry": industry.strip(),
        "currency": currency.strip().upper() or "SGD",
        "currency_unit": "thousands",
        "annual_revenue": 1_200_000,
        "employees": 2_800,
        "units": units,
    }


def write_org_pack_json(
    out_path: Path,
    *,
    company_name: str,
    industry: str,
    base_domain: str = "retail",
    currency: str = "SGD",
    divisions: Sequence[str] = ("Core Platform Division", "Operations Division"),
) -> Path:
    """Write a WorldLoom organisation pack JSON file to disk."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_org_pack_dict(
        company_name=company_name,
        industry=industry,
        base_domain=base_domain,
        currency=currency,
        divisions=divisions,
    )
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out_path


def write_proposal_spec_yaml(
    out_path: Path,
    *,
    subject: str,
    id_prefix: str | None = None,
    sizes_mb: Sequence[int] = (5,),
    world_pack: str | None = None,
    domain: str | None = None,
    agency_name: str | None = None,
    currency: str | None = None,
    prose_provider: str = "deterministic",
) -> Path:
    """Write a ProposalSpec YAML file to disk."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    spec_dict: dict[str, Any] = {
        "subject": subject,
        "sizes_mb": [max(1, round(float(s))) for s in sizes_mb],
        "sections_per_chapter": 1,
        "annex_sections": 1,
        "figures": 6,
        "prose": {"provider": prose_provider},
    }
    if id_prefix:
        spec_dict["id_prefix"] = id_prefix.strip()
    if world_pack:
        spec_dict["world_pack"] = world_pack
    elif domain:
        spec_dict["domain"] = domain
    if agency_name:
        spec_dict["agency_name"] = agency_name
    if currency:
        spec_dict["currency"] = currency

    out_path.write_text(yaml.safe_dump(spec_dict, sort_keys=False), encoding="utf-8")
    return out_path


def run_interactive_wizard(out_dir: Path, *, seed: int = 2026) -> dict[str, Any]:
    """Prompt the user for company and output settings, then optionally run WorldLoom + BigLoom."""
    out_dir.mkdir(parents=True, exist_ok=True)

    mode = (
        typer.prompt(
            "1. Generation mode ('proposal' for single-topic .docx up to 1 GiB, "
            "or 'corpus' for multi-format .docx/.xlsx/.pptx/.pdf)",
            default="proposal",
        )
        .strip()
        .lower()
    )
    if mode not in {"proposal", "corpus"}:
        raise typer.BadParameter("Mode must be 'proposal' or 'corpus'.")

    source = (
        typer.prompt(
            "2. Company source ('custom' to define your own company, "
            "'domain' for an industry preset, or 'pack' for a bundled/JSON pack)",
            default="custom",
        )
        .strip()
        .lower()
    )
    if source not in {"custom", "domain", "pack"}:
        raise typer.BadParameter("Company source must be 'custom', 'domain', or 'pack'.")

    world_pack: str | None = None
    domain: str | None = None
    agency_name: str | None = None
    currency: str | None = None

    if source == "custom":
        company_name = typer.prompt("   Company / agency name", default="Merlion Sovereign Cloud")
        industry = typer.prompt("   Industry / sector", default="Public Sector Digital")
        base_domain = typer.prompt(
            "   Base WorldLoom domain (retail, banking, insurance, procurement)",
            default="retail",
        )
        currency = typer.prompt("   Currency (3-letter ISO code)", default="SGD").strip().upper()
        divisions_raw = typer.prompt(
            "   Divisions / business units (comma-separated)",
            default="Core Platform Division, Cyber Defence Division, Data Services Division",
        )
        divisions = [d.strip() for d in divisions_raw.split(",") if d.strip()]
        pack_path = write_org_pack_json(
            out_dir / "org-pack.json",
            company_name=company_name,
            industry=industry,
            base_domain=base_domain,
            currency=currency,
            divisions=divisions,
        )
        world_pack = str(pack_path)
        agency_name = company_name
    elif source == "domain":
        domain = (
            typer.prompt(
                "   WorldLoom domain (retail, banking, insurance, procurement)",
                default="retail",
            )
            .strip()
            .lower()
        )
    else:
        world_pack = typer.prompt(
            "   WorldLoom pack name (e.g. retail-close) or path to .json",
            default="retail-close",
        ).strip()

    if mode == "proposal":
        subject = typer.prompt(
            "3. Proposal subject / programme title",
            default="Greater Southern Waterfront Digital Twin Programme",
        )
        default_short = (
            "".join(w[0].upper() for w in subject.split() if w[:1].isalnum())[:6] or "PRG"
        )
        id_prefix = typer.prompt("   Short reference prefix", default=default_short)
        sizes_raw = typer.prompt(
            "4. Target file sizes in MiB (comma-separated integers)", default="5"
        )
        sizes_mb_int = [max(1, round(float(x.strip()))) for x in sizes_raw.split(",") if x.strip()]
        use_deterministic = typer.confirm(
            "5. Use fast deterministic prose instead of calling Vertex Gemini?",
            default=True,
        )
        spec_path = write_proposal_spec_yaml(
            out_dir / "proposal-spec.yaml",
            subject=subject,
            id_prefix=id_prefix,
            sizes_mb=sizes_mb_int,
            world_pack=world_pack,
            domain=domain,
            agency_name=agency_name,
            currency=currency,
            prose_provider="deterministic" if use_deterministic else "gemini",
        )
        run_now = typer.confirm("6. Run WorldLoom and build the proposal now?", default=True)
        if not run_now:
            return {
                "mode": "proposal",
                "executed": False,
                "out": str(out_dir),
                "spec": str(spec_path),
                "world_pack": world_pack,
                "domain": domain,
            }
        spec = load_proposal_spec(spec_path)
        result = build_proposal(spec, out_dir=out_dir, seed=seed, skip_prose=False)
        verification = verify_proposal_outputs(spec, out_dir=out_dir, build_result=result)
        return {
            "mode": "proposal",
            "executed": True,
            "out": str(out_dir),
            "spec": str(spec_path),
            "passed": verification.passed,
            "manifest_entries": result.manifest_entries,
            "total_eval_rows": verification.total_eval_rows,
            "errors": verification.errors,
        }

    sizes_raw = typer.prompt("3. Target file sizes in MiB (comma-separated)", default="18,50")
    sizes_mb = [float(x.strip()) for x in sizes_raw.split(",") if x.strip()]
    formats_raw = typer.prompt(
        "4. Document formats (comma-separated: docx,xlsx,pptx,pdf)",
        default="docx,xlsx,pptx,pdf",
    )
    formats = [x.strip() for x in formats_raw.split(",") if x.strip()]
    run_now = typer.confirm("5. Run WorldLoom and build the corpus now?", default=True)
    if not run_now:
        return {
            "mode": "corpus",
            "executed": False,
            "out": str(out_dir),
            "world_pack": world_pack,
            "domain": domain,
            "sizes_mb": sizes_mb,
            "formats": formats,
        }

    entries = build_corpus(
        out_dir=out_dir,
        sizes_mb=sizes_mb,
        seed=seed,
        formats=formats,
        world_pack=world_pack,
        domain=domain,
    )
    cases_path = out_dir / "cases.json"
    cases = generate_queries(manifest_path=out_dir / "manifest.jsonl", out_path=cases_path)
    snapshots = load_corpus_snapshots(out_dir)
    qual_report = qualify_corpus(snapshots, cases, check_retrieval=True)
    return {
        "mode": "corpus",
        "executed": True,
        "out": str(out_dir),
        "manifest": str(out_dir / "manifest.jsonl"),
        "cases": str(cases_path),
        "total_large_files": len(entries),
        "total_cases": len(cases),
        "qualified": qual_report.passed,
    }
