# Implementation Plan: WorldLoom Blueprint and Pack Ingestion (`worldloom_blueprint_ingest_20261004`)

## Phase 1: WorldLoom Context Extraction and Grounded Builder (`build.py` and `cli.py`) [checkpoint: bfde924]

- [x] Task: Write unit tests for WorldLoom pack and SDK domain ingestion (Red Phase) 490ef13
  - [x] Create `tests/test_worldloom_ingest.py` testing `build_corpus` and CLI `bigloom build` with `world_pack="retail-close"` and `domain="banking"`
  - [x] Verify that inspected document units contain the WorldLoom company name, business units, and cost centres, and pass `qualify_corpus`
- [x] Task: Implement WorldLoom ingestion in `src/bigloom/build.py` and `src/bigloom/cli.py` (Green Phase) bfde924
  - [x] Add `_resolve_world_context` to `src/bigloom/build.py` using `World.load` and `worldloom.sdk.company`
  - [x] Update `build_corpus` and `bigloom build` CLI options (`--world-pack`, `--domain`) and `README.md`
  - [x] Run full `pytest` suite and `ruff check .` with at least 90% coverage
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) bfde924
