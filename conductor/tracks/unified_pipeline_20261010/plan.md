# Implementation Plan: Unified Multi-Format Large-File Pipeline (`bigloom build` and `bigloom init`)

## Phase 1: Unified Pipeline Implementation and Verification
- [x] Task 1: Update `tests/test_wizard.py` and `tests/test_pipeline.py` to test the unified `bigloom init` and `bigloom build` flow with `--sizes-mb` and `--formats` (including 1 GiB budget splitting and `evals.csv` output).
- [x] Task 2: Update `src/bigloom/build.py` to scale image plate chunks up to `1024 MiB` (`1 GiB`), ground golden/canary facts in the WorldLoom `FactLedger`, and write `evals.csv` alongside `manifest.jsonl`.
- [x] Task 3: Unify `src/bigloom/wizard.py` and `src/bigloom/cli.py` so `bigloom init` and `bigloom build` use one unified flow with `--sizes-mb` and `--formats`.
- [x] Task 4: Update `README.md` to document the single unified pipeline.
- [x] Task 5: Run `pytest --cov=src/bigloom`, `ruff check .`, `validate_mermaid.py README.md`, and `check_git_hygiene.py .`.
