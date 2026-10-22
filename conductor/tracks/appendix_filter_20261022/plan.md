# Plan: Appendix and ID Filter

Track ID: `appendix_filter_20261022`. Spec: `spec.md` in this folder.

## Phase 1: Appendix and Caption Filter [checkpoint: 7f99def]

- [x] Task: Check the depth rule first.
    - [x] Confirm that `evidence.evidence_position` reads IR sections only, and that no depth rule reads `LongDocument` appendices. Result: confirmed. The text fact sits in a body section, and the removed appendices come after the body, so depth cannot fall.
- [x] Task: Write failing tests (`tests/test_appendix_filter.py`).
    - [x] Unit: the filter removes the 4 appendices from a `LongDocument` and keeps the other appendices in letter order.
    - [x] Unit: the filter removes " (ART-####)" from block source captions and from the "Schedules incorporated" note.
    - [x] Unit: the "Related documents" rows use the document title as the label.
    - [x] Unit: a test fails when one of the 4 appendix headings is not in the WorldLoom `longform.py` source.
    - [x] Unit: the wrap restores `worldloom.longform.document` after the render pass, also after an error.
- [x] Task: Implement `src/bigloom/formats/longform_filter.py` with `dataclasses.replace`, and the wrap in `build._render_pass`.
- [x] Task: Phase Verification and Checkpoint (refer to `workflow.md`).

## Phase 2: Readable Reference and Deck [checkpoint: 7f99def]

- [x] Task: Write failing tests.
    - [x] Unit: the readable reference uses company initials, domain, year, and document number, and holds no WorldLoom ID.
    - [x] Unit: the deck "related" lines hold no WorldLoom ID.
    - [x] Integration (1 MB build, four formats): each target and trap holds 0 WorldLoom ID strings. The ID set comes from the world: fact, event, artifact, company, unit, service, system, category, and lore IDs.
    - [x] Integration: none of the 4 appendix headings appears in any target or trap.
- [x] Task: Implement the readable reference and the deck change.
- [x] Task: Extra ID sources found by the integration test, all fixed in the same module: the `Fact` column of figure tables, ID-only table columns and ID cells (all formats, through `scrub_ir`), review comments with bare IDs (now plain words), revision summaries, file properties (`WorldloomFacts`, `WorldloomProvenance`, metadata with IDs), and the hidden workbook sheet "Lineage". The readable reference uses slashes (`GTA/FIN/2026/024`), because a dash form matched the WorldLoom ID pattern.
- [x] Task: Phase Verification and Checkpoint (refer to `workflow.md`).

## Phase 3: CLI Help and Final Checks [checkpoint: 7f99def]

- [x] Task: Write a failing test: `bigloom build --help` and `bigloom init --help` list `template` and `handshake`.
- [x] Task: Fix the help text in `cli.py`.
- [x] Task: Build the 1 MB sets in all four formats for retail and GovTech. Run the gate. Text fact depth must be unit 6 or deeper. Result: both sets pass. Smallest depth: unit 35 (GovTech deck).
- [x] Task: Run the full suite, `ruff check .`, and the Git hygiene check.
- [x] Task: Upload the 1 MB GovTech set to SharePoint `building-bigloom/appendix-filter` for review. (10 of 10 files.)
- [x] Task: Phase Verification and Checkpoint (refer to `workflow.md`).
