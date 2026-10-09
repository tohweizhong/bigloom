# BigLoom

BigLoom builds large test files (1 MB to 100 MB) on top of [WorldLoom (`synthetic-foundry`)](https://github.com/vamsiramakrishnan/synthetic-foundry) and prevents target leakage in connector and RAG evaluations.

## Prerequisite Dependency: `synthetic-foundry` (`worldloom`)

BigLoom requires the [`synthetic-foundry`](https://github.com/vamsiramakrishnan/synthetic-foundry) package (imported in Python as `worldloom`). This package is not published on PyPI. You must install it from a local clone before you run `bigloom`.

BigLoom uses three modules from `worldloom`:

| `worldloom` Module | How BigLoom Uses It |
| :--- | :--- |
| `worldloom.World` and `worldloom.sdk.company` | Loads enterprise blueprints, company entities, cost centres, and the `FactLedger` (canonical facts and draft predecessor facts). |
| `worldloom.native_artifacts.inspect_artifact` | Parses rendered `.docx`, `.xlsx`, and `.pptx` files into numbered text units (paragraphs, sheets, or slides) to verify fact placement. |
| `worldloom.evaluate.bm25` and `worldloom.evaluate.tfidf` | Ranks every file in the corpus against each evaluation query to confirm that the large target file ranks first. |

## Problem

When you evaluate a connector or search agent on large files (such as 18 MB, 50 MB, and 100 MB DOCX, XLSX, PPTX, and PDF files), target leakage happens in two ways:

1. **Cross-file leakage:** The connector indexes every file in the workspace. A small file (under 1 MB) can contain the same number or topic as a 50 MB file. The agent then answers the 50 MB question from the small file.
2. **Snippet leakage:** The search index returns an early paragraph or title snippet from the large file. The agent answers the question from the snippet without calling `download_document` or `fetch_documents`.

## Offline Pipeline

BigLoom runs offline in six stages:

| Stage | Module | What It Does |
| :--- | :--- | :--- |
| **1. Build large files** | `src/bigloom/build.py` | Renders `.docx`, `.xlsx`, `.pptx`, and `.pdf` files at requested byte sizes (`--sizes-mb`), creates one `< 1 MB` canary trap file per large file, and writes `manifest.jsonl`. |
| **2. Generate queries** | `src/bigloom/queries.py` | Reads `manifest.jsonl` and generates `cases.json` with two high-entropy questions per large file (one deep `text` fact at `unit >= 5` and one `image` chart fact). |
| **3. Qualify corpus** | `src/bigloom/qualify.py` | Uses `worldloom.native_artifacts.inspect_artifact`, `pypdf`, and `worldloom.evaluate.{bm25,tfidf}` to check high entropy, global answer uniqueness, deep placement, image-only text exclusion, canary isolation, and retrieval ranking. |
| **4. Import run logs** | `src/bigloom/adapters.py` | Converts vendor-neutral JSON/JSONL logs, OpenAI/MCP message traces, and CSV evaluation tables into `responses.json`. |
| **5. Grade responses** | `src/bigloom/grade.py` | Grades each query response into `CORRECT_WITH_DOWNLOAD`, `SNIPPET_ONLY_LEAK`, `CROSS_FILE_LEAK_CANARY`, `CROSS_FILE_LEAK_CITATION`, or `WRONG_ANSWER`. |
| **6. Render scorecard** | `src/bigloom/report.py` | Builds a Markdown scorecard (`scorecard.md`) grouped by file size tier (`18 MB`, `50 MB`, `100 MB`), document format, and modality. |

## Generated Files Reference

The pipeline passes data between stages through five files:

| File | Produced By | Consumed By | What It Contains |
| :--- | :--- | :--- | :--- |
| `manifest.jsonl` | `bigloom build` | `bigloom queries`, `bigloom report`, `upload_m365.py` | One JSON line per large file (`ManifestEntry`). Records the large `target_file` path, byte size, and SHA-256 hash, the paired `< 1 MB` `distractor_file` path, byte size, and SHA-256 hash, the planted `text_golden_value` and `image_golden_value` in the large file, and the planted `text_canary_value` and `image_canary_value` in the small trap file. |
| `cases.json` | `bigloom queries` | `bigloom qualify`, `bigloom import-run`, `bigloom grade`, `bigloom report` | A JSON array of `EvalCase` objects (two questions per large file: one `text` and one `image`). Each case holds the question `query`, the expected `target_file`, the `golden_value`, the minimum allowed text unit index (`min_unit_index`), and the `canary_trap` value from the small distractor file. |
| `responses.json` | `bigloom import-run` (or a harness) | `bigloom grade` | A JSON array of `EvalResponse` objects captured from the system under test. Each entry records `case_id`, `answer_text`, `cited_files`, and `tool_calls` (such as `download_document`). |
| `grade_report.json` | `bigloom grade` | `bigloom report` | A `GradeReport` JSON object containing total counts and per-case verdicts (`CORRECT_WITH_DOWNLOAD`, `SNIPPET_ONLY_LEAK`, `CROSS_FILE_LEAK_CANARY`, `CROSS_FILE_LEAK_CITATION`, or `WRONG_ANSWER`). |
| `scorecard.md` | `bigloom report` | Human reader | A Markdown report showing accuracy and leakage rates across file size tiers, document formats, and modalities. |

### Example `manifest.jsonl` Record (`ManifestEntry`)

```json
{
  "file_id": "docx_18mb",
  "format": "docx",
  "target_file": "target_docx_18mb.docx",
  "target_size_bytes": 18874512,
  "target_sha256": "a3f5...",
  "distractor_file": "trap_docx_18mb_draft.docx",
  "distractor_size_bytes": 42180,
  "distractor_sha256": "91c2...",
  "topic": "Meridian Ledger Close",
  "period": "FY2026-Q4",
  "distractor_period": "FY2025-Q1 Preliminary Draft",
  "text_metric_label": "Reconciliation Settlement Token",
  "text_golden_value": "RST-2026Q4-849201",
  "text_canary_value": "RST-2025Q1-193847",
  "text_unit_index": 7,
  "image_chart_title": "Regional Variance Breakdown",
  "image_golden_value": "RVB-994120",
  "image_canary_value": "RVB-112094"
}
```

## Quick Start

Clone `synthetic-foundry` next to `bigloom` and install both packages in a virtual environment:

```bash
git clone https://github.com/vamsiramakrishnan/synthetic-foundry.git ../synthetic-foundry
python3 -m venv .venv
.venv/bin/pip install -e "../synthetic-foundry[docx,pptx,xlsx,pdf]"
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
```

## CLI Commands

```bash
# 1. Build large target files, < 1 MB distractor traps, and manifest.jsonl
bigloom build --out-dir ./artifacts --sizes-mb 18,50,100 --formats docx,xlsx,pptx,pdf --world-pack retail-close --seed 42

# 2. Generate two evaluation cases per large file (cases.json) from manifest.jsonl
bigloom queries --manifest ./artifacts/manifest.jsonl --out ./artifacts/cases.json

# 3. Qualify the rendered directory and dataset before uploading to a connector
bigloom qualify --corpus-dir ./artifacts --cases ./artifacts/cases.json

# 4. Import saved evaluation logs (JSON, JSONL, agent traces, or CSV) into responses.json
bigloom import-run --input ./raw_logs.jsonl --cases ./artifacts/cases.json --out ./responses.json

# 5. Grade a completed evaluation run and detect target leakage
bigloom grade --cases ./artifacts/cases.json --responses ./responses.json > ./grade_report.json

# 6. Render a Markdown scorecard by size tier, format, and modality
bigloom report --cases ./artifacts/cases.json --grade-report ./grade_report.json --manifest ./artifacts/manifest.jsonl --out ./scorecard.md
```

## Evaluation Harnesses

Vendor-specific runners live under `harnesses/` so the core `bigloom` package stays independent of any cloud vendor:

- **[`harnesses/gemini_enterprise/`](./harnesses/gemini_enterprise/README.md):** Uploads the files listed in `manifest.jsonl` to SharePoint or OneDrive via Microsoft Graph, runs `cases.json` against Discovery Engine `streamAssist`, exports `responses.json`, and grades runs with `bigloom grade` and `gemini-3.8-flash`.


