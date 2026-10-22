# Plan: Realism Loop, Round 1

## Phase 1: Metric Vector in BigLoom [checkpoint: 271f878]

- [x] Task: Write tests (`tests/test_realism_metrics.py`): per-1000-word rates, dates after the document date, sentence masking, twin rule (Jaccard and manifest), grader digest.
- [x] Task: Implement `src/bigloom/realism_metrics.py`.
- [x] Task: Measure round 0 again with this module (`runs/realism/metrics_r0_bigloom.json`).
- [x] Task: Phase Verification and Checkpoint (refer to `workflow.md`).

## Phase 2: Round 1

- [x] Task: Build round 1 with the appendix filter and the handshake writer.
- [x] Task: Measure the round 1 vector.
- [x] Task: Build 20 blind pairs and run 3 judges with the round 1 prompt.
- [x] Task: Write the round 0 and round 1 receipts.
- [x] Task: Phase Verification and Checkpoint (refer to `workflow.md`).

## Phase 3: First Draft of `docs/self-improvement.md`

- [x] Task: Write the draft with measured numbers only. Mark the proposer, the holdout, and the promotion rule "not built".
- [x] Task: Phase Verification and Checkpoint (refer to `workflow.md`).
