# Implementation Plan: Gemini Enterprise Evaluation Harness (`harnesses/gemini_enterprise/`)

## Phase 1: StreamAssist Parser, M365 Uploader, and Batch Harness

- [ ] Task: Build `parse_stream_assist.py` and `upload_m365.py` with TDD unit tests
  - [ ] Write failing unit tests in `tests/test_ge_harness.py` for `parse_stream_assist_chunks()`, `chunks_to_eval_response()`, and `upload_manifest_files()` (simple `PUT` under 4 MB and resumable session at or above 4 MB).
  - [ ] Implement `harnesses/gemini_enterprise/parse_stream_assist.py` to extract answer text, `assist_tokens`, `cited_files`, and `downloaded_files` from raw `StreamAssistResponse` chunks.
  - [ ] Implement `harnesses/gemini_enterprise/upload_m365.py` to read `manifest.jsonl` and upload artifacts to OneDrive or SharePoint via Microsoft Graph.
- [ ] Task: Build `harness.py`, configuration files, and documentation with TDD unit tests
  - [ ] Expand `tests/test_ge_harness.py` with tests for `is_auth_error()`, `evaluate_single_record_with_judge()` (using `gemini-3.8-flash` default and deterministic fallback), and end-to-end `--eval-only` execution producing `responses.json`, `scorecard.md`, `report.md`, and `assist_tokens.json`.
  - [ ] Implement `harnesses/gemini_enterprise/harness.py` with Phase 1 (`streamAssist` runner), Phase 2 (BigLoom deterministic grading + parallel `gemini-3.8-flash` judge), and Phase 3 (combined Markdown report and `EvalResponse` export).
  - [ ] Add `harnesses/gemini_enterprise/config.example.json`, `harnesses/gemini_enterprise/requirements.txt`, `harnesses/gemini_enterprise/login_workforce.sh`, `harnesses/gemini_enterprise/README.md`, and update `.gitignore` and root `README.md`.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
