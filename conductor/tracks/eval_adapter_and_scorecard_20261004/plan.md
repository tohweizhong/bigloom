# Implementation Plan: Vendor-Neutral Run Adapter and Size-Tier Scorecard (`eval_adapter_and_scorecard_20261004`)

## Phase 1: Vendor-Neutral Run Adapter (`adapters.py`)

- [ ] Task: Write unit tests for `adapters.py` (Red Phase)
  - [ ] Create `tests/test_adapters.py` testing conversion of generic JSON/JSONL logs, OpenAI/MCP-style message traces, directory inputs, and CSV tables into `EvalResponse` records
  - [ ] Test automatic query-to-`case_id` matching using `--cases`
- [ ] Task: Implement `src/bigloom/adapters.py` (Green Phase)
  - [ ] Implement `import_run_responses` supporting JSON, JSONL, agent trace objects, CSV files, and directory inputs
  - [ ] Run `pytest tests/test_adapters.py` and confirm all adapter tests pass
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: Size-Tier and Modality Scorecard (`report.py`) and CLI (`cli.py`)

- [ ] Task: Write unit tests for `report.py` and new CLI commands (Red Phase)
  - [ ] Create `tests/test_report.py` testing Markdown scorecard tables (overall, size tier, format, modality, and failure details) and CLI `import-run` and `report` commands
- [ ] Task: Implement `src/bigloom/report.py` and update `src/bigloom/cli.py` (Green Phase)
  - [ ] Implement `render_scorecard_markdown` in `src/bigloom/report.py`
  - [ ] Add `bigloom import-run` and `bigloom report` to `src/bigloom/cli.py` and document them in `README.md`
  - [ ] Run full `pytest` suite and `ruff check .` with at least 85% coverage
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
