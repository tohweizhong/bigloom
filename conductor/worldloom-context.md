# WorldLoom (synthetic-foundry) Project Context

Last Updated: 16 Oct 2026 SGT
Updated By: Jetski repo-research subagent

Repository: `/usr/local/google/home/weizhongt/coding/sharepoint-research/worldloom/synthetic-foundry`
Commit: `3fcf194ed692ad004f26312202c9eff799bcbe57` (merge of PR #63, 28 Sep 2026 07:25 SGT)

## Project Identity

- **Name:** `worldloom`. The repository, the Python package, and the command share this name (`pyproject.toml:6`, `README.md:13`).
- **Type:** Python library plus Typer CLI. The console script is `worldloom = "worldloom.cli:app"` (`pyproject.toml:131-132`).
- **Purpose:** It generates a synthetic enterprise world (company, facts, events, history). It then renders that state into workbooks, documents, slides, PDFs, tickets, and knowledge pages, plus evaluation cases tied to the evidence (`README.md:3-7`, `pyproject.toml:10`).
- **Domain:** Synthetic data for retrieval, RAG, document extraction, temporal questions, and agent workflow evaluation (`README.md:9-11`, `pyproject.toml:18-27`).
- **Version and status:** `0.1.0`, unreleased, Alpha. Nothing is on PyPI. Every install starts from a checkout (`src/worldloom/__init__.py:153`, `README.md:30-31`, `pyproject.toml:29-32`).
- **Licence and author:** Apache-2.0. Author Vamsi Ramakrishnan. Upstream `https://github.com/vamsiramakrishnan/worldloom` (`pyproject.toml:12-16`, `pyproject.toml:62`).
- **Key design rule:** The library never calls a language model. A coding harness (the "agent") writes the prose. WorldLoom checks that prose against the world (`README.md:31`, `AGENTS.md:13-24`, `pyproject.toml:79-80`).
- **Determinism:** A corpus replays byte for byte from `seed + recipe + generation ledger`. CI rebuilds corpora and compares bytes on every push (`AGENTS.md:29-30`).

## Project Structure (Repo Map)

Source: `find . -maxdepth 3` and `ls` output, Phase 1. The agent read no source file in Phase 1.

| Path | Kind | Notes |
| --- | --- | --- |
| `pyproject.toml` | Root config | Python package metadata. |
| `README.md`, `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `RELEASING.md`, `SECURITY.md` | Documentation | `CHANGELOG.md` is 251 KB. |
| `Dockerfile`, `.dockerignore` | Infrastructure | Container build. |
| `.mcp.json` | Infrastructure | MCP server registration for agents. |
| `.pre-commit-config.yaml` | Tooling | Pre-commit hooks. |
| `.github/workflows/` | CI | `ci.yml`, `determinism-sweep.yml`, `docs.yml`, `process-bindings-check.yml`, `release.yml`, `slow-tests.yml`. |
| `.claude/commands/` | Agent commands | `worldloom-act`, `-build`, `-design`, `-evalrun`, `-evaluate`, `-narrate`, `-render`. |
| `.claude/skills/` | Agent skills | 19 skills, for example `worldloom-sdk`, `worldloom-packs`, `worldloom-synthesis`. |
| `docs/` | Documentation | About 50 pages. Examples: `architecture.md`, `connector-serving.md`, `enterprise-corpus.md`, `gemini-enterprise.md`, `sdk.md`, `studio.md`. |
| `site/` | Docs site | Astro site (`astro.config.mjs`, `package.json`). |
| `src/worldloom/` | Python package | 204 entries at top level. |
| `src/worldloom/cli.py` | Entry point | Main CLI (candidate). |
| `src/worldloom/mcp.py` | Entry point | MCP server (candidate). |
| `src/worldloom/*_cli.py` | Sub-app entry points | `connector_serving_cli`, `contracts_cli`, `dataset_cli`, `enterprise_qualification_cli`, `interview_cli`, `packkit_cli`, `quality_cli`, `seams_cli`, `studio_cli`, `synthesis_cli`. |
| `src/worldloom/sdk.py`, `enterprise_sdk.py` | Python API | SDK surface (candidate). |
| `src/worldloom/models.py`, `world.py`, `company.py` | Data model | Candidate schema files. |
| `src/worldloom/connector_*.py` | Connector layer | `connector_data`, `_definition`, `_emulator`, `_eval_runtime`, `_fields`, `_keys`, `_payload`, `_projection`, `_query`, `_realism`, `_results`, `_seed`, `_trace`. |
| `src/worldloom/connectors/` | Connector layer | `anvil.py`, `anvil_provider.py`, `anvil_surface.mjs`, `contracts.py`, `enterprise.py`, `serving.py`, `surface.py`, `query/`. |
| `src/worldloom/render/` | Artifact renderers | `docx.py`, `pptx.py`, `xlsx.py`, `pdf.py`, `html.py`, `markdown.py`, `ooxml.py`, `bundles.py`, `enterprise/`. |
| `src/worldloom/studio/` | Studio web app | `server.py`, `service.py`, `store.py`, `worker.py`, `static/`. |
| `src/worldloom/gemini_enterprise/` | GE integration | `cli.py`, `datastore.py`, `cases.py`, `results.py`. |
| `src/worldloom/evalrun/` | Eval runner | 35 modules, for example `runner.py`, `grader.py`, `cli.py`. |
| `src/worldloom/compiler/`, `pipeline/`, `generators/`, `narrative/`, `synthesis/`, `interview/`, `packkit/`, `process_bindings/`, `actors/`, `evaluate/`, `evals/` | Subsystems | Generation and evaluation subsystems. |
| `src/worldloom/_data/`, `src/worldloom/data/` | Package data | `_data` has 144 files: `artifact-types`, `connectors`, `packs`, `pcf`, `onet`, `locales`, `process-catalogue`, and more. |
| `examples/` | Sample inputs | `hospital/`, `retail-close/` (world plus JSONL ledgers), `packs/`, `enterprise-evals/`, `episodes/`, `studio/`. |
| `evals/` | Repo-level evals | `enterprise_minimum.py`, `executive_narration.py`, `alphaevolve/`. |
| `tools/` | Scripts | Ingest (`ingest_onet.py`, `ingest_apqc.py`), harvest, `build_sor_connector.py`, `measure_*.py`, `sweep.py`. |
| `tests/` | Tests | 347 entries. |

## Technology Stack

| Layer | Technology | Source |
| --- | --- | --- |
| Language | Python 3.11 or later. CI tests 3.11, 3.12, 3.13. | `pyproject.toml:17`, `.github/workflows/ci.yml:95` |
| Build backend | hatchling. Version is read from `src/worldloom/__init__.py`. | `pyproject.toml:1-3`, `pyproject.toml:134-135` |
| Core dependencies | `pydantic>=2.6`, `typer>=0.12`, `rich>=13.0`, `networkx>=3.2`, `numpy>=1.26` | `pyproject.toml:44-59` |
| Renderer extras | `xlsx` (openpyxl), `docx` (python-docx), `pdf` (reportlab), `pptx` (python-pptx) | `pyproject.toml:68-71` |
| Dataframe extras | `polars`, `pandas`, `arrow` (pyarrow) | `pyproject.toml:72-74` |
| MCP extra | `mcp>=2.2,<3`, for `worldloom mcp` over stdio | `pyproject.toml:75-81` |
| Embeddings extra | `model2vec>=0.6`, `huggingface-hub>=0.24`. This is the only part that downloads weights. | `pyproject.toml:82-98` |
| `all` extra | The four renderers plus `mcp` | `pyproject.toml:101-107` |
| `ingest` extra | openpyxl, faker, babel, pycountry, geonamescache, holidays. Used only by `tools/ingest_*.py`. | `pyproject.toml:108-119` |
| `dev` extra | pytest, the renderers, mcp, hypothesis | `pyproject.toml:120-129` |
| Wheel contents | `src/worldloom` plus `examples/` copied to `worldloom/_examples` | `pyproject.toml:137-141` |
| Lint | ruff 0.15.8 (no formatter) | `pyproject.toml:147-204`, `.pre-commit-config.yaml:4-17` |
| Types | mypy 2.3.1, with a module debt list (`ignore_errors`) | `pyproject.toml:218-321`, `.github/workflows/ci.yml:53` |
| Tests | pytest. Slow tests are deselected by default. | `pyproject.toml:323-337` |
| Container | `python:3.12-slim`, two stages. Installs the wheel with `[all]`. | `Dockerfile:16-34` |
| Docs site | Astro 5 plus Starlight, npm, in `site/` | `AGENTS.md:212`, `AGENTS.md:136-137` |
| Concurrency | No async in `src/`. One thread pool in `narrative/compiler.py`, one in `evalrun.runner.run_cases`. | `AGENTS.md:181-183` |

## Configuration

- There is no `.env.example` file. The root has no `.env*` file (Phase 1 `ls -a`).
- `.mcp.json` registers one MCP server named `worldloom`. It runs `worldloom mcp` with an empty `env` (`.mcp.json:1-9`).
- `pyproject.toml` holds all gates: extras, ruff, mypy, and pytest configuration (`AGENTS.md:189`).
- The version is single-sourced in `src/worldloom/__init__.py` (`pyproject.toml:7-9`, `src/worldloom/__init__.py:153`).
- The Studio container uses a `/workspace` volume for company revisions, jobs, and datasets. It exposes port 8765 (`Dockerfile:35-44`).
- Runtime environment variables found in source (detail in the Environment Variable Dependency Chain section):

| Variable | Read at | Default when unset |
| --- | --- | --- |
| `WORLDLOOM_OUTPUT` | `src/worldloom/cli.py:884` | Refusals print as prose. `json` gives one JSON line on stderr. |
| `WORLDLOOM_DATASET_WORKERS` | `src/worldloom/evals/dataset.py:258` | `packkit.policy("dataset.workers")` |
| `WORLDLOOM_STUDIO_HARNESS` | `src/worldloom/studio/worker.py:75`, `src/worldloom/studio/server.py:68-71` | No harness command |
| `WORLDLOOM_VECTOR_CACHE` | `src/worldloom/evaluate/embedding.py:203-207` | `.worldloom/vectors` |
| `WORLDLOOM_CONTRACTS_CACHE` | `src/worldloom/connectors/contracts.py:59`, `:211-215` | `~/.cache/worldloom/contracts` |
| `WORLDLOOM_ANVIL` | `src/worldloom/evalrun/anvil.py:74`, `:86` | `anvil` on `PATH` |
| `--tokens-env <NAME>` (name given by flag) | `src/worldloom/connector_serving_cli.py:19`, `:57-64` | No tokens. A set flag with an unset variable raises `ValueError`. |

## Development Workflow

Commands come from `AGENTS.md:95-108`, `README.md:320-326`, and `.github/workflows/ci.yml`.

| Step | Command | Source |
| --- | --- | --- |
| Install (checkout) | `python -m pip install -e '.[all,dev]'` | `README.md:323` |
| Install hooks | `pre-commit install` (ruff-check plus `worldloom docs --check`) | `AGENTS.md:97`, `.pre-commit-config.yaml:1-31` |
| Check install | `worldloom doctor` (names the missing extra) | `AGENTS.md:98`, `AGENTS.md:207-209` |
| Tests | `pytest -q` (slow tests deselected) | `AGENTS.md:100`, `pyproject.toml:337` |
| Slow tests | `pytest -m slow -q` | `AGENTS.md:102` |
| Lint | `ruff check .` | `AGENTS.md:103` |
| Types | `mypy` | `AGENTS.md:104` |
| Golden corpus | `worldloom validate retail-close` | `AGENTS.md:106`, `.github/workflows/ci.yml:135-136` |
| Docs drift | `worldloom docs --check`. After a CLI change, run `worldloom docs` and commit the new reference. | `AGENTS.md:107`, `AGENTS.md:237-241` |
| Wheel | `pipx run build` | `README.md:63` |
| Container | `docker build -t worldloom .` | `README.md:75` |
| Docs site | `cd site && npm ci && npm run build` | `AGENTS.md:136-137` |

CI jobs in `ci.yml`: `lint` (ruff and mypy on 3.11), `dispersed-replay` (byte identity on 3.12), `test` (pytest matrix, docs check, golden corpus, build and render validation) (`.github/workflows/ci.yml:28-146`).

## Architecture Patterns

- **Layered pipeline around one immutable world.** `World` is a dataclass and the single entry point for load, build, and validate (`AGENTS.md:34-35`, `src/worldloom/world.py:65`, `src/worldloom/world.py:151`, `src/worldloom/world.py:1146`).
- **Thin waist of frozen pydantic models.** Every model uses `ConfigDict(frozen=True, extra="forbid")` (`src/worldloom/models.py:33-40`, `AGENTS.md:36-39`).
- **Pipeline stages** (`AGENTS.md:41-54`):
  1. `generators/` mint entities, facts, and events from recipe steps with seeded RNG streams and `ids.Minter`.
  2. `documents.py` compiles `ArtifactIntent` to `ArtifactIR`. `compiler/` is the deterministic artifact compiler.
  3. `narrative/` takes prose requests, validates claims, and writes the generation ledger.
  4. `render/` turns IR into bytes. `workspace.py` writes a permissioned shared-drive tree.
  5. `validate.py` is the coherence gate. `evaluate/` scores retrieval hardness.
- **Determinism spine.** Generation ledger, recipe, and content-addressed receipts make every corpus replay byte for byte (`AGENTS.md:56-69`). No `random`, `uuid`, wall clock, or builtin `hash()` in `src/` (`AGENTS.md:141-149`).
- **Registration seams.** `register_domain`, `register_step`, `register_domain_checks`, `register_artifact_types`, `registries.declare`, and `narrative/prompts.register`. `__init__._install()` imports every vertical unconditionally (`AGENTS.md:157-163`, `src/worldloom/__init__.py:158`).
- **Thin CLI monolith.** `cli.py` is about 397 KB. It imports lazily inside command bodies. `@app.callback()` runs `_install()` before every command (`AGENTS.md:70-72`, `src/worldloom/cli.py:666`).
- **Agent is the writer.** All write paths use file handshakes (`requests` then `accept`), validated all or nothing (`src/worldloom/mcp.py:3-9`, `AGENTS.md:13-24`).
- **Three library seams** named by `worldloom seams`: `connectors/` (connector emulation and trace grading), `evals/` (eval-first design to proof), `pipeline/` (typed orchestration) (`AGENTS.md:82`, `src/worldloom/cli.py:127`).
- **Data-driven connector emulation.** One emulator reads JSON connector definitions with search, paging, projection, workflows, ACLs, idempotency, faults, and a frozen clock (`README.md:289-294`, `src/worldloom/connector_definition.py:323-350`).
- **Typed errors and stable refusal codes.** `CorpusError`, `CoherenceError`, `RecipeError`, `NarrationError`, `RenderError`, plus `ValidationReport`. CLI refusals use the `_REFUSALS` registry (`AGENTS.md:165-169`, `src/worldloom/cli.py:860-890`).

## External Integrations

| Integration | Direction | How | Source |
| --- | --- | --- | --- |
| Coding harness (`claude`, `codex`) | WorldLoom calls the installed CLI with its own login | `narrate loop --harness`, `evalrun run --harness`, `studio serve --harness` | `README.md:194-206`, `src/worldloom/studio_cli.py:44-75` |
| MCP clients | Client calls WorldLoom | `worldloom mcp` over stdio | `.mcp.json:1-9`, `src/worldloom/mcp.py:725-727` |
| MCP agents over HTTP | Agent calls WorldLoom | `enterprise-evals serve`, StreamableHTTP at `/mcp` | `src/worldloom/connector_serving_cli.py:27-34`, `:82-87` |
| Anvil (vendor API simulator) | WorldLoom starts `anvil simulate serve` per connector per case | `evalrun run --connectors anvil`. CLI found by `WORLDLOOM_ANVIL` or `PATH`. | `src/worldloom/evalrun/anvil.py:1-15`, `:74-90` |
| Gemini Enterprise Eval Studio / Discovery Engine | Export only. WorldLoom writes files. It does not call the API. | `gemini-enterprise datastore` writes `documents.jsonl` (`gcsSource`, `dataSchema: "document"`, `content.uri`, `aclInfo`) | `src/worldloom/gemini_enterprise/cli.py:22-58`, `src/worldloom/gemini_enterprise/datastore.py:1-30` |
| Vendor API contracts (OpenAPI 3, Swagger 2, Discovery) | Fetch and cache | `worldloom contracts fetch/build` | `src/worldloom/connectors/contracts.py:55-62`, `src/worldloom/contracts_cli.py:50-74` |
| Hugging Face Hub (model2vec weights) | Download, optional | `evaluate --retriever embedding` | `pyproject.toml:82-98` |
| Jira, Confluence, ServiceNow | No live call | Rendered bundles only. "Rendering a Jira or ServiceNow bundle does not write to a live tenant." | `README.md:181-187` |
| Language model APIs | None | The package never calls a model service | `README.md:31`, `pyproject.toml:79-80` |

## API Surface / Route Map

### CLI: top-level commands (`worldloom <command>`)

Root app: `src/worldloom/cli.py:35-39`. Console script: `pyproject.toml:132`.

| Command | Line | Command | Line |
| --- | --- | --- | --- |
| `demo` | `cli.py:1117` | `build` | `cli.py:1144` |
| `render` | `cli.py:4109` | `mosaic` | `cli.py:4206` |
| `inspect` | `cli.py:4662` | `status` | `cli.py:4748` |
| `validate` | `cli.py:4843` | `verify` | `cli.py:4895` |
| `migrate` | `cli.py:5054` | `evolve` | `cli.py:5211` |
| `formats` | `cli.py:5427` | `evaluate` | `cli.py:5464` |
| `search` | `cli.py:5648` | `diversity` | `cli.py:5828` |
| `topology` | `cli.py:6126` | `series` | `cli.py:6215` |
| `mcp` | `cli.py:6380` | `twin` | `cli.py:6415` |
| `mutate` | `cli.py:6520` | `stats` | `cli.py:6649` |
| `fidelity` | `cli.py:6707` | `calibrate` | `cli.py:6774` |
| `actors` | `cli.py:6999` | `workspace` | `cli.py:7792` |
| `archetypes` | `cli.py:7849` | `doctor` | `cli.py:7863` |
| `version` | `cli.py:8018` | `docs` | `cli.py:8024` |
| `spaces` | `cli.py:8186` | `seams` | `cli.py:127` |

Important `build` flags: `--seed`, `--period`, `--out`, `--incident/--no-incident`, `--pack`, `--episode`, `--employees`, `--periods`, `--format/-f`, `--eval-density`, `--narrate`, `--replay`, `--distractors`, `--access`, `--messiness`, `--realism`, `--overwrite` (`src/worldloom/cli.py:1147-1559`). `workspace` takes `--out`, `--overwrite`, and `--noise none|lived_in|neglected` (`src/worldloom/cli.py:7792-7840`).

### CLI: sub-apps

| Sub-app | Commands | Source |
| --- | --- | --- |
| `evals` | `export`, `construct`, plus `calibration` (`ingest`, `report`) and `dataset` (`compile`, `verify`) | `cli.py:40-41`, `cli.py:5287-5304`, `cli.py:111-112`, `quality_cli.py:167-215`, `dataset_cli.py:13-37` |
| `narrate` | `requests`, `accept`, `loop`, plus `readers` (`requests`, `accept`) | `cli.py:3200-3319`, `cli.py:110`, `quality_cli.py:99-119` |
| `plan` | `requests`, `accept` | `cli.py:3831-3862` |
| `pack` | `check`, `profiles`, `params`, `facets`, `messiness`, `landscapes`, `locales`, `targets`, `texts`, `export`, `spec`, `template`, plus packkit `kinds`, `list`, `show`, `lint`, `install`, `tree`, `from-tree`, `diff`, `author`, `interview request/accept` | `cli.py:7090-7723`, `cli.py:129`, `packkit_cli.py:33-235` |
| `act` | `requests`, `accept` | `cli.py:3955-4019` |
| `compose` | `requests`, `accept` | `cli.py:3440-3478` |
| `probe` | `open`, `next`, `accept`, `show`, `worlds`, `resolve` | `cli.py:3579-3782` |
| `causal` | `check`, `trace` | `cli.py:6857-6897` |
| `present` | `describe`, `brief`, `lint` | `cli.py:8080-8141` |
| `fleet` | `qualify`, `curate` | `cli.py:5100-5167` |
| `benchmark` | `run` | `cli.py:5760` |
| `enterprise-evals` | `space`, `plan`, `housekeeping`, `validate`, `build`, `score`, `simulate`, `serve`, `qualify` | `cli.py:134-520`, `cli.py:108-109` |
| `industry` | `list`, `programme`, `project` | `cli.py:278-335` |
| `synth` | `example`, `check`, `build`, `verify`, `merge`, `intervene`, `compare`, `search`, `team` | `synthesis_cli.py:38-152`, `cli.py:125` |
| `studio` | `serve`, `init`, `show`, `run`, `evalrun`, `next`, `advance`, `prepare-native`, `interview request/accept`, `pack list/install/author/use`, `pack interview request/accept` | `studio_cli.py:11-427`, `cli.py:126` |
| `gemini-enterprise` | `datastore`, `cases`, `score` | `gemini_enterprise/cli.py:16-119`, `cli.py:128` |
| `evalrun` | `cases`, `requests`, `run`, `merge`, `plan`, `summarize`, `compare`, `import-served`, `import-studio`, `agreement`, `autopsy`, `curriculum`, `export`, `improve`, `corners`, `prove`, `frontier`, `value`, `improve-proposer`, `noise`, `campaign` | `evalrun/cli.py:107-1756`, `cli.py:129` |
| `contracts` | `fetch`, `build`, `trim`, `coverage`, `surface` | `contracts_cli.py:50-165`, `cli.py:130` |
| `interview` | `run`, `next`, `answer`, `status`, `build`, `measure` | `interview_cli.py:76-229`, `cli.py:131` |

### MCP stdio server (`worldloom mcp`)

Transport: stdio (`src/worldloom/mcp.py:725-727`). Needs the `mcp` extra (`src/worldloom/mcp.py:40-57`). The tools are read-only, except the probe tools. The probe tools write only the probe file that the caller names (`src/worldloom/mcp.py:3-26`).

| Tool | Purpose | Line |
| --- | --- | --- |
| `measure_corpus` | Near-duplicate passage groups in a corpus | `mcp.py:329` |
| `corpus_topology` | Dependency graph, services ranked by impact | `mcp.py:344` |
| `corpus_series` | Trend, season, and residual of a fact series | `mcp.py:358` |
| `validate_corpus` | Full coherence gate, violations as data | `mcp.py:378` |
| `probe_open` | Start a probe from a premise | `mcp.py:391` |
| `probe_next` | Next probe question with bounds | `mcp.py:418` |
| `probe_answer` | Answer one probe question | `mcp.py:434` |
| `probe_worlds` | Worlds the probe allows | `mcp.py:525` |
| `probe_resolve` | Turn a settled probe into parameter overrides | `mcp.py:546` |
| `evalrun_cases` | Describe a compiled enterprise case set | `mcp.py:563` |
| `evalrun_run` | Run a built-in agent over the case set | `mcp.py:582` |
| `evalrun_plan` | Grade a planner on the plan axis | `mcp.py:608` |
| `evalrun_summarize` | Summary of a run directory | `mcp.py:633` |
| `evalrun_compare` | Compare two run directories by case | `mcp.py:648` |

### StreamableHTTP MCP server (`worldloom enterprise-evals serve`)

- Defaults: host `127.0.0.1`, port `8000`, path `/mcp`, uvicorn with one worker (`src/worldloom/connector_serving_cli.py:15-16`, `:82-87`).
- Input: an exported corpus directory or an `EnterpriseCorpus` JSON file (`src/worldloom/connector_serving_cli.py:44-46`).
- A non-loopback host needs bearer tokens of at least 24 characters (`src/worldloom/connectors/serving.py:1204-1210`).
- The ASGI app is stateless HTTP with JSON responses and DNS rebinding protection (`src/worldloom/connectors/serving.py:1326-1340`).
- Run state is in memory. Scale out with `--worker-id` and sticky routing by run id (`src/worldloom/connector_serving_cli.py:23`, `:27-33`).

Evaluation tools (7 registered, `src/worldloom/connectors/serving.py:1235-1259`):

| Tool | Arguments | Read only | Purpose |
| --- | --- | --- | --- |
| `eval_list` | `offset`, `limit` | Yes | List evaluation questions |
| `eval_begin` | `query_id` | No | Start an isolated run. Returns `run_id`. |
| `eval_trace` | `run_id`, `offset`, `limit` | Yes | Read observed tool spans |
| `eval_grade` | `run_id` | Yes | Grade calls and record state |
| `eval_score` | `run_id`, `answer`, `artifacts`, `planned_dag` | Yes | Three-axis grade (plan, trajectory, outcomes) |
| `eval_ask` | `run_id`, `question`, `about` | No | Ask the simulated user a question |
| `eval_end` | `run_id` | No | Grade and release the run |

Connector tools: one tool per connector definition tool, with an extra `run_id` argument. With `--surface contract`, the server serves Anvil contract operations instead (`src/worldloom/connectors/serving.py:1264-1325`, `src/worldloom/connector_serving_cli.py:25`). The docs name connector tools in `connector.tool` form, for example `servicenow.get_record` (`docs/connector-serving.md:21-23`). SharePoint has 17 tools (see Tool Definitions).

Serving limits (defaults from policy `connectors.serving.<limit>`): 32 live runs, 4 runs per principal, 4,096 connector calls per run, 64 KiB request bodies, 1 MiB connector responses, 100,000 initial records, and a ceiling of 100 tools that includes the evaluation tools. An oversized connector response rolls back that call (`docs/connector-serving.md:41-56`). Runs are lost when the process stops. Retrieve the trace before `eval_end` (`docs/connector-serving.md:33-38`).

> The evaluation tool count does not agree across three places. `--check` prints `"evaluation_tools": 5` (`src/worldloom/connector_serving_cli.py:83`). The docs say six (`docs/connector-serving.md:44-45`). The code registers 7, including `eval_ask` (`src/worldloom/connectors/serving.py:1235-1259`). The code is the source of truth.

### Studio HTTP server (`worldloom studio serve`)

- Defaults: host `127.0.0.1`, port `8765`, workspace `./worldloom-workspace` (`src/worldloom/studio_cli.py:44-48`). The container binds `0.0.0.0:8765` (`Dockerfile:39`, `Dockerfile:44`).
- Server: stdlib `http.server` with a loopback `Host` check. No authentication. Body limit 4,000,000 bytes (`src/worldloom/studio/server.py:9`, `:20-39`, `README.md:79-84`).
- Dispatch: `StudioHandler.dispatch` (`src/worldloom/studio/server.py:154`).

| Method | Path | Line |
| --- | --- | --- |
| GET | `/`, `/app.js`, `/creation.js`, `/style.css` (static) | `server.py:161` |
| GET | `/api/bootstrap` | `server.py:166` |
| GET | `/api/preset` | `server.py:170` |
| GET | `/api/packs` | `server.py:176` |
| GET | `/api/packs/{a}/{b}` | `server.py:180` |
| GET | `/api/jobs/{id}` | `server.py:183` |
| GET | `/api/projects/{id}` | `server.py:199-201` |
| GET | `/api/projects/{id}/workflow`, `/creation`, `/native-sources`, `/native-queryset`, `/agent-results`, `/native-artifact`, `/history`, `/evidence`, `/evals` | `server.py:204-243` |
| POST | `/api/projects` | `server.py:262` |
| POST | `/api/packs` | `server.py:265` |
| POST | `/api/packs/author` | `server.py:269` |
| POST | `/api/jobs/{id}/retry` | `server.py:285` |
| POST | `/api/projects/{id}/{action}`, where action is `revise`, `interview-request`, `interview-accept`, `interview-apply`, `packs`, `select-narration`, `prepare-data`, `prepare-native`, `run` | `server.py:289-330` |

Error codes: 404 route not found, 400 pack refused, 409 conflict, 422 value error (`src/worldloom/studio/server.py:335-342`).

## Runtime Dependency Graph

WorldLoom has no database and no required background service. Most commands are one-shot processes that read and write a corpus directory.

```text
1. Batch CLI:   shell -> worldloom <cmd> -> corpus directory (world.json + *.jsonl + rendered files)
2. MCP stdio:   MCP client -> worldloom mcp (stdio) -> corpus paths given per call
3. Connector:   agent -> HTTP 127.0.0.1:8000/mcp (uvicorn, 1 worker) -> ConnectorEvaluationService (in-memory runs) -> EnterpriseCorpus on disk
4. Studio:      browser -> http.server 127.0.0.1:8765 -> Studio service -> workspace directory
                                                  \-> child: python -m worldloom.studio.worker <root> <job> -> optional harness (codex | claude)
5. Anvil runs:  worldloom evalrun run --connectors anvil -> anvil simulate serve (1 server per connector per case)
                -> python -m worldloom.anvil_provider (state provider); agent gets ANVIL_* variables
```

Sources: (1) `AGENTS.md:110-121`. (2) `.mcp.json:1-9`, `src/worldloom/mcp.py:725-727`. (3) `src/worldloom/connector_serving_cli.py:15-16`, `:44-46`, `:73-87`. (4) `src/worldloom/studio_cli.py:44-75`, `src/worldloom/studio/server.py:68-75`. (5) `src/worldloom/evalrun/anvil.py:1-15`, `src/worldloom/evalrun/harness.py:62-70`.

## Local Dev Runbook

1. Clone and create a virtual environment: `python -m venv .venv` then `source .venv/bin/activate` (`README.md:39-42`).
2. Install with all renderers and dev tools: `python -m pip install -e '.[all,dev]'` (`README.md:323`).
3. Check the install: `worldloom doctor` (`AGENTS.md:98`).
4. Build a corpus: `worldloom build --seed 8128 --incident --narrate --out ./corpus` (`README.md:45`).
5. Render files: `worldloom render ./corpus -f xlsx -f docx -f pptx -f pdf -f markdown` (`README.md:46`).
6. Validate: `worldloom validate ./corpus` (`README.md:47`).
7. Score retrieval: `worldloom evaluate ./corpus --retriever both` (`README.md:48`).
8. Write the permissioned drive tree: `worldloom workspace ./corpus -o ./drive` (`README.md:183`).
9. Check the next stage: `worldloom status ./corpus` (`README.md:49`).
10. Optional, Studio UI: `worldloom studio serve`, then open `http://127.0.0.1:8765` (`README.md:21`, `src/worldloom/studio_cli.py:44-48`).
11. Optional, connector MCP server: `worldloom enterprise-evals build ./corpus ./cases ...` then `worldloom enterprise-evals serve <corpus>` on port 8000 (`AGENTS.md:126`, `src/worldloom/connector_serving_cli.py:13-16`).
12. Optional, container: `docker build -t worldloom .` then `docker run --rm -p 127.0.0.1:8765:8765 -v worldloom-workspace:/workspace worldloom` (`README.md:75-76`).

## Environment Variable Dependency Chain

No variable is required for the core build, render, and validate loop. The Quickstart needs "No model service or credentials" (`README.md:35-36`).

| Variable | Consumer | Effect when missing |
| --- | --- | --- |
| `WORLDLOOM_OUTPUT` | CLI `_refuse` (`src/worldloom/cli.py:866-884`) | Refusals print as prose. Set to `json` to get one JSON line on stderr. |
| `WORLDLOOM_DATASET_WORKERS` | `evals.dataset.dataset_workers` (`src/worldloom/evals/dataset.py:251-262`) | Uses `packkit.policy("dataset.workers")`. Changes speed only, not output. |
| `WORLDLOOM_STUDIO_HARNESS` | Studio server sets it for the worker child. The worker reads it (`src/worldloom/studio/server.py:68-71`, `src/worldloom/studio/worker.py:75`). | Harness jobs (`interview`, `narrate`, `foundry`, harness `evalrun`) fail with "start Studio with a coding harness command" (`src/worldloom/studio/server.py:316-322`). |
| `WORLDLOOM_VECTOR_CACHE` | `evaluate/embedding.py` (`:196-207`) | Cache goes to `.worldloom/vectors`. |
| `WORLDLOOM_CONTRACTS_CACHE` | `connectors/contracts.default_cache` (`src/worldloom/connectors/contracts.py:58-59`, `:211-215`) | Fetched sources and built bundles go to `~/.cache/worldloom/contracts` when no `--cache` is given. |
| `WORLDLOOM_ANVIL` | `evalrun/anvil.find_anvil` (`src/worldloom/evalrun/anvil.py:72-90`) | Uses `anvil` on `PATH`. If neither exists, Anvil runs fail with `AnvilError`. |
| Name given by `--tokens-env` | `enterprise-evals serve` (`src/worldloom/connector_serving_cli.py:19`, `:56-66`) | Without the flag: no auth, loopback only. With the flag but no variable: `ValueError`, refusal `connector_serve_failed`. |
| `ANVIL_BASE_URL`, `ANVIL_<CONNECTOR>_BASE_URL`, `ANVIL_CONNECTORS`, `ANVIL_TOKEN` | Set by WorldLoom for the agent under test (`src/worldloom/evalrun/harness.py:64-70`, `src/worldloom/evalrun/anvil.py:9-11`) | Output, not input. The agent cannot reach Anvil without them. |

## Domain Glossary

| Term | Definition | Source |
| --- | --- | --- |
| World | Immutable dataclass that holds the company, entities, facts, events, artifacts, evals, and ledgers of one corpus | `src/worldloom/world.py:65-150` |
| Corpus | The on-disk form of a world: `world.json` plus JSONL files and rendered artifacts | `src/worldloom/corpus.py:41-74` |
| Canonical fact | A dated, authoritative value about a subject. Documents and evals cite facts by ID. | `src/worldloom/models.py:499-512` |
| `{{fact:ID}}` | Placeholder that agent prose must use for every figure. A typed number gives the `bare_number` rejection. | `AGENTS.md:17-19` |
| Recipe | Record of every input that affects a build, so `build --replay` is byte-identical | `AGENTS.md:61-63` |
| Generation ledger | `generation-ledger.jsonl`. Accepted model outputs keyed by seed, call site, ordinal, fact digest, model id, prompt version. | `AGENTS.md:58-60`, `src/worldloom/models.py:1294-1304` |
| Receipt | Content-addressed record of digests left by any external input (priors, surface values, imports) | `AGENTS.md:64-69` |
| Artifact intent | Plan for one document: type, domain, audience, author, required facts, size profile | `src/worldloom/models.py:614-660` |
| Artifact IR | Structure and tables of a document without prose. Renderers consume it. | `AGENTS.md:44-46`, `src/worldloom/models.py:1059` |
| Size profile | `small`, `medium`, `long`, `xlong` on an artifact intent | `src/worldloom/models.py:647` |
| Intentional error | A recorded, reproducible defect placed in an artifact on purpose | `src/worldloom/models.py:1175-1183` |
| Episode | A bounded business process run, for example `MonthEndClose`, `QuarterlyCapitalReturn`, `QuarterlyReserving`, `PurchaseToPayCycle` | `README.md:218-221` |
| Pack | Data that sets a world's shape and lore for an industry | `src/worldloom/cli.py:52-55` |
| Mosaic / fleet | A population of different companies, with qualification and curation for a purpose | `README.md:223-233` |
| Harness | An installed coding agent CLI (`claude`, `codex`) that writes prose for WorldLoom | `README.md:194-206` |
| Connector definition | JSON data (`worldloom.connector-definition/v1`) that drives the emulator for one product | `src/worldloom/connector_definition.py:323-350` |
| Enterprise corpus | Planned queries, connector dataset, and per-query fixtures for multi-connector agent evals | `src/worldloom/enterprise_corpus.py:45-48` |
| Run (`run_id`) | One isolated connector state for one evaluation query on the serving app | `src/worldloom/connectors/serving.py:1238-1239` |
| Three axes | Plan, trajectory, and outcomes. Each eval case is graded on all three. | `AGENTS.md:81`, `src/worldloom/connectors/serving.py:1244-1250` |
| Reference agent | Built-in agent. It is the executable ceiling of a dataset, not a model claim. | `README.md:127-130` |
| Anvil | External vendor-API simulator that WorldLoom can drive per connector per case | `src/worldloom/evalrun/anvil.py:1-15` |
| Noise (`lived_in`, `neglected`) | Drive untidiness: copies, misfilings, personal versions, archive leftovers of real content | `src/worldloom/cli.py:7797-7802` |
| Coherence gate | `validate.py`: referential, graph, financial, temporal, lore, and actor checks | `AGENTS.md:52-54` |

## Data Model Overview

No SQL database exists. The data model is frozen pydantic models (`src/worldloom/models.py:33-40`) written as JSON and JSONL files (`src/worldloom/corpus.py:41-74`).

### Corpus files

| File | Content | Source |
| --- | --- | --- |
| `world.json` | Company, entities, access policies, metadata | `src/worldloom/corpus.py:41` |
| `lore.jsonl` | Lore commitments | `corpus.py:42` |
| `facts.jsonl` | Canonical facts | `corpus.py:43` |
| `events.jsonl` | Enterprise events | `corpus.py:44` |
| `artifact-intents.jsonl` | Artifact intents | `corpus.py:45` |
| `artifact-ir.jsonl` | Artifact IR | `corpus.py:46` |
| `artifact-manifest.jsonl` | Rendered artifact manifest | `corpus.py:47` |
| `intentional-errors.jsonl` | Planted defects | `corpus.py:48` |
| `evals.jsonl` | Evaluation cases | `corpus.py:49` |
| `detail.jsonl`, `causal.jsonl` | Detail tables, causal traces | `corpus.py:55`, `corpus.py:59` |
| `generation-ledger.jsonl` | Accepted authored outputs | `corpus.py:60` |
| `masterdata.json`, `actor-*.jsonl` | Master data and actor simulation records | `corpus.py:70-74` |

### Core entities (`src/worldloom/models.py`)

| Entity | Key fields | Relationships | Line |
| --- | --- | --- | --- |
| `Entity` | `id`, `name` | Base for organisation entities | `:269` |
| `Company` | `industry`, `headquarters`, `fiscal_year_start_month`, `currency` (default `AUD`), `employees_total` | Root of the world | `:276` |
| `BusinessUnit`, `CostCentre`, `Category`, `Site` | Entity fields | Organisation structure | `:306`, `:380`, `:385`, `:400` |
| `Employee` | `title`, `joined`, `left`, `function`, `traits` | `manager_id` to Employee, `business_unit_id`, `cost_centre_id`, `persona_id` | `:329` |
| `System` | `purpose`, `is_system_of_record_for`, `introduced`, `retired` | `owner_id` to Employee | `:356` |
| `Service` | `purpose`, `criticality_tier` (1 to 4) | `owner_id`, `system_id`, `depends_on` to Service | `:367` |
| `EnterpriseEvent` | `kind`, `occurred_at`, `summary` | `actors`, `services`, `systems`, `business_units`, `caused_by` to Event, `lore_ids` | `:477` |
| `CanonicalFact` | `kind`, `subject`, `period`, `value` (`Quantity`), `text_value`, `valid_from`, `valid_to`, `authority` | `event_id`, `supersedes` to Fact, `source_system`, `lore_ids` | `:499` |
| `ArtifactIntent` | `artifact_type`, `domain`, `audience`, `size_profile`, `budget` | `author_id`, `approver_id`, `required_fact_ids`, `triggered_by`, `revises` | `:614` |
| `ArtifactIR` | Sections, tables, charts, flow diagrams | Built from an intent | `:1059` |
| `ArtifactManifestEntry` | `title`, `artifact_type`, `path`, `media_type`, `created_at`, `authority`, `lifecycle`, `version` | `intent_id`, `author_id`, `access_policy_id`, `supersedes`, `revises`, `derived_from` | `:1107` |
| `AccessPolicy` | `label`, `allow_people`, `allow_functions`, `allow_business_units`, `deny_people` | Referenced by manifest entries | `:1152` |
| `IntentionalError` | `error_type`, `observed_value`, `canonical_value`, `detectable` | `artifact_id`, `canonical_fact_id` | `:1175` |
| `EvaluationCase` | `question`, `evaluation_type`, `expected_answer`, `temporal_cutoff`, `expects_abstention`, `difficulty` | `expected_fact_ids`, `required_artifact_ids`, `distractor_artifact_ids` | `:1188` |
| `GenerationLedgerEntry` | `key`, `call_site`, `ordinal`, `world_seed`, `input_facts_digest`, `model_id`, `prompt_version`, `output` | Keyed replay of authored prose | `:1294` |

### Workspace output (`worldloom workspace`)

`workspace.write` copies the rendered files into a folder tree and writes `permissions.jsonl` beside them (`src/worldloom/workspace.py:507-585`).

- It needs a corpus on disk with rendered `artifacts/`. Otherwise it raises `ValueError` (`src/worldloom/workspace.py:519-530`).
- It copies bytes. It does not render again (`src/worldloom/workspace.py:511-513`).
- With `--overwrite`, it deletes the target tree first (`src/worldloom/workspace.py:532-536`).
- Each `permissions.jsonl` row has `path`, `artifact_id`, `title`, `owner`, `readers`, `policy`, `created`, and optional `superseded_by`, `noise`, `copy_of` (`src/worldloom/workspace.py:557-570`).
- Noise adds copies of real files as a fraction of real files: `none` 0.0, `lived_in` 0.12, `neglected` 0.35. Kinds are `copy`, `misfiled`, `versioned`, `archived` (`src/worldloom/workspace.py:56`, `:66`).
- It invents nothing. Folders, titles, owners, and readers come from the manifest, roster, and access policies (`src/worldloom/workspace.py:25-29`).

### Connector and enterprise eval entities

| Entity | Key fields | Source |
| --- | --- | --- |
| `EnterpriseCorpus` | `queries` (`PlannedEnterpriseQuery`), `connector_data` (`ConnectorDataset`), `fixtures` | `src/worldloom/enterprise_corpus.py:45-48` |
| `QueryFixture` | `query_id`, `input_record_ids`, `destination_record_id`, `overrides`, `expected_side_effects`, `expected_fact_ids`, `expected_evidence_ids` | `src/worldloom/enterprise_corpus.py:35-43` |
| `StateOverride` | `kind`, `connector`, `record_id`, `details` | `src/worldloom/enterprise_corpus.py:28-32` |
| `ConnectorDefinition` | `connector`, `version`, `vendor_product`, `maturity`, `clock`, `id`, `payload_shape`, `query_language`, `acl`, `errors`, `faults`, `field_manifests`, `validation_rules` | `src/worldloom/connector_definition.py:323-350` |
| `ConnectorToolDefinition` | `op`, `entities`, `params`, `page_size`, `max_results`, `projection`, `idempotency` | `src/worldloom/connector_definition.py:220-230` |

Shipped connector definitions (`src/worldloom/_data/connectors/_order.json`): `jira`, `servicenow`, `salesforce`, `confluence`, `sharepoint`, `drive`, `outlook`, `email`, `onedrive`, `teams`, `slack`, `teamwork_graph`, `rovo`, `sor`.

| Connector | Product | Entities | Query language | Source |
| --- | --- | --- | --- | --- |
| `sharepoint` | SharePoint Online (Microsoft Graph) | `docx`, `xlsx`, `pptx`, `pdf`, `list_item`, `site_page`, `folder`, `csv` | `odata` | `_data/connectors/sharepoint.json:5`, `:44` |
| `onedrive` | OneDrive for Business (Microsoft Graph) | `docx`, `xlsx`, `pptx`, `pdf`, `file`, `folder` | `odata` | `_data/connectors/onedrive.json` |
| `drive` | Google Drive (Workspace) | `gdoc`, `gsheet`, `gslides`, `pdf`, `docx`, `xlsx`, `folder`, `pptx` | `drive_q` | `_data/connectors/drive.json` |
| `confluence` | Confluence Cloud | `page`, `blogpost`, `comment`, `attachment`, `space` | `cql` | `_data/connectors/confluence.json` |
| `jira` | Jira Cloud | `epic`, `story`, `bug`, `task`, `subtask`, `sprint`, `comment`, `attachment` | `jql` | `_data/connectors/jira.json` |

## Tool Definitions

There is no `tools.yaml` and no database tool file. Tool definitions are JSON connector definitions in `src/worldloom/_data/connectors/*.json`. Each tool has an operation (`op`), target entities, parameters, and paging limits (`src/worldloom/connector_definition.py:220-230`). The serving app marks a tool read only when `tool.op` is in `_READ_OPS = {"search", "get", "download"}` (`src/worldloom/connectors/serving.py:30`, `:1325`).

SharePoint tools, as an example. All 17 tools have `page_size` 200 and `max_results` 5000 (`src/worldloom/_data/connectors/sharepoint.json:223-540`).

| Tool | `op` | Entities | Read only |
| --- | --- | --- | --- |
| `search_files` | search | `docx`, `xlsx`, `pptx`, `pdf`, `csv`, `html`, `markdown` | Yes |
| `get_file` | get | same file types | Yes |
| `create_file` | create | same file types | No |
| `update_file` | update | same file types | No |
| `delete_file` | delete | same file types | No |
| `convert_file` | transform | `docx`, `pdf` | No |
| `get_list_items` | search | `list_item` | Yes |
| `create_list_item`, `update_list_item`, `delete_list_item` | create, update, delete | `list_item` | No |
| `search_pages` | search | `site_page` | Yes |
| `get_page` | get | `site_page` | Yes |
| `create_page`, `update_page` | create, update | `site_page` | No |
| `list_folder` | get | `folder` | Yes |
| `create_folder` | create | `folder` | No |
| `move_file` | move | file types plus `folder` | No |

The "Read only" column applies `_READ_OPS` to `op` (`src/worldloom/connectors/serving.py:30`).

The MCP tool lists are in the API Surface section.

## Open Questions

1. **Evaluation tool count.** Code registers 7 tools. `--check` reports 5. Docs say 6 (`src/worldloom/connectors/serving.py:1235-1259`, `src/worldloom/connector_serving_cli.py:83`, `docs/connector-serving.md:44-45`). The 100-tool ceiling counts these tools, so the real headroom is unclear.
2. **Connector count.** The README says "Twelve definitions" (`README.md:289-291`). `_data/connectors/` ships 14 connector files, including `email` and `sor` (`src/worldloom/_data/connectors/_order.json`).
3. **Exact connector tool names on the wire.** The docs show `servicenow.get_record` (`docs/connector-serving.md:21`). The agent did not read how `ConnectorEvaluationService.tools` builds its keys. <!-- TODO: Could not determine from available files -->
4. **Largest file size.** Resolved. `xlong` is 40 sections of 420 words, about 60 pages (`src/worldloom/sizing.py:45-50`). A doctype can set its own `SizeBudget` of up to 400 sections of 5,000 words (`src/worldloom/models.py:604-611`). These limits control words, not bytes.
5. **Studio routes coverage.** The route table comes from `StudioHandler.dispatch`, lines 154-342. The agent did not check for other handlers in `src/worldloom/studio/`.
6. **`gemini-enterprise cases` and `score`.** Resolved. `cases` writes one CSV for each evaluation shape with the columns `query`, `golden`, `case_id`, `evaluation_type`, `difficulty`, `expects_abstention`, at most 100 rows, plus `manifest.json` with one rubric for each shape (`src/worldloom/gemini_enterprise/cases.py:44-207`). `score` joins Eval Studio result CSVs to the cases on the query text and reports mean score, TTFA, and TTLT by shape and difficulty (`src/worldloom/gemini_enterprise/results.py:97-175`).
7. **Release status.** Nothing is on PyPI and no tag exists (`README.md:86-88`). A consumer must pin a commit. This document uses commit `3fcf194`.
