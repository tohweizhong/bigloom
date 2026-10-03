# Specification: WorldLoom Blueprint and Pack Ingestion (`worldloom_blueprint_ingest_20261004`)

## 1. Overview
This feature track integrates `worldloom.world.World` and `worldloom.sdk` directly into [`src/bigloom/build.py`](file:///usr/local/google/home/weizhongt/coding/bigloom/src/bigloom/build.py) and `bigloom build`. Instead of relying only on static topic strings, `bigloom build` can load a WorldLoom pack (`--world-pack`, such as `retail-close`), synthesize a WorldLoom company blueprint (`--domain`, such as `retail`, `banking`, or `insurance`), or load an exported WorldLoom directory (`--corpus-dir`).

## 2. Functional Requirements

### 2.1 WorldLoom Source Resolution (`src/bigloom/build.py`)
- Support three WorldLoom grounding sources in `build_corpus` and `bigloom build`:
  1. `--world-pack`: Loads a named WorldLoom pack or path via `World.load(world_pack)`.
  2. `--domain`: Builds a deterministic WorldLoom `World` via `worldloom.sdk.company(domain, seed=seed).build().world` (supporting `retail`, `banking`, and `insurance`).
  3. `--corpus-dir`: Loads a WorldLoom world directory if `company.json` is present, or reads markdown and text files from `--corpus-dir`.
- Extract grounded enterprise context from the resolved `World`:
  - Company name and currency (`world.company.name`, `world.company.currency` or `SGD`).
  - Business units (`world.business_units`), cost centres (`world.cost_centres`), systems (`world.systems`), and sites (`world.sites`).
  - Canonical facts (`world.facts`) when present.

### 2.2 Grounded Document Prose and High-Entropy Facts
- Weave the extracted WorldLoom company name, business unit names, cost centre codes, system names, and site names into the preamble units (`1..5`) and deep planted section (`unit >= 6`) of every rendered `.docx`, `.xlsx`, `.pptx`, and `.pdf` file.
- Use the company's currency code (such as `AUD`, `USD`, or `SGD`) for high-entropy `text_golden_value` and `text_canary_value` figures while preserving global uniqueness and qualification compliance.

## 3. Non-Functional Requirements
- **Backward Compatibility:** Existing calls to `build_corpus` without `--world-pack` or `--domain` remain 100% deterministic and pass all existing tests.
- **Qualification Gate Compliance:** Every corpus built from `--world-pack` or `--domain` must pass `bigloom qualify --check-retrieval` with zero violations.
- **Code Coverage:** Maintain at least 90% test coverage across `src/bigloom/`.

## 4. Acceptance Criteria
1. Running `bigloom build --world-pack retail-close` and `bigloom build --domain banking` produces rendered files whose text units contain the WorldLoom company name, business units, and cost centres.
2. Running `bigloom queries` and `bigloom qualify` on a WorldLoom-grounded build exits with code `0` and zero violations.
3. All unit tests pass with zero `ruff` warnings.

## 5. Out of Scope
- Modifying the upstream `worldloom` (`synthetic-foundry`) library.
