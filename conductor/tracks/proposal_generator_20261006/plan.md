# Implementation Plan: Reusable Proposal Generator (`proposal_generator_20261006`)

## Phase 1: Topic File, Organisation Pack, and Tech Stack
- [ ] Task: Add PyYAML to `tech-stack.md` and `pyproject.toml`
  - [ ] Add a dated note in `tech-stack.md` that explains why the topic file uses YAML
- [ ] Task: Write unit tests for topic and pack loading (Red Phase)
  - [ ] Create `tests/test_proposal_topic.py` for a valid `topics/gsw.yaml`, a missing field, a bad fact position, and an unknown middle chapter
  - [ ] Test that the organisation pack loader reads the agency name, the marking, and the name lists from `govtech-pack.json`-style input
- [ ] Task: Implement `src/bigloom/proposal_topic.py` and `topics/gsw.yaml` (Green Phase)
  - [ ] Pydantic models `ProposalTopic`, `FactTemplate`, `PlateWords`, and `OrgPack`
  - [ ] Move the GSW title, context, chapters, facts, and plate words from `make_gsw_proposal.py` into `topics/gsw.yaml`
  - [ ] Run `pytest` and confirm that the topic tests pass
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: Prose Step with Cache
- [ ] Task: Write unit tests for the prose step (Red Phase)
  - [ ] Create `tests/test_proposal_prose.py` with a fake Gemini client
  - [ ] Test that the first run writes the outline and sections to the cache, and that a second run makes no calls
  - [ ] Test that HTTP 401 and 403 stop the run with no retry, and that other errors retry
  - [ ] Test that `--skip-prose` with a missing cache file gives a clear error
- [ ] Task: Implement `src/bigloom/proposal_prose.py` (Green Phase)
  - [ ] `VertexGemini` client: REST call, gcloud token with optional account, token refresh, backoff
  - [ ] `write_prose` and `load_prose` with a cache for each topic
  - [ ] Run `pytest` and confirm that the prose tests pass
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: Build Step, Trap File, Outputs, and CLI
- [ ] Task: Write unit tests for the build step and the CLI (Red Phase)
  - [ ] Create `tests/test_proposal_build.py` with a small cached prose set and a 3 MB target
  - [ ] Test the size window (target to target plus 3 percent), the ZIP check, and repeatable output from the same seed
  - [ ] Test that the `end` facts come after the last image in `word/document.xml`
  - [ ] Test that every eval answer is in the target file and that no trap answer is in the target file
  - [ ] Test `bigloom proposal` through the Typer test runner
- [ ] Task: Implement `src/bigloom/proposal_build.py` and update `src/bigloom/cli.py` (Green Phase)
  - [ ] Plate drawers that read words from the topic file, plus the grain encoder
  - [ ] `.docx` writer, trap writer, `manifest.jsonl`, `evals.jsonl`, and `evals.csv`
  - [ ] Add `bigloom proposal` to `src/bigloom/cli.py` and document it in `README.md`
  - [ ] Run the full `pytest` suite and `ruff check .` with at least 80 percent coverage for new code
- [ ] Task: Compare with the one-off script
  - [ ] Build the GSW file from the existing prose cache with `--skip-prose`, at 200 MiB
  - [ ] Confirm the size window, the word count, and the fact positions
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
