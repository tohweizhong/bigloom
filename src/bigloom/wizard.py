"""Interactive CLI wizard (`bigloom init`) that configures WorldLoom and runs BigLoom."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import typer
import yaml
from worldloom import packs

from .build import build_corpus
from .proposal import build_proposal, load_proposal_spec, verify_proposal_outputs
from .proposal.facts import DEFAULT_GIVEN, DEFAULT_SURNAMES
from .qualify import load_corpus_snapshots, qualify_corpus
from .queries import generate_queries

DEFAULT_SYSTEM_BRANDS_BY_DOMAIN: dict[str, dict[str, str]] = {
    "retail": {
        "erp": "WOG Finance and Procurement System",
        "mdm": "Agency Reference Data Register",
        "platform": "GCC Data Platform",
        "commerce": "Citizen Services Portal",
        "pos": "Service Centre Counter System",
    },
    "banking": {
        "core_banking": "Sovereign Core Banking Ledger",
        "collateral": "National Collateral Register",
        "risk_platform": "Prudential Risk Aggregation Platform",
        "reg_portal": "MAS Regulatory Filing Portal",
        "market_data": "Sovereign Treasury Market Feed",
    },
    "insurance": {
        "policy_admin": "National Policy Administration System",
        "claims": "Enterprise Claims Management Ledger",
        "actuarial": "Actuarial Reserving Platform",
        "general_ledger": "Sovereign Insurance General Ledger",
        "reinsurance": "Treaty Reinsurance Register",
    },
    "procurement": {
        "sourcing": "Whole-of-Government Sourcing Portal",
        "procure": "Enterprise Requisition and Order System",
        "receipting": "Site Goods Receipting System",
        "ap_ledger": "Central Accounts Payable Subledger",
        "general_ledger": "Sovereign Accrual General Ledger",
    },
}

DEFAULT_LORE_TARGET_BY_DOMAIN: dict[str, str] = {
    "retail": "data_quality_incident/inventory",
    "banking": "data_quality_incident/collateral",
    "insurance": "triangle_distortion/long_tail",
    "procurement": "receipting_visibility/subcontract",
}


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "custom-org"


def parse_facets(raw: str) -> dict[str, str]:
    """Parse a comma-separated 'key=value' string into a WorldLoom facets dictionary."""
    result: dict[str, str] = {}
    for item in raw.split(","):
        part = item.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        if k.strip() and v.strip():
            result[k.strip()] = v.strip()
    return result


def build_org_pack_dict(
    *,
    company_name: str,
    industry: str,
    base_domain: str = "retail",
    currency: str = "SGD",
    divisions: Sequence[str] = ("Core Platform Division", "Operations Division"),
    annual_revenue: int = 1_700_000,
    employees: int = 3_900,
    fiscal_year_start_month: int = 4,
    headquarters: str = "Mapletree Business City, Singapore",
    regions: Sequence[str] = ("Central", "East", "North", "North-East", "West"),
    seasonality: str = "flat",
    estate: str = "large",
    landscape: str | None = None,
    given_names: Sequence[str] | None = None,
    surnames: Sequence[str] | None = None,
    system_brands: Mapping[str, str] | None = None,
    cfo_voice: str = (
        "formal and precise, British spelling, acronym-heavy, writes about the agency "
        "in the third person"
    ),
    cfo_phrases: Sequence[str] = (
        "within the approved FY budget",
        "on a Whole-of-Government basis",
        "in line with IM8 requirements",
    ),
    lore_assertion: str = (
        "Under the 2018 cloud-first policy, legacy agency codes and the cloud data "
        "platform mapping are still maintained by hand."
    ),
) -> dict[str, Any]:
    """Construct a lint-clean WorldLoom organisation pack dictionary from user answers."""
    domain_key = base_domain.strip().lower() or "retail"
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

    default_brands = dict(
        DEFAULT_SYSTEM_BRANDS_BY_DOMAIN.get(
            domain_key, DEFAULT_SYSTEM_BRANDS_BY_DOMAIN["retail"]
        )
    )
    if system_brands:
        for k, v in system_brands.items():
            if k in default_brands and v.strip():
                default_brands[k] = v.strip()

    lore_target = DEFAULT_LORE_TARGET_BY_DOMAIN.get(
        domain_key, "data_quality_incident/inventory"
    )
    lore_entries: list[dict[str, Any]] = [
        {
            "kind": "decision",
            "assertion": lore_assertion.strip(),
            "effective_from": "2018-06",
            "constrains": [
                {
                    "kind": "event_likelihood",
                    "target": lore_target,
                    "effect": (
                        "A hand-maintained code mapping drifts, so reconciliation "
                        "failures recur after each migration wave"
                    ),
                    "magnitude": 2.0,
                }
            ],
        }
    ]

    given_pool = list(dict.fromkeys(list(given_names or []) + list(DEFAULT_GIVEN)))
    family_pool = list(dict.fromkeys(list(surnames or []) + list(DEFAULT_SURNAMES)))

    payload: dict[str, Any] = {
        "name": _slugify(company_name),
        "base": domain_key,
        "description": (
            f"SYNTHETIC. {company_name.strip()} ({industry.strip()}). All figures are invented."
        ),
        "company_name": company_name.strip(),
        "industry": industry.strip(),
        "currency": currency.strip().upper() or "SGD",
        "currency_unit": "thousands",
        "fiscal_year_start_month": max(1, min(12, int(fiscal_year_start_month))),
        "annual_revenue": max(1_000, int(annual_revenue)),
        "employees": max(10, int(employees)),
        "headquarters": headquarters.strip() or "Mapletree Business City, Singapore",
        "regions": [r.strip() for r in regions if r.strip()] or ["Central", "East", "West"],
        "seasonality": seasonality.strip().lower() or "flat",
        "estate": estate.strip().lower() or "large",
        "name_pools": {
            "given": given_pool,
            "family": family_pool,
        },
        "system_brands": default_brands,
        "voices": {
            "cfo": {
                "voice": cfo_voice.strip(),
                "phrases": [p.strip() for p in cfo_phrases if p.strip()],
            }
        },
        "units": units,
        "lore": lore_entries,
    }
    if landscape:
        payload["landscape"] = landscape.strip().lower()
    return payload


def write_org_pack_json(
    out_path: Path,
    *,
    company_name: str,
    industry: str,
    base_domain: str = "retail",
    currency: str = "SGD",
    divisions: Sequence[str] = ("Core Platform Division", "Operations Division"),
    annual_revenue: int = 1_700_000,
    employees: int = 3_900,
    fiscal_year_start_month: int = 4,
    headquarters: str = "Mapletree Business City, Singapore",
    regions: Sequence[str] = ("Central", "East", "North", "North-East", "West"),
    seasonality: str = "flat",
    estate: str = "large",
    landscape: str | None = None,
    given_names: Sequence[str] | None = None,
    surnames: Sequence[str] | None = None,
    system_brands: Mapping[str, str] | None = None,
    cfo_voice: str = (
        "formal and precise, British spelling, acronym-heavy, writes about the agency "
        "in the third person"
    ),
    cfo_phrases: Sequence[str] = (
        "within the approved FY budget",
        "on a Whole-of-Government basis",
        "in line with IM8 requirements",
    ),
    lore_assertion: str = (
        "Under the 2018 cloud-first policy, legacy agency codes and the cloud data "
        "platform mapping are still maintained by hand."
    ),
) -> Path:
    """Write a WorldLoom organisation pack JSON file to disk."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_org_pack_dict(
        company_name=company_name,
        industry=industry,
        base_domain=base_domain,
        currency=currency,
        divisions=divisions,
        annual_revenue=annual_revenue,
        employees=employees,
        fiscal_year_start_month=fiscal_year_start_month,
        headquarters=headquarters,
        regions=regions,
        seasonality=seasonality,
        estate=estate,
        landscape=landscape,
        given_names=given_names,
        surnames=surnames,
        system_brands=system_brands,
        cfo_voice=cfo_voice,
        cfo_phrases=cfo_phrases,
        lore_assertion=lore_assertion,
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
    locale: str | None = None,
    facets: Mapping[str, str] | None = None,
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
    if locale:
        spec_dict["locale"] = locale
    if facets:
        spec_dict["facets"] = dict(facets)

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
    locale: str | None = None
    facets: dict[str, str] = {}
    pack_lint_findings: list[str] = []

    if source == "custom":
        company_name = typer.prompt("   Company / agency name", default="Merlion Sovereign Cloud")
        industry = typer.prompt("   Industry / sector", default="Public Sector Digital")
        base_domain = (
            typer.prompt(
                "   Base WorldLoom domain (retail, banking, insurance, procurement)",
                default="retail",
            )
            .strip()
            .lower()
        )
        currency = typer.prompt("   Currency (3-letter ISO code)", default="SGD").strip().upper()
        divisions_raw = typer.prompt(
            "   Divisions / business units (comma-separated)",
            default="Core Platform Division, Cyber Defence Division, Data Services Division",
        )
        divisions = [d.strip() for d in divisions_raw.split(",") if d.strip()]

        advanced = typer.confirm(
            "   Configure advanced WorldLoom blueprint options "
            "(scale, geography, systems, people, facets, lore)?",
            default=False,
        )
        annual_revenue = 1_700_000
        employees = 3_900
        fy_start = 4
        seasonality = "flat"
        headquarters = "Mapletree Business City, Singapore"
        regions: list[str] = ["Central", "East", "North", "North-East", "West"]
        estate = "large"
        given_names: list[str] | None = None
        surnames: list[str] | None = None
        system_brands: dict[str, str] | None = None
        cfo_voice = (
            "formal and precise, British spelling, acronym-heavy, writes about the "
            "agency in the third person"
        )
        lore_assertion = (
            "Under the 2018 cloud-first policy, legacy agency codes and the cloud data "
            "platform mapping are still maintained by hand."
        )

        if advanced:
            annual_revenue = int(
                typer.prompt("   Annual revenue (in currency_unit thousands)", default="1700000")
            )
            employees = int(typer.prompt("   Employees (headcount)", default="3900"))
            fy_start = int(typer.prompt("   Fiscal year start month (1-12)", default="4"))
            seasonality = typer.prompt(
                "   Seasonality (flat, christmas, summer)", default="flat"
            ).strip()
            locale = (
                typer.prompt(
                    "   Locale (singapore, australia, united_kingdom, germany, japan, india, "
                    "china, hong_kong, malaysia, indonesia, taiwan, gulf)",
                    default="singapore",
                )
                .strip()
                .lower()
            )
            headquarters = typer.prompt(
                "   Headquarters location", default="Mapletree Business City, Singapore"
            )
            regions_raw = typer.prompt(
                "   Regions (comma-separated)",
                default="Central, East, North, North-East, West",
            )
            regions = [r.strip() for r in regions_raw.split(",") if r.strip()]
            estate = typer.prompt("   Technology estate size (small, medium, large)", default="large")
            erp_key = "erp" if base_domain == "retail" else next(
                iter(
                    DEFAULT_SYSTEM_BRANDS_BY_DOMAIN.get(
                        base_domain, DEFAULT_SYSTEM_BRANDS_BY_DOMAIN["retail"]
                    )
                )
            )
            platform_key = "platform" if base_domain == "retail" else list(
                DEFAULT_SYSTEM_BRANDS_BY_DOMAIN.get(
                    base_domain, DEFAULT_SYSTEM_BRANDS_BY_DOMAIN["retail"]
                )
            )[2]
            erp_brand = typer.prompt(
                f"   Primary ledger/ERP system name ({erp_key})",
                default="WOG Finance and Procurement System",
            )
            platform_brand = typer.prompt(
                f"   Data/risk platform name ({platform_key})",
                default="GCC Data Platform",
            )
            system_brands = {erp_key: erp_brand, platform_key: platform_brand}
            given_raw = typer.prompt(
                "   Employee given names (comma-separated)",
                default=", ".join(DEFAULT_GIVEN[:8]),
            )
            given_names = [g.strip() for g in given_raw.split(",") if g.strip()]
            surname_raw = typer.prompt(
                "   Employee family surnames (comma-separated)",
                default=", ".join(DEFAULT_SURNAMES[:8]),
            )
            surnames = [s.strip() for s in surname_raw.split(",") if s.strip()]
            cfo_voice = typer.prompt("   CFO executive voice style", default=cfo_voice)
            facets_raw = typer.prompt(
                "   WorldLoom facets (comma-separated key=value: listing, governance, scale, "
                "maturity, competition, margin_profile, trading_pattern)",
                default="listing=state_owned,scale=enterprise",
            )
            facets = parse_facets(facets_raw)
            lore_assertion = typer.prompt("   Historical lore decision assertion", default=lore_assertion)

        pack_path = write_org_pack_json(
            out_dir / "org-pack.json",
            company_name=company_name,
            industry=industry,
            base_domain=base_domain,
            currency=currency,
            divisions=divisions,
            annual_revenue=annual_revenue,
            employees=employees,
            fiscal_year_start_month=fy_start,
            headquarters=headquarters,
            regions=regions,
            seasonality=seasonality,
            estate=estate,
            given_names=given_names,
            surnames=surnames,
            system_brands=system_brands,
            cfo_voice=cfo_voice,
            lore_assertion=lore_assertion,
        )
        loaded_pack = packs.load(str(pack_path))
        pack_lint_findings = packs.lint(loaded_pack)
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
        locale_raw = typer.prompt(
            "   Optional WorldLoom locale (e.g. singapore, australia, united_kingdom, or blank)",
            default="singapore",
        ).strip()
        locale = locale_raw.lower() if locale_raw else None
        facets_raw = typer.prompt(
            "   Optional WorldLoom facets (comma-separated key=value, or blank)",
            default="",
        ).strip()
        facets = parse_facets(facets_raw)
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
            locale=locale,
            facets=facets,
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
                "locale": locale,
                "facets": facets,
                "pack_lint_findings": pack_lint_findings,
            }
        spec = load_proposal_spec(spec_path)
        result = build_proposal(spec, out_dir=out_dir, seed=seed, skip_prose=False)
        verification = verify_proposal_outputs(spec, out_dir=out_dir, build_result=result)
        return {
            "mode": "proposal",
            "executed": True,
            "out": str(out_dir),
            "spec": str(spec_path),
            "locale": locale,
            "facets": facets,
            "pack_lint_findings": pack_lint_findings,
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
            "locale": locale,
            "facets": facets,
            "pack_lint_findings": pack_lint_findings,
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
        locale=locale,
        facets=facets,
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
        "locale": locale,
        "facets": facets,
        "pack_lint_findings": pack_lint_findings,
        "total_large_files": len(entries),
        "total_cases": len(cases),
        "qualified": qual_report.passed,
    }
