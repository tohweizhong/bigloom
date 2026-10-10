# Specification: Unified Multi-Format Large-File Pipeline (`bigloom build` and `bigloom init`)

## Overview
Combine the separate `proposal` and `corpus` modes into one unified BigLoom pipeline (`bigloom build` and `bigloom init`). Support file sizes up to `1024 MiB` (`1 GiB`) across `.docx`, `.xlsx`, `.pptx`, and `.pdf` through two core flags: `--sizes-mb` and `--formats`. Ensure every generated corpus produces `manifest.jsonl`, `cases.json`, and `evals.csv` and passes the `bigloom qualify` anti-leakage gate.

## Functional Requirements
1. **Single Unified Pipeline (`bigloom build` and `bigloom init`)**:
   - Remove the `proposal` vs `corpus` mode question from `bigloom init` (`src/bigloom/wizard.py`).
   - Accept `--sizes-mb` (from `0.1` up to `1024` MiB / `1 GiB`) and `--formats` (`docx,xlsx,pptx,pdf`) on both `bigloom build` and `bigloom init`.
   - Ground every generated file in WorldLoom (`world.company`, `world.business_units`, `world.cost_centres`, `world.systems`, `world.sites`, and `world.facts` via `.episodes("2026-01", periods=2)`), planting canonical golden facts and superseded/comparator draft canary facts.
2. **Scalable Multi-Format Rendering up to 1 GiB (`src/bigloom/build.py`)**:
   - Scale `_split_image_budgets` chunk sizing dynamically (up to `32 MiB` per plate for files `>= 100 MiB`) and use WorldLoom vector engineering plates (`make_figs` from `src/bigloom/proposal/plates.py`) alongside high-entropy RGB plates so `.docx`, `.xlsx`, `.pptx`, and `.pdf` files scale up to `1024 MiB` (`1 GiB`) without memory blowup or `shape-ballast.bin`.
   - Automatically write `manifest.jsonl`, `cases.json` (via `generate_queries`), and `evals.csv` (`query,golden`) in the output directory.
3. **Streamlined Interactive Wizard (`bigloom init` in `src/bigloom/wizard.py`)**:
   - Prompt only for:
     1. Company source (`custom`, `domain`, or `pack`) and WorldLoom company/blueprint settings.
     2. Target file sizes in MiB (`--sizes-mb`, default `"18,50,100"`, supports up to `1024`).
     3. File formats (`--formats`, default `"docx,xlsx,pptx,pdf"`).
     4. Confirm immediate build and qualification (`Y/n`).
4. **Documentation (`README.md`)**:
   - Update `README.md` to present a single unified workflow (`bigloom init` or `bigloom build --sizes-mb ... --formats ...`) without any separate `proposal` vs `corpus` mode distinction.

## Acceptance Criteria
- `bigloom init` never asks to choose between `proposal` and `corpus` mode.
- `bigloom build` and `bigloom init` accept `--sizes-mb` (up to `1024`) and `--formats` (`docx,xlsx,pptx,pdf`) and produce `large/`, `traps/`, `manifest.jsonl`, `cases.json`, and `evals.csv`.
- All unit tests pass with `>= 90%` coverage and `ruff check .` reports 0 errors.
