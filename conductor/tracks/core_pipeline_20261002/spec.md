# Specification: Core BigLoom Pipeline (`core_pipeline_20261002`)

## 1. Overview
This MVP track builds the complete four-step offline pipeline for BigLoom: `bigloom build`, `bigloom queries`, `bigloom qualify`, and `bigloom grade`. It also builds the `pytest` test suite that proves target-leakage prevention and detection across `.docx`, `.xlsx`, `.pptx`, and `.pdf` files.

## 2. Functional Requirements

### 2.1 Large-File and Trap Builder (`src/bigloom/build.py` and `bigloom build`)
- Accept an optional WorldLoom corpus directory (`--corpus-dir`) and a deterministic integer seed (`--seed`, default `42`). When `--corpus-dir` is omitted, generate synthetic enterprise topics, entities, and figures from `--seed`.
- Accept custom target file sizes in megabytes via `--sizes-mb` (for example, `--sizes-mb 1,18,50,100`) and file formats via `--formats` (default `docx,xlsx,pptx,pdf`).
- Render one large target file for each requested size and format using compression-resistant noisy chart images (`Pillow`) and structured pages, slides, or rows.
- Place each target text fact deep inside the document (`unit >= 5`) and each target image fact inside a chart image only (never in document text).
- Automatically render one paired small distractor file (under 1 MB) for each large file on the same project topic (using an earlier draft or prior fiscal year) with a distinct canary value.
- Write `manifest.jsonl` containing file metadata, byte sizes, SHA-256 digests, planted facts, and paired distractor paths.

### 2.2 Query Generator (`src/bigloom/queries.py` and `bigloom queries`)
- Read `manifest.jsonl` and generate two [`EvalCase`](file:///usr/local/google/home/weizhongt/coding/bigloom/src/bigloom/models.py#L22-L41) entries for each large target file:
  1. One `text` modality question targeting the deep text or table fact (`min_unit_index >= 5`).
  2. One `image` modality question targeting the chart-only fact.
- Ensure every question names the topic and period without naming the file path.
- Ensure every `golden_value` and `canary_value` is high-entropy (such as 7-digit currency amounts, two-decimal percentages, or specific alphanumeric codes).
- Write the generated cases to `cases.json`.

### 2.3 Qualification Gate (`src/bigloom/qualify.py` and `bigloom qualify`)
- Inspect all rendered `.docx`, `.pptx`, `.xlsx` (via `worldloom.native_artifacts.inspect_artifact`), and `.pdf` (via `pypdf`) files on disk.
- Enforce eight violation checks: `LOW_ENTROPY_GOLDEN_VALUE`, `MISSING_TARGET_FILE`, `GOLDEN_MISSING_IN_TARGET`, `SHALLOW_PLACEMENT_SNIPPET_RISK`, `IMAGE_FACT_LEAKED_IN_TEXT`, `DUPLICATE_GOLDEN_IN_OTHER_FILE`, `CANARY_MISSING_IN_DISTRACTOR`, `CANARY_COLLIDES_WITH_TARGET`, and `TARGET_NOT_RANKED_FIRST` (via WorldLoom `Bm25` and `TfIdf`).

### 2.4 Leakage Grader (`src/bigloom/grade.py` and `bigloom grade`)
- Grade evaluation responses into `CORRECT_WITH_DOWNLOAD`, `SNIPPET_ONLY_LEAK`, `CROSS_FILE_LEAK_CANARY`, `CROSS_FILE_LEAK_CITATION`, or `WRONG_ANSWER`.
- Enforce word-boundary matching so substrings inside unrelated numbers do not cause false matches.

## 3. Non-Functional Requirements
- **Determinism:** Given the same `--seed` and `--sizes-mb`, `bigloom build` and `bigloom queries` must produce identical facts and questions.
- **Test Speed:** Unit tests in `pytest` must use small byte tiers (such as `0.2 MB` to `1 MB`) so the test suite finishes in under 15 seconds while exercising the exact same code paths as 100 MB builds.
- **Code Coverage:** Maintain at least 80% test coverage across `src/bigloom/`.

## 4. Acceptance Criteria
1. Running `bigloom build` followed by `bigloom queries` and `bigloom qualify` exits with code `0` and zero violations across `.docx`, `.xlsx`, `.pptx`, and `.pdf`.
2. Negative unit tests corrupt each anti-leakage rule (low entropy, duplicate fact, shallow unit index, image fact in text, missing canary, and wrong BM25/TF-IDF rank) and confirm that `bigloom qualify` catches each violation.
3. Grading unit tests simulate full downloads, snippet-only answers, small-file canary fallbacks, wrong-file citations, and wrong answers, and confirm that `bigloom grade` assigns the exact `LeakageVerdict`.

## 5. Out of Scope
- Live connector upload scripts (SharePoint, Google Drive, Confluence).
- Live agent or search API callers.
