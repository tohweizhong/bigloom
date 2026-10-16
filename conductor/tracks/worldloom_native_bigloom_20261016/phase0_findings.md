# Phase 0 Findings

- **Track:** `worldloom_native_bigloom_20261016`
- **Date:** 16 Oct 2026 14:32 SGT
- **WorldLoom commit:** `3fcf194`
- **Test corpus:** `worldloom build --seed 8128 --incident --periods 3 --distractors 4 --realism enterprise --narrate --locale singapore` (50 documents, 14 types). Git ignores the output in `runs/phase0/`.
- **Files for review:** SharePoint `building-bigloom/phase0` and `building-bigloom/phase0/t4-with-picture`.

## Summary

| Test | Question | Result | Decision |
| :--- | :--- | :--- | :--- |
| T1 | Does a section added to the IR appear in the rendered file? | Pass for DOCX and PDF. Fail for PPTX and revision files. | Evidence slide after rendering. Upload only the main file of each target. |
| T2 | Does a superseded draft exist for each target type? | Distractor drafts: 4 documents only. Revision files `v0.1` and `v0.2`: every DOCX document. | New trap rule. |
| T3 | Do the target and its trap rank in positions 1 to 3? | Whole-file ranking fails for the workbook. Passage ranking passes for all four formats. | Rank passages, not whole files. |
| T4 | Can BigLoom add a picture and a slide after rendering? | Pass for DOCX, PPTX, and PDF. | Post-render picture and evidence slide. |
| T6 | Does the enterprise deck lay out correctly in PowerPoint? | Fail. Titles run off the slide, and text sits over titles. A post-render fix corrects 106 boxes on 23 slides. | BigLoom fixes broken boxes after rendering. |
| T5 | Does template prose pass the quality checks? | Pass with one period. Fail with three periods (repeated sentences). | One period for each world, one document of each type in a test set. |

## T1. Section added to the IR

Script: `phase0/t1_ir_section.py`, `phase0/t1b_hidden_section.py`.

| File | Position of the golden value |
| :--- | :--- |
| CFO memo DOCX | Unit 291 of 2,170 |
| Executive summary DOCX | Unit 204 of 1,689 |
| CFO memo PDF | Page 6 of 27 |
| Executive summary PDF | Page 4 of 21 |
| Executive summary PPTX | Not present |
| Revision DOCX files `v0.1`, `v0.2` | Present in each file |

- The enterprise PPTX renderer assembles the deck from the executive summary prose, the workbook, the memo, the incident review, and the fact ledger (`render/enterprise/pptx.py:1-18`). It does not show tables from the executive summary.
- A hidden section with the appendix set to "append" also does not reach the deck. In DOCX and PDF, it moves to the appendix.
- The enterprise renderer writes revision files from the same IR, so an added section reaches every revision file.

## T2. Drafts for trap files

Script: `phase0/t2_drafts.py`.

- `--distractors 4` gave drafts for one incident review, one knowledge article, one working note, and some Confluence pages. The CFO memo, executive summary, close calendar, and workbook got none.
- The enterprise renderer writes `v0.1` and `v0.2` for every DOCX document in `artifacts/revisions/`. Some documents also get `v1.1`. PDF, PPTX, and XLSX get no revision files.

**Trap rule:** Word targets use the `v0.1` revision from a second render pass with the canary value. PDF, slide, and workbook targets use the same document from a second pass with the canary value, with no padding, marked as a draft. The golden value goes only into the first pass, and BigLoom keeps only the main file from it.

## T3. Retrieval ranking

Scripts: `phase0/t3_ranking.py`, `phase0/t3b_workbook_questions.py`, `phase0/t3c_passage_ranking.py`.

Two test defects were found and fixed: the question used the creation month instead of the reporting period, and the workbook text included cell type markers, sheet states, and formulas. The current `qualify.py` joins workbook text in the same way, so FR5 must add the filter.

| Target | Whole file, BM25 / TF-IDF (target, trap) | Passages, BM25 / TF-IDF (target, trap) |
| :--- | :--- | :--- |
| CFO memo (DOCX) | 1, 2 / 3, 6 | 1, 2 / 5, 6 |
| Incident review (PDF) | 1, 2 / 2, 1 | 1, 2 / 2, 1 |
| Executive summary (PPTX) | 1, 2 / 3, 4 | 3, 4 / 1, 2 |
| Month-end workbook (XLSX) | 5, 6 / 7, 8 | 3, 4 / 1, 2 |

