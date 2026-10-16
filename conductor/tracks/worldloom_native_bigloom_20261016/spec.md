# Spec: WorldLoom-Native BigLoom

- **Track ID:** `worldloom_native_bigloom_20261016`
- **Type:** Refactor
- **Status:** Draft for approval (16 Oct 2026 13:50 SGT)
- **Source:** [Research report](./research_report.md), Part 1. WorldLoom context: [worldloom-context.md](../../worldloom-context.md)
- **WorldLoom pin:** commit `3fcf194`

## 1. Overview

The `bigloom build` files do not read like real documents. BigLoom writes its own prose from 4 templates, writes its own layout, and repeats the header line in every paragraph to pass the rank-first gate.

This track makes BigLoom take all content and layout from WorldLoom. BigLoom keeps only the test design.

### Rule

**BigLoom chooses and arranges WorldLoom output. BigLoom does not write content of its own. Written content that a person chooses goes into a WorldLoom pack.**

### Decisions recorded

| Decision | Value | Date |
| :--- | :--- | :--- |
| Seven specs | Approved | 16 Oct 2026 13:46 SGT |
| Retrieval gate | Target and trap both in positions 1 to 3, in BM25 or TF-IDF | 16 Oct 2026 13:41 SGT |
| Retrieval unit | Rank passages, not whole files. A file takes the position of its best passage (page, slide, sheet, or about 250 words). | 16 Oct 2026 14:24 SGT |
| PPTX evidence | BigLoom adds an evidence slide after rendering. The deck does not show added IR sections. | 16 Oct 2026 14:14 SGT |
| Revision files | BigLoom uploads only the main file of each target. Revision files stay local. | 16 Oct 2026 14:14 SGT |
| Periods and test sets | One period for each world. One test set uses one world, with one document of each type. The template writer repeats sentence forms across months and across worlds. | 16 Oct 2026 14:30 SGT |
| Trap rule | Word: the `v0.1` revision from a second render pass with the canary. PDF, slides, workbook: the same document from a second pass with the canary, no padding, marked as a draft. | 16 Oct 2026 14:16 SGT |
| Test phase before the full build | Approved | 16 Oct 2026 13:46 SGT |
| `bigloom proposal` | Fold in as a WorldLoom document type | 16 Oct 2026 13:47 SGT |
| Restore path for the old proposal code | Git tag `proposal-v1`, pushed before the fold-in | 16 Oct 2026 13:52 SGT |
| Narration writer | `--writer template` (`ComposedProvider`) is the default and the only writer in this track. The Jetski handshake and the Claude Code or Codex loop are roadmap items. | 16 Oct 2026 13:58 SGT |

## 2. Phase 0: Test Phase

Phase 0 answers five questions with one 1 MB file in each format. It changes no production code. Its result decides the final plan for Phases 1 to 7.

| # | Question | Pass condition |
| :--- | :--- | :--- |
| T1 | Can the enterprise renderer render one document after BigLoom adds a table section to its IR? | Valid DOCX, PDF, and PPTX. The added section appears at unit 6 or deeper. |
| T2 | Does a superseded draft exist for each target document type? | A list of types with drafts and types without drafts. A fallback for each type without a draft. |
| T3 | Does a natural question put the target and its trap in positions 1 to 3? | Pass for 4 of 4 formats, with no header repeats. |
| T4 | Can BigLoom add a picture to an enterprise PDF, DOCX, and PPTX after rendering? | The file opens. The layout does not change. The image value is not in the text. |
| T5 | Does `ComposedProvider` prose under `enterprise/v2` pass the realism checks in FR5? | `prose_quality` shows no template openers above its threshold and no repeated sentences. Two builds give the same text. |

Phase 0 writes `phase0_findings.md` in the track folder. If a question fails, the track stops for your decision.

## 3. Functional Requirements

### FR1. Corpus as input (Spec 1)

1. `bigloom build --corpus <dir>` reads a WorldLoom corpus with `World.load`.
2. The wizard writes a pack or a company specification, then runs `worldloom build` and the narration step.
3. If no corpus exists, `bigloom build` runs `worldloom build` into `<out>/corpus/` and narrates it with the default writer.
4. If the narration of a corpus is not complete, BigLoom fills the open sections with the default writer and records `narration: partial` in the manifest.
5. If the WorldLoom package is not installed, BigLoom stops and prints the install command for commit `3fcf194`.
3. `manifest.jsonl` records the WorldLoom commit, seed, recipe digest, model ID, and prompt version.
4. BigLoom removes `default_world()` and `_extract_world_pools`.

### FR2. Company pack with document types (Spec 2)

1. A GovTech company pack, base `retail`, holds the company, units, name pools, system brands, voices, and lore.
2. The pack declares at least 16 document types in `artifact_types`.
3. The pack sets `episode_text` and `evaluation_text`.
4. `worldloom pack check` and `worldloom pack lint` pass.
5. GovTech terms appear only in GovTech builds.

### FR3. Narration through WorldLoom (Spec 3)

