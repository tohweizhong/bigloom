# Plan: Appendix and ID Filter

Track ID: `appendix_filter_20261022`. Spec: `spec.md` in this folder.

## Phase 1: Appendix and Caption Filter

- [ ] Task: Check the depth rule first.
    - [ ] Confirm that `evidence.evidence_position` reads IR sections only, and that no depth rule reads `LongDocument` appendices. Record the result in this plan.
- [ ] Task: Write failing tests (`tests/test_appendix_filter.py`).
    - [ ] Unit: the filter removes the 4 appendices from a `LongDocument` and keeps the other appendices in letter order.
    - [ ] Unit: the filter removes " (ART-####)" from block source captions and from the "Schedules incorporated" note.
    - [ ] Unit: the "Related documents" rows use the document title as the label.
    - [ ] Unit: a test fails when one of the 4 appendix headings is not in the WorldLoom `longform.py` source.
    - [ ] Unit: the wrap restores `worldloom.longform.document` after the render pass, also after an error.
- [ ] Task: Implement `src/bigloom/formats/longform_filter.py` with `dataclasses.replace`, and the wrap in `build._render_pass`.
- [ ] Task: Phase Verification and Checkpoint (refer to `workflow.md`).

## Phase 2: Readable Reference and Deck

- [ ] Task: Write failing tests.
    - [ ] Unit: the readable reference uses company initials, domain, year, and document number, and holds no WorldLoom ID.
    - [ ] Unit: the deck "related" lines hold no WorldLoom ID.
    - [ ] Integration (1 MB build, four formats): each target and trap holds 0 WorldLoom ID strings. The ID set comes from the world: fact, event, artifact, company, unit, service, system, category, and lore IDs.
    - [ ] Integration: none of the 4 appendix headings appears in any target or trap.
- [ ] Task: Implement the readable reference and the deck change.
- [ ] Task: Phase Verification and Checkpoint (refer to `workflow.md`).

## Phase 3: CLI Help and Final Checks

- [ ] Task: Write a failing test: `bigloom build --help` and `bigloom init --help` list `template` and `handshake`.
- [ ] Task: Fix the help text in `cli.py`.
- [ ] Task: Build the 1 MB sets in all four formats for retail and GovTech. Run the gate. Text fact depth must be unit 6 or deeper.
- [ ] Task: Run the full suite, `ruff check .`, and the Git hygiene check.
- [ ] Task: Upload the 1 MB GovTech set to SharePoint `building-bigloom/appendix-filter` for review.
- [ ] Task: Phase Verification and Checkpoint (refer to `workflow.md`).
