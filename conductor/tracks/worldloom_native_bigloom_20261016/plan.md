# Implementation Plan: WorldLoom-Native BigLoom

- **Track ID:** `worldloom_native_bigloom_20261016`
- **Spec:** `spec.md` (approved 16 Oct 2026 14:01 SGT)
- **Method:** Each task follows `workflow.md`: write failing tests, implement, refactor, check coverage, commit, attach a Git note. Each phase ends with a verification checkpoint.

## Phase 0: Test Phase

No production code changes in this phase. Test scripts go in the track folder under `phase0/`.

- [x] Task: Build one small WorldLoom corpus at commit `3fcf194` with `--realism enterprise --distractors 4` and the `ComposedProvider` narration.
- [x] Task: T1. Add a table section to a copy of one IR and render it with the enterprise DOCX, PDF, and PPTX renderers.
    - [x] Confirm that each file opens and that the section appears at unit 6 or deeper.
- [x] Task: T2. List the target document types that have a superseded draft, and the types that do not.
    - [x] Propose one fallback trap for each type without a draft.
- [x] Task: T3. Write one natural question for each of 4 targets and run BM25 and TF-IDF over targets and traps.
    - [x] Confirm that each target and its trap rank in positions 1 to 3.
- [x] Task: T4. Add a picture to a rendered DOCX, PPTX, and PDF.
    - [x] Confirm that each file opens, the layout does not change, and the image value is not in the text.
- [x] Task: T5. Run `prose_quality` on the template prose and build the corpus two times.
    - [x] Confirm the thresholds and that both builds give the same text.
- [x] Task: Write `phase0_findings.md` with the result of T1 to T5 and the changes they cause to Phases 1 to 8.
- [x] Task: Phase Verification and Checkpoint (refer to `workflow.md`). **Stop for your decision if any test fails.**

## Phase 1: Corpus as Input (FR1) [checkpoint: e22f989]

- [x] Task: Update `tech-stack.md`. Record the WorldLoom pin `3fcf194`, the enterprise renderers, and `ComposedProvider`.
- [x] Task: Write failing tests for `bigloom build --corpus-dir <dir>` (the existing flag now reads a WorldLoom corpus with `world.json`).
    - [x] Loads a corpus with `World.load`.
    - [x] With no corpus, builds one into `<out>/corpus/`.
    - [x] With incomplete narration, fills the open sections and records `narration: partial`.
    - [x] With no WorldLoom package, stops with the install command.
    - [x] The manifest records the commit, seed, recipe digest, model ID, and prompt version.
- [x] Task: Implement the corpus loader and the new manifest fields.
- [x] Task: Remove `default_world()` from `prose_writer.py`. (`_extract_world_pools` moves to Phase 4, because the old renderers still read its pools.)
- [x] Task: Change the wizard so that it writes a pack or company specification and runs `worldloom build`.
- [x] Task: Phase Verification and Checkpoint (refer to `workflow.md`). (coverage 96 percent, corpus.py 87 percent, ruff clean)

## Phase 2: Company Pack with Document Types (FR2) [checkpoint: 545683b]

- [x] Task: Write failing tests.
    - [x] `worldloom pack check` and `pack lint` pass on the GovTech pack.
    - [x] A GovTech build makes at least 16 distinct document types.
    - [x] No GovTech term appears in a `retail` build.
- [x] Task: Write the GovTech company pack: company, units, name pools, system brands, voices, lore.
- [x] Task: Add at least 16 `artifact_types` to the pack, based on the catalogue in `make_large_files.py` and `make_100mb_files.py`.
- [x] Task: Add `episode_text` and `evaluation_text` to the pack.
- [x] Task: Run the Phase 0 T5 check again with one period and the new document types. `repeated_sentence_rate` must be 0.2 or less. Result: 0.027 mean and all pack types under 0.2 in each document; 0.44 across the corpus (template writer limit, see phase0_findings.md).
- [x] Task: Phase Verification and Checkpoint (refer to `workflow.md`).

## Phase 3: Template Writer Flag (FR3) [checkpoint: e0fd6d3]

- [x] Task: Write failing tests.
    - [x] `--writer template` is the default and narrates every section with `ComposedProvider`.
    - [x] The manifest records `narration: composed` and the provider ID.
    - [x] An unknown `--writer` value stops the run with the list of values that work.
    - [x] Two builds give the same text.
- [x] Task: Implement the `--writer` flag on `bigloom build` and the wizard, with `enterprise/v2` as the realism profile.
- [x] Task: Remove the `Writer` class and its 4 sentence templates from `prose_writer.py`. (Moved to Phase 4, because the old renderers call `Writer` until Phase 4 replaces them.)
- [x] Task: Phase Verification and Checkpoint (refer to `workflow.md`).

## Phase 4: Render through WorldLoom, then Add Test Evidence (FR4)

