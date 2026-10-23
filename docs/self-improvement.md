# Realism self-improvement loop: instructions

These are the instructions for the agent that runs the BigLoom realism loop (the orchestrator).
Follow them in order. This file holds instructions only. Results go to
[`docs/realism/loop-log.md`](realism/loop-log.md). Lessons for the proposer go to
[`docs/realism/lessons.md`](realism/lessons.md).

## 1. Goal

Make the DOCX, PDF, and PPTX files that BigLoom builds read like real Singapore agency documents.
The loop has two levels:

- **Level 1, the writer policy.** Each round changes one rule in the writer policy and keeps the
  change only when it wins on train and on holdout.
- **Level 2, the loop itself.** When Level 1 stops making progress, you find the cause and propose a
  change to the metrics, the corpus, or the procedure. The user must approve each Level 2 change.

## 2. Start of each session

1. Read the "Current state" and "Open items" sections of `docs/realism/loop-log.md`.
2. Run `git log --oneline -5` on `realism-loop` and on `realism-v2`. Make sure that they agree with
   the current state.
3. Make sure that `main` is at `ba4b981`.
4. Do the open items in order. Start a new round only when no open item blocks it.

## 3. Hard rules

Stop and correct the work at once if you break one of these rules.

1. **One change.** A candidate policy changes one rule of the champion and nothing else.
2. **Holdout isolation.** No proposer message, proposer input, or file that the proposer reads
   contains a holdout seed (`3101`, `3102`), a holdout number, or a holdout passage.
3. **Fresh writers.** Each round uses new writer subagents. A writer sees only the text of the
   candidate policy and its own requests. Never give a writer an earlier `responses.json`, and never
   tell a writer to copy earlier output.
4. **No code change during a run.** Do not change code while the writers or a build of a round run.
5. **Protected places.** Never commit or merge to `main`. Do not edit the WorldLoom repository. Do not
   upload files. Do not use Vertex AI. Every model role is a Jetski subagent.
6. **Real samples.** Each receipt holds two sample passages from the current round's train set.
7. **No facade work.** No dummy content and no facade tests. A new test must fail on the old code.
   Show the failing run.
8. **Writing.** Write in Simplified Technical English. Report each time in SGT (GMT+8).

## 4. Information barriers

| Role | May read | Must never read |
|---|---|---|
| Proposer subagent | Champion policy, `docs/realism/loop/train-*.json`, `docs/realism/lessons.md`, `policies/PROPOSER.md` | `docs/realism/receipts/round*.json`, `docs/realism/loop-log.md`, this file, `runs/` |
| Writer subagent | The candidate policy text, its own `requests.json` | Any other file under `runs/`, `policies/`, or `docs/` |
| Judge subagent | Masked passage pairs only | Receipts, policies, file names |
| Orchestrator (you) | Everything | Nothing is forbidden, but never copy holdout data into a proposer input |

## 5. Round procedure (Level 1)

Use the v2 code. Round `N` uses the folders `runs/loop/r<NNN>t` (train) and `runs/loop/r<NNN>h`
(holdout). The train seeds are `2026` (2 MB) and `2027` (5 MB). The holdout seeds are `3101` (2 MB)
and `3102` (5 MB). The values are in `realism_loop.TRAIN` and `realism_loop.HOLDOUT`.

1. **Propose.** Start a fresh proposer subagent. Give it `policies/PROPOSER.md`, the champion path,
   and the output path `policies/writer/round-<NNN>.md`. Check its output:
   - The diff against the champion holds one rule change only.
   - The reply names one target metric, and the "why" cites a train number only.
   - The target metric can gain more than its band on train (section 7, step 1). If it cannot, reject
     the proposal and ask again.
2. **Prepare.** Run `realism_loop.prepare_round` for the train seeds and the holdout seeds. It copies
   the cached raw corpus and removes old responses.
3. **Write.** Start one fresh writer subagent for each seed. Give each writer the full text of the
   candidate policy and the path of its `seed-<n>/narration/requests.json`. Tell it to write
   `seed-<n>/narration/responses.json`. Give it nothing else.
4. **Fact gate.** Run `bigloom narrate accept --out-dir <seed-n> --from <responses.json>` for each
   seed. If a seed fails, start one new fresh writer for that seed. If it fails a second time, record
   the round as rejected for the fact gate.
5. **Build gate.** Run `realism_loop.build_round` for train and for holdout. A gate violation rejects
   the round. Record the violation.
