# Specification: Large-File Production on WorldLoom (`bigloom proposal`)

Revised 6 Oct 2026 SGT. This spec uses only the three WorldLoom outputs needed for large-file transport and target-leakage tests.

## 1. Overview
BigLoom adds the `bigloom proposal` command. This command builds long, realistic `.docx` proposals from 5 MiB up to 1024 MiB (`1 GiB`) to test large-file transport (such as `b/568347688`) and stop target leakage.

BigLoom uses three outputs from WorldLoom:
1. **Organisation entities (`World`):** Company name, currency, security marking, business units, systems, sites, and staff names.
2. **Canonical and draft facts (`world.facts`):** High-entropy facts from the WorldLoom `FactLedger` for the target file, paired with predecessor (`supersedes`) or prior-period facts for the `< 1 MB` trap file.
3. **Byte inspection (`native_artifacts.inspect_artifact`):** Post-build verification of paragraphs, tables, and media parts in the `.docx` output.

BigLoom does not use WorldLoom's narrative claim compiler (`NarrativeRequest` and `claims.validate`) or `LongDocument` renderer. Instead, BigLoom generalizes `make_gsw_proposal.py` behind a YAML spec file (`specs/gsw_proposal.yaml`).

## 2. Functional Requirements

### 2.1 Spec File (YAML)
- The spec file defines the world source (`world_pack` or `domain`), the proposal topic (title, short title, document reference, filenames, chapters, middle chapter, zones, work packages, phases, and forbidden leak terms), `sizes_mb`, `figures`, and the prose provider (`deterministic` or `gemini`).
- A Pydantic model (`ProposalSpec`) validates the YAML file. A bad file raises an error that names the invalid field.
- The repository includes `specs/gsw_proposal.yaml` (200 MiB target), `specs/tuas_proposal.yaml` (500 MiB target), and `specs/pdd_proposal.yaml` (1024 MiB target).

### 2.2 World and Facts (WorldLoom)
- The command loads the world from `World.load(world_pack)`, a WorldLoom org-pack JSON file, or `sdk.company(domain, seed=seed).build().world`.
- The command selects unique facts from `world.facts` and formats values with `worldloom.narrative.references.render_value`.
- For each target fact, the command selects a trap value from its `supersedes` predecessor fact in `world.facts`, or from a distinct comparator fact of the same kind when no predecessor exists.

### 2.3 Prose Generator and Cache (BigLoom)
- In `deterministic` mode, BigLoom writes chapter and section prose offline from the world entities and topic context without network calls.
- In `gemini` mode, BigLoom calls Vertex AI REST (`generateContent`, default model `gemini-3.8-flash`) with a token from `gcloud auth print-access-token`.
- Prompts instruct Gemini not to invent budget totals, contingency percentages, approval references, go-live dates, sponsor names, or sensor counts.
- BigLoom caches outlines and section prose under `<out>/_prose_cache` keyed by topic and section index. A second run with the same cache makes no Gemini calls.
- On HTTP 401 or 403, the Gemini client stops immediately and prints the error. On transient errors, it retries with exponential backoff.

### 2.4 Grained Plate Weight Layer (BigLoom)
- BigLoom draws six plate types (`zone`, `gantt`, `budget`, `render`, `section`, `sensors`) using the world agency name, security marking, and topic entities.
- Each plate blends light noise (`GRAIN = 12`) and encodes as JPEG so ZIP compression does not shrink the `.docx` archive.
- The weight layer does not add raw binary ballast parts (`worldloom/shape-ballast.bin`).
- For each target in `sizes_mb` (including `200`, `500`, and `1024` MiB), BigLoom scales the per-figure byte budget in batches until the `.docx` file sits between `target_bytes` and `target_bytes * 1.03` within at most 3 attempts.
- All sizes built from the same spec share identical `word/document.xml` text and differ only in `word/media/` image bytes.

### 2.5 Evidence Positions and Trap Twin (BigLoom)
- BigLoom places text facts at `start` (Executive summary), `middle` (`middle_chapter`), and `end` (final approval annex on a new page after the last figure).
- BigLoom places image-only facts inside the first (`start`), middle (`middle`), and last (`end`) plates. Image fact values must not appear in the document text.
- BigLoom writes one `< 1 MB` draft twin (`traps/<trap_filename>`) with the same questions, draft text answers, and draft plates drawn from the same random state with different values.

### 2.6 Verification and Outputs
- BigLoom checks every output `.docx` with `zipfile.ZipFile.testzip()` and `worldloom.native_artifacts.inspect_artifact`.
- BigLoom verifies that every target text fact exists in the target `.docx`, that `end` text facts appear after the last image, that no image fact value appears in the target text, that no trap value appears in the target `.docx`, and that no `leak_terms` appear anywhere.
- Outputs in `--out`:
  - `docx/<filename>` for each target size in `sizes_mb`
  - `traps/<trap_filename>` (under 1 MB)
  - `manifest.jsonl` (with byte size, word count, figure count, and SHA-256)
  - `evals.jsonl` and `evals.csv` (`query,golden`) with `id`, `file`, `modality`, `position`, `question`, `answer`, `trap_answer`, `fact_id`, and `locator` (`DocxLocator`).

## 3. Non-Functional Requirements
- File type: `.docx` only in this track.
- No changes to WorldLoom (`synthetic-foundry`).
- Unit tests use the `deterministic` prose provider or a fake Gemini client and make no network calls.
- Test coverage for new code: at least 80 percent. `ruff check .` passes with zero warnings.
- `tech-stack.md` documents `PyYAML` before implementation.
- Peak memory for builds from 200 MiB up to 1024 MiB (`1 GiB`) stays below 3 GB by encoding figures in bounded batches.

## 4. Acceptance Criteria
1. `bigloom proposal --spec specs/gsw_proposal.yaml --out <dir>` validates the YAML spec and produces `docx/<file>`, `traps/<file>`, `manifest.jsonl`, `evals.jsonl`, and `evals.csv`.
2. Every world fact ID recorded in `evals.jsonl` exists in `world.facts`, and its trap value comes from a predecessor or comparator fact.
3. A second run against an existing `_prose_cache` makes zero Gemini calls.
4. With two sizes in `sizes_mb` (such as `[5, 10]`), both `.docx` files have identical `word/document.xml` text and differ only in `word/media/` parts.
5. `native_artifacts.inspect_artifact` confirms that all text facts resolve, `end` facts sit after the last image, image values do not leak into text, and trap values do not leak into the target file.
6. An invalid YAML spec raises a validation error that names the offending field.
