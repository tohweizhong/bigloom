# Implementation Plan: WorldLoom Blueprint and Pack Ingestion (`worldloom_blueprint_ingest_20261004`)

## Phase 1: WorldLoom Context Extraction and Grounded Builder (`build.py` and `cli.py`)

- [~] Task: Write unit tests for WorldLoom pack and SDK domain ingestion (Red Phase)
  - [ ] Create `tests/test_worldloom_ingest.py` testing `build_corpus` and CLI `bigloom build` with `world_pack="retail-close"` and `domain="banking"`
  - [ ] Verify that inspected document units contain the WorldLoom company name, business units, and cost centres, and pass `qualify_corpus`
- [ ] Task: Implement WorldLoom ingestion in `src/bigloom/build.py` and `src/bigloom/cli.py` (Green Phase)
  - [ ] Add `_extract_world_context` to `src/bigloom/build.py` using `World.load` and `worldloom.sdk.company`
  - [ ] Update `build_corpus` and `bigloom build` CLI options (`--world-pack`, `--domain`) and `README.md`
  - [ ] Run full `pytest` suite and `ruff check .` with at least 90% coverage
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
