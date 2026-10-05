# Specification: Large-File Production on WorldLoom (`bigloom proposal`)

Revised 6 Oct 2026 SGT. This revision replaces the first spec, which used a topic file with its own facts and prose rules. See the design note `large_file_on_worldloom.md`.

## 1. Overview
BigLoom gets a new command, `bigloom proposal`. It makes long, realistic native documents at large byte sizes for transport tests, for example the fetch-to-GCS design for SharePoint and OneDrive (b/568347688).

BigLoom does not own business content. WorldLoom gives the world, the facts, the document structure, the prose contract, and the renderer. BigLoom adds the transport-test layer: realistic weight, evidence at several byte positions, a trap twin, and checks.

The command replaces the one-off script `sharepoint-research/worldloom/make_gsw_proposal.py`.

## 2. Functional Requirements

### 2.1 Spec file (YAML)
- The spec file holds: the world (`pack` or `domain`), the document genre, a free-text subject, the format, the sizes, the evidence positions, the trap mode, the weight mode, and the prose provider.
- The command validates the spec file with a Pydantic model. A bad file gives an error that names the bad field.
- The repository includes `specs/gsw_proposal.yaml`, with the GovTech pack and the Greater Southern Waterfront subject.

### 2.2 World and facts (WorldLoom)
- The command loads the world with `World.load(pack)` or `sdk.company(domain)`.
- The command selects the evidence facts from the WorldLoom `FactLedger`. It does not make facts.
- Each selected fact must be unique in the target document. Its value must not appear in other places in the document.

### 2.3 Structure (WorldLoom)
- The command builds the document structure from `longform.LongDocument`: cover, document control, approval block, contents, sections, tables, appendices, and revision history.
- If no `LongDocument` family fits the genre, BigLoom adds the genre on its side. BigLoom does not change WorldLoom.

### 2.4 Prose (WorldLoom contract, BigLoom adapter)
- The command writes prose through the WorldLoom narrative provider contract. The writer refers to facts as `{{fact:ID}}`. WorldLoom checks the claims.
- Providers: `deterministic` and `composed` (WorldLoom, no model), and `gemini` (BigLoom adapter).
- The Gemini adapter calls Vertex AI REST with a token from `gcloud auth print-access-token`. Flags: `--project`, `--account`, `--model` (default `gemini-3.8-flash`), `--workers`.
- The adapter keeps a cache keyed on the request digest. A second run with the same world, genre, and subject makes no model calls.
- On HTTP 401 or 403, the adapter stops and prints the error. It does not retry. On other errors, it retries with backoff.

### 2.5 Render (WorldLoom)
- The command renders the document with the WorldLoom renderer for the format. This track supports `.docx` only.

### 2.6 Weight layer (BigLoom)
- The weight layer adds realistic figures that BigLoom draws from world entities, for example sites, business units, systems, and phases. Each figure has light grain, so ZIP compression does not make it smaller.
- The weight layer does not add raw ballast parts, for example `worldloom/shape-ballast.bin`.
- `sizes_mb` sets one or more targets. The command adjusts the figure size until each file is between the target and 3 percent over it, with a maximum of 3 builds for each size.
- Only the weight layer depends on the size. All sizes use the same prose.

### 2.7 Evidence positions (BigLoom)
- The spec file lists evidence positions as fractions of the document (0.0 to 1.0) with a modality: `text` or `image`.
- A `text` fact at position 1.0 must come after the last media part.
- An `image` fact appears only in the pixels of one figure. Its value must not appear in the document text.
- The command records each position as a WorldLoom `EvidenceRef` with a `DocxLocator`.

### 2.8 Trap twin (BigLoom, WorldLoom facts)
- The command writes one small draft file (under 1 MB) with the same questions.
- The draft values come from the WorldLoom revision predecessor facts. If a fact has no predecessor, the command picks a different fact and records the choice.
- Each trap figure shows the same entity as its target figure, with the draft value.

### 2.9 Checks and outputs
- The command checks each output file with `native_artifacts.inspect_artifact` and with a ZIP check.
- The command checks that each locator points at its fact, that no trap value is in the target file, and that the end facts come after the last media part.
- Outputs: `docx/<file>` for each size, `traps/<file>`, `manifest.jsonl` (with byte size and SHA-256 for each file), `evals.jsonl`, and `evals.csv` (`query,golden`).
- Each eval row has: id, file, modality, position, question, answer, trap answer, fact id, and locator.

## 3. Non-Functional Requirements
- File type: `.docx` only in this track.
- No change to WorldLoom (`synthetic-foundry`).
- Tests use the WorldLoom deterministic provider or a fake Gemini client. Tests make no network calls.
- Coverage for new code: at least 80 percent. `ruff check .` passes.
- `tech-stack.md` adds PyYAML before the code uses it.
- Peak memory for a 200 MiB file stays below 3 GB.

## 4. Acceptance Criteria
1. `bigloom proposal --spec specs/gsw_proposal.yaml --out <dir>` with `sizes_mb: [200]` makes a `.docx` file between 200 MiB and 206 MiB.
2. Every evidence fact id exists in the WorldLoom `FactLedger` of the world.
3. A second run with the same spec makes no Gemini calls.
4. With `sizes_mb: [5, 10]`, both files have the same `word/document.xml`. Only the media parts differ.
5. Every locator resolves to its fact in the output bytes. The end text facts come after the last image.
6. Every eval answer is in the target file. No trap answer is in the target file. Every trap answer is a WorldLoom predecessor fact or a recorded substitute.
7. A bad spec file gives a validation error that names the bad field.

## 5. Out of Scope
- `.pptx`, `.pdf`, and `.xlsx` output.
- Changes to WorldLoom. Upstream proposals (several `EvidenceRef`s for each shape plan, an image evidence modality for `.docx`, a realistic ballast hook) come later.
- Upload to SharePoint or OneDrive.
- Text-only files where text makes most of the bytes.
