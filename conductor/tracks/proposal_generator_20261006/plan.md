# Implementation Plan: Large-File Production on WorldLoom (`proposal_generator_20261006`)

Revised 6 Oct 2026 SGT to use only the three required WorldLoom outputs (`World` entities, `world.facts` canonical and draft facts, and `native_artifacts.inspect_artifact`).

## Phase 1: Spec File, World Entities, and Fact Selection [checkpoint: c0bfd61]
- [x] Task: Add `PyYAML` to `conductor/tech-stack.md` and `pyproject.toml` 37b92ed
- [x] Task: Write unit tests for `ProposalSpec` and WorldLoom fact selection (Red Phase) c0bfd61
  - [x] Create `tests/test_proposal_spec.py` testing valid YAML specs (`gsw`, `tuas`, `pdd`), missing fields, invalid positions/modalities, and mutually exclusive `world_pack` vs `domain`
  - [x] Create `tests/test_proposal_facts.py` testing `World` loading, `FactLedger` fact selection, predecessor/comparator trap pairing, and start/middle/end text and image fact generation
- [x] Task: Implement `src/bigloom/proposal/spec.py`, `src/bigloom/proposal/facts.py`, and `specs/*.yaml` (Green Phase) c0bfd61
  - [x] Implement Pydantic models (`ProposalSpec`, `EvidencePosition`, `ProseConfig`) in `src/bigloom/proposal/spec.py`
  - [x] Implement WorldLoom entity and `FactLedger` loader in `src/bigloom/proposal/facts.py`
  - [x] Add `specs/gsw_proposal.yaml` (200 MiB), `specs/tuas_proposal.yaml` (500 MiB), and `specs/pdd_proposal.yaml` (1024 MiB)
  - [x] Run `pytest` and confirm that all Phase 1 tests pass
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md) c0bfd61

## Phase 2: Cached Prose Generator and Grained Plate Weight Layer
- [x] Task: Write unit tests for prose generation, caching, and grained plate encoding (Red Phase) 1a50f6b
  - [x] Create `tests/test_proposal_prose.py` testing `deterministic` prose generation, fake `VertexGeminiClient` caching (second run makes zero calls), HTTP 401/403 immediate stop, and transient error retry
  - [x] Create `tests/test_proposal_plates.py` testing the six plate drawers (`zone`, `gantt`, `budget`, `render`, `section`, `sensors`), trap plate reproduction from saved RNG state, and batched JPEG grain scaling
- [~] Task: Implement `src/bigloom/proposal/prose.py` and `src/bigloom/proposal/plates.py` (Green Phase)
  - [ ] Implement `VertexGeminiClient`, `write_prose`, `load_prose`, and deterministic offline prose generator in `src/bigloom/proposal/prose.py`
  - [ ] Implement the six grained plate drawers and batched `encode_all` loop in `src/bigloom/proposal/plates.py`
  - [ ] Run `pytest` and confirm that all Phase 2 tests pass
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: DOCX Assembly, Byte Verification (`inspect_artifact`), and CLI (`bigloom proposal`)
- [ ] Task: Write unit tests for `.docx` assembly, multi-size XML identity, verification checks, and CLI (Red Phase)
  - [ ] Create `tests/test_proposal_build.py` testing multi-size builds (`sizes_mb`), identical `word/document.xml` across sizes, absence of `shape-ballast.bin`, `end` text facts placed after the last image, image facts absent from text, trap twin isolation, leak-term detection, and `bigloom proposal` CLI execution
- [ ] Task: Implement `src/bigloom/proposal/builder.py`, `src/bigloom/proposal/verify.py`, and `bigloom proposal` CLI command (Green Phase)
  - [ ] Implement `.docx` writer, `< 1 MB` trap twin writer, `manifest.jsonl` (with SHA-256), `evals.jsonl` (with `DocxLocator`), and `evals.csv` in `src/bigloom/proposal/builder.py`
  - [ ] Implement `verify_proposal_outputs` using `zipfile.ZipFile.testzip()`, `worldloom.native_artifacts.inspect_artifact`, and `find_leaks` in `src/bigloom/proposal/verify.py`
  - [ ] Wire `bigloom proposal` in `src/bigloom/cli.py` and document it in `README.md`
  - [ ] Run `pytest` and `ruff check .` and confirm >= 80% coverage
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