- The workbook has 23,027 words, about 4 times the memo. Four question forms, including forms that name the sheet, all failed under whole-file ranking.
- Passage ranking splits each file into pages, slides, sheets, or chunks of about 250 words. A file takes the position of its best passage. All four formats pass.
- The measure names in this test came from a shortcut, so some read badly, for example "approved cause reserve". FR6 takes names from the pack.

## T4. Post-render additions

Script: `phase0/t4_post_render.py`.

| File | Change | Image value in text |
| :--- | :--- | :--- |
| CFO memo DOCX | Picture and caption at 60 percent of the body, 2 more units | No |
| Executive summary PPTX | Evidence slide in the middle, 22 slides to 23, golden text value present | No |
| Incident review PDF | Picture page in the middle, 12 pages to 13 | No |

All three files reopen in their own readers. A person must check the look of the added parts.

## T5. Template prose quality

Script: `phase0/t5_prose_quality.py`.

| Check | Limit | Three periods | One period |
| :--- | :--- | :--- | :--- |
| Repeated sentences | 0.2 or less | 0.512 to 0.522 (fail) | 0.138 (pass) |
| Template openers | 0.1 or less | 0.0 | 0.0 |
| Slug leaks, number spelling defects | 0 | 0 | 0 |
| Sentences in each section | 3.5 or more | 4.68 | Not measured |
| Words in each paragraph | 22 or more | 32.1 | Not measured |
| Same text in two builds | Same digest | Same | Not measured |

The template writer repeats sentence forms for one document type every month, and across worlds. Examples: "Taken division by division, the picture is clearer." and "Close is now expected on <date>."

## T6. Deck layout (found in visual review)

Script: `phase0/t6_fix_deck_layout.py`. Review file: SharePoint `building-bigloom/phase0/t6-deck-layout-fixed`.

- The user reviewed the deck in PowerPoint Online. The agenda title sat outside the slide, slides 3 and 4 had the title over the text, and the slide 5 title ran past the edge.
- Cause: the template layouts give the title and body boxes a width of 16.00 in and a height of 0.00 in, on a slide 13.33 in wide. The date, footer, and slide number boxes on each slide also have a height of 0. The renderer scales 4:3 template layouts to 16:9 (`render/enterprise/pptx.py:44`), and this step does not give valid sizes.
- Fix: BigLoom sets valid sizes on every layout and slide box with no height or with a width greater than the slide. The fix changed 106 boxes on 23 slides. No broken box remained. The user approved the look on 16 Oct 2026 14:36 SGT.
- WorldLoom is not changed. An upstream report is not part of this track.

## Changes to the Plan

1. Spec decisions table: PPTX evidence slide, main file only, trap rule, passage ranking, one period for each world, and one document of each type in a test set.
2. FR5: passage ranking and the workbook text filter.
3. Phase 2: run T5 again after the pack adds its document types.
4. Phase 4: the PPTX evidence slide, the PPTX layout fix, and the second render pass for traps.

## Addendum: Phase 2 Results (16 Oct 2026 15:05 SGT)

- **T5 again with the GovTech pack (one period, 35 documents):** repeated sentences in each document are 0.027 on average. Every pack type is under 0.2. Across the corpus the rate is 0.44, because the template writer uses the same sentence forms for the same facts in different document types. Decision: the realism gate checks each document (FR5). The corpus-level rate needs the roadmap agent writers.
- **WorldLoom gaps found:** `pack check` does not catch an undeclared artifact domain (`technology`), an author function that cannot own a domain (Audit and `finance`), or an author who cannot open their own document. The build catches them. A corpus loaded after its build does not register the pack document types again, so renderers skip them. BigLoom now installs them from the recipe record (`corpus.install_pack_types`).
- **Subject limit:** all 16 GovTech types draw on the retail month-end facts (revenue, margin, close, incident). WorldLoom has no public-sector engine, so subjects such as Singpass or LifeSG need pack episodes (`worldloom-process` skill), which is a roadmap item.
