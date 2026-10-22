# Plan: Realism Loop, Round 1

## Phase 1: Metric Vector in BigLoom

- [x] Task: Write tests (`tests/test_realism_metrics.py`): per-1000-word rates, dates after the document date, sentence masking, twin rule (Jaccard and manifest), grader digest.
- [x] Task: Implement `src/bigloom/realism_metrics.py`.
- [x] Task: Measure round 0 again with this module (`runs/realism/metrics_r0_bigloom.json`).
- [ ] Task: Phase Verification and Checkpoint (refer to `workflow.md`).

## Phase 2: Round 1

- [ ] Task: Build round 1 with the appendix filter and the handshake writer.
- [ ] Task: Measure the round 1 vector.
- [ ] Task: Build 20 blind pairs and run 3 judges with the round 1 prompt.
- [ ] Task: Write the round 0 and round 1 receipts.
- [ ] Task: Phase Verification and Checkpoint (refer to `workflow.md`).

## Phase 3: First Draft of `docs/self-improvement.md`

- [ ] Task: Write the draft with measured numbers only. Mark the proposer, the holdout, and the promotion rule "not built".
- [ ] Task: Phase Verification and Checkpoint (refer to `workflow.md`).