6. **Length guard.** Compare the prose word count of each file with the champion. If a file has less
   than 80% of the champion prose, record a writer failure, not a policy result. Run that seed again
   with a fresh writer one time.
7. **Decide.** Call `realism_loop.decide` with the champion and candidate vectors. Use its output as
   the decision. Never write a decision by hand.
8. **Judges.** If the decision is a promotion, run three masked judge subagents on 20 pairs each
   (`realism_pairs.build_pairs`). Give the judge results to `decide` again for the judge guard.
9. **Record.** Write the receipt and the train receipt (section 6). Commit them on `realism-loop`.
10. **Promote.** If the candidate wins, it becomes the champion. Update "Current state" in
    `loop-log.md`.

## 6. Receipts and records

After each round, write these files:

| File | Content | Proposer may read |
|---|---|---|
| `docs/realism/receipts/round<N>.json` | Full receipt: train and holdout vectors, decision, samples | No |
| `docs/realism/loop/train-<NNN>.json` | Train vector, per-file train numbers, writer notes, samples | Yes |
| `docs/realism/loop-log.md` | One row in Appendix A, update to "Current state" | No |
| `docs/realism/lessons.md` | One row in "Loop v2 rounds" with train numbers only, plus any new lesson | Yes |

Check each receipt before you commit it:

- `grader_sha256` is the digest in "Current state". If the digest changed, stop. A grader change is a
  Level 2 change.
- `samples` holds exactly two passages. Each `file` comes from `runs/loop/r<NNN>t/set/large`.
- `samples_method` names the folder that the extractor read.
- `candidate_policy_sha256` matches `sha256sum` of the policy file.
- `decision` is the output of `realism_loop.decide`.
- Known floors are recorded, for example the cover abstract repeats in each PDF.

A helper that returns an empty list or a zero count for a whole set is an error. Examine the input
path before you record the result.

## 7. Improve the loop (Level 2)

### When to start Level 2

Start Level 2 when one of these conditions is true:

- **No room.** No metric can gain more than its band on train. Measure this before each proposal:
  for each metric in `realism_loop.BANDS`, compare the champion's distance to the real median with
  the band.
- **Plateau.** Three rounds in a row were rejected for the same reason.
- **Disagreement.** Train and holdout move in opposite directions on the same metric for two rounds.
- **Judges.** The masked judges still tell real from synthetic every time after a promotion.

### How to do Level 2

1. **Find the cause.** Look at the files, not only the vector. For each metric with a problem, list
   the sentences or phrases that cause it, and find which part of BigLoom or WorldLoom made them.
2. **Classify the cause.** The cause is one of: writer policy, BigLoom corpus or renderer, grader,
   real reference, or procedure (seeds, number of writers).
3. **Propose one change to the user.** State the cause, the change, the expected effect, and the
   test that will show it. Wait for approval.
4. **Make the change on `realism-v2`.** Add a test that fails on the old code. Show the failing run
   and the passing run. Do not change code while a round runs.
5. **Measure the champion again.** Rebuild the champion prose on the new code with no new writer
   runs. Record it as a rescore, not a round. Old and new receipts use different graders. Do not
   compare their numbers directly.
6. **Record.** Add the change and the rescore to `loop-log.md`. Add the lesson to `lessons.md`
   with train numbers only. Update `policies/PROPOSER.md` if the proposer needs to know the change.
7. **Merge.** Merge `realism-v2` into `realism-loop` and push. Never merge into `main`.

### Order of the design changes

Propose these changes in this order, unless the evidence shows a better order:

1. **Repeat runs.** Run two writers on each seed and score the mean. The noise between two writers is
   larger than every band.
2. **More train seeds.** Add new train seeds that are not holdout seeds. The current train pair does
   not show the commercial phrase problem.
3. **A new signal for distance from real.** Add a metric that the judges' clues point to, for
   example prose density without padding, or the judge error rate as a scored metric.
4. **An archive of near misses.** Keep candidates that won on holdout but lost on train. Let the
   proposer start from one of them.

## 8. Stop and ask the user

Stop the loop and ask the user when one of these happens:

- A quota error (429). Report the reset time in SGT. Do not retry.
- A permission or credential error. Give the exact command that fixes it.
- The grader digest changes without an approved Level 2 change.
- A Level 2 condition is true (section 7).
- The review set is ready. Give the folder path and the file names.

## 9. Report

After each round or Level 2 change, report in five lines or fewer: the step, the result, the
decision, any rule break, and any blocker. Use SGT for every time.
