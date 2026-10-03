# Specification: Vendor-Neutral Run Adapter and Size-Tier Scorecard (`eval_adapter_and_scorecard_20261004`)

## 1. Overview
This feature track adds two vendor-neutral offline modules and CLI commands to BigLoom:
1. `bigloom import-run` (`src/bigloom/adapters.py`) converts saved agent or RAG evaluation logs (generic JSON/JSONL run logs, OpenAI/MCP-style message traces, and CSV evaluation exports) into normalized [`EvalResponse`](file:///usr/local/google/home/weizhongt/coding/bigloom/src/bigloom/models.py#L109-L115) records.
2. `bigloom report` (`src/bigloom/report.py`) joins `manifest.jsonl`, `cases.json`, and `grade_report.json` to render a Markdown scorecard broken down by file size tier, document format, and question modality.

## 2. Functional Requirements

### 2.1 Vendor-Neutral Run Adapter (`src/bigloom/adapters.py` and `bigloom import-run`)
- Accept an input path (`--input`, file or directory), an output JSON path (`--out`), and an optional `--cases` path to match responses by query text when `case_id` is absent.
- Support three vendor-neutral input formats automatically:
  1. **Generic JSON / JSONL Run Logs:** Files containing a list or `results` / `cases` array of dictionaries with fields such as `case_id` / `id` / `query`, `answer_text` / `answer` / `response` / `output`, `cited_files` / `citations` / `sources`, and `tool_calls` / `tools`.
  2. **Agent Message and Tool-Call Traces:** JSON or JSONL traces containing `messages` or `steps` arrays (such as OpenAI, MCP, or OpenTelemetry agent traces) with assistant text, `tool_calls` (`function.name` or `name`), and source document citations.
  3. **CSV Evaluation Tables:** CSV files with columns for `case_id` (or `query`), `answer_text` (or `answer`), `cited_files` (or `citations`), and `tool_calls` (or `tools`).
- Write a JSON array of validated [`EvalResponse`](file:///usr/local/google/home/weizhongt/coding/bigloom/src/bigloom/models.py#L109-L115) objects ready for `bigloom grade`.

### 2.2 Size-Tier and Modality Scorecard (`src/bigloom/report.py` and `bigloom report`)
- Accept `--cases` (`cases.json`), `--grade-report` (`grade_report.json`), `--out` (`scorecard.md`), and optional `--manifest` (`manifest.jsonl`).
- Compute pass rate (`CORRECT_WITH_DOWNLOAD`) and leakage rate (`SNIPPET_ONLY_LEAK` + `CROSS_FILE_LEAK_CANARY` + `CROSS_FILE_LEAK_CITATION`) across:
  1. **Overall Summary Table:** Total cases, count, and percentage for each [`LeakageVerdict`](file:///usr/local/google/home/weizhongt/coding/bigloom/src/bigloom/models.py#L99-L106).
  2. **File Size Tier Table:** Grouped by size tier (such as `1 MB`, `18 MB`, `50 MB`, `100 MB` derived from `manifest.jsonl` or the target filename).
  3. **Document Format Table:** Grouped by `.docx`, `.xlsx`, `.pptx`, and `.pdf`.
  4. **Modality Table:** Grouped by `text` and `image`.
  5. **Leakage and Failure Details:** Per-case table listing every non-passing case (`verdict != CORRECT_WITH_DOWNLOAD`) with its target file, verdict, and detail string.

## 3. Non-Functional Requirements
- **Vendor Neutrality:** No dependency on or reference to any proprietary search product or cloud vendor.
- **Zero External Network Calls:** All log parsing and report generation run offline using the Python standard library (`json`, `csv`, `pathlib`, `re`) and Pydantic.
- **Code Coverage:** Maintain at least 85% test coverage across `src/bigloom/`.

## 4. Acceptance Criteria
1. `bigloom import-run` converts sample JSON/JSONL run logs, OpenAI/MCP-style agent traces, and CSV files into valid `responses.json` files that `bigloom grade` accepts.
2. `bigloom report` produces a deterministic Markdown scorecard with all five sections (overall summary, size tier, format, modality, and failure details).
3. All unit tests in `tests/test_adapters.py` and `tests/test_report.py` pass with zero `ruff` warnings.

## 5. Out of Scope
- Live API calls to any external LLM or search service.