1. The realism profile is `enterprise/v2`.
2. BigLoom and the wizard take a `--writer` flag. In this track, the only value is `template`, and it is the default.
3. `--writer template` narrates every section with `ComposedProvider.for_world(world)`.
4. The manifest records `narration: composed` and the provider ID.
5. The ledger stays with the corpus.
6. The `--writer` flag leaves room for the roadmap values `handshake`, `claude`, and `codex`. An unknown value stops the run with a list of the values that work.

### FR4. Render through WorldLoom, then add test evidence (Spec 4)

1. WorldLoom enterprise renderers write DOCX, PDF, and PPTX. `render/xlsx.py` writes XLSX with detail tables.
2. BigLoom adds the text fact as a table section in a copy of the IR, at unit 6 or deeper.
3. BigLoom adds the image fact as a picture after rendering.
4. The trap file is the superseded draft of the same document, with the canary value added. Phase 0 sets the fallback for types without drafts.
5. BigLoom pads bytes with media or an unreferenced ZIP member. PDF uses an embedded file stream.
6. Each document gets its own `style_seed`.

### FR5. Qualification v2 (Spec 5)

1. A new violation code replaces `TARGET_NOT_RANKED_FIRST`. The best passage of the target and the best passage of its trap must both rank in positions 1 to 3, in BM25 or TF-IDF. A passage is one PDF page, one slide, one sheet, or about 250 words of a Word file. Long sheets split into passages of about 250 words.
1a. The text reader drops workbook type markers, sheet states, and formulas before ranking.
2. Fact depth comes from renderer locators.
3. New realism checks fail a file for repeated sentences, template openers, header repeats, cut words, or pages with fewer than 40 words.
4. A second reader handles files above 512 MiB and PDF files.
5. The clean fixture in `tests/test_qualify.py` no longer repeats the topic in every paragraph.

### FR6. Natural questions (Spec 6)

1. The subject comes from the document title and type.
2. The metric label comes from the fact kind.
3. The wording comes from the pack `evaluation_text`.
4. The fixed labels "Authorized Capital Reserve", "Q4 Peak Thermal Efficiency", and "Final Audit Report" are removed.

### FR7. Fold in `bigloom proposal` (Spec 7)

0. Before any change to `src/bigloom/proposal/` or `specs/`, add the Git tag `proposal-v1` at the last commit that holds the old code, and push the tag to `origin`. To restore the old code, use `git checkout proposal-v1 -- src/bigloom/proposal specs` or `git worktree add ../bigloom-proposal-v1 proposal-v1`.
1. The funding proposal becomes a pack document type with a large `SizeBudget`.
2. It uses the same narration, renderers, evidence steps, and gate as other files.
3. `src/bigloom/proposal/` keeps no fixed chapters, name lists, plates, or paragraph templates.
4. Proposals up to 1 GiB remain possible through padding.

### FR8. Audit and removal

1. A static test finds no module-level list or tuple of content strings in `src/bigloom/`. An allow-list holds test design constants only.
2. The audit table in Part 5 of the report is the checklist.

## 4. Non-Functional Requirements

1. **Determinism:** the same corpus, seed, and ledger give the same text.
2. **Offline tests:** tests make no model calls.
3. **Quality gates:** coverage above 80 percent, `ruff check .` passes.
4. **Language:** documentation and the skill use Simplified Technical English.

## 5. Acceptance Criteria

1. Phase 0 passes all five questions, or you approve a fallback for each failed question.
2. The static test in FR8 passes.
3. The realism checks in FR5 pass for the 1 MB and 18 MB sets in all four formats.
4. `bigloom qualify` passes with the top 3 rule for the `retail` and GovTech packs.
5. Two builds with the same corpus and ledger give the same text.
6. A funding proposal builds through the same path as the other files.
7. You review the 1 MB set in SharePoint `BigLoom-Eval` and approve it.

## 6. Out of Scope

1. Changes to WorldLoom. If a gap needs a WorldLoom change, the track stops for your decision.
2. **Roadmap, not this track:**
   - `--writer handshake` for Jetski: `narrate requests`, the agent writes `responses.json`, then `narrate accept`.
   - `--writer claude` and `--writer codex`: `worldloom narrate loop --harness <name>`.
   - A thin BigLoom skill that guides a harness agent through the handshake.
   - Unattended model calls through `ExecProvider`.
3. Changes to `bigloom grade`, the `streamAssist` harness, and the SharePoint upload.
4. A new upload of the 50 MB and 100 MB sets. This happens after you approve the 1 MB set.

## 7. Risks

| Risk | Action |
| :--- | :--- |
| A renderer rejects the added IR section | Phase 0 T1. Fallback: add the section after rendering. |
| Some document types have no draft | Phase 0 T2. Fallback set for each type. |
| Natural questions do not reach the top 3 | Phase 0 T3. Stop for your decision. |
| Template prose stays below agent quality | Phase 0 T5 measures it. The roadmap writers raise it later. |
| WorldLoom changes under BigLoom | Pin commit `3fcf194`. |
