# Specification: Gemini Enterprise Evaluation Harness (`harnesses/gemini_enterprise/`)

## Overview
This track creates a standalone evaluation harness in `harnesses/gemini_enterprise/` modeled after `bless_limitations`. The core `src/bigloom/` package stays vendor-neutral. The harness uploads generated BigLoom corpora to Microsoft 365, runs queries through Discovery Engine `streamAssist`, exports `EvalResponse` JSON, and grades answers with `bigloom grade` and `gemini-3.8-flash`.

## Functional Requirements

1. **Subfolder Isolation (`harnesses/gemini_enterprise/`):**
   - Place all Gemini Enterprise and Microsoft Graph code inside `harnesses/gemini_enterprise/`.
   - Do not add Google Cloud or Microsoft Graph imports to `src/bigloom/`.
   - Provide `config.example.json`, `requirements.txt`, `login_workforce.sh`, and `README.md` inside `harnesses/gemini_enterprise/`.

2. **Microsoft Graph Uploader (`harnesses/gemini_enterprise/upload_m365.py`):**
   - Read `manifest.jsonl` from a BigLoom build directory.
   - Authenticate to Microsoft Graph with Azure client credentials (`TENANT_ID`, `CLIENT_ID`, `CLIENT_SECRET`).
   - Upload files under 4 MB to OneDrive or SharePoint with a single HTTP `PUT` request.
   - Upload files of 4 MB or larger with a Graph Resumable Upload Session in 1.25 MB chunks (`320 KB * 4`).

3. **StreamAssist Runner and Parser (`harnesses/gemini_enterprise/harness.py` and `parse_stream_assist.py`):**
   - Read `cases.json` from a BigLoom build directory.
   - Query Discovery Engine `AssistantServiceClient.stream_assist` (or REST `streamAssist`) with `tools_spec` for configured `data_store_ids`.
   - Record Time to First Token (`ttft_ms`), total latency (`total_latency_ms`), `assist_tokens`, and raw chunks in `raw_responses/`.
   - Stop immediately on authentication errors (`RefreshError`, `Unauthenticated`, `PermissionDenied`) so expired tokens do not pollute results.
   - Parse `cited_files` from `textGroundingMetadata.references` and `groundingSources`.
   - Detect `downloaded_files` from `action` tool blocks or deep-read thought chunks.
   - Export normalized `EvalResponse` records (`responses.json`) for deterministic grading.

4. **Dual Grading and Reporting (`harnesses/gemini_enterprise/harness.py`):**
   - Run deterministic BigLoom grading (`grade_responses`) and Markdown scorecard generation (`render_scorecard_markdown`).
   - Optionally evaluate each response in parallel with the Vertex AI judge (`gemini-3.8-flash` by default, configurable via `--judge-model`).
   - Write a combined Markdown report (`reports/report.md`) and `reports/assist_tokens.json`.
   - Support `--eval-only` to re-grade saved `raw_responses/` without calling `streamAssist`.

## Non-Functional Requirements
- **Unit Testable Offline:** All uploader, chunk parser, `EvalResponse` exporter, and judge fallback functions must run offline in `pytest` with mocked HTTP and gRPC clients.
- **Zero Credential Leaks:** `.gitignore` must exclude `harnesses/gemini_enterprise/config.json`, `.env`, `raw_responses/`, and `assist_tokens.json`.
- **Code Coverage:** Maintain at least 85% line coverage across the test suite with zero `ruff` warnings.

## Acceptance Criteria
- `upload_m365.py` selects simple `PUT` for `< 4 MB` files and resumable chunked upload for `>= 4 MB` files.
- `parse_stream_assist.py` extracts answer text, `assist_tokens`, `cited_files`, and `downloaded_files` from raw `StreamAssistResponse` chunks and builds valid `EvalResponse` objects.
- `harness.py` supports live execution, `--eval-only` re-grading, deterministic `bigloom grade` + `bigloom report` output, and parallel `gemini-3.8-flash` judge evaluation.
- `pytest` passes all unit tests for the new harness module.

## Out of Scope
- Modifying the core `src/bigloom/` package to depend on `google-cloud-discoveryengine` or `msal`.
- Publishing internal x20 dashboards from the public GitHub repository.
