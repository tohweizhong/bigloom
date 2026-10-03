# BigLoom

BigLoom builds large test files (1 MB to 100 MB) on top of [WorldLoom (`synthetic-foundry`)](https://github.com/vamsiramakrishnan/synthetic-foundry) and prevents target leakage in connector and RAG evaluations.

## Problem

When you evaluate a connector or search agent on large files (such as 18 MB, 50 MB, and 100 MB DOCX, XLSX, PPTX, and PDF files), target leakage happens in two ways:

1. **Cross-file leakage:** The connector indexes every file in the workspace. A small file (under 1 MB) may contain the same number or topic as a 50 MB file. The agent answers the 50 MB question from the small file.
2. **Snippet leakage:** The search index returns an early paragraph or title snippet from the large file. The agent answers the question from the snippet without calling `download_document` or `fetch_documents`.

## Offline Pipeline

BigLoom runs offline in six stages:

| Stage | Module | What it enforces |
| :--- | :--- | :--- |
| **1. Build large files** | `src/bigloom/build.py` | Renders `.docx`, `.xlsx`, `.pptx`, and `.pdf` files at requested byte sizes (`--sizes-mb`), creates one `< 1 MB` canary trap file per large file, and writes `manifest.jsonl`. |
| **2. Generate queries** | `src/bigloom/queries.py` | Reads `manifest.jsonl` and generates `cases.json` with two high-entropy questions per large file (one deep `text` fact at `unit >= 5` and one `image` chart fact). |
| **3. Qualify corpus** | `src/bigloom/qualify.py` | Uses `worldloom.native_artifacts.inspect_artifact`, `pypdf`, and `worldloom.evaluate.{bm25,tfidf}` to check high entropy, global answer uniqueness, deep placement, image-only text exclusion, canary isolation, and retrieval ranking. |
| **4. Import run logs** | `src/bigloom/adapters.py` | Converts vendor-neutral JSON/JSONL logs, OpenAI/MCP message traces, and CSV evaluation tables into `responses.json`. |
| **5. Grade responses** | `src/bigloom/grade.py` | Grades each query response into `CORRECT_WITH_DOWNLOAD`, `SNIPPET_ONLY_LEAK`, `CROSS_FILE_LEAK_CANARY`, `CROSS_FILE_LEAK_CITATION`, or `WRONG_ANSWER`. |
| **6. Render scorecard** | `src/bigloom/report.py` | Builds a Markdown scorecard (`scorecard.md`) broken down by file size tier (`18 MB`, `50 MB`, `100 MB`), document format, and modality. |

## Quick Start

```bash
python3 -m venv .venv
.venv/bin/pip install -e "../synthetic-foundry[docx,pptx,xlsx,pdf]"
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
```

## CLI Commands

```bash
# 1. Build large target files and < 1 MB distractor traps (from a WorldLoom pack, domain, or seed)
bigloom build --out-dir ./artifacts --sizes-mb 18,50,100 --formats docx,xlsx,pptx,pdf --world-pack retail-close --seed 42

# 2. Generate two evaluation cases per large file from manifest.jsonl
bigloom queries --manifest ./artifacts/manifest.jsonl --out ./artifacts/cases.json

# 3. Qualify the rendered directory and dataset before uploading to a connector
bigloom qualify --corpus-dir ./artifacts --cases ./artifacts/cases.json

# 4. Import saved evaluation logs (JSON, JSONL, agent traces, or CSV)
bigloom import-run --input ./raw_logs.jsonl --cases ./artifacts/cases.json --out ./responses.json

# 5. Grade a completed evaluation run and detect target leakage
bigloom grade --cases ./artifacts/cases.json --responses ./responses.json > ./grade_report.json

# 6. Render a Markdown scorecard by size tier, format, and modality
bigloom report --cases ./artifacts/cases.json --grade-report ./grade_report.json --manifest ./artifacts/manifest.jsonl --out ./scorecard.md
```
