# Gemini Enterprise Evaluation Harness

This subfolder runs BigLoom large-file evaluations against Gemini Enterprise (`streamAssist`). The core `src/bigloom/` package remains vendor-neutral.

## Files

| File | Purpose |
| :--- | :--- |
| `run_eval.sh` | Runs the smoke test (2 cases) or the full test suite (16 cases) in one command. |
| `upload_m365.py` | Uploads files from `manifest.jsonl` to OneDrive or SharePoint via Microsoft Graph (`PUT` under 4 MB, resumable session at or above 4 MB). |
| `harness.py` | Runs `cases.json` against `streamAssist`, grades with `bigloom grade` and `gemini-3.8-flash`, and writes `scorecard.md` and `report.md`. |
| `parse_stream_assist.py` | Extracts answer text, `assist_tokens`, `cited_files`, and `tool_calls` from raw `StreamAssistResponse` chunks. |
| `login_workforce.sh` | Signs in to `gcloud` with Workforce Identity Federation (WIF) and sets Application Default Credentials. |
| `config.example.json` | Template for GCP project, engine, location, and data store IDs. |

## Steps

1. Sign in with Workforce Identity Federation in your Microsoft 365 browser profile:

```bash
cd harnesses/gemini_enterprise
bash login_workforce.sh
export GCP_ACCESS_TOKEN=$(gcloud auth application-default print-access-token)
```

2. Run the smoke test (2 cases):

```bash
bash run_eval.sh smoke
```

3. Run the full suite (16 cases across `.docx`, `.xlsx`, `.pptx`, and `.pdf`):

```bash
bash run_eval.sh full
```

4. Re-grade saved raw responses offline without calling `streamAssist`:

```bash
bash run_eval.sh full --eval-only
```
