# Spec: Realism Loop, Round 1 (Feature)

Track ID: `realism_loop_20261022`. Source: realism RSI handoff, sections 2 to 8, items 5 and 6
(`~/.gemini/jetski/brain/962bad5e-098a-42ae-a058-de8668e68825/bigloom_realism_rsi_handoff.md`).
Decisions: the user said "go with your recommendations" on 22 Oct 2026 23:04 SGT.

## Overview

BigLoom measures realism as a vector and with blind judges. Round 0 used scratch scripts in
another session. This track moves the metric script into BigLoom, measures round 1 (appendix
filter on, handshake writer), and writes the first draft of `docs/self-improvement.md`.

## Functional requirements

1. FR1. `src/bigloom/realism_metrics.py` holds the metric vector. Text readers, sentence rule,
   and defect patterns are the same as the round 0 script. Rates are per 1000 words.
2. FR2. Sentence reuse compares different documents only. Files of the same document type (from
   the manifest) are size twins. Without a manifest, a sentence Jaccard of 0.8 or more marks twins.
3. FR3. Each result holds `grader_sha256`. Round 0 is measured again with this module, so all
   rounds use one grader.
4. FR4. Round 1 build: `--sizes-mb 2,5 --formats docx,pdf,pptx --world-pack packs/govtech.json
   --seed 2026`, appendix filter on, handshake writer (a Jetski subagent writes the prose and
   `bigloom narrate accept` validates it).
5. FR5. Blind judges: 20 pairs, the round 1 judge prompt (adds "The documents are dated 2025 and
   2026. A 2026 date is not a clue."), 3 judges on model option `pro`. The answer key stays in
   the conversation until all judges reply.
6. FR6. A receipt JSON for each round: build command, grader digest, judge prompt digest, judge
   model options, date (SGT), scores.
7. FR7. `docs/self-improvement.md` first draft with measured numbers only. Anything not built is
   marked "not built".

## Out of scope

- The proposer and the holdout (a later full loop round).
- Commercial terms from `"base": "retail"`.
- Any WorldLoom change. No Vertex AI.

## Acceptance criteria

1. Metric tests pass, including the twin rule and the grader digest.
2. Round 0 and round 1 vectors and the round 1 judge error rate are in receipts.
3. The first draft of `docs/self-improvement.md` exists and holds only measured numbers.
