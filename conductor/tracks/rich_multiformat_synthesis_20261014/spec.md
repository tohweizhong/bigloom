# Specification: Rich Multi-Format Document, Chart, and Workbook Synthesis (`bigloom build`)

## Overview
Replace the stub document renderers and static-noise image generator in `src/bigloom/build.py` with the rich chart drawers, tight byte encoders, grounded prose writer, and multi-sheet workbook generators from `sharepoint-research/worldloom/make_large_files.py` and `make_15mb_files.py`. Ensure that every generated `.docx`, `.xlsx`, `.pptx`, and `.pdf` file opens cleanly in Office and SharePoint Online, embeds readable charts with image-only facts, plants deep text facts at unit index `>= 6`, pairs with a `< 1 MiB` canary trap twin, and passes `bigloom qualify`.

## Functional Requirements
1. **Rich High-Resolution Chart and Diagram Drawers (`src/bigloom/charts.py`)**:
   - Port all 13 `2400x1600` / `1180x2400` chart and diagram drawers (`line`, `bar`, `donut`, `stacked`, `heatmap`, `kpi`, `gantt`, `architecture`, `org`, `whiteboard`, `memo`, `floor`, `phone`) from `make_large_files.py`.
   - Print the high-entropy image golden value (`image_golden_value`) or canary value (`image_canary_value`) visibly inside the primary figure plate without leaking the value into the document text.
   - Port the `encode_tight` byte-budget encoder using `Image.LANCZOS` scaling and a 12 percent noise grain (`Image.effect_noise` blended at `alpha=0.12`) so figures stay crisp and readable while reaching the target file size.

2. **Grounded Multi-Paragraph Prose and Tables (`src/bigloom/prose_writer.py`)**:
   - Derive all prose sentences, names, divisions, vendors, services, roles, fiscal months, quarters, section headings, risks, mitigations, and chart pools directly from `WorldLoom` (`World`, `corpus_locale(world)`, `ComposedProvider.for_world(world)`, `world.artifact_irs`, `world._masterdata`, `world.events`, `world.lore`, `world.facts`, and `worldloom.divisions.POOLS`) with zero hardcoded static lists.
   - Ensure zero hardcoded government acronyms (`GeBIZ`, `IM8`, `SHIP-HATS`, `SGTS`, `Singpass`, `LifeSG`, `Myinfo`, `NRIC`) appear in private-sector corpora.

3. **Rich Multi-Format Document Renderers (`src/bigloom/build.py`)**:
   - **`.docx`**: Render multi-section Word documents with headers, footers, author metadata, synthetic test marking, a 4-column risk mitigation table, a financial overview section at paragraph index `>= 6` containing the golden or canary text fact, and captioned figure plates.
   - **`.pptx`**: Render `16:9` widescreen PowerPoint decks with a themed title band, title slide, agenda slide, section bullet slides, financial overview slide at slide index `>= 6` containing the text fact, and figure slides with bullet takeaways and speaker notes.
   - **`.pdf`**: Render A4 PDF documents using `reportlab.platypus.SimpleDocTemplate` with page headers, page numbers, cover page, multi-section prose, financial overview table on page `>= 6` containing the text fact, and scaled figure plates.
   - **`.xlsx`**: Render multi-sheet Excel workbooks (`README`, `Summary`, `Charts`, and `1,500` operational ledger rows across `budget`, `procurement`, `pipeline`, and `auth` schemas) with the planted text fact at unit index `>= 6` and embedded figure plates on the `Charts` worksheet.

4. **Qualification and Pipeline Compatibility (`src/bigloom/qualify.py` and `src/bigloom/queries.py`)**:
   - Preserve the `ManifestEntry` schema (`manifest.jsonl`), `cases.json`, and `evals.csv` outputs.
   - Ensure every generated corpus passes `bigloom qualify` with zero violations (`LOW_ENTROPY_GOLDEN_VALUE`, `SHALLOW_PLACEMENT_SNIPPET_RISK`, `IMAGE_FACT_LEAKED_IN_TEXT`, `DUPLICATE_GOLDEN_IN_OTHER_FILE`, `CANARY_MISSING_IN_DISTRACTOR`, `TARGET_NOT_RANKED_FIRST`).

## Non-Functional Requirements
- Deterministic output for a given `--seed`.
- `.xlsx` workbooks must pass `worldloom.native_artifacts.inspect_artifact` in under 1 second per workbook.
- All code and documentation must follow Simplified Technical English (ASD-STE100).

## Acceptance Criteria
- `bigloom build` generates rich `.docx`, `.xlsx`, `.pptx`, and `.pdf` files with crisp charts (`12%` grain blend) and multi-section prose instead of RGB static noise.
- `bigloom qualify` passes with `0` violations on a multi-format corpus built by `bigloom build`.
- `pytest --cov=src/bigloom` passes with `>= 85%` coverage and `ruff check .` reports `0` lint errors.

## Out of Scope
- Modifying the `BigLoom-Ning` SharePoint folder.
- Building a web UI.
