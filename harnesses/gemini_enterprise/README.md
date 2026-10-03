# Gemini Enterprise Evaluation Harness

This subfolder runs BigLoom large-file evaluations against Gemini Enterprise (`streamAssist`). The core `src/bigloom/` package remains vendor-neutral.

## Files

| File | Purpose |
| :--- | :--- |
| `upload_m365.py` | Uploads files from `manifest.jsonl` to OneDrive or SharePoint via Microsoft Graph (`PUT` under 4 MB, resumable session at or above 4 MB). |
| `harness.py` | Runs `cases.json` against `streamAssist`, grades with `bigloom grade` and `gemini-3.8-flash`, and writes `reports/scorecard.md` and `reports/report.md`. |
| `parse_stream_assist.py` | Extracts answer text, `assist_tokens`, `cited_files`, and `tool_calls` from raw `StreamAssistResponse` chunks. |
| `login_workforce.sh` | Signs in to `gcloud` with Workforce Identity Federation (WIF) and sets Application Default Credentials. |
| `config.example.json` | Template for GCP project, engine, location, and data store IDs. |

## Steps

1. Copy `config.example.json` to `config.json` and fill in your project and engine IDs.
2. Upload your generated BigLoom artifacts to SharePoint or OneDrive:

```bash
python3 harnesses/gemini_enterprise/upload_m365.py \
  --manifest ./artifacts/manifest.jsonl \
  --remote-folder BigLoom-Eval
```

3. Sign in with Workforce Identity Federation:

```bash
bash harnesses/gemini_enterprise/login_workforce.sh
```

4. Run the evaluation harness:

```bash
python3 harnesses/gemini_enterprise/harness.py \
  --config harnesses/gemini_enterprise/config.json \
  --cases ./artifacts/cases.json \
  --manifest ./artifacts/manifest.jsonl \
  --runs 3
```

5. Re-grade saved raw responses offline without calling `streamAssist`:

```bash
python3 harnesses/gemini_enterprise/harness.py \
  --cases ./artifacts/cases.json \
  --manifest ./artifacts/manifest.jsonl \
  --eval-only
```
