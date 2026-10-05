# Implementation Plan: Large-File Production on WorldLoom (`proposal_generator_20261006`)

Revised 6 Oct 2026 SGT to follow the WorldLoom-based spec.

## Phase 0: WorldLoom Integration Spike
- [ ] Task: Answer the three open questions in the design note, with a short script and no product code
  - [ ] Find a `LongDocument` family that fits a funding proposal, or record that BigLoom must add a genre
  - [ ] Run the narrative claim check on one section of 1,000 or more words with the composed provider
  - [ ] Find how `render/docx.py` places figures, and choose: add figures after the render, or through a hook
  - [ ] Find which facts in the GovTech world have revision predecessors
- [ ] Task: Record the answers in `spec.md` (section 2) and adjust Phases 1 to 3 if needed
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 1: Spec File, World, and Fact Selection
- [ ] Task: Add PyYAML to `tech-stack.md` and `pyproject.toml`, with a dated note
- [ ] Task: Write unit tests for the spec model and fact selection (Red Phase)
  - [ ] Create `tests/test_proposal_spec.py` for a valid spec, a missing field, a bad position, a bad modality, and both `pack` and `domain` set
  - [ ] Create `tests/test_proposal_facts.py`: selected facts exist in the `FactLedger`, are unique, and have predecessors or recorded substitutes
- [ ] Task: Implement `src/bigloom/proposal/spec.py` and `src/bigloom/proposal/facts.py` (Green Phase)
  - [ ] Pydantic models `ProposalSpec`, `EvidencePosition`, `ProseConfig`
  - [ ] World loading through `World.load` and `sdk.company`, using the existing `_resolve_world_context` logic where it fits
  - [ ] Add `specs/gsw_proposal.yaml`
  - [ ] Run `pytest` and confirm that the tests pass
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: Structure, Prose Provider, and Render
- [ ] Task: Write unit tests for the structure, the Gemini adapter, and the render (Red Phase)
  - [ ] Create `tests/test_proposal_prose.py` with the WorldLoom deterministic provider and a fake Gemini client
  - [ ] Test that the cache prevents a second model call, that HTTP 401 and 403 stop with no retry, and that other errors retry
  - [ ] Test that the rendered `.docx` holds every evidence fact from `{{fact:ID}}` references, spelled by WorldLoom
- [ ] Task: Implement `src/bigloom/proposal/structure.py`, `gemini_provider.py`, and `render.py` (Green Phase)
  - [ ] Build the `LongDocument` plan, or the BigLoom genre from Phase 0
  - [ ] `VertexGeminiProvider` behind the `ExecProvider` contract, with a cache keyed on the request digest
  - [ ] Render with `worldloom.render.docx`
  - [ ] Run `pytest` and confirm that the tests pass
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: Weight Layer, Evidence Positions, Trap Twin, Checks, and CLI
- [ ] Task: Write unit tests (Red Phase)
  - [ ] Create `tests/test_proposal_weight.py`: size window for each target, the same `word/document.xml` for two sizes, no `shape-ballast.bin` part
  - [ ] Create `tests/test_proposal_evidence.py`: locators resolve, end text facts come after the last image, image values are absent from the text
  - [ ] Create `tests/test_proposal_trap.py`: trap values are predecessor facts or recorded substitutes, and no trap value is in the target file
  - [ ] Test `bigloom proposal` through the Typer test runner with small sizes
- [ ] Task: Implement `src/bigloom/proposal/weight.py`, `evidence.py`, `trap.py`, `verify.py`, and update `src/bigloom/cli.py` (Green Phase)
  - [ ] Figure drawers that take entities from the world, plus the grain encoder and the size loop
  - [ ] Evidence placement by position and modality, recorded as `EvidenceRef` with `DocxLocator`
  - [ ] Trap twin writer
  - [ ] Checks with `native_artifacts.inspect_artifact`, the ZIP check, and the locator check
  - [ ] `manifest.jsonl` with SHA-256, `evals.jsonl`, and `evals.csv`
  - [ ] Document `bigloom proposal` in `README.md`
  - [ ] Run the full `pytest` suite and `ruff check .` with at least 80 percent coverage for new code
- [ ] Task: End-to-end run
  - [ ] Build the GSW spec at 200 MiB with the Gemini provider
  - [ ] Build 500 MiB from the same cache with no model calls, and record time and peak memory
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
