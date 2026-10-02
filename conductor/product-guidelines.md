# Product Guidelines: BigLoom

## 1. Writing and Prose Style (Simplified Technical English)
- Write all documentation, CLI help strings, error messages, and log text in Simplified Technical English (ASD-STE100).
- Keep sentences short: maximum 25 words for descriptions and maximum 20 words for instructions.
- Write one instruction in each sentence.
- Use the active voice. Do not use contractions or semicolons.
- Keep noun clusters to at most three words.

## 2. CLI UX and Determinism
- Every command (`bigloom build`, `bigloom queries`, `bigloom qualify`, `bigloom grade`) must accept explicit input and output paths.
- File generation and query generation must be deterministic for a given random seed.
- Commands must exit with code `0` on pass and code `1` when any qualification violation occurs.
- Output files must use clean, machine-readable JSON or JSONL schemas validated by frozen Pydantic models.

## 3. Quality and Anti-Leakage Standards
- No dummy content, no facade tests, and no hardcoded bypasses.
- Inspect actual rendered bytes on disk (`.docx`, `.xlsx`, `.pptx`, `.pdf`) rather than trusting in-memory generation requests.
- Enforce high-entropy golden and canary values so that a model cannot guess the answer by chance.
