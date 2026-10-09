# Specification: Interactive WorldLoom Interface (`bigloom init`) and Custom Pack Documentation

## Overview
Add an interactive command-line wizard (`bigloom init`) so users can configure a synthetic company and run WorldLoom and BigLoom from one interface. Support custom WorldLoom organisation pack JSON files (`.pack(str(path))`) in both `bigloom build` and `bigloom proposal`. Document the WorldLoom CLI and the four company input modes in `README.md`.

## Functional Requirements
1. **Custom Org-Pack JSON Support**:
   - Update `src/bigloom/build.py` (`_resolve_world_context`) so when `world_pack` points to a `.json` file on disk, it reads the `base` domain (default `"retail"`) and builds the world via `sdk.company(base_domain, seed=seed).pack(str(candidate)).build().world`.
   - Update `src/bigloom/proposal/facts.py` (`_load_world`) so when `spec.world_pack` points to a `.json` file on disk, it calls `sdk.company(base_domain, seed=seed).pack(str(candidate)).build().world` so custom `units`, `company_name`, and `currency` populate `world.company` and `world.business_units`.
2. **Interactive Wizard (`bigloom init` in `src/bigloom/wizard.py` and `src/bigloom/cli.py`)**:
   - Prompt the user step by step via `typer.prompt` and `typer.confirm`:
     1. Generation mode: `proposal` (single-topic 5 to 1024 MiB `.docx` funding proposal) or `corpus` (multi-format `.docx`, `.xlsx`, `.pptx`, `.pdf` corpus).
     2. Company source:
        - `custom`: ask for company name, industry label, base domain (`retail`, `saas`, `manufacturing`, `healthcare`, `logistics`), 3-letter currency code (for example `SGD`), and comma-separated division names. Write a valid WorldLoom `org-pack.json` into the output directory.
        - `domain`: ask for a WorldLoom industry domain (`retail`, `saas`, `manufacturing`, `healthcare`, `logistics`).
        - `pack`: ask for a bundled WorldLoom pack name (`aurora-energy`, `borealis-health`, `cygnus-Holdings`, `draco-logistics`, `ecliptic-cloud`, `falcon-defense`, `gemini-biotech`, `helios-grid`) or path to an existing `.json` pack.
     3. Target sizes in MiB (comma-separated, for example `5` or `18,50`).
     4. For `proposal` mode: ask for the proposal subject, short subject, project code, and whether to skip Vertex Gemini prose generation (`--skip-prose`, default `True` for dry runs). Write `proposal-spec.yaml` into the output directory.
     5. For `corpus` mode: ask for comma-separated formats (default `docx,xlsx,pptx,pdf`).
     6. Ask whether to run the build immediately (`--run / --no-run` or interactive confirmation). When confirmed, execute `build_proposal` + `verify_proposal_outputs` (for `proposal` mode) or `build_corpus` + `generate_queries` + `qualify_corpus` (for `corpus` mode) and print the JSON summary.
3. **README Documentation**:
   - Document the `.venv/bin/worldloom` CLI commands (`worldloom build`, `worldloom pack`, `worldloom demo`, `worldloom render`).
   - Document the four ways to supply company inputs to BigLoom (`bigloom init` interactive wizard, `--domain`, `--world-pack` bundled or custom JSON, and `--corpus-dir`).

## Acceptance Criteria
- `bigloom init` runs interactively via `CliRunner` in `tests/test_wizard.py` for both `proposal` and `corpus` modes, writes valid `org-pack.json` and `proposal-spec.yaml` files, and executes the backend build and verification.
- Custom `.json` org packs populate `world.company.name`, `world.company.currency`, and `world.business_units` in both `bigloom build` and `bigloom proposal`.
- `pytest --cov=src/bigloom` passes with >= 90% coverage and `ruff check .` reports 0 errors.
