# Implementation Plan: Core BigLoom Pipeline (`core_pipeline_20261002`)

## Phase 1: Environment, Data Models, and Qualification Gate (`qualify.py`) [checkpoint: b0cfca1]

- [x] Task: Set up the virtual environment and test dependencies 65c1305
  - [x] Install `worldloom` (`synthetic-foundry`) and `bigloom[dev]` with `pytest-cov` in `.venv`
  - [x] Add `ManifestEntry` model to `src/bigloom/models.py` for `manifest.jsonl` serialization
- [x] Task: Write unit tests for `models.py` and `qualify.py` (Red Phase) 82e6a73
  - [x] Create `tests/test_qualify.py` to test all nine `ViolationCode` rules on `.docx`, `.xlsx`, `.pptx`, and `.pdf` bytes
  - [x] Include word-boundary collision tests so short substrings inside longer numbers do not match falsely
- [x] Task: Update `qualify.py` to pass all qualification tests (Green Phase) b0cfca1
  - [x] Add word-boundary matching to `_unit_matches` in `src/bigloom/qualify.py`
  - [x] Run `pytest` and confirm all qualification tests pass
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) b0cfca1

## Phase 2: Leakage Grader (`grade.py`) [checkpoint: c0d44b3]

- [x] Task: Write unit tests for `grade.py` (Red Phase) 3e8fffb
  - [x] Create `tests/test_grade.py` covering `CORRECT_WITH_DOWNLOAD`, `SNIPPET_ONLY_LEAK`, `CROSS_FILE_LEAK_CANARY`, `CROSS_FILE_LEAK_CITATION`, and `WRONG_ANSWER`
  - [x] Add negative tests where `golden_value` or `canary_value` appears only as a partial substring of another number
- [x] Task: Update `grade.py` with word-boundary matching and pass all grading tests (Green Phase) c0d44b3
  - [x] Use regex word-boundary checks for `golden_value` and `canary_value` in `src/bigloom/grade.py`
  - [x] Run `pytest` and confirm all grading tests pass
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) c0d44b3

## Phase 3: Large-File Builder (`build.py`), Query Generator (`queries.py`), and CLI (`cli.py`)

- [~] Task: Write unit tests for `build.py`, `queries.py`, and `cli.py` (Red Phase)
  - [ ] Create `tests/test_pipeline.py` testing `bigloom build`, `bigloom queries`, `bigloom qualify`, and `bigloom grade` end to end
  - [ ] Verify determinism from `--seed`, custom byte tiers (`--sizes-mb`), paired `< 1 MB` trap files, and two high-entropy questions per large file
- [ ] Task: Implement `src/bigloom/build.py` (Green Phase)
  - [ ] Support both `--corpus-dir` (WorldLoom corpus) and standalone `--seed` synthesis
  - [ ] Render `.docx`, `.xlsx`, `.pptx`, and `.pdf` files with deep text facts (`unit >= 5`), noisy Pillow chart images, and `< 1 MB` canary trap files
  - [ ] Write `manifest.jsonl` with byte sizes, SHA-256 hashes, planted facts, and distractor paths
- [ ] Task: Implement `src/bigloom/queries.py` and update `src/bigloom/cli.py` (Green Phase)
  - [ ] Generate two high-entropy `EvalCase` items (one `text`, one `image`) per large file from `manifest.jsonl` and write `cases.json`
  - [ ] Add `bigloom build` and `bigloom queries` commands to `src/bigloom/cli.py` and update `README.md`
  - [ ] Run full `pytest` suite and verify at least 80% code coverage
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
