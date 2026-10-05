# Specification: Reusable Proposal Generator (`bigloom proposal`)

## 1. Overview
BigLoom gets a new command, `bigloom proposal`. It makes one long, text-heavy synthetic document from a YAML topic file. The first topic is the Greater Southern Waterfront (GSW) funding proposal. The command replaces the one-off script `sharepoint-research/worldloom/make_gsw_proposal.py`.

The file is for transport tests of large files, for example the fetch-to-GCS design for SharePoint and OneDrive (b/568347688). Gemini writes the prose. Site plates with grain make the byte size.

## 2. Functional Requirements

### 2.1 Topic file (YAML)
- The topic file holds: title, short name, document reference for questions, file names, context text for Gemini, chapter list, the middle chapter, fact templates, and plate words (site names, work packages, phases).
- Each fact template has a position: `start`, `middle`, or `end`. The command puts `end` facts on the last page, after the last plate.
- The command validates the topic file with a Pydantic model. A bad file gives a clear error and no output.
- The repository includes `topics/gsw.yaml`.

### 2.2 Organisation pack
- The command reads the agency name, the marking, and the name lists from an organisation pack (`--org-pack`), for example `govtech-pack.json`.
- The command does not import `make_large_files.py`.

### 2.3 Prose step
- The command calls Gemini through Vertex AI REST. It gets the token from `gcloud auth print-access-token`, with an optional `--account`.
- Flags: `--project`, `--account`, `--model` (default `gemini-3.8-flash`), `--workers` (default 8).
- The command keeps the outline and the sections in a prose cache for each topic (`--cache-dir`). A second run with the same topic makes no Gemini calls.
- On HTTP 401 or 403, the command stops and prints the error. It does not retry. On other errors, it retries with backoff.
- `--skip-prose` builds from the cache only. A missing cache file gives a clear error.

### 2.4 Build step
- The command draws the plates (zoning plan, phasing chart, cost chart, aerial render, seawall cross-section, sensor plan). Each plate prints one value.
- `--target-bytes` sets the size. The command adjusts the plate size until the file is between the target and 3 percent over it, with a maximum of 3 builds.
- `--figures` sets the plate count. `--seed` makes the output repeatable.
- Image facts are in the first, the middle, and the last plate.
- The command checks the ZIP structure of the output file.

### 2.5 Trap file
- The command writes one small draft file (under 1 MB) with the same questions and different values.
- Each trap plate shows the same site as its target plate, with a different value.

### 2.6 Outputs
- `docx/<file>`, `traps/<file>`, `manifest.jsonl`, `evals.jsonl`, and `evals.csv` (`query,golden`).
- Each eval row has: id, file, modality, position, question, answer, trap answer, and evidence.

## 3. Non-Functional Requirements
- File type: `.docx` only in this track.
- Tests use a fake Gemini client. Tests make no network calls.
- Coverage for new code: at least 80 percent. `ruff check .` passes.
- `tech-stack.md` adds PyYAML before the code uses it.
- Peak memory for a 200 MiB file stays below 3 GB.

## 4. Acceptance Criteria
1. `bigloom proposal --topic topics/gsw.yaml --org-pack <pack> --out <dir> --target-bytes 209715200` makes a `.docx` file between 200 MiB and 206 MiB.
2. A second run with `--skip-prose` makes no Gemini calls.
3. The `end` facts are in the last paragraphs of `word/document.xml`, after the last image.
4. Every eval answer is in the target file. No trap answer is in the target file.
5. With the same seed and the same cache, two runs give the same facts and answers.
6. A bad topic file gives a validation error that names the bad field.

## 5. Out of Scope
- `.pptx`, `.pdf`, and `.xlsx` output.
- Upload to SharePoint or OneDrive. `upload_m365.py` already does this.
- Text-only files where text makes most of the bytes.
- Changes to WorldLoom or `make_large_files.py`.
- The five-layer generalisation (topic brief, document types, plate library, pack currency and voice, size profile). See [generalization.md](./generalization.md). Deferred to a later track.
