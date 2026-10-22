# Spec: Appendix and ID Filter (Bug fix)

Track ID: `appendix_filter_20261022`. Source: realism RSI handoff, section 6, items 1 to 4 (`~/.gemini/jetski/brain/962bad5e-098a-42ae-a058-de8668e68825/bigloom_realism_rsi_handoff.md`).

## Overview

Round 0 of the realism loop found 21.15 WorldLoom IDs per 1000 words in BigLoom output. Real files have 0. The blind judges used these IDs as a clue. The IDs come from WorldLoom `longform.document()` at pin `53bb44a`. BigLoom fixes them itself while it renders. WorldLoom does not change (user decision, option A).

## ID sources (verified in `longform.py` at `53bb44a`)

| # | Visible text | Location | Action |
|---|---|---|---|
| 1 | Appendix "Sources of figures" | line 1039 | Remove |
| 2 | Appendix "Data lineage" | line 1060 | Remove |
| 3 | Appendix "Measures and sources" | line 1076 | Remove |
| 4 | Appendix "Chronology of events" | line 1090 | Remove |
| 5 | Source captions "<title> (ART-####), sheet <name>" | lines 964, 969, 1002 | Remove " (ART-####)" |
| 6 | Note "Schedules incorporated from <title> (ART-####), ..." | line 974 | Remove " (ART-####)" |
| 7 | Appendix "Related documents": row labels are artifact IDs | line 1119 | Keep the appendix. Use the document title as the row label. |
| 8 | Deck "related" lines "<title> (ART-####)" | `render/enterprise/pptx.py` line 335 | Remove the IDs from the deck |
| 9 | Document reference "CO-0001-FINANCE-ART-0024" on the cover, control table, and running heads | line 1157 | Replace with a readable reference, for example "GTA-FIN-2026-024" |

## Functional requirements

1. FR1. While BigLoom renders (`build._render_pass`), BigLoom wraps `worldloom.longform.document` and changes the returned `LongDocument` with `dataclasses.replace`. The wrap ends after the render pass.
2. FR2. The filter applies to target files and trap files, in all four formats.
3. FR3. The filter makes the changes in the table above. Appendix letters stay in sequence (A, B, C) after removal.
4. FR4. The readable reference uses the company initials, the domain, the year, and the document number. It holds no WorldLoom ID string.
5. FR5. The filter fails loudly when WorldLoom renames one of the 4 appendix headings: BigLoom checks that each removed heading exists in the WorldLoom source, and a test fails when one is missing.
6. FR6. `bigloom build --help` and `bigloom init --help` list the writers that work: `template` and `handshake`.

## Non-functional requirements

- No change to the WorldLoom repository.
- The removed appendices make files smaller. Padding covers the size (user decision).
- The text fact and the image fact keep their depth rules. Check first: `evidence.evidence_position` reads IR sections, not `LongDocument` appendices.

## Acceptance criteria

1. A rendered target and trap in each format hold 0 WorldLoom ID strings. The test takes the ID set from the world itself: fact, event, artifact, company, unit, service, system, category, and lore IDs.
2. None of the 4 appendix headings appears in any target or trap.
3. A test fails if WorldLoom renames one of the 4 appendix headings.
4. The 1 MB gate passes for all four formats (retail and GovTech), with text fact depth of unit 6 or deeper.
5. The full test suite passes. `ruff` is clean.

## Out of scope

- Commercial terms from `"base": "retail"` (handoff 4.2, item 7).
- The metric script move and round 1 (handoff items 5 and 6). They become a separate track.
- Any WorldLoom change.