- [ ] Task: Write failing tests.
    - [ ] Each target has a cover, contents, numbered sections, and native charts.
    - [ ] The text fact sits at unit 6 or deeper.
    - [ ] The image fact is in a picture and not in the text.
    - [ ] The trap is the superseded draft of the same document, or the Phase 0 fallback, and holds the canary.
    - [ ] Each file reaches its target size.
    - [ ] Two documents in one world have different `style_seed` values.
- [ ] Task: Implement the text fact section in a copy of the IR.
- [ ] Task: Implement rendering through the enterprise DOCX, PDF, and PPTX renderers, and `render/xlsx.py` with detail tables.
- [ ] Task: Implement picture insertion for DOCX, PPTX, and PDF.
- [ ] Task: Implement the trap by the Phase 0 trap rule: a second render pass with the canary value (`v0.1` revision for Word, the unpadded main file for other formats).
- [ ] Task: Implement the PPTX evidence slide after rendering.
- [ ] Task: Implement the PPTX layout fix after rendering: give a valid size to every layout and slide placeholder with no height or with a width greater than the slide (Phase 0 T6).
- [ ] Task: Keep only the main file of each target. Do not upload revision files.
- [ ] Task: Implement byte padding: media or an unreferenced ZIP member for OOXML, an embedded file stream for PDF.
- [ ] Task: Remove `_render_docx`, `_render_pdf`, `_render_pptx`, `_render_xlsx`, and the unused parts of `charts.py`.
- [ ] Task: Remove `_extract_world_pools` and the pool code that only the old renderers use (moved from Phase 1).
- [ ] Task: Remove the `Writer` class and its 4 sentence templates (moved from Phase 3).
- [ ] Task: Phase Verification and Checkpoint (refer to `workflow.md`).

## Phase 5: Qualification v2 (FR5)

- [ ] Task: Write failing tests.
    - [ ] The new top 3 code fires when the target or the trap ranks below position 3.
    - [ ] Fact depth comes from renderer locators.
    - [ ] Each realism check fires on a file with that defect: repeated sentences, template openers, header repeats, cut words, pages with fewer than 40 words.
    - [ ] The second reader reads a PDF and a file above 512 MiB.
- [ ] Task: Replace `TARGET_NOT_RANKED_FIRST` with the top 3 code in `qualify.py` and `models.py`.
- [ ] Task: Implement locator-based depth and the realism checks.
- [ ] Task: Implement the second reader.
- [ ] Task: Rewrite the clean fixture in `tests/test_qualify.py` so that it does not repeat the topic in every paragraph.
- [ ] Task: Phase Verification and Checkpoint (refer to `workflow.md`).

## Phase 6: Natural Questions (FR6)

- [ ] Task: Write failing tests.
    - [ ] The subject comes from the document title and type.
    - [ ] The metric label comes from the fact kind.
    - [ ] The wording comes from the pack `evaluation_text`.
    - [ ] No two questions in one set share a fixed label.
- [ ] Task: Rewrite `queries.py`. Remove "Authorized Capital Reserve", "Q4 Peak Thermal Efficiency", and "Final Audit Report".
- [ ] Task: Phase Verification and Checkpoint (refer to `workflow.md`).

## Phase 7: Fold in `bigloom proposal` (FR7)

- [ ] Task: Add the Git tag `proposal-v1` at the last commit with the old proposal code and push it to `origin`. Confirm the tag on GitHub.
- [ ] Task: Write failing tests.
    - [ ] A funding proposal builds through the same pack, writer, renderers, evidence steps, and gate.
    - [ ] `src/bigloom/proposal/` holds no fixed chapters, name lists, plates, or paragraph templates.
    - [ ] A proposal can reach 1 GiB through padding.
- [ ] Task: Add a funding proposal document type with a large `SizeBudget` to the GovTech pack.
- [ ] Task: Replace the `proposal/` build path with the shared path. Keep the `bigloom proposal` command as an entry point.
- [ ] Task: Remove the fixed content from `proposal/facts.py`, `spec.py`, `prose.py`, `plates.py`, and `builder.py`.
- [ ] Task: Phase Verification and Checkpoint (refer to `workflow.md`).

## Phase 8: Audit and Final Review (FR8)

- [ ] Task: Write the static test: no module-level list or tuple of content strings in `src/bigloom/`, with an allow-list for test design constants.
- [ ] Task: Remove any content that the static test finds.
- [ ] Task: Build the 1 MB and 18 MB sets in all four formats for the `retail` and GovTech packs. Run `bigloom qualify`.
- [ ] Task: Run the full test suite with coverage, `ruff check .`, and the Git hygiene check.
- [ ] Task: Upload the 1 MB set to SharePoint `BigLoom-Eval` and share the links for your review.
- [ ] Task: Phase Verification and Checkpoint (refer to `workflow.md`).
