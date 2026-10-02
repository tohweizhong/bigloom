# BigLoom

BigLoom builds large test files (1 MB to 100 MB) on top of [WorldLoom (`synthetic-foundry`)](https://github.com/vamsiramakrishnan/synthetic-foundry) and prevents target leakage in connector evaluations.

## Problem

When you evaluate a connector on large files (for example, 10 MB to 100 MB DOCX, XLSX, PPTX, and PDF files), target leakage happens in two ways:

1. **Cross-file leakage:** The connector indexes every file in the workspace. A small file (for example, 0.5 MB) may contain the same number or topic as a 50 MB file. The agent answers the 50 MB question from the 0.5 MB file.
2. **Snippet leakage:** The search index returns an early paragraph or title snippet from the large file. The agent answers the question from the snippet without calling `download_document` or `fetch_documents`.

## Architecture

BigLoom stops leakage at two gates:

| Stage | Module | What it enforces |
| :--- | :--- | :--- |
| **1. Build-time qualification** | `src/bigloom/qualify.py` | Uses `worldloom.native_artifacts.inspect_artifact`, `pypdf`, and `worldloom.evaluate.{bm25,tfidf}` to check global answer uniqueness, deep placement (`min_unit_index`), image-only text exclusion, canary isolation, and leave-one-out retrieval. |
| **2. Eval-time grading** | `src/bigloom/grade.py` | Grades each query into `CORRECT_WITH_DOWNLOAD`, `SNIPPET_ONLY_LEAK`, `CROSS_FILE_LEAK_CANARY`, `CROSS_FILE_LEAK_CITATION`, or `WRONG_ANSWER`. |

## Quick Start

```bash
python3 -m venv .venv
.venv/bin/pip install -e "../synthetic-foundry[docx,pptx,xlsx,pdf]"
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
```

## CLI Commands

```bash
# 1. Qualify a rendered directory and dataset before uploading to a connector
bigloom qualify --corpus-dir ./artifacts --cases ./cases.json

# 2. Grade a completed evaluation run and detect target leakage
bigloom grade --cases ./cases.json --responses ./responses.json
```
