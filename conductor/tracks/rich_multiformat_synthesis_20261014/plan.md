# Implementation Plan: Rich Multi-Format Document, Chart, and Workbook Synthesis (`bigloom build`)

## Phase 1: Rich Chart Drawers, Tight Encoder, and Grounded Prose Engine [checkpoint: 43fe367]
- [x] Task: Write failing unit tests in `tests/test_charts_and_prose.py` for all 13 chart drawers, the 12 percent noise grain `encode_tight` byte-budget encoder, and the grounded `Writer` prose and table generator. (1aa387c)
  - [x] Verify that each of the 13 chart drawers (`line`, `bar`, `donut`, `stacked`, `heatmap`, `kpi`, `gantt`, `architecture`, `org`, `whiteboard`, `memo`, `floor`, `phone`) renders a high-resolution `PIL.Image` and embeds the requested metric text visibly.
  - [x] Verify that `encode_tight` hits a target byte budget using `Image.LANCZOS` and `Image.blend` at `alpha=0.12` without producing full-frame static noise.
  - [x] Verify that `Writer` generates multi-paragraph prose, risk tables, and financial overview rows grounded in WorldLoom entities.
- [x] Task: Implement `src/bigloom/charts.py` and `src/bigloom/prose_writer.py` to pass all unit tests in `tests/test_charts_and_prose.py`. (43fe367)
  - [x] Port the 13 chart and diagram drawers and `encode_tight` into `src/bigloom/charts.py`.
  - [x] Port `Writer`, `SENTENCES`, `RISKS`, `MITIGATIONS`, and the 4 operational Excel sheet definitions (`budget`, `procurement`, `pipeline`, `auth`) into `src/bigloom/prose_writer.py`.
- [x] Task: Phase Verification & Checkpoint (Refer to `workflow.md`). (43fe367)

## Phase 2: Rich Multi-Format Renderers in `src/bigloom/build.py` and Pipeline Qualification
- [~] Task: Update `tests/test_pipeline.py` with failing assertions for rich multi-section `.docx`, `.pptx`, `.pdf`, and multi-sheet `.xlsx` outputs (`README`, `Summary`, `Charts`, and operational rows).
  - [ ] Assert that `.docx` files contain multi-section headings, a 4-column risk table, deep text fact placement (`unit_index >= 6`), and captioned crisp chart images.
  - [ ] Assert that `.pptx` files use `16:9` widescreen layout, title and agenda slides, section slides, speaker notes, and deep fact placement (`slide >= 6`).
  - [ ] Assert that `.pdf` files use `reportlab.platypus.SimpleDocTemplate` with A4 page headers, financial tables, and deep fact placement (`page >= 6`).
  - [ ] Assert that `.xlsx` files contain `README`, `Summary`, `Charts`, and operational data rows and pass `worldloom.native_artifacts.inspect_artifact` and `bigloom qualify` with zero violations.
- [ ] Task: Upgrade `src/bigloom/build.py` to use `src/bigloom/charts.py` and `src/bigloom/prose_writer.py` across `.docx`, `.xlsx`, `.pptx`, and `.pdf` target and trap files.
  - [ ] Replace `_make_chart_png` and the stub renderers (`_render_docx`, `_render_xlsx`, `_render_pptx`, `_render_pdf`) in `src/bigloom/build.py`.
  - [ ] Keep `ManifestEntry`, `cases.json`, and `evals.csv` compatible with `bigloom queries` and `bigloom qualify`.
- [ ] Task: Run full test suite (`pytest --cov=src/bigloom`), linter (`ruff check .`), and git hygiene check (`check_git_hygiene.py .`).
- [ ] Task: Phase Verification & Checkpoint (Refer to `workflow.md`).
